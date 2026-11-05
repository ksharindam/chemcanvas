# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2025-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
try:
    from PyQt6.QtCore import QSettings, Qt
    from PyQt6.QtGui import QPixmap, QIcon
    from PyQt6.QtWidgets import (QWidget, QDialog, QTableWidget, QDialogButtonBox,
        QGridLayout, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem, QLabel,
        QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
        QFormLayout, QRadioButton, QButtonGroup, QGroupBox
    )
except:
    from PyQt5.QtCore import QSettings, Qt
    from PyQt5.QtGui import QPixmap, QIcon
    from PyQt5.QtWidgets import (QWidget, QDialog, QTableWidget, QDialogButtonBox,
        QGridLayout, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem, QLabel,
        QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
        QFormLayout, QRadioButton, QButtonGroup, QGroupBox
    )

from app_data import App, Settings, Default


def newSpinBox(parent, range_, single_step):
    spinBox = QSpinBox(parent)
    spinBox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    spinBox.setRange(*range_)
    spinBox.setSingleStep(single_step)
    return spinBox

def newDoubleSpinBox(parent, range_, single_step):
    spinBox = QDoubleSpinBox(parent)
    spinBox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    spinBox.setRange(*range_)
    spinBox.setSingleStep(single_step)
    spinBox.setDecimals(1)
    return spinBox


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
        self.categoryTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.categoryTable.setAlternatingRowColors(True)
        self.categoryTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)# required for table.selectRow()
        self.categoryTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.categoryTable.horizontalHeader().setHidden(True)
        self.categoryTable.verticalHeader().setHidden(True)
        self.categoryTable.setColumnCount(1)
        self.categoryTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.settingsContainer = QWidget(self)
        self.settingsContainerLayout = QVBoxLayout(self.settingsContainer)
        btnBoxContainer = QWidget(self)
        btnBoxLayout = QHBoxLayout(btnBoxContainer)
        btnBoxLayout.setContentsMargins(0,0,0,0)
        self.resetBtn = QPushButton("Reset to Default", self)
        btnBoxLayout.addWidget(self.resetBtn)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel, parent=self)
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
        self.fontSizeSpin = newSpinBox(self, (6, 60), 1)
        self.fontSizeSpin.setSuffix(" px")
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
        lengthLabel = QLabel("Length :", self)
        self.lengthSpin = newSpinBox(self, (12, 120), 1)
        lineWidthLabel = QLabel("Line Width :", self)
        self.widthSpin = newDoubleSpinBox(self, (1, 6), 0.1)
        doubleBondGapLabel = QLabel("Double Bond Spacing :", self)
        self.doubleBondGapSpin = newDoubleSpinBox(self, (1, 30), 0.1)
        boldWidthLabel = QLabel("Bold Width :", self)
        self.boldWidthSpin = newDoubleSpinBox(self, (3, 20), 0.1)
        hashSpacingLabel = QLabel("Hashed Wedge Spacing :", self)
        self.hashSpacingSpin = newSpinBox(self, (150, 400), 10)
        self.hashSpacingSpin.setSuffix(" %")
        layout.addWidget(lengthLabel, 0,0,1,1)
        layout.addWidget(self.lengthSpin, 0,1,1,1)
        layout.addWidget(lineWidthLabel, 1,0,1,1)
        layout.addWidget(self.widthSpin, 1,1,1,1)
        layout.addWidget(doubleBondGapLabel, 2,0,1,1)
        layout.addWidget(self.doubleBondGapSpin, 2,1,1,1)
        layout.addWidget(boldWidthLabel, 3,0,1,1)
        layout.addWidget(self.boldWidthSpin, 3,1,1,1)
        layout.addWidget(hashSpacingLabel, 4,0,1,1)
        layout.addWidget(self.hashSpacingSpin, 4,1,1,1)

    def setValues(self, values):
        self.lengthSpin.setValue(values["bond_length"])
        self.widthSpin.setValue(values["bond_width"])
        self.doubleBondGapSpin.setValue(values["bond_spacing"])
        self.boldWidthSpin.setValue(values["bold_width"])
        self.hashSpacingSpin.setValue(int(values["hash_spacing"]*100))

    def getValues(self):
        values = {"bond_length": self.lengthSpin.value(),
            "bond_width": self.widthSpin.value(),
            "bond_spacing": self.doubleBondGapSpin.value(),
            "bold_width": self.boldWidthSpin.value(),
            "hash_spacing": self.hashSpacingSpin.value()/100,
        }
        return values


class MarksSettingsWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        label1 = QLabel("Electron Dot Size :", self)
        self.dotSizeSpin = newDoubleSpinBox(self, (1, 10), 0.1)
        self.dotSizeSpin.setToolTip("Diameter of Lone Pair or Free Radical dot")
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
        self.lineWidthSpin = newDoubleSpinBox(self, (1, 10), 0.1)
        self.lineWidthSpin.setToolTip("Line width (px)")
        # head icon
        headImage = QLabel(self)
        headImage.setPixmap(QPixmap(":/icons/arrow-dimensions.png"))
        # head length
        label2 = QLabel("Head Length :", self)
        self.headLengthSpin = newDoubleSpinBox(self, (2.5, 25), 0.1)
        self.headLengthSpin.setToolTip("multiple of line width")
        # head width
        label3 = QLabel("Head Width :", self)
        self.headWidthSpin = newDoubleSpinBox(self, (1, 10), 0.1)
        self.headWidthSpin.setToolTip("multiple of line width")
        # head depth
        label4 = QLabel("Head Depth :", self)
        self.headDepthSpin = newDoubleSpinBox(self, (0, 7), 0.1)
        self.headDepthSpin.setToolTip("multiple of line width")
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
        self.fontSizeSpin = newSpinBox(self, (9, 90), 1)
        self.fontSizeSpin.setSuffix(" px")
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
        self.marginLabel = QLabel("Margin :", self)
        self.marginSpin = newSpinBox(self, (0, 200), 5)
        self.marginSpin.setSuffix(" px")
        # PNG settings
        self.pngGroupBox = QGroupBox("PNG", self)
        self.pngGroupLayout = QGridLayout(self.pngGroupBox)
        self.pngGroupLayout.setContentsMargins(0,0,0,0)
        self.dpiLabel = QLabel("DPI :", self)
        self.dpiSpin = newSpinBox(self, (25, 400), 50)
        self.backgroundLabel = QLabel("Background :", self)
        self.backgroundCombo = QComboBox(self)
        self.backgroundCombo.addItems(["Transparent", "White"])
        self.pngGroupLayout.addWidget(self.dpiLabel, 0,0,1,1)
        self.pngGroupLayout.addWidget(self.dpiSpin, 0,1,1,1)
        self.pngGroupLayout.addWidget(self.backgroundLabel, 1,0,1,1)
        self.pngGroupLayout.addWidget(self.backgroundCombo, 1,1,1,1)
        # SVG settings
        self.svgGroupBox = QGroupBox("SVG", self)
        self.svgGroupLayout = QVBoxLayout(self.svgGroupBox)
        self.svgGroupLayout.setContentsMargins(0,0,0,0)
        self.svgAtomTextBtn = QCheckBox("Atom text as vector shapes", self)
        self.svgAtomTextBtn.setToolTip("Better consistency but\ngenerates larger file size")
        self.svgGroupLayout.addWidget(self.svgAtomTextBtn)

        self.btnBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel, parent=self)
        layout.addWidget(self.pngGroupBox, 0,0,1,2)
        layout.addWidget(self.svgGroupBox, 1,0,1,2)
        layout.addWidget(self.marginLabel, 2,0,1,1)
        layout.addWidget(self.marginSpin, 2,1,1,1)
        layout.addWidget(self.btnBox, 3,0,1,2)
        # set values
        self.dpiSpin.setValue(Settings.image_export_dpi)
        self.marginSpin.setValue(Settings.image_export_margin)
        bg = self.color_dict.get(Settings.image_export_background, "Transparent")
        self.backgroundCombo.setCurrentIndex(self.backgroundCombo.findText(bg))
        self.svgAtomTextBtn.setChecked(Settings.svg_atom_text_as_path)
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

    def getSvgAtomTextAsPath(self):
        return self.svgAtomTextBtn.isChecked()



