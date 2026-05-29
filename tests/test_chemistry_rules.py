import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chemcanvas")))

from PyQt5.QtWidgets import QApplication

from atom import Atom
from bond import Bond
from molecule import Molecule
from widgets import PeriodicTableDialog


def bonded_atom(mol, atom, symbol="C", bond_type="single"):
    other = mol.new_atom(symbol)
    bond = mol.new_bond()
    bond.set_type(bond_type)
    bond.connect_atoms(atom, other)
    return other, bond


class ValencyRulesTest(unittest.TestCase):
    def test_carbon_with_four_single_bonds_is_valid(self):
        mol = Molecule()
        carbon = mol.new_atom("C")

        for _ in range(4):
            bonded_atom(mol, carbon)

        self.assertEqual(carbon.bond_order_sum, 4)
        self.assertFalse(carbon.has_valency_error)

    def test_carbon_with_five_single_bonds_is_invalid(self):
        mol = Molecule()
        carbon = mol.new_atom("C")

        for _ in range(5):
            bonded_atom(mol, carbon)

        self.assertEqual(carbon.bond_order_sum, 5)
        self.assertTrue(carbon.has_valency_error)

    def test_carbon_double_double_valid_but_triple_double_invalid(self):
        mol = Molecule()
        carbon = mol.new_atom("C")

        _, first_bond = bonded_atom(mol, carbon, bond_type="double")
        _, second_bond = bonded_atom(mol, carbon, bond_type="double")

        self.assertEqual(carbon.bond_order_sum, 4)
        self.assertFalse(carbon.has_valency_error)

        first_bond.set_type("triple")

        self.assertEqual(carbon.bond_order_sum, 5)
        self.assertTrue(carbon.has_valency_error)

    def test_hydrogen_with_two_single_bonds_is_invalid(self):
        mol = Molecule()
        hydrogen = mol.new_atom("H")

        for _ in range(2):
            bonded_atom(mol, hydrogen)

        self.assertEqual(hydrogen.bond_order_sum, 2)
        self.assertTrue(hydrogen.has_valency_error)

    def test_functional_group_does_not_raise_valency_error(self):
        group_atom = Atom("Ph")

        self.assertTrue(group_atom.is_group)
        self.assertIsNone(group_atom.max_allowed_valency)
        self.assertFalse(group_atom.has_valency_error)


class PeriodicTableDialogTest(unittest.TestCase):
    def test_dialog_builds_all_element_buttons(self):
        app = QApplication.instance() or QApplication([])
        dialog = PeriodicTableDialog()

        self.assertEqual(len(dialog.findChildren(type(dialog.layout().itemAt(0).widget()))), 118)

        dialog.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
