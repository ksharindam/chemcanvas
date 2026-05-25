# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2025-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (QWidget, QDialog, QTableWidget, QDialogButtonBox,
    QGridLayout, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem, QLabel, QSpinBox, QSizePolicy,
    QPushButton, QDoubleSpinBox, QComboBox, QRadioButton
)
from app_data import Settings, Default

class SettingsDialog(QDialog):
    """ custom drawing style settings dialog """
    category_index = 0

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Drawing Settings")
        self.resize(540, 400)
        layout = QGridLayout(self)
        self.categoryTable = QTableWidget(self)
        self.categoryTable.setMaximumWidth(200)
        self.categoryTable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.categoryTable.setAlternatingRowColors(True)
        self.categoryTable.setSelectionBehavior(self.categoryTable.SelectRows)# required for table.selectRow()
        self.categoryTable.setSelectionMode(self.categoryTable.SingleSelection)
        self.categoryTable.horizontalHeader().setHidden(True)
        self.categoryTable.verticalHeader().setHidden(True)
        self.categoryTable.setColumnCount(1)
        self.categoryTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.settingsContainer = QWidget(self)
        self.settingsContainerLayout = QVBoxLayout(self.settingsContainer)
        btnBoxContainer = QWidget(self)
        btnBoxLayout = QHBoxLayout(btnBoxContainer)
        btnBoxLayout.setContentsMargins(0,0,0,0)
        self.resetBtn = QPushButton("Reset to Default", self)
        btnBoxLayout.addWidget(self.resetBtn)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel, parent=self)
        btnBoxLayout.addWidget(self.btnBox)
        layout.addWidget(self.categoryTable, 0,0,1,1)
        layout.addWidget(self.settingsContainer, 0,1,1,1)
        layout.addWidget(btnBoxContainer, 1,0,1,2)
        # connect signals
        self.categoryTable.itemClicked.connect(self.onItemClick)
        self.resetBtn.clicked.connect(self.resetToDefault)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)
        titles = ["Document", "Atom", "Bond", "Marks", "Arrow", "Plus"]
        self.categoryTable.setRowCount(len(titles))
        for i,title in enumerate(titles):
            item = QTableWidgetItem(title)
            self.categoryTable.setItem(i, 0, item)
        # load global settings
        self.settings = dict(vars(Settings))
        self.new_settings = {}
        # show last used category
        self.curr_text = None
        self.curr_widget = None
        self.settingsContainerLayout.addStretch()
        self.categoryTable.selectRow(SettingsDialog.category_index)
        self.showCategory(titles[SettingsDialog.category_index])


    def onItemClick(self, tableitem):
        """ Swich category """
        title = tableitem.text()
        self.showCategory(title)
        SettingsDialog.category_index = tableitem.row()

    def showCategory(self, title):
        if title==self.curr_text:
            return
        if self.curr_widget:
            self.new_settings.update(self.curr_widget.getValues())
            self.settings.update(self.new_settings)
            self.settingsContainerLayout.removeWidget(self.curr_widget)
            self.curr_widget.deleteLater()
        class_name = "%sSettingsWidget" % title.replace(" ", "")
        self.curr_widget = globals()[class_name](self.settingsContainer)
        self.settingsContainerLayout.insertWidget(0, self.curr_widget)
        self.curr_text = title
        self.curr_widget.setValues(self.settings)


    def resetToDefault(self):
        for key,val in dict(vars(Default)).items():
            if not key.startswith("__"):
                self.new_settings[key] = val
        self.settings.update(self.new_settings)
        self.curr_widget.setValues(self.settings)


    def accept(self):
        self.new_settings.update(self.curr_widget.getValues())
        settings = QSettings("chemcanvas", "chemcanvas", self)
        settings.beginGroup("Custom_Style")
        for key,val in self.new_settings.items():
            setattr(Settings, key, val)
            settings.setValue(key, str(val))
        settings.endGroup()
        QDialog.accept(self)



class AtomSettingsWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        label1 = QLabel("Font Size :", self)
        self.fontSizeSpin = QSpinBox(self)
        self.fontSizeSpin.setSuffix(" px")
        self.fontSizeSpin.setAlignment(Qt.AlignHCenter)
        self.fontSizeSpin.setRange(6, 60)
        layout.addWidget(label1, 0,0,1,1)
        layout.addWidget(self.fontSizeSpin, 0,1,1,1)

    def setValues(self, values):
        self.fontSizeSpin.setValue( values["atom_font_size"])

    def getValues(self):
        values = {"atom_font_size": self.fontSizeSpin.value()}
        return values


class BondSettingsWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        # bond length
        label1 = QLabel("Bond Length :", self)
        self.lengthSpin = QSpinBox(self)
        self.lengthSpin.setSuffix(" px")
        self.lengthSpin.setAlignment(Qt.AlignHCenter)
        self.lengthSpin.setRange(10, 100)
        # bond width
        label2 = QLabel("Bond Width :", self)
        self.widthSpin = QDoubleSpinBox(self)
        self.widthSpin.setAlignment(Qt.AlignHCenter)
        self.widthSpin.setDecimals(1)
        self.widthSpin.setSingleStep(0.1)
        self.widthSpin.setRange(0.1, 10)
        # bond spacing
        label3 = QLabel("Bond Spacing :", self)
        self.spacingSpin = QDoubleSpinBox(self)
        self.spacingSpin.setAlignment(Qt.AlignHCenter)
        self.spacingSpin.setDecimals(1)
        self.spacingSpin.setSingleStep(0.1)
        self.spacingSpin.setRange(0.1, 20)
        # add widgets to layout
        layout.addWidget(label1, 0,0,1,1)
        layout.addWidget(self.lengthSpin, 0,1,1,1)
        layout.addWidget(label2, 1,0,1,1)
        layout.addWidget(self.widthSpin, 1,1,1,1)
        layout.addWidget(label3, 2,0,1,1)
        layout.addWidget(self.spacingSpin, 2,1,1,1)

    def setValues(self, values):
        self.lengthSpin.setValue( values["bond_length"])
        self.widthSpin.setValue( values["bond_width"])
        self.spacingSpin.setValue( values["bond_spacing"])

    def getValues(self):
        values = {"bond_length": self.lengthSpin.value(),
                "bond_width": self.widthSpin.value(),
                "bond_spacing": self.spacingSpin.value()}
        return values


class MarksSettingsWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        # dot size
        label1 = QLabel("Electron Dot Size :", self)
        self.dotSizeSpin = QSpinBox(self)
        self.dotSizeSpin.setSuffix(" px")
        self.dotSizeSpin.setAlignment(Qt.AlignHCenter)
        self.dotSizeSpin.setRange(1, 20)
        layout.addWidget(label1, 0,0,1,1)
        layout.addWidget(self.dotSizeSpin, 0,1,1,1)

    def setValues(self, values):
        self.dotSizeSpin.setValue( values["electron_dot_size"])

    def getValues(self):
        values = {"electron_dot_size": self.dotSizeSpin.value()}
        return values


class ArrowSettingsWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        # line width
        label1 = QLabel("Line Width :", self)
        self.lineWidthSpin = QDoubleSpinBox(self)
        self.lineWidthSpin.setToolTip("Line width (px)")
        self.lineWidthSpin.setAlignment(Qt.AlignHCenter)
        self.lineWidthSpin.setDecimals(1)
        self.lineWidthSpin.setSingleStep(0.2)
        self.lineWidthSpin.setRange(1, 10)
        # head icon
        headImage = QLabel(self)
        headImage.setPixmap(QPixmap(":/icons/arrow-dimensions.png"))
        # head length
        label2 = QLabel("Head Length :", self)
        self.headLengthSpin = QDoubleSpinBox(self)
        self.headLengthSpin.setToolTip("multiple of line width")
        self.headLengthSpin.setAlignment(Qt.AlignHCenter)
        self.headLengthSpin.setDecimals(1)
        self.headLengthSpin.setSingleStep(0.5)
        self.headLengthSpin.setRange(2.5, 25)
        # head width
        label3 = QLabel("Head Width :", self)
        self.headWidthSpin = QDoubleSpinBox(self)
        self.headWidthSpin.setToolTip("multiple of line width")
        self.headWidthSpin.setDecimals(1)
        self.headWidthSpin.setSingleStep(0.5)
        self.headWidthSpin.setRange(1, 10)
        # head depth
        label4 = QLabel("Head Depth :", self)
        self.headDepthSpin = QDoubleSpinBox(self)
        self.headDepthSpin.setToolTip("multiple of line width")
        self.headDepthSpin.setDecimals(1)
        self.headDepthSpin.setSingleStep(0.5)
        self.headDepthSpin.setRange(0, 7)
        # add widgets to layout
        layout.addWidget(label1, 0,0,1,1)
        layout.addWidget(self.lineWidthSpin, 0,1,1,1)
        layout.addWidget(headImage, 1,1,1,1)
        layout.addWidget(label2, 2,0,1,1)
        layout.addWidget(self.headLengthSpin, 2,1,1,1)
        layout.addWidget(label3, 3,0,1,1)
        layout.addWidget(self.headWidthSpin, 3,1,1,1)
        layout.addWidget(label4, 4,0,1,1)
        layout.addWidget(self.headDepthSpin, 4,1,1,1)


    def setValues(self, values):
        l,w,d = values["arrow_head_dimensions"]
        self.headLengthSpin.setValue(l)
        self.headWidthSpin.setValue(w)
        self.headDepthSpin.setValue(d)
        self.lineWidthSpin.setValue(values["arrow_line_width"])

    def getValues(self):
        l = self.headLengthSpin.value()
        w = self.headWidthSpin.value()
        d = self.headDepthSpin.value()
        return {"arrow_head_dimensions": (l,w,d),
                "arrow_line_width": self.lineWidthSpin.value()}


class PlusSettingsWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        label1 = QLabel("Font Size :", self)
        self.fontSizeSpin = QSpinBox(self)
        self.fontSizeSpin.setSuffix(" px")
        self.fontSizeSpin.setAlignment(Qt.AlignHCenter)
        self.fontSizeSpin.setRange(9, 90)
        layout.addWidget(label1, 0,0,1,1)
        layout.addWidget(self.fontSizeSpin, 0,1,1,1)

    def setValues(self, values):
        self.fontSizeSpin.setValue( values["plus_size"])

    def getValues(self):
        values = {"plus_size": self.fontSizeSpin.value()}
        return values


