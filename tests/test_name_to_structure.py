import os
import sys
import urllib.error
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chemcanvas")))

from PyQt5.QtWidgets import QApplication

from app_data import App
from molecule import Molecule
from name_to_structure import NameToStructureError, resolve_name_to_document
from text import Text
from tool_helpers import draw_recursively
from main import Window


app = QApplication.instance() or QApplication(sys.argv)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.text.encode("utf-8")

    def close(self):
        pass


def sdf_for_ethane():
    return "\n".join([
        "ethane",
        "  ChemCanvas",
        "",
        "  2  1  0  0  0  0            999 V2000",
        "    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0",
        "    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0",
        "  1  2  1  0  0  0  0",
        "M  END",
        "> <PUBCHEM_IUPAC_NAME>",
        "ethane",
        "",
        "$$$$",
        "",
    ])


class NameToStructureResolverTest(unittest.TestCase):
    def test_local_common_names_convert_to_molecules(self):
        cases = {
            "water": 1,
            "ethanol": 3,
            "benzene": 6,
        }
        for name, atom_count in cases.items():
            with self.subTest(name=name):
                doc = resolve_name_to_document(name)
                mol = doc.objects[0]
                self.assertEqual(mol.class_name, "Molecule")
                self.assertEqual(len(mol.atoms), atom_count)
                self.assertEqual(mol.name, name)

    def test_pubchem_sdf_conversion_path_is_used_for_unknown_local_name(self):
        requested = []

        def fake_urlopen(url, timeout=10):
            requested.append((url, timeout))
            return FakeResponse(sdf_for_ethane())

        doc = resolve_name_to_document("mock ethane", urlopen=fake_urlopen)

        self.assertEqual(len(requested), 1)
        self.assertIn("/compound/name/mock-ethane/SDF", requested[0][0])
        self.assertEqual(requested[0][1], 10)
        self.assertEqual(len(doc.objects), 1)
        self.assertEqual(len(doc.objects[0].atoms), 2)
        self.assertEqual(doc.objects[0].name, "mock ethane")

    def test_unknown_name_raises_clean_conversion_error(self):
        def fake_urlopen(url, timeout=10):
            raise urllib.error.HTTPError(url, 404, "not found", {}, FakeResponse(""))

        with self.assertRaises(NameToStructureError) as ctx:
            resolve_name_to_document("not a compound", urlopen=fake_urlopen)

        self.assertIn("No structure found", str(ctx.exception))


