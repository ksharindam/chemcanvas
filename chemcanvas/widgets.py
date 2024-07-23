# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2024 Arindam Chaudhuri <arindamsoft94@gmail.com>

# This module contains some custom widgets and dialogs

import platform
import urllib.request

from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QEventLoop, QTimer, QUrl
from PyQt5.QtGui import QPainter, QPixmap, QColor, QDesktopServices

from PyQt5.QtWidgets import ( QDialog, QDialogButtonBox, QGridLayout,
    QLineEdit, QPushButton, QLabel, QApplication, QSizePolicy,
    QTextEdit, QWidget, QHBoxLayout
)

from __init__ import __version__


palette_colors = [
    "#000000", "#404040", "#6b6b6b", "#808080", "#909090", "#ffffff",
    "#790874", "#f209f1", "#09007c", "#000def", "#047f7d", "#05fef8",
    "#7e0107", "#f00211", "#fff90d", "#07e00d", "#067820", "#827d05",
]


class PaletteWidget(QLabel):
    """ Color Palette that holds many colors"""
    colorSelected = pyqtSignal(tuple)# in (r, g, b) format

    def __init__(self, parent, color_index=0):
        QLabel.__init__(self, parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.cols = 18
        self.rows = 1
        self.cell_size = 22
        self.curr_index = color_index
        self.pixmap = QPixmap(self.cols*self.cell_size, self.rows*self.cell_size)
        self.drawPalette()

    def setCurrentIndex(self, index):
        if index >= len(palette_colors):
            return
        self.curr_index = index
        self.drawPalette()# for showing color selection change
        color = QColor(palette_colors[index]).getRgb()[:3]
        self.colorSelected.emit(color)

    def drawPalette(self):
        cols, rows, cell_size = self.cols, self.rows, self.cell_size
        self.pixmap.fill()
        painter = QPainter(self.pixmap)
        for i,color in enumerate(palette_colors):
            painter.setBrush(QColor(color))
            x, y = (i%cols)*cell_size, (i//cols)*cell_size
            if i==self.curr_index:
                painter.drawRect( x+1, y+1, cell_size-3, cell_size-3)
                # visual feedback for selected color cell
                painter.setBrush(Qt.white)
                painter.drawRect( x+6, y+6, cell_size-13, cell_size-13)
                painter.setBrush(QColor(color))
            else:
                painter.drawRect( x, y, cell_size-1, cell_size-1)
        painter.end()
        self.setPixmap(self.pixmap)

    def mousePressEvent(self, ev):
        x, y = ev.x(), ev.y()
        if x == 0 or y == 0: return
        row = y // self.cell_size
        col = x // self.cell_size
        index = row * self.cols + col
        self.setCurrentIndex(index)



#  ----------------- Text Display or Input Dialog -----------------

class TextBoxDialog(QDialog):
    """ A text input or display dialog with copy/paste button """
    def __init__(self, title, text, parent, mode="display"):
        QDialog.__init__(self, parent)
        self.mode = mode # display or input
        self.resize(480, 100)
        # create widgets
        self.titleWidget = QLabel(title, self)
        self.textBox = QLineEdit(text, self)
        if mode=="input":
            copy_paste_mode, btns = "Paste", QDialogButtonBox.Ok|QDialogButtonBox.Cancel
        else: # display text
            copy_paste_mode, btns = "Copy", QDialogButtonBox.Close
            self.textBox.setFocusPolicy(Qt.ClickFocus)
        self.copyPasteBtn = QPushButton(copy_paste_mode, parent)
        self.btnBox = QDialogButtonBox(btns, parent=self)
        # layout widgets
        layout = QGridLayout(self)
        layout.addWidget(self.titleWidget, 0,0, 1,2)
        layout.addWidget(self.textBox, 1,0, 1,1)
        layout.addWidget(self.copyPasteBtn, 1,1, 1,1)
        layout.addWidget(self.btnBox, 2,0, 1,2)

        self.copyPasteBtn.clicked.connect(self.copyPaste)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)

    def copyPaste(self):
        if self.mode == "display":# copy
            QApplication.clipboard().setText(self.textBox.text())
        elif self.mode == "input":# paste
            text = QApplication.clipboard().text()
            if text:
                self.textBox.setText(text)

    def text(self):
        return self.textBox.text()


# ------------------- Update Dialog -------------------

class UpdateDialog(QDialog):
    """ Dialog for checking for updates """
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Check for Update")
        layout = QGridLayout(self)
        currentVersionLabel = QLabel("Current Version : %s"%__version__, self)
        self.latestVersionLabel = QLabel("Latest Release : x.x.x", self)
        self.textView = QTextEdit(self)
        self.textView.setReadOnly(True)
        self.updateBtn = QPushButton("Check for Update", self)
        closeBtn = QPushButton("Cancel", self)
        buttonBox = QWidget(self)
        buttonLayout = QHBoxLayout(buttonBox)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.updateBtn)
        buttonLayout.addWidget(closeBtn)

        layout.addWidget(currentVersionLabel, 0,0,1,1)
        layout.addWidget(self.latestVersionLabel, 1,0,1,1)
        layout.addWidget(self.textView, 2,0,1,1)
        layout.addWidget(buttonBox, 3,0,1,1)

        closeBtn.clicked.connect(self.reject)
        self.updateBtn.clicked.connect(self.checkForUpdate)

        self.textView.hide()
        self.latest_version = ""


    def checkForUpdate(self):
        if self.latest_version:
            return self.download()

        self.updateBtn.setEnabled(False)
        # show textView and enlarge window and place to center
        win_w = self.width()
        win_h = self.height()
        self.textView.show()
        self.move(self.pos() - QPoint((500-win_w)/2, (300-win_h)/2))# place center
        self.resize(500,300)
        self.textView.setPlainText("Checking for Update...")
        wait(100)

        try:
            latest_version, changelog = latest_version_info("ksharindam/chemcanvas")
        except RuntimeError as e:
            self.textView.setPlainText(str(e))
            self.updateBtn.setEnabled(True)
            return

        if latest_version:
            self.latestVersionLabel.setText("Latest Release : %s"%latest_version)

        if is_later_than(latest_version, __version__):# latest version is available
            self.latest_version = latest_version
            self.textView.setPlainText(changelog)
            self.updateBtn.setText("Download")
        else:
            self.textView.setPlainText("You are already using the latest version")

        self.updateBtn.setEnabled(True)



    def download(self):
        if platform.system()=="Windows":
            filename = "ChemCanvas.exe"
        # currently we provide x86_64 and armhf AppImage
        elif platform.system()=="Linux":
            arch = platform.machine()=="armv7l" and "armhf" or "x86_64"
            filename = "ChemCanvas-%s.AppImage" % arch
        # platform not supported, or may be could not detect properly
        else:
            addr = "https://github.com/ksharindam/chemcanvas/releases/latest"
            QDesktopServices.openUrl(QUrl(addr))
            return
        addr = "https://github.com/ksharindam/chemcanvas/releases/latest/download/%s" % filename
        QDesktopServices.openUrl(QUrl(addr))


