#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>

import sys, os

sys.path.append(os.path.dirname(__file__)) # for enabling python 2 like import

from __init__ import __version__, COPYRIGHT_YEAR, AUTHOR_NAME, AUTHOR_EMAIL
from ui_mainwindow import Ui_MainWindow

from paper import Paper, SvgPaper, draw_graphicsitem
from tools import *
from app_data import App, find_template_icon
from fileformat_ccml import CcmlFormat
from template_manager import TemplateManager
from smiles import SmilesReader, SmilesGenerator
from coords_generator import calculate_coords
from widgets import PaletteWidget, TextBoxDialog


from PyQt5.QtCore import Qt, qVersion, QSettings, QEventLoop, QTimer, QSize, QDir
from PyQt5.QtGui import QIcon, QPainter, QPixmap

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStyleFactory, QGridLayout, QGraphicsView, QSpacerItem,
    QFileDialog, QAction, QActionGroup, QToolButton, QInputDialog,
    QSpinBox, QFontComboBox, QSizePolicy, QLabel, QMessageBox, QSlider, QDialog
)

import io
import platform

DEBUG = False
def debug(*args):
    if DEBUG: print(*args)



class Window(QMainWindow, Ui_MainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        App.window = self

        self.setWindowTitle("ChemCanvas - " + __version__)
        self.setWindowIcon(QIcon(":/icons/color.png"))

        self.vertexGrid = QGridLayout(self.leftFrame)
        self.templateGrid = QGridLayout(self.rightFrame)

        # add zoom icon
        zoom_icon = QLabel(self)
        zoom_icon.setPixmap(QPixmap(":/icons/zoom-in.png"))
        self.statusbar.addPermanentWidget(zoom_icon)
        # add zoom slider
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(1,8)# 25% to 200%
        #slider.setSingleStep(1)# does not work
        self.slider.setPageStep(1)
        self.slider.setValue(4)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setMaximumWidth(100)
        self.statusbar.addPermanentWidget(self.slider)
        self.slider.valueChanged.connect(self.onZoomSliderMoved)
        self.zoomLabel = QLabel("100%", self)
        self.statusbar.addPermanentWidget(self.zoomLabel)

        # setup graphics view
        self.graphicsView.setMouseTracking(True)
        self.graphicsView.setBackgroundBrush(Qt.gray)
        self.graphicsView.setAlignment(Qt.AlignHCenter)
        # this improves drawing speed
        self.graphicsView.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        # makes small circles and objects smoother
        self.graphicsView.setRenderHint(QPainter.Antialiasing, True)
        # create scene
        self.paper = Paper(0,0,826,1169, self.graphicsView)
        App.paper = self.paper

        self.toolBar.setIconSize(QSize(22,22))
        # add main actions
        self.toolBar.addAction(self.actionOpen)
        self.toolBar.addAction(self.actionSave)
        self.toolBar.addAction(self.actionUndo)
        self.toolBar.addAction(self.actionRedo)

        self.toolBar.addSeparator()

        # for settings bar, i.e below main toolbar
        # stores all actions (including QActionGroup and separators) in settingsbar.
        # maps settings_key to QAction which helps to obtain the widget associated to
        # a particular settings key.
        self.settingsbar_actions = {}

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
        atomsLabel = QLabel("Elements :", self)
        self.vertexGrid.addWidget(atomsLabel, 0, 0, 1,4)

        self.vertexGroup = QActionGroup(self.leftFrame)
        self.vertexGroup.triggered.connect(self.onVertexTypeChange)
        for i, atom_symbol in enumerate(atomtools_template):
            action = QAction(atom_symbol, self)
            action.key = "atom"
            action.value = atom_symbol
            action.setCheckable(True)
            self.vertexGroup.addAction(action)
            # create tool button
            btn = QToolButton(self.leftFrame)
            btn.setDefaultAction(action)
            self.vertexGrid.addWidget(btn, 1+i//4, i%4, 1,1)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        #self.vertexLayout.addSeparator()
        groupsLabel = QLabel("Functional Groups :", self)
        self.vertexGrid.addWidget(groupsLabel, 1+i, 0, 1,4)
        i += 2

        # add funcional groups
        for j, group_formula in enumerate(grouptools_template):
            action = QAction("-"+group_formula, self)
            action.key = "group"
            action.value = group_formula
            action.setCheckable(True)
            self.vertexGroup.addAction(action)
            # create tool button
            btn = QToolButton(self.leftFrame)
            btn.setDefaultAction(action)
            row, col = j//2, j%2
            self.vertexGrid.addWidget(btn, i+row, 2*col, 1,2)# each button occupies 2 columns
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # stretch last row, to align buttons to top
        self.vertexGrid.setRowStretch(i+j, 1)

        templatesLabel = QLabel("Templates :", self.rightFrame)
        self.templateGrid.addWidget(templatesLabel, 0, 0, 1,2)
        # add templates
        self.templateGroup = QActionGroup(self.rightFrame)
        self.templateGroup.triggered.connect(self.onTemplateChange)
        App.template_manager = TemplateManager()
        cols = 2
        for i, template_name in enumerate(App.template_manager.template_names):
            template = App.template_manager.templates[template_name]
            action = QAction(template.name, self)
            action.key = "template"
            action.value = template.name
            action.setCheckable(True)
            self.templateGroup.addAction(action)
            # create toolbutton
            btn = QToolButton(self.rightFrame)
            btn.setDefaultAction(action)
            row, col = i//cols+1, i%cols
            self.templateGrid.addWidget(btn, row, col, 1,1)
            icon_path = find_template_icon(template.name)
            if icon_path:
                action.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(32,32))
                #btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.templateGrid.setRowStretch(self.templateGrid.rowCount(), 1)


        # select structure tool
        self.selectToolByName("StructureTool")
        # select template
        if App.template_manager.template_names:
            template_name = App.template_manager.template_names[0]
            toolsettings.setValue("TemplateTool", "template", template_name)
            App.template_manager.selectTemplate(template_name)

        # Connect signals
        self.actionQuit.triggered.connect(self.close)
        self.actionOpen.triggered.connect(self.openFile)
        self.actionSave.triggered.connect(self.saveFile)
        self.actionSaveAs.triggered.connect(self.saveFileAs)
        self.actionPNG.triggered.connect(self.exportAsPNG)
        self.actionSVG.triggered.connect(self.exportAsSVG)

        self.actionUndo.triggered.connect(self.undo)
        self.actionRedo.triggered.connect(self.redo)
        self.actionGenSmiles.triggered.connect(self.generateSmiles)
        self.actionReadSmiles.triggered.connect(self.readSmiles)
        self.actionAbout.triggered.connect(self.showAbout)

        # Load settings and Show Window
        self.settings = QSettings("chemcanvas", "chemcanvas", self)
        width = int(self.settings.value("WindowWidth", 840))
        height = int(self.settings.value("WindowHeight", 540))

        # other things to initialize
        QDir.setCurrent(QDir.homePath())
        self.filename = ''

        # show window
        self.resize(width, height)
        self.show()
        self.graphicsView.horizontalScrollBar().setValue(0)
        self.graphicsView.verticalScrollBar().setValue(0)


    def onZoomSliderMoved(self, val):
        self.graphicsView.resetTransform()
        scale = val*0.25
        self.graphicsView.scale(scale, scale)
        self.zoomLabel.setText("%i%%"%(100*scale))

    def onToolClick(self, action):
        """ a slot which is called when tool is clicked """
        self.setToolByName(action.name)

    def selectToolByName(self, tool_name):
        if App.tool and App.tool.class_name == tool_name:
            return
        for action in self.toolGroup.actions():
            if action.name == tool_name:
                action.setChecked(True)
                break
        self.setToolByName(tool_name)

    def setToolByName(self, tool_name):
        if App.tool:
            if App.tool.class_name == tool_name:# already selected
                return
            App.tool.clear()
        self.clearStatus()
        self.clearSettingsBar()
        toolsettings.setScope(tool_name)
        App.tool = tool_class(tool_name)()
        self.createSettingsBar(tool_name)

    def clearSettingsBar(self):
        # remove previously added subtoolbar items
        for key,item in self.settingsbar_actions.items():
            if isinstance(item, QActionGroup):
                for action in item.actions():
                    self.subToolBar.removeAction(action)
                    item.removeAction(action)
                    action.deleteLater()
            else:
                self.subToolBar.removeAction(item)

            # dont need to delete the associated widget, as the toolbar takes ownership of it.
            item.deleteLater()

        self.settingsbar_actions.clear()


    def createSettingsBar(self, tool_name):
        """ used by setToolByName()"""
        if not tool_name in settings_template:
            return
        groups = settings_template[tool_name]
        # create subtools
        for group_type, group_name, templates in groups:
            if group_type=="ButtonGroup":
                toolGroup = QActionGroup(self.subToolBar)
                selected_value = toolsettings[group_name]
                for (action_name, title, icon_name) in templates:
                    action = self.subToolBar.addAction(QIcon(":/icons/%s.png"%icon_name), title)
                    action.key = group_name
                    action.value = action_name
                    action.setCheckable(True)
                    toolGroup.addAction(action)
                    if action_name == selected_value:
                        action.setChecked(True)

                self.settingsbar_actions[group_name] = toolGroup
                toolGroup.triggered.connect(self.onSubToolClick)
                self.settingsbar_actions[group_name+"_separator"] = self.subToolBar.addSeparator()

            elif group_type=="SpinBox":
                spinbox = QSpinBox() # ToolBar takes ownership of the widget
                spinbox.setRange(*templates)
                spinbox.setValue(toolsettings[group_name])
                spinbox.key = group_name
                action = self.subToolBar.addWidget(spinbox)
                self.settingsbar_actions[group_name] = action
                spinbox.valueChanged.connect(self.onSpinValueChange)

            elif group_type=="FontComboBox":
                widget = QFontComboBox()
                index = widget.findText(toolsettings[group_name])# -1 if not found
                if index >=0:
                    widget.setCurrentIndex(index)
                widget.key = group_name
                action = self.subToolBar.addWidget(widget)
                self.settingsbar_actions[group_name] = action
                widget.currentIndexChanged.connect(self.onFontChange)

            elif group_type=="PaletteWidget":
                widget = PaletteWidget(self.subToolBar, toolsettings["color_index"])
                widget.key = group_name
                action = self.subToolBar.addWidget(widget)
                self.settingsbar_actions[group_name] = action
                widget.colorSelected.connect(self.onColorSelect)

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

    def setCurrentToolProperty(self, key, val):
        """ Used by Tools, set current tool settings value """
        action = self.settingsbar_actions[key]

        if isinstance(action, QActionGroup):
            for action in action.actions():
                if action.value == val:
                    action.setChecked(True)
                    # programmatically checking action will not emit triggered() signal and
                    # will not update settings. So we are doing it here.
                    toolsettings[key] = val
                    return True

        widget = self.subToolBar.widgetForAction(action)

        if isinstance(widget, QSpinBox):
            widget.setValue(val)

        elif isinstance(widget, QFontComboBox):
            index = widget.findText(val)# -1 if not found
            if index >=0:
                widget.setCurrentIndex(index)

        elif isinstance(widget, PaletteWidget):
            widget.setCurrentIndex(val)

        else:
            return False
        return True


    def onSubToolClick(self, action):
        """ On click on a button on subtoolbar """
        App.tool.onPropertyChange(action.key, action.value)
        toolsettings[action.key] = action.value

    def onSpinValueChange(self, val):
        spinbox = self.sender()# get sender of this signal
        App.tool.onPropertyChange(spinbox.key, val)
        toolsettings[spinbox.key] = val

    def onFontChange(self, index):
        combo = self.sender()
        App.tool.onPropertyChange(combo.key, val)
        toolsettings[combo.key] = combo.itemText(index)

    def onColorSelect(self, color):
        """ This is a slot which receives colorSelected() signal from PaletteWidget """
        widget = self.sender()
        App.tool.onPropertyChange(widget.key, color)
        toolsettings[widget.key] = color
        toolsettings["color_index"] = widget.curr_index


    def onVertexTypeChange(self, action):
        """ called when one of the item in vertexGroup is clicked """
        toolsettings.setValue("StructureTool", "atom", action.value)
        self.selectToolByName("StructureTool")
        if action.key=="group":
            self.setCurrentToolProperty("bond_type", "normal")

    def onTemplateChange(self, action):
        """ called when one of the item in templateGroup is clicked """
        toolsettings.setValue("TemplateTool", action.key, action.value)
        self.selectToolByName("TemplateTool")
        App.template_manager.selectTemplate(action.value)


    # ------------------------ FILE -------------------------

    def openFile(self, filename=None):
        # get filename to open
        if filename:
            if not os.path.exists(filename):
                return False
        else:
            filters = ["ChemCanvas Markup Language (*.ccml)"]
            filename, filtr = QFileDialog.getOpenFileName(self, "Open File",
                        self.filename, ";;".join(filters))
            if not filename:
                return False
        # open file
        ccml_reader = CcmlFormat()
        objects = ccml_reader.read(filename)
        if not objects:
            return False
        # On Success
        for obj in objects:
            App.paper.addObject(obj)
            draw_recursively(obj)
        self.filename = filename
        return True

    def saveFile(self, filename=None):
        ccml_writer = CcmlFormat()
        if filename:
            return ccml_writer.write(App.paper.objects, filename)
        elif self.filename:
            return ccml_writer.write(App.paper.objects, self.filename)
        else:
            return self.saveFileAs()


    def getSaveFileName(self, extension):
        if self.filename:
            name, ext = os.path.splitext(self.filename)
        else:
            name = "mol"
        return name + "." + extension


    def saveFileAs(self):
        path = self.getSaveFileName("ccml")
        filters = ["ChemCanvas Markup Language (*.ccml)"]
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        path, ";;".join(filters))
        if not filename:
            return False
        if self.saveFile(filename):
            self.filename = filename
            return True
        return False


    def exportAsPNG(self):
        image = App.paper.getImage()
        if image.isNull():
            return
        path = self.getSaveFileName("png")
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        path, "PNG Image (*.png)")
        if not filename:
            return
        image.save(filename)


    def exportAsSVG(self):
        path = self.getSaveFileName("svg")
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        path, "SVG Image (*.svg)")
        if not filename:
            return

        items = App.paper.get_items_of_all_objects()
        svg_paper = SvgPaper()
        for item in items:
            draw_graphicsitem(item, svg_paper)
        x1,y1, x2,y2 = App.paper.allObjectsBoundingBox()
        x1, y1, x2, y2 = x1-6, y1-6, x2+6, y2+6
        svg_paper.setViewBox(x1,y1, x2-x1, y2-y1)
        svg = svg_paper.getSvg()
        # save file
        with io.open(filename, 'w', encoding='utf-8') as svg_file:
            svg_file.write(svg)


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
        mols = [obj for obj in App.paper.objects if obj.class_name=="Molecule"]
        if not mols:
            self.showStatus("No molecule is drawn ! Please draw a molecule first.")
            return
        smiles_gen = SmilesGenerator()
        smiles = smiles_gen.generate(mols[-1])
        dlg = TextBoxDialog("Generated SMILES :", smiles, self)
        dlg.setWindowTitle("SMILES")
        dlg.exec()

    def readSmiles(self):
        dlg = TextBoxDialog("Enter SMILES :", "", self, mode="input")
        if dlg.exec()!=QDialog.Accepted:
            return
        text = dlg.text()
        reader = SmilesReader()
        mol = reader.read(text)
        if not mol:
            return
        calculate_coords(mol, bond_length=1.0, force=1)
        App.paper.addObject(mol)
        draw_recursively(mol)
        App.paper.save_state_to_undo_stack("Read SMILES")

    # ------------------------- Others -------------------------------

    def showStatus(self, msg):
        self.statusbar.showMessage(msg)

    def clearStatus(self):
        self.statusbar.clearMessage()

    def showAbout(self):
        lines = ("<h1>ChemCanvas</h1>",
            "A Chemical Drawing Tool<br><br>",
            "Version : %s<br>" % __version__,
            "Qt : %s<br>" % qVersion(),
            "Copyright &copy; %s %s &lt;%s&gt;" % (COPYRIGHT_YEAR, AUTHOR_NAME, AUTHOR_EMAIL))
        QMessageBox.about(self, "About ChemCanvas", "".join(lines))

    def closeEvent(self, ev):
        """ Save all settings on window close """
        return QMainWindow.closeEvent(self, ev)



def wait(millisec):
    loop = QEventLoop()
    QTimer.singleShot(millisec, loop.quit)
    loop.exec()




def main():
    app = QApplication(sys.argv)
    # use fusion style on Windows platform
    if platform.system()=="Windows" and "Fusion" in QStyleFactory.keys():
        app.setStyle(QStyleFactory.create("Fusion"))
    # get absolute filename
    if len(sys.argv)>1 and os.path.exists(os.path.abspath(sys.argv[-1])):
        filename = os.path.abspath(sys.argv[-1])
    else:
        filename = ""
    # load window
    win = Window()
    if filename:
        win.openFile(filename)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