class NameToStructureWindowTest(unittest.TestCase):
    def setUp(self):
        self.window = Window()
        self.window.actionShowNameBoxesForNewConversions.setChecked(True)

    def tearDown(self):
        self.window.close()
        app.processEvents()

    def molecules(self):
        return [obj for obj in self.window.paper.objects if isinstance(obj, Molecule)]

    def labels(self):
        return [obj for obj in self.window.paper.objects if isinstance(obj, Text)]

    def test_conversion_creates_one_movable_name_label_per_molecule(self):
        self.assertTrue(self.window.convertNameToStructure("water", show_errors=False))
        self.assertTrue(self.window.convertNameToStructure("benzene", show_errors=False))

        mols = self.molecules()
        labels = self.labels()
        self.assertEqual(len(mols), 2)
        self.assertEqual(len(labels), 2)
        self.assertEqual([mol.name_label for mol in mols], labels)
        self.assertEqual([label.text for label in labels], ["water", "benzene"])
        for mol in mols:
            self.assertGreater(mol.name_label.bounding_box()[1], mol.bounding_box()[3])

        labels[0].move_by(20, 10)
        labels[0].draw()
        self.assertNotEqual(labels[0].bounding_box(), labels[1].bounding_box())

    def test_selected_molecule_label_can_be_hidden_and_shown_again(self):
        self.assertTrue(self.window.convertNameToStructure("ethanol", show_errors=False))
        mol = self.molecules()[0]
        first_label = mol.name_label
        self.window.paper.selectObject(mol.atoms[0])

        self.assertTrue(self.window.toggleNameLabelForSelectedMolecule())
        self.assertIsNone(mol.name_label)
        self.assertNotIn(first_label, self.window.paper.objects)

        self.assertTrue(self.window.toggleNameLabelForSelectedMolecule())
        self.assertIsNotNone(mol.name_label)
        self.assertEqual(mol.name_label.text, "ethanol")
        self.assertGreater(mol.name_label.bounding_box()[1], mol.bounding_box()[3])

    def test_generated_methane_suppresses_implicit_hydrogen_label(self):
        self.assertTrue(self.window.convertNameToStructure("methane", show_errors=False))
        mol = self.molecules()[0]
        atom = mol.atoms[0]

        self.assertTrue(mol.name_to_structure_generated)
        self.assertTrue(mol.hide_implicit_hydrogen_labels)
        self.assertEqual(atom.hydrogens, 4)
        self.assertEqual([item.text for item in atom._main_items], ["C"])

    def test_generated_molecule_preparation_removes_explicit_hydrogen_atoms(self):
        mol = Molecule()
        carbon = mol.new_atom("C")
        for _ in range(4):
            hydrogen = mol.new_atom("H")
            bond = mol.new_bond()
            bond.connect_atoms(carbon, hydrogen)

        self.window.prepareNameToStructureMolecule(mol)

        self.assertEqual([atom.symbol for atom in mol.atoms], ["C"])
        self.assertEqual(len(mol.bonds), 0)
        self.assertEqual(carbon.hydrogens, 4)

    def test_delete_selected_generated_atom_in_structure_tool_removes_whole_molecule_and_label(self):
        self.assertTrue(self.window.convertNameToStructure("ethanol", show_errors=False))
        mol = self.molecules()[0]
        label = mol.name_label
        self.window.selectToolByName("StructureTool")
        self.window.paper.selectObject(mol.atoms[0])

        App.tool.on_key_press("Delete", "")

        self.assertNotIn(mol, self.window.paper.objects)
        self.assertNotIn(label, self.window.paper.objects)

    def test_mac_backspace_delete_key_removes_selected_generated_molecule(self):
        self.assertTrue(self.window.convertNameToStructure("ethanol", show_errors=False))
        mol = self.molecules()[0]
        label = mol.name_label
        self.window.selectToolByName("StructureTool")
        self.window.paper.selectObject(mol.atoms[0])

        App.tool.on_key_press("Backspace", "")

        self.assertNotIn(mol, self.window.paper.objects)
        self.assertNotIn(label, self.window.paper.objects)

    def test_settings_bar_delete_action_removes_selected_generated_molecule(self):
        self.assertTrue(self.window.convertNameToStructure("benzene", show_errors=False))
        mol = self.molecules()[0]
        label = mol.name_label
        self.window.selectToolByName("MoveTool")
        self.window.paper.selectObject(mol.atoms[0])

        App.tool.on_property_change("action", "Delete Selected")

        self.assertNotIn(mol, self.window.paper.objects)
        self.assertNotIn(label, self.window.paper.objects)

    def test_undo_after_generated_molecule_delete_restores_without_crash(self):
        self.assertTrue(self.window.convertNameToStructure("ethanol", show_errors=False))
        mol = self.molecules()[0]
        self.window.selectToolByName("StructureTool")
        self.window.paper.selectObject(mol.atoms[0])
        App.tool.on_key_press("Backspace", "")

        self.window.undo()

        self.assertIn(mol, self.window.paper.objects)
        self.assertIsNotNone(mol.name_label)
        self.assertIn(mol.name_label, self.window.paper.objects)

    def test_delete_selected_manual_atom_preserves_normal_partial_delete(self):
        mol = Molecule()
        atoms = [mol.new_atom("C") for _ in range(3)]
        for index, atom in enumerate(atoms):
            atom.x = index * 40
            atom.y = 0
        for left, right in zip(atoms, atoms[1:]):
            bond = mol.new_bond()
            bond.connect_atoms(left, right)
        self.window.paper.addObject(mol)
        draw_recursively(mol)
        self.window.selectToolByName("StructureTool")
        self.window.paper.selectObject(atoms[0])

        App.tool.on_key_press("Delete", "")

        self.assertIn(mol, self.window.paper.objects)
        self.assertEqual(len(mol.atoms), 2)
        self.assertEqual(len(mol.bonds), 1)


if __name__ == "__main__":
    unittest.main()
