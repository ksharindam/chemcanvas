# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QRadioButton, QButtonGroup,
    QSpinBox, QFormLayout, QDialogButtonBox
)


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
