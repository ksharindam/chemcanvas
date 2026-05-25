import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chemcanvas")))

from PyQt5.QtWidgets import QApplication

from main import Window


app = QApplication.instance() or QApplication(sys.argv)


class OpenExistingFileTest(unittest.TestCase):
    def setUp(self):
        self.window = Window()
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.window.close()
        self.tmpdir.cleanup()
        app.processEvents()

    def smiles_file(self, name, text):
        path = os.path.join(self.tmpdir.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_open_file_sets_active_filename_and_clean_title(self):
        path = self.smiles_file("ethane.smi", "CC")

        self.assertTrue(self.window.openFile(path))

        self.assertEqual(self.window.filename, path)
        self.assertEqual(self.window.windowTitle(), "ethane.smi")
        self.assertFalse(self.window.paper.undo_manager.has_unsaved_changes())
        self.assertTrue(self.window.paper.objects)

    def test_second_open_replaces_previous_filename(self):
        first = self.smiles_file("ethane.smi", "CC")
        second = self.smiles_file("water.smi", "O")

        self.assertTrue(self.window.openFile(first))
        self.assertTrue(self.window.openFile(second))

        self.assertEqual(self.window.filename, second)
        self.assertEqual(self.window.windowTitle(), "water.smi")
        self.assertFalse(self.window.paper.undo_manager.has_unsaved_changes())

    def test_missing_file_does_not_change_active_filename(self):
        existing = self.smiles_file("ethane.smi", "CC")
        missing = os.path.join(self.tmpdir.name, "missing.smi")
        self.assertTrue(self.window.openFile(existing))

        self.assertFalse(self.window.openFile(missing))

        self.assertEqual(self.window.filename, existing)
        self.assertEqual(self.window.windowTitle(), "ethane.smi")

    def test_unsupported_file_does_not_change_active_filename(self):
        existing = self.smiles_file("ethane.smi", "CC")
        unsupported = self.smiles_file("notes.xyznotchem", "not chemistry")
        self.assertTrue(self.window.openFile(existing))

        self.assertFalse(self.window.openFile(unsupported))

        self.assertEqual(self.window.filename, existing)
        self.assertEqual(self.window.windowTitle(), "ethane.smi")


if __name__ == "__main__":
    unittest.main()
