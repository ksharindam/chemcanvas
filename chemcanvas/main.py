#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>

import sys, os

sys.path.append(os.path.dirname(__file__)) # for enabling python 2 like import

from __init__ import __version__
from ui_mainwindow import Ui_MainWindow

from paper import Paper
from tools import *
from app_data import App, find_icon
from import_export import readCcmlFile, writeCcml
from template_manager import TemplateManager
from smiles import SmilesReader, SmilesGenerator
from coords_generator import calculate_coords

from PyQt5.QtCore import Qt, QSettings, QEventLoop, QTimer, QSize
from PyQt5.QtGui import QIcon, QPainter

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGridLayout, QGraphicsView, QSpacerItem,
    QFileDialog, QAction, QActionGroup, QToolButton, QInputDialog
)

import xml.dom.minidom as Dom


DEBUG = False
def debug(*args):
    if DEBUG: print(*args)

SCREEN_DPI = 100
HOMEDIR = os.path.expanduser("~")


class Window(QMainWindow, Ui_MainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.templateGrid = QGridLayout(self.rightFrame)
        # this improves drawing speed
        self.graphicsView.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        # makes small circles and objects smoother
        self.graphicsView.setRenderHint(QPainter.Antialiasing, True)
        self.paper = Paper(0,0,600,600, self.graphicsView)
        App.paper = self.paper

        # for settings bar, i.e below main toolbar
        self.settingsbar_separators = []
        self.settingsbar_actiongroups = []

        # add toolbar actions
        self.toolGroup = QActionGroup(self.toolBar)# also needed to manually check the buttons
        self.toolGroup.triggered.connect(self.onToolClick)
        for tool_name in toolbar_tools:
            title, icon_name = tools_template[tool_name]
            action = self.toolBar.addAction(QIcon(":/icons/%s.png"%icon_name), title)
            action.name = tool_name
            action.setCheckable(True)
            self.toolGroup.addAction(action)

        # create atomtool actions
        self.vertexGroup = QActionGroup(self.leftToolBar)
        self.vertexGroup.triggered.connect(self.onVertexTypeChange)
        for atom_symbol in atomtools_template:
            action = self.leftToolBar.addAction(atom_symbol)
            action.key = "atom"
            action.value = atom_symbol
            action.setCheckable(True)
            self.vertexGroup.addAction(action)

        self.leftToolBar.addSeparator()

        # add funcional groups
        for group_formula in grouptools_template:
            action = self.leftToolBar.addAction("-"+group_formula)
            action.key = "atom"
            action.value = group_formula
            action.setCheckable(True)
            self.vertexGroup.addAction(action)

        # add templates
        self.templateGroup = QActionGroup(self.rightFrame)
        self.templateGroup.triggered.connect(self.onTemplateChange)
        App.template_manager = TemplateManager()
        for template_name in App.template_manager.template_names:
            template = App.template_manager.templates[template_name]
            action = QAction(template.name, self)
            action.key = "template"
            action.value = template.name
            action.setCheckable(True)
            self.templateGroup.addAction(action)
            # create toolbutton
            btn = QToolButton(self.rightFrame)
            btn.setDefaultAction(action)
            self.templateGrid.addWidget(btn)
            icon_path = find_icon(template.name)
            if icon_path:
                action.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(32,32))
                #btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.templateGrid.setRowStretch(self.templateGrid.rowCount(), 1)

        # select structure tool
        self.selectToolByName("StructureTool")
        App.template_manager.selectTemplate(toolsettings.getValue("TemplateTool","template"))

        # Connect signals
        self.actionQuit.triggered.connect(self.close)
        self.actionOpen.triggered.connect(self.openFile)
        self.actionSave.triggered.connect(self.saveFile)
        self.actionUndo.triggered.connect(self.undo)
        self.actionRedo.triggered.connect(self.redo)
        self.actionGenSmiles.triggered.connect(self.generateSmiles)
        self.actionReadSmiles.triggered.connect(self.readSmiles)

        # Load settings and Show Window
        self.settings = QSettings("chemcanvas", "chemcanvas", self)
        width = int(self.settings.value("WindowWidth", 840))
        height = int(self.settings.value("WindowHeight", 540))

        # other things to initialize
        self.filename = ''

        # show window
        self.resize(width, height)
        self.show()


    def onToolClick(self, action):
        """ a slot which is called when tool is clicked """
        self.setToolByName(action.name)

    def selectToolByName(self, tool_name):
        if App.tool and App.tool.name == tool_name:
            return
        for action in self.toolGroup.actions():
            if action.name == tool_name:
                action.setChecked(True)
                break
        self.setToolByName(tool_name)

    def setToolByName(self, tool_name):
        if App.tool:
            if App.tool.name == tool_name:# already selected
                return
            App.tool.clear()
        App.tool = tool_class_dict[tool_name]()
        self.createSettingsBar(tool_name)

    def clearSettingsBar(self):
        # remove previously added subtoolbar items
        for toolGroup in self.settingsbar_actiongroups:
            for item in toolGroup.actions():
                self.subToolBar.removeAction(item)
                toolGroup.removeAction(item)
                item.deleteLater()
            toolGroup.deleteLater()
        # remove separators
        for item in self.settingsbar_separators:
            self.subToolBar.removeAction(item)
            item.deleteLater()

        self.settingsbar_separators.clear()
        self.settingsbar_actiongroups.clear()

    def createSettingsBar(self, tool_name):
        """ used by setToolByName()"""
        self.clearSettingsBar()
        if not tool_name in settings_template:
            return
        toolsettings.setScope(tool_name)
        groups = settings_template[tool_name]
        # create subtools
        for group_name, templates in groups:
            toolGroup = QActionGroup(self.subToolBar)
            selected_value = toolsettings[group_name]
            for (action_name, title, icon_name) in templates:
                action = self.subToolBar.addAction(QIcon(":/icons/%s.png"%icon_name), title)
                action.key = group_name
                action.value = action_name
                action.setCheckable(True)
                toolGroup.addAction(action)
                if action_name == selected_value:
                    #App.tool.onPropertyChange(action_name, selected_value)
                    action.setChecked(True)

            self.settingsbar_actiongroups.append(toolGroup)
            toolGroup.triggered.connect(self.onSubToolClick)
            self.settingsbar_separators.append(self.subToolBar.addSeparator())

        # among both left and right dock, we want to keep selected only one item.
        # either an atom, or a group or a template
        # When switching to StructureTool, deselect selected template
        if tool_name=="StructureTool":
            selected_template = self.templateGroup.checkedAction()
            if selected_template:
                selected_template.setChecked(False)
            value = toolsettings["atom"]
            for action in self.vertexGroup.actions():
                if action.value == value:
                    action.setChecked(True)
                    break
        elif tool_name=="TemplateTool":
            selected_vertex = self.vertexGroup.checkedAction()
            if selected_vertex:
                selected_vertex.setChecked(False)
            value = toolsettings["template"]
            for action in self.templateGroup.actions():
                if action.value == value:
                    action.setChecked(True)
                    break


    def onSubToolClick(self, action):
        """ On click on a button on subtoolbar """
        #App.tool.onPropertyChange(action.key, action.value)
        toolsettings[action.key] = action.value

    def onVertexTypeChange(self, action):
        """ called when one of the item in vertexGroup is clicked """
        toolsettings.setValue("StructureTool", action.key, action.value)
        self.selectToolByName("StructureTool")

    def onTemplateChange(self, action):
        """ called when one of the item in templateGroup is clicked """
        toolsettings.setValue("TemplateTool", action.key, action.value)
        self.selectToolByName("TemplateTool")
        App.template_manager.selectTemplate(action.value)

    # ------------------------ FILE -------------------------

    def openFile(self, filename=None):
        if not filename:
            filename = "mol.xml"
        objects = readCcmlFile(filename)
        for obj in objects:
            App.paper.addObject(obj)
        sorted_objects = sorted(objects, key=lambda x : x.redraw_priority)
        [obj.drawSelfAndChildren() for obj in sorted_objects]

    def saveFile(self, filename=None):
        if not filename:
            filename = "mol.xml"
        writeCcml(App.paper, filename)

    def readTemplates(self):
        for mol in template_mols:
            icon = App.getIcon(mol.name)
            btn = QToolButton(icon, mol.name)
            self.templateGrid.addWidget(btn)

    # ------------------------ EDIT -------------------------

    def undo(self):
        App.paper.undo()

    def redo(self):
        App.paper.redo()

    # ---------------------  Chemistry ----------------------------

    def generateSmiles(self):
        smiles_gen = SmilesGenerator()
        mols = [obj for obj in App.paper.objects if obj.object_type=="Molecule"]
        print(smiles_gen.generate(mols[-1]))

    def readSmiles(self):
        text, ok = QInputDialog.getText(self, "Read SMILES", "Enter SMILES :")
        if not ok:
            return
        reader = SmilesReader()
        mol = reader.read(text)
        if not mol:
            return
        calculate_coords(mol, bond_length=1.0, force=1)
        App.paper.addObject(mol)
        mol.drawSelfAndChildren()

    # ------------------------- Others -------------------------------

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
