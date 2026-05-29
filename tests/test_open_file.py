import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chemcanvas")))

from PyQt5.QtCore import QMimeData, Qt, QUrl
from PyQt5.QtWidgets import QApplication

from main import Window


app = QApplication.instance() or QApplication(sys.argv)


class FakeDropEvent:
    def __init__(self, mime_data, modifiers=Qt.NoModifier):
        self._mime_data = mime_data
        self._modifiers = modifiers
        self.accepted = False
        self.ignored = False
        self.drop_action = None

    def mimeData(self):
        return self._mime_data

    def keyboardModifiers(self):
        return self._modifiers

    def setDropAction(self, action):
        self.drop_action = action

    def acceptProposedAction(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


class OpenExistingFileTest(unittest.TestCase):
    def setUp(self):
        self.window = Window()
        self._original_recent_files = self.window.recentFiles()
        self.window.clearRecentFiles()
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.window.setRecentFiles(self._original_recent_files)
        self.window.close()
        self.tmpdir.cleanup()
        app.processEvents()

    def smiles_file(self, name, text):
        path = os.path.join(self.tmpdir.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def mime_for_paths(self, *paths):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
        return mime

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
        first_objects = list(self.window.paper.objects)
        self.assertTrue(self.window.openFile(second))

        self.assertEqual(self.window.filename, second)
        self.assertEqual(self.window.windowTitle(), "water.smi")
        self.assertFalse(self.window.paper.undo_manager.has_unsaved_changes())
        self.assertFalse(any(obj in self.window.paper.objects for obj in first_objects))

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

    def test_supported_file_drop_is_accepted(self):
        path = self.smiles_file("ethane.smi", "CC")
        event = FakeDropEvent(self.mime_for_paths(path))

        self.assertTrue(self.window._acceptSupportedFileDrop(event))

        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)
        self.assertEqual(event.drop_action, Qt.CopyAction)

    def test_unsupported_file_drop_is_ignored(self):
        path = self.smiles_file("notes.xyznotchem", "not chemistry")
        event = FakeDropEvent(self.mime_for_paths(path))

        self.assertFalse(self.window._acceptSupportedFileDrop(event))

        self.assertFalse(event.accepted)
        self.assertTrue(event.ignored)

    def test_plain_file_drop_replaces_current_document(self):
        first = self.smiles_file("ethane.smi", "CC")
        second = self.smiles_file("water.smi", "O")
        self.assertTrue(self.window.openFile(first))
        first_objects = list(self.window.paper.objects)
        event = FakeDropEvent(self.mime_for_paths(second))

        self.assertTrue(self.window._handleFileDrop(event))

        self.assertTrue(event.accepted)
        self.assertEqual(self.window.filename, second)
        self.assertFalse(any(obj in self.window.paper.objects for obj in first_objects))

    def test_modifier_file_drop_inserts_into_current_document(self):
        first = self.smiles_file("ethane.smi", "CC")
        second = self.smiles_file("water.smi", "O")
        self.assertTrue(self.window.openFile(first))
        first_objects = list(self.window.paper.objects)
        event = FakeDropEvent(self.mime_for_paths(second), Qt.ControlModifier)

        self.assertTrue(self.window._handleFileDrop(event))

        self.assertTrue(event.accepted)
        self.assertEqual(self.window.filename, first)
        self.assertTrue(all(obj in self.window.paper.objects for obj in first_objects))
        self.assertGreater(len(self.window.paper.objects), len(first_objects))

    def test_multiple_file_drop_opens_extra_files_in_new_windows(self):
        first = self.smiles_file("ethane.smi", "CC")
        second = self.smiles_file("water.smi", "O")
        third = self.smiles_file("methane.smi", "C")
        opened_in_new_windows = []
        self.window.openFileInNewWindow = lambda path: opened_in_new_windows.append(path) or True

        self.assertTrue(self.window._openDroppedFiles([first, second, third]))

        self.assertEqual(self.window.filename, first)
        self.assertEqual(opened_in_new_windows, [second, third])

    def test_open_file_records_recent_file(self):
        path = self.smiles_file("ethane.smi", "CC")

        self.assertTrue(self.window.openFile(path))

        self.assertEqual(self.window.recentFiles(), [path])

    def test_reopening_recent_file_moves_it_to_top_without_duplicate(self):
        first = self.smiles_file("ethane.smi", "CC")
        second = self.smiles_file("water.smi", "O")

        self.assertTrue(self.window.openFile(first))
        self.assertTrue(self.window.openFile(second))
        self.assertTrue(self.window.openFile(first))

        self.assertEqual(self.window.recentFiles(), [first, second])

    def test_recent_files_persist_in_settings(self):
        path = self.smiles_file("ethane.smi", "CC")
        self.assertTrue(self.window.openFile(path))

        second_window = Window()
        try:
            self.assertEqual(second_window.recentFiles(), [path])
        finally:
            second_window.clearRecentFiles()
            second_window.close()

    def test_recent_menu_prunes_missing_files(self):
        existing = self.smiles_file("ethane.smi", "CC")
        missing = os.path.join(self.tmpdir.name, "missing.smi")
        self.window.setRecentFiles([missing, existing])

        self.window.refreshRecentFilesMenu()

        self.assertEqual(self.window.recentFiles(), [existing])
        actions = [action for action in self.window.menuOpenRecent.actions()
                   if not action.isSeparator()]
        self.assertEqual(actions[0].text(), "ethane.smi")
        self.assertTrue(actions[0].isEnabled())

    def test_recent_file_action_opens_path(self):
        path = self.smiles_file("ethane.smi", "CC")
        opened = []
        self.window.openFile = lambda filename: opened.append(filename) or True
        self.window.setRecentFiles([path])
        self.window.refreshRecentFilesMenu()

        self.window.menuOpenRecent.actions()[0].trigger()

        self.assertEqual(opened, [path])

    def test_clear_recent_files_empties_storage_and_menu(self):
        path = self.smiles_file("ethane.smi", "CC")
        self.window.setRecentFiles([path])

        self.window.clearRecentFiles()

        self.assertEqual(self.window.recentFiles(), [])
        actions = [action for action in self.window.menuOpenRecent.actions()
                   if not action.isSeparator()]
        self.assertEqual(actions[0].text(), "No Recent Files")
        self.assertFalse(actions[0].isEnabled())
        self.assertEqual(actions[-1].text(), "Clear Recent Files")
        self.assertFalse(actions[-1].isEnabled())


if __name__ == "__main__":
    unittest.main()
