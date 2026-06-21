# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2025-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (QWidget, QDialog, QTableWidget, QDialogButtonBox,
    QGridLayout, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem, QLabel, QSpinBox, QSizePolicy,
    QPushButton, QDoubleSpinBox, QComboBox,
    QFormLayout, QRadioButton, QButtonGroup
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
        titles = ["Atom", "Bond", "Marks", "Arrow", "Plus"]
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
        label1 = QLabel("Length :", self)
        self.lengthSpin = QSpinBox(self)
        self.lengthSpin.setAlignment(Qt.AlignHCenter)
        self.lengthSpin.setRange(12, 120)
        label2 = QLabel("Line Width :", self)
        self.widthSpin = QDoubleSpinBox(self)
        self.widthSpin.setAlignment(Qt.AlignHCenter)
        self.widthSpin.setDecimals(1)
        self.widthSpin.setSingleStep(0.1)
        self.widthSpin.setRange(1, 6)
        label3 = QLabel("Double Bond Gap :", self)
        self.doubleBondGapSpin = QDoubleSpinBox(self)
        self.doubleBondGapSpin.setAlignment(Qt.AlignHCenter)
        self.doubleBondGapSpin.setDecimals(1)
        self.doubleBondGapSpin.setSingleStep(0.2)
        self.doubleBondGapSpin.setRange(1, 30)
        layout.addWidget(label1, 0,0,1,1)
        layout.addWidget(self.lengthSpin, 0,1,1,1)
        layout.addWidget(label2, 1,0,1,1)
        layout.addWidget(self.widthSpin, 1,1,1,1)
        layout.addWidget(label3, 2,0,1,1)
        layout.addWidget(self.doubleBondGapSpin, 2,1,1,1)

    def setValues(self, values):
        self.lengthSpin.setValue(values["bond_length"])
        self.widthSpin.setValue(values["bond_width"])
        self.doubleBondGapSpin.setValue(values["bond_spacing"])

    def getValues(self):
        values = {"bond_length": self.lengthSpin.value(),
            "bond_width": self.widthSpin.value(),
            "bond_spacing": self.doubleBondGapSpin.value(),
        }
        return values


class MarksSettingsWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        label1 = QLabel("Electron Dot Size :", self)
        self.dotSizeSpin = QDoubleSpinBox(self)
        self.dotSizeSpin.setToolTip("Diameter of Lone Pair or Free Radical dot")
        self.dotSizeSpin.setAlignment(Qt.AlignHCenter)
        self.dotSizeSpin.setDecimals(1)
        self.dotSizeSpin.setSingleStep(0.1)
        self.dotSizeSpin.setRange(1, 10)
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
        self.headWidthSpin.setAlignment(Qt.AlignHCenter)
        self.headWidthSpin.setDecimals(1)
        self.headWidthSpin.setSingleStep(0.5)
        self.headWidthSpin.setRange(1, 10)
        # head depth
        label4 = QLabel("Head Depth :", self)
        self.headDepthSpin = QDoubleSpinBox(self)
        self.headDepthSpin.setToolTip("multiple of line width")
        self.headDepthSpin.setAlignment(Qt.AlignHCenter)
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




#************************* Page Setup Dialog  *************************#

PAGE_SIZE_PRESETS = {
    "A4": (595.0, 842.0),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
}

def get_page_size_name(width, height):
    for name, size in PAGE_SIZE_PRESETS.items():
        if abs(width-size[0]) < 0.5 and abs(height-size[1]) < 0.5:
            return name
    return "Custom"


