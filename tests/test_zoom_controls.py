import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chemcanvas")))

from PyQt5.QtWidgets import QApplication

from main import Window


app = QApplication.instance() or QApplication(sys.argv)


class ZoomControlsTest(unittest.TestCase):
    def setUp(self):
        self.window = Window()

    def tearDown(self):
        self.window.close()
        app.processEvents()

    def test_zoom_index_is_clamped_and_updates_label(self):
        self.window.setZoomIndex(-10)
        self.assertEqual(self.window.slider.value(), 0)
        self.assertEqual(self.window.zoomLabel.text(), "25%")
        self.assertFalse(self.window.actionZoomOut.isEnabled())

        self.window.setZoomIndex(999)
        self.assertEqual(self.window.slider.value(), len(self.window.zoom_levels)-1)
        self.assertEqual(self.window.zoomLabel.text(), "200%")
        self.assertFalse(self.window.actionZoomIn.isEnabled())

    def test_zoom_buttons_and_reset_share_slider_state(self):
        reset_index = self.window.zoom_levels.index(100)
        self.window.zoomReset()
        self.assertEqual(self.window.slider.value(), reset_index)

        self.window.zoomIn()
        self.assertEqual(self.window.slider.value(), reset_index + 1)

        self.window.zoomOut()
        self.assertEqual(self.window.slider.value(), reset_index)

    def test_zoom_shortcuts_are_registered(self):
        zoom_in = [shortcut.toString() for shortcut in self.window.actionZoomIn.shortcuts()]
        self.assertIn("Ctrl++", zoom_in)
        self.assertIn("Ctrl+=", zoom_in)
        self.assertEqual(self.window.actionZoomOut.shortcut().toString(), "Ctrl+-")
        self.assertEqual(self.window.actionZoomReset.shortcut().toString(), "Ctrl+0")


if __name__ == "__main__":
    unittest.main()
