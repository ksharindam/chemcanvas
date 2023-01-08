#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
from PyQt5.QtCore import Qt, QSettings, QEventLoop, QTimer
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
        self.atomtool_actions = []
        self.current_tool_index = tools_list.index(StructureTool)

        toolGroup = QActionGroup(self.toolBar)
        toolGroup.triggered.connect(self.onToolClick)
        for (name, title, icon, subtool_groups) in tools_template:
            action = self.toolBar.addAction(QIcon(icon), title)
            action.setCheckable(True)
            toolGroup.addAction(action)
            self.tool_actions.append(action)

        # create atomtool actions
        atomsGroup = QActionGroup(self.leftToolBar)
        atomsGroup.triggered.connect(self.onAtomChange)
        for atom_symbol in atomtools_template:
            action = self.leftToolBar.addAction(atom_symbol)
            action.setCheckable(True)
            if atom_symbol=="C":
                action.setChecked(True)
            atomsGroup.addAction(action)
            self.atomtool_actions.append(action)

        self.filename = ''
        # Show Window
        self.settings = QSettings("chemcanvas", "chemcanvas", self)
        width = int(self.settings.value("WindowWidth", 1040))
        height = int(self.settings.value("WindowHeight", 710))
        self.resize(width, height)

        self.paper = Paper(0,0,600,600, self.graphicsView)
        App.paper = self.paper

        bond_action = self.tool_actions[self.current_tool_index]
        bond_action.setChecked(True)
        self.onToolClick(bond_action)

        self.show()


    def onToolClick(self, action):
        index = self.tool_actions.index(action)
        self.setToolFromIndex(index)

    def setToolFromIndex(self, index):
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

        tool_template = tools_template[index]
        App.tool = tool_template[0]()
        selected_subtools = [App.tool.selected_mode[category] for category in App.tool.modes.keys()]
        # create subtools
        for subtools_group in tool_template[3]:
            toolGroup = QActionGroup(self.subToolBar)
            for (name, title, icon) in subtools_group:
                action = self.subToolBar.addAction(QIcon(icon), title)
                action.setCheckable(True)
                if name in selected_subtools:
                    action.setChecked(True)
                toolGroup.addAction(action)
                self.subtool_actions.append(action)

            self.subtool_actiongroups.append(toolGroup)
            toolGroup.triggered.connect(self.onSubToolClick)
            self.subtool_separators.append(self.subToolBar.addSeparator())
        self.current_tool_index = index


    def onSubToolClick(self, action):
        """ On click on a button on subtoolbar """
        index = self.subtool_actions.index(action)
        App.tool.selectMode(index)

    def onAtomChange(self, action):
        if type(App.tool) != StructureTool:
            self.tool_actions[tools_list.index(StructureTool)].setChecked(True)
            self.setToolFromIndex(tools_list.index(StructureTool))
        index = self.atomtool_actions.index(action)
        App.tool.selectAtomType(index)

    def closeEvent(self, ev):
        """ Save all settings on window close """
        return QMainWindow.closeEvent(self, ev)




def wait(millisec):
    loop = QEventLoop()
    QTimer.singleShot(millisec, loop.quit)
    loop.exec()



def main():
    app = QApplication(sys.argv)
    win = Window()
#    if len(sys.argv)>1 and os.path.exists(os.path.abspath(sys.argv[-1])):
#        win.loadFile(os.path.abspath(sys.argv[-1]))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