#************************* Page Setup Dialog  *************************#

PAGE_SIZE_PRESETS = {
    "A4": (595.0, 842.0),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
}

def get_page_size_name(width, height):
    """ get size name from width and height in points """
    for name, size in PAGE_SIZE_PRESETS.items():
        if abs(width-size[0]) < 1.0 and abs(height-size[1]) < 1.0:
            return name
    return "Custom"


class PageSetupDialog(QDialog):
    def __init__(self, parent, count, page_size, margins):
        """ page_size and margins are in px unit @render_dpi """
        super().__init__(parent)
        self.setWindowTitle("Page Setup")
        landscape = page_size[0] > page_size[1]
        page_size_pt = [x*72/Settings.render_dpi for x in page_size]
        size_name = get_page_size_name(min(page_size_pt), max(page_size_pt))
        if size_name=="Custom":
            landscape = False
        custom_size = [round(x*2.54/Settings.render_dpi,1) for x in page_size]

        self.countLabel = QLabel("Pages Count :", self)
        self.countSpin = newSpinBox(self, (1, 200), 1)
        self.countSpin.setValue(count)

        self.sizeLabel = QLabel("Page Size :", self)
        self.sizeCombo = QComboBox(self)
        self.sizeCombo.addItems(["A4", "Letter", "Legal", "Custom"])
        if size_name in ["A4", "Letter", "Legal", "Custom"]:
            self.sizeCombo.setCurrentText(size_name)

        self.customSizeLabel = QLabel("Custom WxH (cm) :")
        self.customSizeContainer = QWidget(self)
        customSizeLayout = QHBoxLayout(self.customSizeContainer)
        customSizeLayout.setContentsMargins(0,0,0,0)
        self.widthSpin = newDoubleSpinBox(self, (5.0, 99.9), 0.5)
        self.heightSpin = newDoubleSpinBox(self, (5.0, 99.9), 0.5)
        for i,widget in enumerate((self.widthSpin, self.heightSpin)):
            widget.setValue(custom_size[i])
            customSizeLayout.addWidget(widget)

        self.portraitBtn = QRadioButton("Portrait", self)
        self.landscapeBtn = QRadioButton("Landscape", self)
        self.orientGroup = QButtonGroup(self)
        self.orientGroup.addButton(self.portraitBtn)
        self.orientGroup.addButton(self.landscapeBtn)

        self.marginsLabel = QLabel("Margins (cm) :", self)
        self.marginTop = newDoubleSpinBox(self, (0, 9.9), 0.1)
        self.marginRight = newDoubleSpinBox(self, (0, 9.9), 0.1)
        self.marginBottom = newDoubleSpinBox(self, (0, 9.9), 0.1)
        self.marginLeft = newDoubleSpinBox(self, (0, 9.9), 0.1)
        margins_cm = [round(2.54*v/Settings.render_dpi,1) for v in margins]
        for i, widget in enumerate([self.marginLeft, self.marginTop, self.marginRight, self.marginBottom]):
            widget.setValue(margins_cm[i])
        self.marginsLayout = QGridLayout()
        self.marginsLayout.setContentsMargins(0,0,0,0)
        self.marginsLayout.addWidget(self.marginTop, 0,1,1,1)
        self.marginsLayout.addWidget(self.marginLeft, 1,0,1,1)
        self.marginsLayout.addWidget(self.marginRight, 1,2,1,1)
        self.marginsLayout.addWidget(self.marginBottom, 2,1,1,1)

        self.saveAsDefaultBtn = QPushButton("Save As Default", self)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.btnBox.addButton(self.saveAsDefaultBtn, QDialogButtonBox.ButtonRole.ResetRole)

        layout = QGridLayout(self)
        layout.addWidget(self.countLabel, 0,0,1,1)
        layout.addWidget(self.countSpin, 0,1,1,1)
        layout.addWidget(self.sizeLabel, 1,0,1,1)
        layout.addWidget(self.sizeCombo, 1,1,1,1)
        layout.addWidget(self.customSizeLabel, 2,0,1,1)
        layout.addWidget(self.customSizeContainer, 2,1,1,1)
        layout.addWidget(self.portraitBtn, 3,0,1,1)
        layout.addWidget(self.landscapeBtn, 3,1,1,1)
        layout.addWidget(self.marginsLabel, 4,0,1,1)
        layout.addLayout(self.marginsLayout, 4,1,1,1)
        layout.addWidget(self.btnBox, 5,0,1,2)

        self.landscapeBtn.setChecked(landscape)
        self.portraitBtn.setChecked(not landscape)

        self.widthSpin.setValue(custom_size[0])
        self.heightSpin.setValue(custom_size[1])

        self.sizeCombo.currentTextChanged.connect(self.toggle_custom_enabled)
        self.saveAsDefaultBtn.clicked.connect(self.saveAsDefault)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)

        self.toggle_custom_enabled()


    def toggle_custom_enabled(self):
        is_custom = self.sizeCombo.currentText() == "Custom"
        self.customSizeLabel.setVisible(is_custom)
        self.customSizeContainer.setVisible(is_custom)
        self.portraitBtn.setVisible(not is_custom)
        self.landscapeBtn.setVisible(not is_custom)

    def getPageCount(self):
        return self.countSpin.value()

    def getPageSize(self):
        """ return page size in px """
        size_name = self.sizeCombo.currentText()
        if size_name in PAGE_SIZE_PRESETS:
            page_size = PAGE_SIZE_PRESETS[size_name]
            w, h = [int(round(x/72*Settings.render_dpi)) for x in page_size]
            if self.landscapeBtn.isChecked():
                w, h = h, w
        else:# Custom
            page_size = self.widthSpin.value(), self.heightSpin.value()
            w, h = [int(round(x/2.54*Settings.render_dpi)) for x in page_size]
        return (w, h)

    def getMargins(self):
        """ return page margins in px """
        margins = []
        for widget in (self.marginLeft, self.marginTop, self.marginRight, self.marginBottom):
            val = Settings.render_dpi * widget.value()/2.54
            margins.append(int(round(val)))
        return tuple(margins)

    def saveAsDefault(self):
        App.new_page_size = self.getPageSize()
        App.new_page_margins = self.getMargins()
        settings = QSettings("chemcanvas", "chemcanvas", self)
        settings.setValue("NewPageSize", "%i,%i"%App.new_page_size)
        settings.setValue("NewPageMargins", "%i,%i,%i,%i"%App.new_page_margins)



#************************* Page Grid Dialog  **************************#

class PageGridDialog(QDialog):
    def __init__(self, parent=None, spacing=20, major_every=5):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Grid Settings")
        form = QFormLayout()
        self.setLayout(form)

        self.spacingSpin = newSpinBox(self, (4, 200), 1)
        self.spacingSpin.setValue(int(spacing))
        form.addRow("Spacing (px)", self.spacingSpin)

        self.majorEverySpin = newSpinBox(self, (1, 20), 1)
        self.majorEverySpin.setValue(int(major_every))
        form.addRow("Major line every", self.majorEverySpin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow("", buttons)

    def getSpacing(self):
        return int(self.spacingSpin.value())

    def getMajorEvery(self):
        return int(self.majorEverySpin.value())
