import sys
import unittest

from PyQt5.QtWidgets import QApplication

from chemcanvas.settings_ui import DocumentSettingsWidget


app = QApplication.instance() or QApplication(sys.argv)


class TestDocumentSettings(unittest.TestCase):
    def setUp(self):
        self.widget = DocumentSettingsWidget(None)

    def test_unit_conversions(self):
        self.widget.setValues({"measurement_unit": "Points", "custom_width": 72.0})
        self.assertEqual(self.widget.widthSpin.value(), 72.0)

        self.widget.unitCombo.setCurrentText("Inches")
        self.widget.onUnitChanged("Inches")
        self.assertAlmostEqual(self.widget.widthSpin.value(), 1.0)

        self.widget.unitCombo.setCurrentText("Points")
        self.widget.onUnitChanged("Points")
        self.assertAlmostEqual(self.widget.widthSpin.value(), 72.0)

    def test_unit_conversions_mm(self):
        self.widget.setValues({"measurement_unit": "Points", "custom_width": 72.0})
        self.widget.unitCombo.setCurrentText("Millimeters")
        self.widget.onUnitChanged("Millimeters")
        self.assertAlmostEqual(self.widget.widthSpin.value(), 25.4)

    def test_preset_application(self):
        self.widget.setValues({"measurement_unit": "Points"})
        self.widget.presetCombo.setCurrentText("A4")
        self.widget.onPresetChanged("A4")
        self.assertEqual(self.widget.widthSpin.value(), 595.0)
        self.assertEqual(self.widget.heightSpin.value(), 842.0)

    def test_get_values(self):
        self.widget.setValues({
            "measurement_unit": "Inches",
            "custom_width": 72.0,
            "custom_height": 144.0,
            "margins": 36.0,
        })
        self.assertEqual(self.widget.widthSpin.value(), 1.0)
        self.assertEqual(self.widget.heightSpin.value(), 2.0)

        vals = self.widget.getValues()
        self.assertEqual(vals["custom_width"], 72.0)
        self.assertEqual(vals["custom_height"], 144.0)
        self.assertEqual(vals["measurement_unit"], "Inches")


if __name__ == "__main__":
    unittest.main()
