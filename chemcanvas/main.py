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
from app_data import App


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
        self.tool_actions = []
        self.subtool_actions = []
        self.subtool_separators = []
        self.subtool_actiongroups = []

        toolGroup = QActionGroup(self.toolBar)
        toolGroup.triggered.connect(self.onToolClick)
        for (name, title, icon, subtools) in tools_template:
            action = self.toolBar.addAction(QIcon(icon), title)
            action.setCheckable(True)
            toolGroup.addAction(action)
            self.tool_actions.append(action)

        self.filename = ''
        # Show Window
        self.settings = QtCore.QSettings("chemcanvas", "chemcanvas", self)
        width = int(self.settings.value("WindowWidth", 1040))
        height = int(self.settings.value("WindowHeight", 710))
        self.resize(width, height)

        self.paper = Paper(0,0,600,600, self.graphicsView)
        App.paper = self.paper

        bond_action = self.tool_actions[tools_list.index("bond")]
        bond_action.setChecked(True)
        self.onToolClick(bond_action)

        self.show()

    def onToolClick(self, action):
        if App.tool:
            App.tool.clear()
        # remove previously added subtoolbar items
        for toolGroup in self.subtool_actiongroups:
            for item in toolGroup.actions():
                self.subToolBar.removeAction(item)
                toolGroup.removeAction(item)
                item.deleteLater()
            toolGroup.deleteLater()
        # remove separators
        for item in self.subtool_separators:
            self.subToolBar.removeAction(item)
            item.deleteLater()

        self.subtool_actions.clear()
        self.subtool_separators.clear()
        self.subtool_actiongroups.clear()

        tool_template = tools_template[self.tool_actions.index(action)]
        App.tool = newToolFromName(tool_template[0])
        selected_subtools = [App.tool.modes[i][mode] for (i,mode) in enumerate(App.tool.selected_modes)]
        # create subtools
        for subtools in tool_template[3]:
            toolGroup = QActionGroup(self.subToolBar)

            for (name, title, icon) in subtools:
                action = self.subToolBar.addAction(QIcon(icon), title)
                action.setCheckable(True)
                if name in selected_subtools:
                    action.setChecked(True)
                toolGroup.addAction(action)
                self.subtool_actions.append(action)

            self.subtool_actiongroups.append(toolGroup)
            toolGroup.triggered.connect(self.onSubToolClick)
            self.subtool_separators.append(self.subToolBar.addSeparator())


    def onSubToolClick(self, action):
        index = self.subtool_actions.index(action)
        App.tool.selectMode(index)

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
