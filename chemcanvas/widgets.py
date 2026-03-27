# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>

# This module contains some custom widgets and dialogs

import os, re
import platform
import urllib.request
from shutil import which

from PyQt5.QtCore import (Qt, pyqtSignal, QPoint, QEventLoop, QTimer, QUrl,
    QSize, QRect, QObject)
from PyQt5.QtGui import (QPainter, QPixmap, QColor, QDesktopServices, QPen, QIcon,
    QFont, QTextCharFormat, QTextCursor)

from PyQt5.QtWidgets import ( QApplication, QDialog, QDialogButtonBox, QGridLayout,
    QLineEdit, QPushButton, QToolButton, QLabel, QApplication, QSizePolicy,
    QTextEdit, QWidget, QHBoxLayout, QLayout,
    QComboBox, QScrollArea, QVBoxLayout, QStyle,
    QWidgetAction, QRadioButton, QColorDialog, QFontComboBox
)

from __init__ import __version__
from app_data import get_icon, basic_colors



class PaletteWidget(QLabel):
    """ Color Palette that holds many colors"""
    colorSelected = pyqtSignal(tuple)# in (r, g, b) format

    def __init__(self, parent, colors=None, cols=6):
        QLabel.__init__(self, parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.colors = colors or basic_colors
        self.color = None # (r,g,b) tuple
        self.cols = cols
        self.rows = -(len(self.colors) // (-cols))# math.ceil() alternative
        self.cell_size = 22
        self.curr_index = 0
        self.pixmap = QPixmap(self.cols*self.cell_size, self.rows*self.cell_size)
        self.drawPalette()

    def setColor(self, color):
        """ color is (r,g,b) tuple. when color==None no color is selected """
        if color:
            for i,clr in enumerate(self.colors):
                if QColor(clr)==QColor(*color):
                    self.color = color
                    self.drawPalette()
                    return
        self.color = None
        self.drawPalette()


    def drawPalette(self):
        cols, rows, cell_size = self.cols, self.rows, self.cell_size
        curr_color = self.color and QColor(*self.color) or None
        self.pixmap.fill()
        painter = QPainter(self.pixmap)
        for i,color in enumerate(self.colors):
            painter.setBrush(QColor(color))
            x, y = (i%cols)*cell_size, (i//cols)*cell_size
            if QColor(color)==curr_color:
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
        color = QColor(self.colors[index]).getRgb()[:3]
        self.setColor(color)
        self.colorSelected.emit(color)


class ColorChooserWidget(QWidget):

    colorSelected = pyqtSignal(tuple)

    def __init__(self, parent=None, colors=None):
        QWidget.__init__(self, parent)
        layout = QGridLayout(self)
        self.noColorBtn = QRadioButton("None", self)
        self.palette = PaletteWidget(self, colors)
        self.moreColorsBtn = QPushButton("More Colors...", self)
        layout.addWidget(self.noColorBtn, 0,0,1,1)
        layout.addWidget(self.palette, 1,0,1,1)
        layout.addWidget(self.moreColorsBtn, 2,0,1,1)
        # connect signals
        self.palette.colorSelected.connect(self.onColorSelect)
        self.noColorBtn.clicked.connect(self.onNoneButtonClick)
        self.moreColorsBtn.clicked.connect(self.onMoreColorsBtnClick)
        self.color = None

    def hideNoneButton(self):
        self.noColorBtn.hide()

    def setColor(self, color):
        self.color = color
        self.noColorBtn.setChecked(color==None)
        self.palette.setColor(color)

    def onColorSelect(self, color):
        self.setColor(color)
        self.colorSelected.emit(color or tuple())# can not emit None

    def onNoneButtonClick(self):
        self.onColorSelect(None)

    def onMoreColorsBtnClick(self):
        color = self.color or (0,0,0)
        color = QColorDialog.getColor(QColor(*color), self)
        if color.isValid():
            self.onColorSelect(color.getRgb()[:3])


class ColorButton(QToolButton):
    def __init__(self, parent, colors=None):
        QToolButton.__init__(self, parent)
        self.setPopupMode(QToolButton.InstantPopup)
        self.colorChooserPopup = ColorChooserWidget(self, colors)
        self.colorChooserPopup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        action = QWidgetAction(self)
        action.setDefaultWidget(self.colorChooserPopup)
        self.addAction(action)
        self.colorChooserPopup.colorSelected.connect(self.setIconColor)
        self.colorChooserPopup.colorSelected.connect(action.trigger)# to close popup

    def popup(self):
        return self.colorChooserPopup

    def setColor(self, color):
        self.setIconColor(color)
        self.popup().setColor(color)

    def setIconColor(self, color):
        fill_color = color or (255,255,255)
        pm = QPixmap(22,22)
        pm.fill(QColor(*fill_color))
        painter = QPainter(pm)
        painter.drawRect(0,0,21,21)
        if not color:
            painter.drawLine(0,0,21,21)
            painter.drawLine(0,21,21,0)
        painter.end()
        self.setIcon(QIcon(pm))

# ---------------------- Template Button Widget -------------------

class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)

        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        available_rect = rect.adjusted(+m.left(), +m.top(), -m.right(), -m.bottom())
        x = available_rect.x()
        y = available_rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Orientation.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > available_rect.right() and line_height > 0:
                x = available_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()



# ---------------------- Template Button Widget -------------------
class PixmapButton(QLabel):
    """ displays a pixmap and works as button """
    clicked = pyqtSignal(QLabel)
    doubleClicked = pyqtSignal()

    def __init__(self, parent):
        QLabel.__init__(self, parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.selected = False
        self._pixmap = None
        self._action = None
        self._mouse_press_pos = None

    def setPixmap(self, pixmap):
        if pixmap.isNull():
            return
        self._pixmap = pixmap
        self.setSelected(self.selected)

    def defaultAction(self):
        return self._action

    def setDefaultAction(self, action):
        self._action = action
        action.toggled.connect(self.setSelected)

    def setSelected(self, select):
        self.selected = select
        if select:
            pm = self._pixmap.copy()
            painter = QPainter(pm)
            painter.setPen(QPen(Qt.blue, 2))
            painter.drawRect(1,1, pm.width()-2, pm.height()-2)
            painter.end()
            QLabel.setPixmap(self, pm)
        else:
            QLabel.setPixmap(self, self._pixmap)

    def mousePressEvent(self, ev):
        if self._action:
            self._action.trigger()
        self._mouse_press_pos = ev.pos()
        self.clicked.emit(self)

    #def mouseReleaseEvent(self, ev):
    #    if ev.pos()==self._mouse_press_pos:
    #        self.clicked.emit()

    def mouseDoubleClickEvent(self, ev):
        self.doubleClicked.emit()



#  -------------------------- Search Box ---------------------------

class SearchBox(QLineEdit):
    """ A LineEdit with search icon and clear button """
    escapePressed = pyqtSignal()
    tabPressed = pyqtSignal()
    arrowPressed = pyqtSignal(int)

    def __init__(self, parent):
        QLineEdit.__init__(self, parent)
        self.setStyleSheet("QLineEdit { padding: 2 22 2 22;}")
        # Create button for showing search icon
        self.searchButton = QToolButton(self)
        self.searchButton.setStyleSheet("QToolButton { border: 0; background: transparent; width: 16px; height: 16px; }")
        self.searchButton.setIcon(get_icon(':/icons/search'))
        # Create button for showing clear icon
        self.clearButton = QToolButton(self)
        self.clearButton.setStyleSheet("QToolButton { border: 0; background: transparent; width: 16px; height: 16px; }")
        self.clearButton.setIcon(get_icon(':/icons/clear'))
        self.clearButton.setCursor(Qt.PointingHandCursor)
        self.clearButton.clicked.connect(self.clear)

    def resizeEvent(self, ev):
        self.searchButton.move(3,3)
        self.clearButton.move(self.width()-22,3)
        QLineEdit.resizeEvent(self, ev)

    def event(self, ev):
        """This functions is used to handle tab key press.
        Because, tab press event is not received by keyPressEvent() """
        if ev.type()==ev.KeyPress and ev.key()==Qt.Key_Tab:
            self.tabPressed.emit()
            return True
        return QLineEdit.event(self, ev)

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Delete:
            self.clear()
            return ev.accept()
        elif ev.key() == Qt.Key_Escape:
            self.escapePressed.emit()
        elif ev.key() in (Qt.Key_Up, Qt.Key_Down):
            self.arrowPressed.emit(ev.key())
        QLineEdit.keyPressEvent(self, ev)



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
    """ Dialog for checking for updates manually """
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Check for Update")
        layout = QGridLayout(self)
        currentVersionLabel = QLabel("Current Version : %s"%__version__, self)
        self.latestVersionLabel = QLabel("Latest Release : x.x.x", self)
        self.textView = QTextEdit(self)
        self.textView.setReadOnly(True)
        self.okBtn = QPushButton("Check for Update", self)
        closeBtn = QPushButton("Cancel", self)
        buttonBox = QWidget(self)
        buttonLayout = QHBoxLayout(buttonBox)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.okBtn)
        buttonLayout.addWidget(closeBtn)

        layout.addWidget(currentVersionLabel, 0,0,1,1)
        layout.addWidget(self.latestVersionLabel, 1,0,1,1)
        layout.addWidget(self.textView, 2,0,1,1)
        layout.addWidget(buttonBox, 3,0,1,1)

        closeBtn.clicked.connect(self.reject)
        self.okBtn.clicked.connect(self.onOkBtnClick)

        self.textView.hide()
        self.latest_version = ""

    def enlarge(self):
        """ show textView and enlarge window and place to center """
        self.textView.show()
        self.okBtn.setEnabled(False)# will be enabled if latest version found
        self.resize(500,300)
        wait(100)# let resize take effect


    def onOkBtnClick(self):
        if self.latest_version:
            return self.download()
        # check for update
        self.textView.setPlainText("Checking for Update...")
        self.move(self.pos() - QPoint(int((500-self.width())/2),
                                      int((300-self.height())/2)))# place center
        self.enlarge()

        try:
            latest_version, changelog = latest_version_info("ksharindam/chemcanvas")
        except RuntimeError as e:
            self.textView.setPlainText(str(e))
            self.okBtn.setEnabled(True)
            return

        if latest_version:
            self.latestVersionLabel.setText("Latest Release : %s"%latest_version)

        if is_later_than(latest_version, __version__):# latest version is available
            self.latest_version = latest_version
            self.changelog = changelog
            self.onNewVersionAvailable()
        else:
            self.textView.setPlainText("You are already using the latest version")


    def onNewVersionAvailable(self):
        self.latestVersionLabel.setText("Latest Release : %s"%self.latest_version)
        self.textView.setPlainText(self.changelog)
        self.okBtn.setText("Download")
        self.okBtn.setEnabled(True)


    def download(self):
        filename = None
        if platform.system()=="Windows":
            filename = "ChemCanvas.exe"
        elif platform.system()=="Linux":
            if which("dpkg") and "APPIMAGE" not in os.environ:
                filename = "chemcanvas_all.deb"
            elif platform.machine() in ("aarch64", "x86_64"):
                filename = "ChemCanvas-%s.AppImage" % platform.machine()
        if filename:
            addr = "https://github.com/ksharindam/chemcanvas/releases/latest/download/%s" % filename
            QDesktopServices.openUrl(QUrl(addr))
            return
        # platform not supported, or may be could not detect properly
        addr = "https://github.com/ksharindam/chemcanvas/releases/latest"
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
    try:
        listA = versionA.split(".")
        listB = versionB.split(".")
        for i in range(3):
            a, b = int(listA[i]), int(listB[i])
            if a > b:
                return True
            elif a < b:
                return False
        return False
    except:
        return False


class UpdateChecker(QObject):
    """ used as worker object to check for update in background in separate thread """
    # latest_version is empty when update check fails
    updateCheckFinished = pyqtSignal(str,str)# str latest_version, str changelog
    def __init__(self, current_version):
        QObject.__init__(self)
        self.current_version = current_version

    def checkForUpdate(self):
        latest_version, changelog = "", ""
        try:
            latest_version, changelog = latest_version_info("ksharindam/chemcanvas")
            if is_later_than(latest_version, self.current_version):
                self.updateCheckFinished.emit(latest_version, changelog)
            else:
                self.updateCheckFinished.emit(self.current_version, "")
        except RuntimeError as e:
            #print(str(e))
            self.updateCheckFinished.emit("","")


class ErrorDialog(QDialog):
    def __init__(self, parent, title, description):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Error !")
        self.resize(480,320)
        layout = QVBoxLayout(self)
        titleContainer = QWidget(self)
        titleLayout = QHBoxLayout(titleContainer)
        titleLayout.setContentsMargins(0,0,0,0)
        iconLabel = QLabel(titleContainer)
        pm = iconLabel.style().standardIcon(QStyle.SP_MessageBoxWarning).pixmap(32)
        iconLabel.setPixmap(pm)
        label = QLabel(title, titleContainer)
        titleLayout.addWidget(iconLabel)
        titleLayout.addWidget(label)
        titleLayout.addStretch()
        self.textView = QTextEdit(self)
        self.textView.setReadOnly(True)
        self.textView.setPlainText(description)
        copyBtn = QPushButton("Copy", self)
        closeBtn = QPushButton("Close", self)
        # buttonbox
        buttonBox = QWidget(self)
        buttonLayout = QHBoxLayout(buttonBox)
        buttonLayout.setContentsMargins(0,0,0,0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(copyBtn)
        buttonLayout.addWidget(closeBtn)
        # layout widgets
        layout.addWidget(titleContainer)
        layout.addWidget(self.textView)
        layout.addWidget(buttonBox)

        copyBtn.clicked.connect(self.copyText)
        closeBtn.clicked.connect(self.reject)

    def copyText(self):
        text = self.textView.toPlainText()
        QApplication.clipboard().setText(text)


def wait(millisec):
    loop = QEventLoop()
    QTimer.singleShot(millisec, loop.quit)
    loop.exec()




class TextEdit(QDialog):
    """ Text editor for TextTool """
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        layout = QGridLayout(self)
        self.formattingBtnContainer = QWidget(self)
        formattingLayout = QHBoxLayout(self.formattingBtnContainer)
        formattingLayout.setSpacing(0)
        formattingLayout.setContentsMargins(0,0,0,0)
        self.boldBtn = QToolButton(self)
        self.boldBtn.setIconSize(QSize(22,22))
        self.boldBtn.setIcon(QIcon(":/icons/bold.png"))
        self.boldBtn.setToolTip("Bold")
        self.boldBtn.setCheckable(True)
        self.italicBtn = QToolButton(self)
        self.italicBtn.setIconSize(QSize(22,22))
        self.italicBtn.setIcon(QIcon(":/icons/italic.png"))
        self.italicBtn.setToolTip("Italic")
        self.italicBtn.setCheckable(True)
        self.underlineBtn = QToolButton(self)
        self.underlineBtn.setIconSize(QSize(22,22))
        self.underlineBtn.setIcon(QIcon(":/icons/underline.png"))
        self.underlineBtn.setToolTip("Underline")
        self.underlineBtn.setCheckable(True)
        self.subscriptBtn = QToolButton(self)
        self.subscriptBtn.setIconSize(QSize(22,22))
        self.subscriptBtn.setIcon(QIcon(":/icons/subscript.png"))
        self.subscriptBtn.setToolTip("Subscript")
        self.subscriptBtn.setCheckable(True)
        self.superscriptBtn = QToolButton(self)
        self.superscriptBtn.setIconSize(QSize(22,22))
        self.superscriptBtn.setIcon(QIcon(":/icons/superscript.png"))
        self.superscriptBtn.setToolTip("Superscript")
        self.superscriptBtn.setCheckable(True)
        self.formulaBtn = QToolButton(self)
        self.formulaBtn.setIconSize(QSize(50,22))
        self.formulaBtn.setIcon(QIcon(":/icons/formula.png"))
        self.formulaBtn.setToolTip("Subscript Numbers")
        self.textEdit = QTextEdit(self)
        self.symbolContainer = QWidget(self)
        symbolLayout = QGridLayout(self.symbolContainer)
        symbolLayout.setSpacing(0)
        symbolLayout.setContentsMargins(0,0,0,0)
        symbols = ["°", "Δ", "α", "β", "γ", "δ", "λ", "μ", "ν", "π", "σ", "‡"]
        for i,symbol in enumerate(symbols):
            btn = QToolButton(self.symbolContainer)
            btn.setText(symbol)
            btn.clicked.connect(self.onSymbolClick)
            symbolLayout.addWidget(btn, i//2, i%2, 1,1)
        # layout toplevel widgets
        layout.addWidget(self.formattingBtnContainer, 0,1,1,1)
        layout.addWidget(self.symbolContainer, 1,0,1,1)
        layout.addWidget(self.textEdit, 1,1,1,1)
        # layout formattings buttons
        for widget in (self.boldBtn, self.italicBtn, self.underlineBtn,
                        self.subscriptBtn, self.superscriptBtn, self.formulaBtn):
            formattingLayout.addWidget(widget)
        # connect signals
        self.boldBtn.clicked.connect(self.toggleBold)
        self.italicBtn.clicked.connect(self.toggleItalic)
        self.underlineBtn.clicked.connect(self.toggleUnderline)
        self.subscriptBtn.clicked.connect(self.toggleSubscript)
        self.superscriptBtn.clicked.connect(self.toggleSuperscript)
        self.formulaBtn.clicked.connect(self.toggleFormula)
        self.textEdit.currentCharFormatChanged.connect(self.onCharFormatChange)
        self.textEdit.setFocus(True)

    def onSymbolClick(self):
        self.textEdit.insertPlainText(self.sender().text())

    def onCharFormatChange(self, fmt):
        self.boldBtn.setChecked(fmt.fontWeight()==QFont.Bold)
        self.italicBtn.setChecked(fmt.fontItalic())
        self.underlineBtn.setChecked(fmt.fontUnderline())
        self.subscriptBtn.setChecked(fmt.verticalAlignment()==QTextCharFormat.AlignSubScript)
        self.superscriptBtn.setChecked(fmt.verticalAlignment()==QTextCharFormat.AlignSuperScript)

    def toggleBold(self):
        fmt = self.textEdit.textCursor().charFormat()
        weight = QFont.Bold if fmt.fontWeight()<QFont.Bold else QFont.Normal
        self.textEdit.setFontWeight(weight)

    def toggleItalic(self):
        fmt = self.textEdit.textCursor().charFormat()
        self.textEdit.setFontItalic(not fmt.fontItalic())

    def toggleUnderline(self):
        fmt = self.textEdit.textCursor().charFormat()
        self.textEdit.setFontUnderline(not fmt.fontUnderline())

    def toggleSubscript(self):
        fmt = self.textEdit.textCursor().charFormat()
        if fmt.verticalAlignment()==QTextCharFormat.AlignSubScript:
            fmt.setVerticalAlignment(QTextCharFormat.AlignNormal)
        else:
            fmt.setVerticalAlignment(QTextCharFormat.AlignSubScript)
        self.textEdit.setCurrentCharFormat(fmt)

    def toggleSuperscript(self):
        fmt = self.textEdit.textCursor().charFormat()
        if fmt.verticalAlignment()==QTextCharFormat.AlignSuperScript:
            fmt.setVerticalAlignment(QTextCharFormat.AlignNormal)
        else:
            fmt.setVerticalAlignment(QTextCharFormat.AlignSuperScript)
        self.textEdit.setCurrentCharFormat(fmt)

    def toggleFormula(self):
        cur = self.textEdit.textCursor()
        if cur.hasSelection():
            text = cur.selectedText()
            start = cur.selectionStart()
        else:
            text = self.textEdit.toPlainText()
            start = 0
        # [( subscript numbers next to alphabet or bracket
        for m in re.finditer("([A-Za-z)\]])(\d+)", text):
            cur.setPosition(start+m.end() - len(m.group(2)))
            cur.setPosition(start+m.end(), QTextCursor.KeepAnchor)
            fmt =  QTextCharFormat()
            fmt.setVerticalAlignment(QTextCharFormat.AlignSubScript)
            cur.mergeCharFormat(fmt)

    def setText(self, text):
        """ set html text """
        self.textEdit.setHtml(text)
        self.textEdit.moveCursor(QTextCursor.End)

    def getText(self):
        """ get html text """
        text = self.textEdit.toPlainText()
        result = ""
        cur = self.textEdit.textCursor()
        prev_fmt = None
        prev_bold, prev_italic, prev_underline = False, False, False
        prev_v_align = QTextCharFormat.AlignNormal
        for i in range(len(text)):
            cur.setPosition(i+1)
            start_tags = []
            end_tags = []
            if  (fmt := cur.charFormat()) != prev_fmt:
                # bold
                if (bold := fmt.fontWeight()==QFont.Bold) != prev_bold:
                    if bold:
                        start_tags.append("<b>")
                    else:
                        end_tags.append("</b>")
                    prev_bold = bold
                # italic
                if (italic := fmt.fontItalic()) != prev_italic:
                    if italic:
                        start_tags.append("<i>")
                    else:
                        end_tags.append("</i>")
                    prev_italic = italic
                # underline
                if (underline := fmt.fontUnderline()) != prev_underline:
                    if underline:
                        start_tags.append("<u>")
                    else:
                        end_tags.append("</u>")
                    prev_underline = underline
                # subscript and superscript
                if (v_align := fmt.verticalAlignment()) != prev_v_align:
                    if prev_v_align==QTextCharFormat.AlignSubScript:
                        end_tags.append("</sub>")
                    elif prev_v_align==QTextCharFormat.AlignSuperScript:
                        end_tags.append("</sup>")
                    if v_align==QTextCharFormat.AlignSubScript:
                        start_tags.append("<sub>")
                    elif v_align==QTextCharFormat.AlignSuperScript:
                        start_tags.append("<sup>")
                    prev_v_align = v_align
            prev_fmt = fmt
            char = text[i].replace("<", "&lt;").replace(">", "&gt;")
            result += "".join(end_tags) + "".join(start_tags) + char
        # close tags at the end
        if len(text):
            if prev_bold:
                result += "</b>"
            if prev_italic:
                result += "</i>"
            if prev_underline:
                result += "</u>"
            if prev_v_align==QTextCharFormat.AlignSubScript:
                result += "</sub>"
            elif prev_v_align==QTextCharFormat.AlignSuperScript:
                result += "</sup>"
        return result.replace("\n", "<br/>")
