#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>

import sys, os
import io
import platform
import re
from datetime import datetime
import traceback

from PyQt5.QtCore import (qVersion, Qt, QSettings, QEventLoop, QTimer, QThread,
    QSize, QDir, QStandardPaths)
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QPalette

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStyleFactory, QGridLayout, QGraphicsView, QSpacerItem, QVBoxLayout,
    QFileDialog, QAction, QActionGroup, QToolButton, QInputDialog, QPushButton, QWidget,
    QSpinBox, QFontComboBox, QSizePolicy, QLabel, QMessageBox, QSlider, QDialog
)

sys.path.append(os.path.dirname(__file__)) # for enabling python 2 like import

from __init__ import __version__, COPYRIGHT_YEAR, AUTHOR_NAME, AUTHOR_EMAIL
from ui_mainwindow import Ui_MainWindow

from paper import Paper
from tools import *
from tool_helpers import draw_recursively, get_objs_with_all_children
from app_data import App, get_icon
from fileformats import *
from template_manager import (TemplateManager, find_template_icon,
    TemplateChooserDialog, TemplateManagerDialog, TemplateSearchWidget)
from fileformat_smiles import Smiles
from widgets import (PaletteWidget, TextBoxDialog, UpdateDialog, UpdateChecker,
    PixmapButton, FlowLayout, SearchBox, wait, ErrorDialog)
from settings_ui import SettingsDialog

from common import str_to_tuple


DEBUG = False
def debug(*args):
    if DEBUG: print(*args)