class DocumentSettingsWidget(QWidget):
    """ document size and unit settings widget """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.units = {
            "Points": 1.0,
            "Pixels": Settings.render_dpi/72,
            "Picas": 12.0,
            "Inches": 72.0,
            "Millimeters": 72/25.4,
            "Centimeters": 72/2.54,
        }
        self.last_unit = "Points"

        layout = QGridLayout(self)

        label1 = QLabel("Page Size :", self)
        self.presetCombo = QComboBox(self)
        self.presetCombo.addItems(["A4", "A3", "Letter", "Legal", "Custom"])
        self.presetCombo.currentTextChanged.connect(self.onPresetChanged)
        layout.addWidget(label1, 0, 0)
        layout.addWidget(self.presetCombo, 0, 1)

        label2 = QLabel("Unit :", self)
        self.unitCombo = QComboBox(self)
        self.unitCombo.addItems(list(self.units.keys()))
        self.unitCombo.currentTextChanged.connect(self.onUnitChanged)
        layout.addWidget(label2, 1, 0)
        layout.addWidget(self.unitCombo, 1, 1)

        label3 = QLabel("Width :", self)
        self.widthSpin = QDoubleSpinBox(self)
        self.widthSpin.setRange(0, 10000)
        self.widthSpin.setDecimals(2)
        layout.addWidget(label3, 2, 0)
        layout.addWidget(self.widthSpin, 2, 1)

        label4 = QLabel("Height :", self)
        self.heightSpin = QDoubleSpinBox(self)
        self.heightSpin.setRange(0, 10000)
        self.heightSpin.setDecimals(2)
        layout.addWidget(label4, 3, 0)
        layout.addWidget(self.heightSpin, 3, 1)

        label5 = QLabel("Margins :", self)
        self.marginSpin = QDoubleSpinBox(self)
        self.marginSpin.setRange(0, 1000)
        self.marginSpin.setDecimals(2)
        layout.addWidget(label5, 4, 0)
        layout.addWidget(self.marginSpin, 4, 1)

        label6 = QLabel("Orientation :", self)
        layout.addWidget(label6, 5, 0)
        self.portraitRadio = QRadioButton("Portrait", self)
        self.portraitRadio.setChecked(True)
        self.landscapeRadio = QRadioButton("Landscape", self)
        self.portraitRadio.toggled.connect(self.onOrientationChanged)

        orientLayout = QHBoxLayout()
        orientLayout.addWidget(self.portraitRadio)
        orientLayout.addWidget(self.landscapeRadio)
        layout.addLayout(orientLayout, 5, 1)

    def onPresetChanged(self, text):
        presets = {
            "A4": (595, 842),
            "A3": (842, 1191),
            "Letter": (612, 792),
            "Legal": (612, 1008),
        }
        if text in presets:
            w, h = presets[text]
            self.updateDimensions(w, h)

    def onUnitChanged(self, new_unit):
        old_scale = self.units.get(self.last_unit, 1.0)
        new_scale = self.units.get(new_unit, 1.0)
        self.widthSpin.setValue((self.widthSpin.value() * old_scale) / new_scale)
        self.heightSpin.setValue((self.heightSpin.value() * old_scale) / new_scale)
        self.marginSpin.setValue((self.marginSpin.value() * old_scale) / new_scale)
        self.last_unit = new_unit

    def onOrientationChanged(self):
        if self.landscapeRadio.isChecked():
            w, h = self.widthSpin.value(), self.heightSpin.value()
            self.widthSpin.setValue(h)
            self.heightSpin.setValue(w)

    def updateDimensions(self, w_pt, h_pt):
        unit = self.unitCombo.currentText()
        scale = self.units.get(unit, 1.0)
        self.widthSpin.setValue(w_pt / scale)
        self.heightSpin.setValue(h_pt / scale)

    def setValues(self, values):
        self.presetCombo.setCurrentText(values.get("page_size_preset", "A4"))
        self.unitCombo.setCurrentText(values.get("measurement_unit", "Points"))
        self.last_unit = self.unitCombo.currentText()

        unit = self.unitCombo.currentText()
        scale = self.units.get(unit, 1.0)
        self.widthSpin.setValue(values.get("custom_width", 595.0) / scale)
        self.heightSpin.setValue(values.get("custom_height", 842.0) / scale)
        self.marginSpin.setValue(values.get("margins", 36.0) / scale)

        if values.get("page_orientation") == "Landscape":
            self.landscapeRadio.setChecked(True)
        else:
            self.portraitRadio.setChecked(True)

    def getValues(self):
        unit = self.unitCombo.currentText()
        scale = self.units.get(unit, 1.0)
        return {
            "page_size_preset": self.presetCombo.currentText(),
            "measurement_unit": unit,
            "custom_width": self.widthSpin.value() * scale,
            "custom_height": self.heightSpin.value() * scale,
            "margins": self.marginSpin.value() * scale,
            "page_orientation": "Landscape" if self.landscapeRadio.isChecked() else "Portrait",
        }



#**************** Document Setup Dialog  *******************#

