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
from app_data import App, find_icon
from import_export import readCcmlFile, writeCcml
from template_manager import TemplateManager
from smiles import SmilesReader, SmilesGenerator
from coords_generator import calculate_coords

from PyQt5.QtCore import Qt, qVersion, QSettings, QEventLoop, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QColor

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGridLayout, QGraphicsView, QSpacerItem,
    QFileDialog, QAction, QActionGroup, QToolButton, QInputDialog,
    QSpinBox, QFontComboBox, QSizePolicy, QLabel, QMessageBox, QSlider
)

import io


DEBUG = False
def debug(*args):
    if DEBUG: print(*args)



class Window(QMainWindow, Ui_MainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        App.window = self

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
            action.key = "atom"
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
        self.clearSettingsBar()
        if not tool_name in settings_template:
            return
        toolsettings.setScope(tool_name)
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
                        #App.tool.onPropertyChange(action_name, selected_value)
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
        widget = self.subToolBar.widgetForAction(action)

        if isinstance(widget, QActionGroup):
            for action in widget.actions():
                if action.value == val:
                    action.setChecked(True)
                    break

        elif isinstance(widget, QSpinBox):
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
        #App.tool.onPropertyChange(action.key, action.value)
        toolsettings[action.key] = action.value

    def onSpinValueChange(self, val):
        spinbox = self.sender()# get sender of this signal
        toolsettings[spinbox.key] = val

    def onFontChange(self, index):
        combo = self.sender()
        toolsettings[combo.key] = combo.itemText(index)

    def onColorSelect(self, color):
        """ This is a slot which receives colorSelected() signal from PaletteWidget """
        widget = self.sender()
        toolsettings[widget.key] = color
        toolsettings["color_index"] = widget.curr_index


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
        # get filename to open
        if filename:
            if not os.path.exists(filename):
                return False
        else:
            filters = ["X-Markup Language (*.xml)", "ChemCanvas Markup Language (*.ccml)"]
            filename, filtr = QFileDialog.getOpenFileName(self, "Open File",
                        self.filename, ";;".join(filters))
            if not filename:
                return False
        # open file
        objects = readCcmlFile(filename)
        if not objects:
            return False
        # On Success
        for obj in objects:
            App.paper.addObject(obj)
            draw_recursively(obj)
        self.filename = filename
        return True

    def saveFile(self, filename=None):
        if filename:
            return writeCcml(App.paper, filename)
        elif self.filename:
            return writeCcml(App.paper, self.filename)
        else:
            return self.saveFileAs()

    def saveFileAs(self):
        path = self.filename or "mol.xml"
        filters = ["X-Markup Language (*.xml)", "ChemCanvas Markup Language (*.ccml)"]
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
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        "mol.png", "PNG Image (*.png)")
        if not filename:
            return
        image.save(filename)


    def exportAsSVG(self):
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        "mol.svg", "SVG Image (*.svg)")
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
        smiles_gen = SmilesGenerator()
        mols = [obj for obj in App.paper.objects if obj.class_name=="Molecule"]
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
        draw_recursively(mol)

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