class PageSetupDialog(QDialog):
    def __init__(self, parent=None, page_count=1, page_size="A4", orientation="Portrait",
                 margins=(0, 0, 0, 0), custom_size=None):
        super().__init__(parent)
        self.setWindowTitle("Page Setup")
        self._custom_size = custom_size or (595, 842)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        self.pageCountSpin = QSpinBox(self)
        self.pageCountSpin.setRange(1, 200)
        self.pageCountSpin.setValue(int(page_count))
        form.addRow("Pages", self.pageCountSpin)

        self.sizeCombo = QComboBox(self)
        self.sizeCombo.addItems(["A4", "Letter", "Legal", "Custom"])
        if page_size in ["A4", "Letter", "Legal", "Custom"]:
            self.sizeCombo.setCurrentText(page_size)
        form.addRow("Page size", self.sizeCombo)

        orient_row = QHBoxLayout()
        self.portraitRadio = QRadioButton("Portrait", self)
        self.landscapeRadio = QRadioButton("Landscape", self)
        self.orientGroup = QButtonGroup(self)
        self.orientGroup.addButton(self.portraitRadio)
        self.orientGroup.addButton(self.landscapeRadio)
        orient_row.addWidget(self.portraitRadio)
        orient_row.addWidget(self.landscapeRadio)
        if orientation == "Landscape":
            self.landscapeRadio.setChecked(True)
        else:
            self.portraitRadio.setChecked(True)
        form.addRow("Orientation", orient_row)

        self.widthSpin = QSpinBox(self)
        self.widthSpin.setRange(100, 5000)
        self.widthSpin.setValue(int(self._custom_size[0]))
        self.heightSpin = QSpinBox(self)
        self.heightSpin.setRange(100, 5000)
        self.heightSpin.setValue(int(self._custom_size[1]))
        wh_row = QHBoxLayout()
        wh_row.addWidget(QLabel("W"))
        wh_row.addWidget(self.widthSpin)
        wh_row.addWidget(QLabel("H"))
        wh_row.addWidget(self.heightSpin)
        form.addRow("Custom (pt)", wh_row)

        t, r, b, l = margins
        self.marginTop = QSpinBox(self); self.marginTop.setRange(0, 500); self.marginTop.setValue(int(t))
        self.marginRight = QSpinBox(self); self.marginRight.setRange(0, 500); self.marginRight.setValue(int(r))
        self.marginBottom = QSpinBox(self); self.marginBottom.setRange(0, 500); self.marginBottom.setValue(int(b))
        self.marginLeft = QSpinBox(self); self.marginLeft.setRange(0, 500); self.marginLeft.setValue(int(l))
        m_row1 = QHBoxLayout()
        m_row1.addWidget(QLabel("Top")); m_row1.addWidget(self.marginTop)
        m_row1.addWidget(QLabel("Right")); m_row1.addWidget(self.marginRight)
        m_row2 = QHBoxLayout()
        m_row2.addWidget(QLabel("Bottom")); m_row2.addWidget(self.marginBottom)
        m_row2.addWidget(QLabel("Left")); m_row2.addWidget(self.marginLeft)
        form.addRow("Margins (pt)", m_row1)
        form.addRow("", m_row2)

        self._toggle_custom_enabled()
        self.sizeCombo.currentTextChanged.connect(self._toggle_custom_enabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_custom_enabled(self, *_):
        is_custom = self.sizeCombo.currentText() == "Custom"
        self.widthSpin.setEnabled(is_custom)
        self.heightSpin.setEnabled(is_custom)

    def getPageCount(self):
        return int(self.pageCountSpin.value())

    def getPageSizePoints(self):
        preset = self.sizeCombo.currentText()
        if preset == "A4":
            w, h = 595, 842
        elif preset == "Letter":
            w, h = 612, 792
        elif preset == "Legal":
            w, h = 612, 1008
        else:
            w, h = int(self.widthSpin.value()), int(self.heightSpin.value())
        if self.landscapeRadio.isChecked():
            w, h = h, w
        return w, h

    def getMarginsPoints(self):
        return (
            int(self.marginTop.value()),
            int(self.marginRight.value()),
            int(self.marginBottom.value()),
            int(self.marginLeft.value()),
        )

    def getOrientation(self):
        return "Landscape" if self.landscapeRadio.isChecked() else "Portrait"

    def getPresetName(self):
        return self.sizeCombo.currentText()



#************************* Page Grid Dialog  **************************#

class PageGridDialog(QDialog):
    def __init__(self, parent=None, spacing=20, major_every=5):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Grid Settings")
        form = QFormLayout()
        self.setLayout(form)

        self.spacingSpin = QSpinBox(self)
        self.spacingSpin.setRange(4, 200)
        self.spacingSpin.setValue(int(spacing))
        form.addRow("Spacing (px)", self.spacingSpin)

        self.majorEverySpin = QSpinBox(self)
        self.majorEverySpin.setRange(1, 20)
        self.majorEverySpin.setValue(int(major_every))
        form.addRow("Major line every", self.majorEverySpin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow("", buttons)

    def getSpacing(self):
        return int(self.spacingSpin.value())

    def getMajorEvery(self):
        return int(self.majorEverySpin.value())