PAGE_SIZE_PRESETS = {
    "A4": (595.0, 842.0),
    "A3": (842.0, 1191.0),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
}

DOCUMENT_UNITS = {
    "pixels": {"suffix": " px", "decimals": 0, "step": 10.0, "minimum": 1.0, "maximum": 20000.0},
    "points": {"suffix": " pt", "decimals": 1, "step": 10.0, "minimum": 1.0, "maximum": 14400.0},
    "picas": {"suffix": " pc", "decimals": 2, "step": 1.0, "minimum": 0.1, "maximum": 1200.0},
    "inches": {"suffix": " in", "decimals": 2, "step": 0.25, "minimum": 0.1, "maximum": 200.0},
    "millimeters": {"suffix": " mm", "decimals": 1, "step": 5.0, "minimum": 1.0, "maximum": 5000.0},
    "centimeters": {"suffix": " cm", "decimals": 2, "step": 0.5, "minimum": 0.1, "maximum": 500.0},
}


def points_to_unit(value, unit):
    if unit == "pixels":
        return value/72 * Settings.render_dpi
    if unit == "points":
        return value
    if unit == "picas":
        return value/12
    if unit == "inches":
        return value/72
    if unit == "millimeters":
        return value/72 * 25.4
    if unit == "centimeters":
        return value/72 * 2.54
    return value


def unit_to_points(value, unit):
    if unit == "pixels":
        return value/Settings.render_dpi * 72
    if unit == "points":
        return value
    if unit == "picas":
        return value*12
    if unit == "inches":
        return value*72
    if unit == "millimeters":
        return value/25.4 * 72
    if unit == "centimeters":
        return value/2.54 * 72
    return value


def page_preset_for_size(width, height):
    for name, size in PAGE_SIZE_PRESETS.items():
        if abs(width-size[0]) < 0.5 and abs(height-size[1]) < 0.5:
            return name
    return "Custom"


class DocumentSetupDialog(QDialog):
    """ document page size and display unit settings """
    def __init__(self, parent, page_size, unit="centimeters"):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Document Setup")
        self.setWindowIcon(QIcon(":/icons/settings.png"))
        self._updating = False
        self.page_width, self.page_height = page_size
        self.unit = unit if unit in DOCUMENT_UNITS else "centimeters"

        layout = QGridLayout(self)
        self.pageSizeLabel = QLabel("Page Size :", self)
        self.pageSizeCombo = QComboBox(self)
        self.pageSizeCombo.addItems(list(PAGE_SIZE_PRESETS.keys()) + ["Custom"])
        self.unitLabel = QLabel("Units :", self)
        self.unitCombo = QComboBox(self)
        self.unitCombo.addItems(DOCUMENT_UNITS.keys())
        self.widthLabel = QLabel("Width :", self)
        self.widthSpin = QDoubleSpinBox(self)
        self.heightLabel = QLabel("Height :", self)
        self.heightSpin = QDoubleSpinBox(self)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel, parent=self)

        for spin in (self.widthSpin, self.heightSpin):
            spin.setAlignment(Qt.AlignHCenter)

        layout.addWidget(self.pageSizeLabel, 0,0,1,1)
        layout.addWidget(self.pageSizeCombo, 0,1,1,1)
        layout.addWidget(self.unitLabel, 1,0,1,1)
        layout.addWidget(self.unitCombo, 1,1,1,1)
        layout.addWidget(self.widthLabel, 2,0,1,1)
        layout.addWidget(self.widthSpin, 2,1,1,1)
        layout.addWidget(self.heightLabel, 3,0,1,1)
        layout.addWidget(self.heightSpin, 3,1,1,1)
        layout.addWidget(self.btnBox, 4,0,1,2)

        self.pageSizeCombo.currentIndexChanged[str].connect(self.onPageSizeChange)
        self.unitCombo.currentIndexChanged[str].connect(self.onUnitChange)
        self.widthSpin.valueChanged.connect(self.onDimensionChange)
        self.heightSpin.valueChanged.connect(self.onDimensionChange)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)

        self.unitCombo.setCurrentIndex(self.unitCombo.findText(self.unit))
        self.updateSpinProperties()
        self.updateSpinValues()
        self.updatePageSizePreset()

    def updateSpinProperties(self):
        spec = DOCUMENT_UNITS[self.unit]
        was_updating = self._updating
        self._updating = True
        for spin in (self.widthSpin, self.heightSpin):
            spin.setDecimals(spec["decimals"])
            spin.setSingleStep(spec["step"])
            spin.setRange(spec["minimum"], spec["maximum"])
            spin.setSuffix(spec["suffix"])
        self._updating = was_updating

    def updateSpinValues(self):
        self._updating = True
        self.widthSpin.setValue(points_to_unit(self.page_width, self.unit))
        self.heightSpin.setValue(points_to_unit(self.page_height, self.unit))
        self._updating = False

    def updatePageSizePreset(self):
        preset = page_preset_for_size(self.page_width, self.page_height)
        index = self.pageSizeCombo.findText(preset)
        if index >= 0:
            self._updating = True
            self.pageSizeCombo.setCurrentIndex(index)
            self._updating = False

    def onPageSizeChange(self, page_size):
        if self._updating or page_size == "Custom":
            return
        self.page_width, self.page_height = PAGE_SIZE_PRESETS[page_size]
        self.updateSpinValues()

    def onUnitChange(self, unit):
        if self._updating:
            return
        self.unit = unit
        self.updateSpinProperties()
        self.updateSpinValues()

    def onDimensionChange(self, value=None):
        if self._updating:
            return
        self.page_width = unit_to_points(self.widthSpin.value(), self.unit)
        self.page_height = unit_to_points(self.heightSpin.value(), self.unit)
        self.updatePageSizePreset()

    def getPageSize(self):
        return self.page_width, self.page_height

    def getUnit(self):
        return self.unit