def latest_version_info(github_repo):
    """ github repo name is in <username>/<repo> format e.g - ksharindam/chemcanvas """
    latest_version = ""
    changelog = ""
    url = "https://api.github.com/repos/%s/releases/latest" % github_repo
    try:
        response = urllib.request.urlopen(url)
        text = response.read().decode("utf-8")
    except:
        raise RuntimeError("Failed to connect !\nCheck your internet connection.")

    pos = text.index('"tag_name"')# parse "tag_name": "v0.1.2"
    if pos >= 0:
        begin = text.index('"', pos+10) + 2
        end = text.index('"', begin)
        latest_version = text[begin:end]
    else:
        raise RuntimeError("Unable to parse release version !")

    # body contains changelog and release info
    pos = text.index("\"body\"")# parse "body": "### Changelog\r\n4.4.1 : fixed bug \r\n"
    if pos >= 0:
        begin = text.index('"', pos+6) + 1
        end = text.index('"', begin)
        body = text[begin:end]
        changelog = "\n".join(body.split("\\r\\n"))

    return latest_version, changelog


def is_later_than(versionA, versionB):
    """ check if versionA is later than versionB (versions must be in x.x.x format) """
    listA = versionA.split(".")
    listB = versionB.split(".")
    for i in range(3):
        if int(listA[i]) > int(listB[i]):
            return True

    return False


def wait(millisec):
    loop = QEventLoop()
    QTimer.singleShot(millisec, loop.quit)
    loop.exec()

