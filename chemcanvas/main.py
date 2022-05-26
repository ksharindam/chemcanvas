#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
from PyQt5 import QtCore
from PyQt5.QtGui import ( QPainter, QColor, QPixmap, QImage, QIcon, QStandardItem,
    QIntValidator, QStandardItemModel, QPainterPath
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout, QLabel,
    QFileDialog, QInputDialog, QAction, QActionGroup, QLineEdit,
    QComboBox, QMessageBox,
    QDialog
)

sys.path.append(os.path.dirname(__file__)) # for enabling python 2 like import

from __init__ import __version__
from ui_mainwindow import Ui_MainWindow

from paper import Paper
from tools import *


DEBUG = False
def debug(*args):
    if DEBUG: print(*args)

SCREEN_DPI = 100
HOMEDIR = os.path.expanduser("~")


class Window(QMainWindow, Ui_MainWindow):
    #renderRequested = QtCore.pyqtSignal(int, float)

    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.actionQuit.triggered.connect(self.close)

        # add toolbar actions
        self.actions_list = []

        toolGroup = QActionGroup(self.toolBar)
        toolGroup.triggered.connect(self.onToolChange)
        for (name, title, icon) in tools_template:
            action = self.toolBar.addAction(QIcon(icon), title)
            action.setCheckable(True)
            toolGroup.addAction(action)
            self.actions_list.append(action)

        self.filename = ''
        # Show Window
        self.settings = QtCore.QSettings("chemcanvas", "chemcanvas", self)
        width = int(self.settings.value("WindowWidth", 1040))
        height = int(self.settings.value("WindowHeight", 710))
        self.resize(width, height)

        self.paper = Paper(0,0,600,600, self.graphicsView)

        bond_action = self.actions_list[tools_list.index("bond")]
        bond_action.setChecked(True)
        self.onToolChange(bond_action)

        self.show()

    def onToolChange(self, action):
        name = tools_list[self.actions_list.index(action)]
        #print("tool changed : " + name)
        self.tool = newToolFromName(name)
        self.paper.setTool(self.tool)
        self.tool.setPaper(self.paper)

    def closeEvent(self, ev):
        """ Save all settings on window close """
        return QMainWindow.closeEvent(self, ev)




def wait(millisec):
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(millisec, loop.quit)
    loop.exec_()



def main():
    app = QApplication(sys.argv)
    win = Window()
#    if len(sys.argv)>1 and os.path.exists(os.path.abspath(sys.argv[-1])):
#        win.loadFile(os.path.abspath(sys.argv[-1]))
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