#**************** PNG Export Settings Dialog  *******************#

class ImageExportSettingsDialog(QDialog):

    color_dict = {"#ffffff": "White"}

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Image Export Settings")
        self.setWindowIcon(QIcon(":/icons/settings.png"))
        layout = QGridLayout(self)
        self.label1 = QLabel("DPI :", self)
        self.label2 = QLabel("Margin :", self)
        self.label3 = QLabel("Background :", self)
        self.dpiSpin = QSpinBox(self)
        self.dpiSpin.setRange(25, 400)
        self.dpiSpin.setSingleStep(50)
        self.marginSpin = QSpinBox(self)
        self.marginSpin.setRange(0, 200)
        self.marginSpin.setSingleStep(5)
        self.backgroundCombo = QComboBox(self)
        self.backgroundCombo.addItems(["Transparent", "White"])
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel, parent=self)
        layout.addWidget(self.label1, 0,0,1,1)
        layout.addWidget(self.dpiSpin, 0,1,1,1)
        layout.addWidget(self.label2, 1,0,1,1)
        layout.addWidget(self.marginSpin, 1,1,1,1)
        layout.addWidget(self.label3, 2,0,1,1)
        layout.addWidget(self.backgroundCombo, 2,1,1,1)
        layout.addWidget(self.btnBox, 3,0,1,2)
        # set values
        self.dpiSpin.setValue(Settings.image_export_dpi)
        self.marginSpin.setValue(Settings.image_export_margin)
        bg = self.color_dict.get(Settings.image_export_background, "Transparent")
        self.backgroundCombo.setCurrentIndex(self.backgroundCombo.findText(bg))
        # connect signals
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)


    def getDpi(self):
        return self.dpiSpin.value()

    def getMargin(self):
        return self.marginSpin.value()

    def getBackground(self):
        color_dict = {name:code for code,name in self.color_dict.items()}# inverse dict
        return color_dict.get(self.backgroundCombo.currentText(), "transparent")