class Window(QMainWindow, Ui_MainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        App.window = self

        self.setWindowTitle("ChemCanvas - " + __version__)
        self.setWindowIcon(QIcon(":/icons/chemcanvas.png"))

        # Load settings
        self.settings = QSettings("chemcanvas", "chemcanvas", self)
        width = int(self.settings.value("WindowWidth", 840))
        height = int(self.settings.value("WindowHeight", 540))
        maximized = self.settings.value("WindowMaximized", "false") == "true"
        curr_dir = self.settings.value("WorkingDir", "")
        show_carbon = self.settings.value("ShowCarbon", "None")
        # load App.Settings
        self.loadSettings()

        # setup layout and other widgets
        self.vertexGrid = QGridLayout(self.leftFrame)
        self.rightGrid = QGridLayout(self.rightFrame)

        # add zoom icon
        icon = get_icon(":/icons/zoom-in")
        icon_pm = icon.pixmap(icon.availableSizes()[0])
        zoom_icon = QLabel(self)
        zoom_icon.setPixmap(icon_pm)
        self.statusbar.addPermanentWidget(zoom_icon)
        # add zoom slider
        self.zoom_levels = [25,30,40,45,50,55,60,65,75,80,90,100,110,120,140,160,180,200]
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0,len(self.zoom_levels)-1)
        #slider.setSingleStep(1)# does not work
        self.slider.setPageStep(1)
        self.slider.setValue(self.zoom_levels.index(100))
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
        basic_scale = max(self.physicalDpiX(), self.physicalDpiY())/Settings.render_dpi
        Settings.basic_scale = basic_scale>1.05 and basic_scale or 1.0
        self.graphicsView.scale(Settings.basic_scale, Settings.basic_scale)
        self.paper = Paper(self.graphicsView)
        App.paper = self.paper
        page_w, page_h = 595/72*Settings.render_dpi, 842/72*Settings.render_dpi
        self.paper.setSize(page_w, page_h)
        App.paper.show_carbon = show_carbon

        # menu actions
        self.showCarbonActionGroup = QActionGroup(self)
        self.showCarbonActionGroup.addAction(self.actionShowNone)
        self.showCarbonActionGroup.addAction(self.actionShowTerminal)
        self.showCarbonActionGroup.addAction(self.actionShowAll)
        for action in self.showCarbonActionGroup.actions():
            if action.text()==show_carbon:
                action.setChecked(True)
        self.showCarbonActionGroup.triggered.connect(self.onShowCarbonModeChange)

        self.toolBar.setIconSize(QSize(22,22))
        # add main actions
        self.toolBar.addAction(self.actionOpen)
        self.toolBar.addAction(self.actionSave)
        self.toolBar.addAction(self.actionUndo)
        self.toolBar.addAction(self.actionRedo)

        self.toolBar.addSeparator()

        # for settings bar, i.e below main toolbar
        # stores all actions (including QActionGroup) associated to properties
        # in settingsbar. maps settings_key to QAction which helps to
        # obtain the widget associated to a particular settings key.
        self.property_actions = {}
        # this contains non-property widgets (eg. button, label, separators etc)
        self.widget_actions = []

        # add toolbar actions
        self.toolGroup = QActionGroup(self.toolBar)# also needed to manually check the buttons
        self.toolGroup.triggered.connect(self.onToolClick)
        for tool_name in toolbar_tools:
            title, icon_name = tools_template[tool_name]
            action = self.toolBar.addAction(get_icon(f":/icons/{icon_name}"), title)
            action.name = tool_name
            action.setCheckable(True)
            self.toolGroup.addAction(action)


        spacer = QWidget(self.toolBar)
        spacer.setSizePolicy(1|2|4,1|4)
        self.toolBar.addWidget(spacer)
        self.searchBox = SearchBox(self.toolBar)
        self.searchBox.setPlaceholderText("Search Molecules ...")
        self.searchBox.setMaximumWidth(240)
        self.toolBar.addWidget(self.searchBox)
        self.templateSearchBtn = PixmapButton(self.toolBar)
        self.templateSearchBtn.setPixmap(QPixmap(":/icons/pubchem.png"))
        self.templateSearchBtn.setToolTip("Search molecules online")
        self.toolBar.addWidget(self.templateSearchBtn)

        # create atomtool actions
        atomsLabel = QLabel("Elements :", self)
        self.vertexGrid.addWidget(atomsLabel, 0, 0, 1,4)
        # contains atom, group and template button actions
        self.structureGroup = QActionGroup(self.leftFrame)
        self.structureGroup.triggered.connect(self.onVertexTypeChange)

        for i, atom_symbol in enumerate(atomtools_template):
            action = QAction(atom_symbol, self)
            action.key = 'atom'
            action.value = atom_symbol
            action.setCheckable(True)
            self.structureGroup.addAction(action)
            # create tool button
            btn = QToolButton(self.leftFrame)
            btn.setDefaultAction(action)
            self.vertexGrid.addWidget(btn, 1+i//4, i%4, 1,1)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        groupsLabel = QLabel("Functional Groups :", self)
        self.vertexGrid.addWidget(groupsLabel, 1+i, 0, 1,4)
        i += 2

        # add funcional groups
        for j, group_formula in enumerate(grouptools_template):
            action = QAction("-"+group_formula, self)
            action.key = 'group'
            action.value = group_formula
            action.setCheckable(True)
            self.structureGroup.addAction(action)
            # create tool button
            btn = QToolButton(self.leftFrame)
            btn.setDefaultAction(action)
            row, col = j//2, j%2
            self.vertexGrid.addWidget(btn, i+row, 2*col, 1,2)# each button occupies 2 columns
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # stretch last row, to align buttons to top
        self.vertexGrid.setRowStretch(i+j, 1)

        templatesLabel = QLabel("Templates :", self.rightFrame)
        # prevent it to expand vertically
        templatesLabel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.rightGrid.addWidget(templatesLabel, 0, 0, 1,2)
        # add templates
        App.template_manager = TemplateManager()
        cols = 3
        for i, template_name in enumerate(App.template_manager.basic_templates):
            template = App.template_manager.templates[template_name]
            action = QAction(template.name, self)
            action.key = 'template'
            action.value = template.name
            action.setCheckable(True)
            self.structureGroup.addAction(action)
            # create toolbutton
            btn = QToolButton(self.rightFrame)
            btn.setDefaultAction(action)
            row, col = i//cols+1, i%cols
            self.rightGrid.addWidget(btn, row, col, 1,1)
            icon_path = find_template_icon(template.name)
            if icon_path:
                action.setIcon(get_icon(icon_path))
                btn.setIconSize(QSize(32,32))

        templatesBtn = QPushButton("More...", self.rightFrame)
        self.rightGrid.addWidget(templatesBtn, self.rightGrid.rowCount(), 0, 1,cols)

        widget = QWidget(self.rightFrame)
        self.rightGrid.addWidget(widget, self.rightGrid.rowCount(), 0, 1,cols)
        self.templateLayout = FlowLayout(widget)
        self.templateLayout.setContentsMargins(0,0,0,0)

        # add template search widget
        self.templateSearchWidget = None
        self.searchBox.textChanged.connect(self.onSearchTextChange)
        self.searchBox.escapePressed.connect(self.searchBox.clear)
        self.templateSearchBtn.clicked.connect(self.onWebSearchClick)

        # select structure tool
        self.selectToolByName("StructureTool")
        self.structureGroup.actions()[0].setChecked(True)# select carbon atom

        # Connect signals
        self.actionQuit.triggered.connect(self.close)
        self.actionOpen.triggered.connect(self.openFile)
        self.actionSave.triggered.connect(self.overwrite)
        self.actionSaveAs.triggered.connect(self.saveFileAs)
        self.actionPNG.triggered.connect(self.exportAsPNG)
        self.actionSVG.triggered.connect(self.exportAsSVG)
        self.actionSvgEditable.triggered.connect(self.exportAsSvgEditable)
        self.actionTemplateManager.triggered.connect(self.manageTemplates)

        self.actionUndo.triggered.connect(self.undo)
        self.actionRedo.triggered.connect(self.redo)
        self.actionGenSmiles.triggered.connect(self.generateSmiles)
        self.actionReadSmiles.triggered.connect(self.readSmiles)
        self.actionDrawingSettings.triggered.connect(self.drawingSettings)
        self.actionCheckForUpdate.triggered.connect(self.checkForUpdate)
        self.actionAbout.triggered.connect(self.showAbout)

        templatesBtn.clicked.connect(self.showTemplateChooserDialog)

        # other things to initialize
        if not curr_dir or not os.path.isdir(curr_dir):
            curr_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        QDir.setCurrent(curr_dir)
        self.filename = ''
        self.selected_filter = ''
        self.actionSave.setEnabled(False)

        # show window
        self.resize(width, height)
        if maximized:
            self.showMaximized()
        else:
            self.show()
        self.graphicsView.horizontalScrollBar().setValue(0)
        self.graphicsView.verticalScrollBar().setValue(0)
        # check for update in background
        last_check_date = self.settings.value("UpdateCheckDate", "20250101")
        last = datetime.strptime(last_check_date, "%Y%m%d")
        today = datetime.now()
        if last>today or (today-last).days>=7:# last>today happens if system date is incorrect
            self.thread = QThread(self)
            self.updater = UpdateChecker(__version__)
            self.updater.moveToThread(self.thread)# must be moved before connecting signals
            self.updater.updateCheckFinished.connect(self.onUpdateCheckFinish)
            self.thread.started.connect(self.updater.checkForUpdate)
            self.thread.finished.connect(self.thread.deleteLater)
            QTimer.singleShot(1000, self.thread.start)


    def loadSettings(self):
        """ Load drawing settings """
        settings = QSettings("chemcanvas", "chemcanvas", self)
        settings.beginGroup("Custom_Style")
        Settings.atom_font_size = int(settings.value("atom_font_size", Settings.atom_font_size))
        Settings.bond_length = int(settings.value("bond_length", Settings.bond_length))
        Settings.bond_width = float(settings.value("bond_width", Settings.bond_width))
        Settings.bond_spacing = float(settings.value("bond_spacing", Settings.bond_spacing))
        Settings.electron_dot_size = float(settings.value("electron_dot_size", Settings.electron_dot_size))
        Settings.arrow_line_width = float(settings.value("arrow_line_width", Settings.arrow_line_width))
        Settings.arrow_head_dimensions = str_to_tuple(settings.value("arrow_head_dimensions",
                                        str(Settings.arrow_head_dimensions)))
        Settings.plus_size = int(settings.value("plus_size", Settings.plus_size))
        settings.endGroup()


    def onWebSearchClick(self):
        if not self.searchBox.text():
            QMessageBox.warning(self, "SearchBox Empty !", "First type compound name in search box, then click this button")
            return
        self.templateSearchWidget.webSearchTemplate()

    def onSearchTextChange(self, text):
        if text and not self.templateSearchWidget:
            self.templateSearchWidget = TemplateSearchWidget(self)
            self.templateSearchWidget.setSearchBox(self.searchBox)
            self.templateSearchWidget.templateSelected.connect(self.useTemplate)
        # show or hide
        self.templateSearchWidget.setVisible(bool(text))


    def useTemplate(self, title):
        """ place template on paper and add to recent templates """
        self.searchBox.clear()
        btn = self.addToRecentTemplates(title)
        btn.defaultAction().trigger()# select the button
        if not self.templateSearchWidget.autoPlacementBtn.isChecked():
            return
        mol = App.template_manager.templates[title]
        x1,y1,x2,y2 = mol.bounding_box()
        x,y = App.paper.find_place_for_obj_size(x2-x1, y2-y1)
        mol = App.template_manager.get_transformed_template(mol, (x,y))
        App.paper.addObject(mol)
        draw_recursively(mol)
        App.paper.save_state_to_undo_stack("add template : %s"% mol.name)

    def addToRecentTemplates(self, title):
        """ show template in recent templates list """
        template = App.template_manager.templates[title]
        for i in range(self.templateLayout.count()):
            widget = self.templateLayout.itemAt(i).widget()
            if widget.defaultAction().value == title:# template already exists in recents
                return widget
        btn = PixmapButton(self)
        paper = Paper()
        thumbnail = paper.renderObjects([template]).scaledToHeight(48, Qt.SmoothTransformation)
        btn.setPixmap(QPixmap.fromImage(thumbnail))
        self.templateLayout.addWidget(btn)
        action = QAction(title, self)
        action.key = "template"
        action.value = title
        action.setCheckable(True)
        self.structureGroup.addAction(action)
        btn.setDefaultAction(action)
        btn.setToolTip(title)
        # if added template Button is not properly visible, remove least used Buttons
        key = lambda t: App.template_manager.templates_usage_count[t]
        recents = sorted(App.template_manager.recent_templates, key=key)
        for template in recents:
            wait(30)# give time to have visible changes
            if btn.visibleRegion().boundingRect().height() >= btn.size().height():
                break
            # remove template btn
            i = App.template_manager.recent_templates.index(template)
            App.template_manager.recent_templates.pop(i)
            widget = self.templateLayout.itemAt(i).widget()
            self.templateLayout.removeWidget(widget)
            widget.deleteLater()
        App.template_manager.recent_templates.append(title)
        App.template_manager.templates_usage_count[title] = 0
        return btn

    def showTemplateChooserDialog(self):
        """ On clicking More templates button, show template chooser dialog """
        dlg = TemplateChooserDialog(self)
        if dlg.exec()==dlg.Accepted:
            title = dlg.selected_template
            btn = self.addToRecentTemplates(title)
            btn.defaultAction().trigger()# select the button

    def manageTemplates(self):
        """ manage template files and its templates """
        dlg = TemplateManagerDialog(self)
        dlg.exec()


    def onZoomSliderMoved(self, index):
        self.graphicsView.resetTransform()
        scale = self.zoom_levels[index] / 100
        self.graphicsView.scale(Settings.basic_scale*scale, Settings.basic_scale*scale)
        self.zoomLabel.setText("%i%%"%int(scale*100))

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
        for key,item in self.property_actions.items():
            if isinstance(item, QActionGroup):
                for action in item.actions():
                    self.subToolBar.removeAction(action)
                    item.removeAction(action)
                    action.deleteLater()
            else:
                self.subToolBar.removeAction(item)

            # dont need to delete the associated widget, as the toolbar takes ownership of it.
            item.deleteLater()

        self.property_actions.clear()

        for action in self.widget_actions:
            self.subToolBar.removeAction(action)
            action.deleteLater()

        self.widget_actions.clear()


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
                    action = self.subToolBar.addAction(get_icon(f":/icons/{icon_name}"), title)
                    action.key = group_name
                    action.value = action_name
                    action.setCheckable(True)
                    toolGroup.addAction(action)
                    if action_name == selected_value:
                        action.setChecked(True)

                self.property_actions[group_name] = toolGroup
                toolGroup.triggered.connect(self.onSubToolClick)
                self.widget_actions.append(self.subToolBar.addSeparator())

            elif group_type=="Button":
                title, icon_name = templates
                icon = icon_name and get_icon(f":/icons/{icon_name}") or QIcon()
                action = self.subToolBar.addAction(icon, title)
                action.key = group_name
                action.value = title

                self.widget_actions.append(action)
                btn = self.subToolBar.widgetForAction(action)
                btn.triggered.connect(self.onButtonClick)

            elif group_type=="SpinBox":
                spinbox = QSpinBox() # ToolBar takes ownership of the widget
                spinbox.setRange(*templates)
                spinbox.setValue(toolsettings[group_name])
                spinbox.key = group_name
                action = self.subToolBar.addWidget(spinbox)
                self.property_actions[group_name] = action
                spinbox.valueChanged.connect(self.onSpinValueChange)

            elif group_type=="FontComboBox":
                widget = QFontComboBox()
                index = widget.findText(toolsettings[group_name])# -1 if not found
                if index >=0:
                    widget.setCurrentIndex(index)
                widget.key = group_name
                action = self.subToolBar.addWidget(widget)
                self.property_actions[group_name] = action
                widget.currentIndexChanged.connect(self.onFontChange)

            elif group_type=="PaletteWidget":
                widget = PaletteWidget(self.subToolBar, toolsettings['color_index'])
                widget.key = group_name
                action = self.subToolBar.addWidget(widget)
                self.property_actions[group_name] = action
                widget.colorSelected.connect(self.onColorSelect)

            elif group_type=="Label":
                title = group_name
                widget = QLabel(title, self.subToolBar)
                action = self.subToolBar.addWidget(widget)
                self.widget_actions.append(action)


    def setCurrentToolProperty(self, key, val):
        """ Used by Tools, set current tool settings value """
        action = self.property_actions[key]

        if isinstance(action, QActionGroup):
            for act in action.actions():
                if act.value == val:
                    act.setChecked(True)
                    # programmatically checking action will not emit triggered() signal and
                    # will not update settings. So we are doing it here.
                    toolsettings[key] = val
                    return True
            return

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


    def onButtonClick(self, action):
        App.tool.on_property_change(action.key, action.value)

    def onSubToolClick(self, action):
        """ On click on a grouped button on subtoolbar """
        App.tool.on_property_change(action.key, action.value)
        toolsettings[action.key] = action.value

    def onSpinValueChange(self, val):
        spinbox = self.sender()# get sender of this signal
        App.tool.on_property_change(spinbox.key, val)
        toolsettings[spinbox.key] = val

    def onFontChange(self, index):
        combo = self.sender()
        App.tool.on_property_change(combo.key, combo.currentText())
        toolsettings[combo.key] = combo.itemText(index)

    def onColorSelect(self, color):
        """ This is a slot which receives colorSelected() signal from PaletteWidget """
        widget = self.sender()
        App.tool.on_property_change(widget.key, color)
        toolsettings[widget.key] = color
        toolsettings['color_index'] = widget.curr_index

    def selectStructure(self, title):
        for action in self.structureGroup.actions():
            if action.value == title:
                action.trigger()

    def onVertexTypeChange(self, action):
        """ called when one of the item in structureGroup is clicked """
        self.selectToolByName("StructureTool")
        toolsettings['structure'] = action.value
        App.tool.on_property_change('mode', action.key)

    def changeStructureToolMode(self, mode):
        """ called by StructureTool.on_property_change(),
        handles selecting and deselecting buttons """
        if mode == toolsettings.getValue("StructureTool", 'mode'):
            return
        toolsettings['mode'] = mode
        # settings for selected mode
        if mode =='atom':
            # select single bond if no bond is selected
            if self.property_actions['bond_type'].checkedAction()==None:
                self.setCurrentToolProperty('bond_type', 'single')
        else:
            # bond should be deselected in all other modes
            if action := self.property_actions['bond_type'].checkedAction():
                action.setChecked(False)
                toolsettings['bond_type'] = None
        # structure should be deselected in ring and chain tool
        if mode in ('chain', 'ring'):
            if action := self.structureGroup.checkedAction():
                action.setChecked(False)
        else:
            # deselect ring or chain tool in all other modes
            if action := self.property_actions['mode'].checkedAction():
                action.setChecked(False)


    # ------------------------ FILE -------------------------

    def enableSaveButton(self, enable):
        self.actionSave.setEnabled(enable)
        if self.filename:
            filename = os.path.basename(self.filename)
            if enable:
                filename = "*" + filename
            self.setWindowTitle(filename)


    def openFile(self, filename=None):
        """ if filename not passed, filename is obtained via FileDialog """
        if filename:
            if not os.path.exists(filename):
                return False
        # get filename to open
        else:
            filtr = get_read_filters()
            filename, filtr = QFileDialog.getOpenFileName(self, "Open File", self.filename,
                            "%s;;All Files (*)" % filtr)
            if not filename:
                return False
        # read file
        try:
            reader = create_file_reader(filename)
            if not reader:
                self.showStatus("Failed to read file : fileformat not supported !")
                return False
            doc = reader.read(filename)
            if reader.status=="failed":
                self.showError("Failed to read file !", reader.message)
                return
            elif reader.status=="warning":
                self.showStatus(reader.message)
            if not doc or not doc.objects:
                return False
        except Exception as e:
            self.showException(e)
            return
        # On Success
        is_new = App.paper.setDocument(doc)
        App.paper.save_state_to_undo_stack("Open File")
        if is_new:
            self.filename = filename
            self.selected_filter = ""# reset
            App.paper.undo_manager.mark_saved_to_disk()
            self.enableSaveButton(False)
        return True


    def saveFile(self, filename):
        App.tool.clear()
        # create format class
        writer = create_file_writer(filename)
        if not writer:
            return False
        # write document
        try:
            doc = App.paper.getDocument()
            writer.write(doc, filename)
            if writer.status=="failed":
                self.showError("Failed to save !", writer.message)
                return
            elif writer.status=="warning":
                self.showStatus(writer.message)
        except Exception as e:
            self.showException(e)
            return
        self.filename = filename
        App.paper.undo_manager.mark_saved_to_disk()
        self.enableSaveButton(False)

    def overwrite(self):
        if not self.filename:
            return self.saveFileAs()
        # partially supported file formats should not be overwritten without confirmation
        if not self.filename.endswith("ccdx"):
            if QMessageBox.question(self, "Overwrite ?", "Overwrite current file ?",
                QMessageBox.Yes|QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
                return
        self.saveFile(self.filename)


    def saveFileAs(self):
        path = self.filename or self.getSaveFileName("ccdx")
        filters = get_write_filters()
        sel_filter = self.selected_filter or choose_filter(filters, path)
        # sel_filter is None if the file format is readable but not writable
        if not sel_filter:
            path = os.path.splitext(path)[0] + ".ccdx"

        filename, sel_filter = QFileDialog.getSaveFileName(self, "Save File",
                        path, filters, sel_filter)
        if not filename:
            return False
        self.selected_filter = sel_filter
        return self.saveFile(filename)


    def getSaveFileName(self, extension):
        if self.filename:
            name, ext = os.path.splitext(self.filename)
        else:
            name = "mol"
        return get_new_filename(name + "." + extension)


    def exportAsPNG(self):
        App.tool.clear()
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
        App.tool.clear()
        path = self.getSaveFileName("svg")
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        path, "SVG Image (*.svg)")
        if not filename:
            return
        try:
            svg = App.paper.getSvg()
            # save file
            with io.open(filename, 'w', encoding='utf-8') as svg_file:
                svg_file.write(svg)
        except Exception as e:
            self.showException(e)

    def exportAsSvgEditable(self):
        App.tool.clear()
        path = self.getSaveFileName("svg")
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        path, "SVG Image (*.svg)")
        if not filename:
            return
        self.saveFile(filename)


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
        try:
            smiles_gen = Smiles()
            smiles = smiles_gen.generate(mols[-1])
            dlg = TextBoxDialog("Generated SMILES :", smiles, self)
            dlg.setWindowTitle("SMILES")
            dlg.exec()
        except Exception as e:
            self.showException(e)

    def readSmiles(self):
        dlg = TextBoxDialog("Enter SMILES :", "", self, mode="input")
        if dlg.exec()!=QDialog.Accepted:
            return
        text = dlg.text()
        try:
            reader = Smiles()
            doc = reader.read_string(text)
            if not doc:
                return
            mol = doc.objects[0]
            App.paper.addObject(mol)
            draw_recursively(mol)
            App.paper.save_state_to_undo_stack("Read SMILES")
        except Exception as e:
            self.showException(e)

    # ------------------------- Others -------------------------------

    def drawingSettings(self):
        dlg = SettingsDialog(self)
        if dlg.exec()==dlg.Accepted:
            objects = get_objs_with_all_children(App.paper.objects)
            atoms = set(o for o in objects if isinstance(o,Atom))
            for atom in atoms:
                atom.font_size = Settings.atom_font_size
                atom.radical_size = Settings.electron_dot_size
            bonds = set(o for o in objects if isinstance(o,Bond))
            for bond in bonds:
                bond.line_width = Settings.bond_width
                bond.line_spacing = Settings.bond_spacing
            arrows = set(o for o in objects if isinstance(o,Arrow))
            for arrow in arrows:
                arrow.line_width = Settings.arrow_line_width
                arrow.update_head_dimensions()
            pluses = set(o for o in objects if isinstance(o,Plus))
            for plus in pluses:
                plus.font_size = Settings.plus_size
            objs = sorted(objects, key=lambda x : x.redraw_priority)
            [o.draw() for o in objs]


    def onShowCarbonModeChange(self, action):
        App.paper.show_carbon = action.text()
        objects = get_objs_with_all_children(App.paper.objects)
        [o.update_visibility() for o in objects if o.class_name=="Atom"]
        objs = sorted(objects, key=lambda x : x.redraw_priority)
        [o.draw() for o in objs]
        self.settings.setValue("ShowCarbon", App.paper.show_carbon)

    def showStatus(self, msg):
        self.statusbar.showMessage(msg)

    def clearStatus(self):
        self.statusbar.clearMessage()

    def showError(self, title, text):
        QMessageBox.critical(self, title, text)

    def showException(self, error):
        dlg = ErrorDialog(self, str(error), traceback.format_exc())
        dlg.exec()


    def checkForUpdate(self):
        """ manual update check """
        dlg = UpdateDialog(self)
        dlg.exec()

    def onUpdateCheckFinish(self, latest_version, changelog):
        """ callback for auto update check """
        self.thread.quit()
        self.updater.deleteLater()
        if latest_version:# check success but may not have new version
            self.settings.setValue("UpdateCheckDate", datetime.now().strftime("%Y%m%d"))
            last_checked_version = self.settings.value("LastCheckedVersion", __version__)
            if latest_version==last_checked_version or latest_version==__version__:
                return
            self.settings.setValue("LastCheckedVersion", latest_version)
            # new version available
            dlg = UpdateDialog(self)
            dlg.latest_version = latest_version
            dlg.changelog = changelog
            dlg.enlarge()
            dlg.onNewVersionAvailable()
            dlg.exec()



    def showAbout(self):
        lines = ("<h1>ChemCanvas</h1>",
            "A Chemical Drawing Tool<br><br>",
            "ChemCanvas : %s<br>" % __version__,
            "Qt : %s<br>" % qVersion(),
            "Python : %s<br>" % platform.python_version(),
            "Copyright &copy; %s %s &lt;%s&gt;" % (COPYRIGHT_YEAR, AUTHOR_NAME, AUTHOR_EMAIL))
        QMessageBox.about(self, "About ChemCanvas", "".join(lines))

    def resizeEvent(self, ev):
        QMainWindow.resizeEvent(self, ev)
        if self.templateSearchWidget:
            self.templateSearchWidget.reposition()

    def closeEvent(self, ev):
        """ Save all settings on window close """
        self.settings.setValue("WindowMaximized", self.isMaximized())
        if not self.isMaximized():
            self.settings.setValue("WindowWidth", self.width())
            self.settings.setValue("WindowHeight", self.height())
        if self.filename:
            self.settings.setValue("WorkingDir", os.path.dirname(self.filename))
        QMainWindow.closeEvent(self, ev)




def get_new_filename(filename):
    # get a new filename with number suffix if filename already exists
    dirpath, filename = os.path.split(filename)
    if dirpath:
        dirpath += "/"
    basename, ext = os.path.splitext(filename)
    match = re.match(r"(.*\D)(\d*)", basename)
    if not match:
        return get_new_filename(dirpath + "mol.ccdx")

    num = match.group(2) and int(match.group(2)) or 1

    path = dirpath + basename + ext
    while os.path.exists(path):
        path = dirpath + match.group(1) + str(num) + ext
        num += 1

    return path


def is_dark_mode():
    """ detects if dark theme is in use """
    defaultPalette = QPalette()
    text = defaultPalette.color(QPalette.WindowText)
    window = defaultPalette.color(QPalette.Window)
    return text.lightness() > window.lightness()



def main():
    app = QApplication(sys.argv)
    App.dark_mode = is_dark_mode()
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
