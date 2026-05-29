# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QSpinBox, QFormLayout, QDialogButtonBox
)


class PageGridDialog(QDialog):
    def __init__(self, parent=None, enabled=False, spacing=20, major_every=5):
        super().__init__(parent)
        self.setWindowTitle("Grid Settings")
        form = QFormLayout()
        self.setLayout(form)

        self.enabledCheck = QCheckBox("Show grid", self)
        self.enabledCheck.setChecked(bool(enabled))
        form.addRow("", self.enabledCheck)

        self.spacingSpin = QSpinBox(self)
        self.spacingSpin.setRange(4, 200)
        self.spacingSpin.setValue(int(spacing))
        form.addRow("Spacing (px)", self.spacingSpin)

        self.majorEverySpin = QSpinBox(self)
        self.majorEverySpin.setRange(1, 20)
        self.majorEverySpin.setValue(int(major_every))
        form.addRow("Major line every", self.majorEverySpin)

        self._toggle_enabled()
        self.enabledCheck.toggled.connect(self._toggle_enabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow("", buttons)

    def _toggle_enabled(self):
        enabled = self.enabledCheck.isChecked()
        self.spacingSpin.setEnabled(enabled)
        self.majorEverySpin.setEnabled(enabled)

    def isGridEnabled(self):
        return self.enabledCheck.isChecked()

    def getSpacing(self):
        return int(self.spacingSpin.value())

    def getMajorEvery(self):
        return int(self.majorEverySpin.value())
