#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>

import sys, os
import io
import platform
import re
from datetime import datetime

from PyQt5.QtCore import (qVersion, Qt, QSettings, QEventLoop, QTimer, QThread,
    QSize, QDir, QStandardPaths)
from PyQt5.QtGui import QIcon, QPainter, QPixmap

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStyleFactory, QGridLayout, QGraphicsView, QSpacerItem, QVBoxLayout,
    QFileDialog, QAction, QActionGroup, QToolButton, QInputDialog, QPushButton, QWidget,
    QSpinBox, QFontComboBox, QSizePolicy, QLabel, QMessageBox, QSlider, QDialog
)

sys.path.append(os.path.dirname(__file__)) # for enabling python 2 like import

from __init__ import __version__, COPYRIGHT_YEAR, AUTHOR_NAME, AUTHOR_EMAIL
from ui_mainwindow import Ui_MainWindow

from paper import Paper, SvgPaper, draw_graphicsitem
from tools import *
from tool_helpers import draw_recursively
from app_data import App
from fileformat import *
from template_manager import (TemplateManager, find_template_icon,
    TemplateChooserDialog, TemplateManagerDialog)
from smiles import SmilesReader, SmilesGenerator
from coords_generator import calculate_coords
from widgets import (PaletteWidget, TextBoxDialog, UpdateDialog, UpdateChecker,
    PixmapButton, FlowLayout)




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

        self.vertexGrid = QGridLayout(self.leftFrame)
        self.rightGrid = QGridLayout(self.rightFrame)

        # add zoom icon
        zoom_icon = QLabel(self)
        zoom_icon.setPixmap(QPixmap(":/icons/zoom-in.png"))
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
            action = self.toolBar.addAction(QIcon(":/icons/%s.png"%icon_name), title)
            action.name = tool_name
            action.setCheckable(True)
            self.toolGroup.addAction(action)

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
                action.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(32,32))

        templatesBtn = QPushButton("More...", self.rightFrame)
        self.rightGrid.addWidget(templatesBtn, self.rightGrid.rowCount(), 0, 1,cols)

        widget = QWidget(self.rightFrame)
        self.rightGrid.addWidget(widget, self.rightGrid.rowCount(), 0, 1,cols)
        self.templateLayout = FlowLayout(widget)
        self.templateLayout.setContentsMargins(0,0,0,0)

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
        self.actionTemplateManager.triggered.connect(self.manageTemplates)

        self.actionUndo.triggered.connect(self.undo)
        self.actionRedo.triggered.connect(self.redo)
        self.actionGenSmiles.triggered.connect(self.generateSmiles)
        self.actionReadSmiles.triggered.connect(self.readSmiles)
        self.actionCheckForUpdate.triggered.connect(self.checkForUpdate)
        self.actionAbout.triggered.connect(self.showAbout)

        templatesBtn.clicked.connect(self.showTemplateChooserDialog)

        # Load settings and Show Window
        self.settings = QSettings("chemcanvas", "chemcanvas", self)
        width = int(self.settings.value("WindowWidth", 840))
        height = int(self.settings.value("WindowHeight", 540))
        maximized = self.settings.value("WindowMaximized", "false") == "true"
        curr_dir = self.settings.value("WorkingDir", "")

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
                    action = self.subToolBar.addAction(QIcon(":/icons/%s.png"%icon_name), title)
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
                icon = icon_name and QIcon(":/icons/%s.png"%icon_name) or QIcon()
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
        prev_mode = toolsettings.getValue("StructureTool", 'mode')
        mode = action.key
        self.selectToolByName("StructureTool")
        if mode != prev_mode:
            toolsettings['mode'] = mode
            if mode =='atom':
                if self.property_actions['bond_type'].checkedAction()==None:
                    self.setCurrentToolProperty('bond_type', 'single')
            if prev_mode=="atom":
                # group and template mode does not need bond selected
                if self.property_actions['bond_type'].checkedAction():
                    self.property_actions['bond_type'].checkedAction().setChecked(False)
                    toolsettings['bond_type'] = None
        toolsettings['structure'] = action.value
        App.tool.on_property_change('mode', mode)



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
        reader = create_file_reader(filename)
        if not reader:
            self.showStatus("Failed to read file : fileformat not supported !")
            return False
        doc = reader.read(filename)
        if not doc:
            self.showStatus("Failed to read file contents !")
            return False
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
        doc = App.paper.getDocument()
        if writer.write(doc, filename):
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


    def showTemplateChooserDialog(self):
        dlg = TemplateChooserDialog(self)
        if dlg.exec()==dlg.Accepted:
            title = dlg.selected_template
            template = App.template_manager.templates[title]
            for i in range(self.templateLayout.count()):
                widget = self.templateLayout.itemAt(i).widget()
                if widget.defaultAction().value == title:# template already exists in recents
                    widget.defaultAction().trigger()# select the button
                    return
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
            # select this button and template
            action.trigger()
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



    def manageTemplates(self):
        dlg = TemplateManagerDialog(self)
        dlg.exec()

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
            "Version : %s<br>" % __version__,
            "Qt : %s<br>" % qVersion(),
            "Copyright &copy; %s %s &lt;%s&gt;" % (COPYRIGHT_YEAR, AUTHOR_NAME, AUTHOR_EMAIL))
        QMessageBox.about(self, "About ChemCanvas", "".join(lines))

    def closeEvent(self, ev):
        """ Save all settings on window close """
        self.settings.setValue("WindowMaximized", self.isMaximized())
        if not self.isMaximized():
            self.settings.setValue("WindowWidth", self.width())
            self.settings.setValue("WindowHeight", self.height())
        if self.filename:
            self.settings.setValue("WorkingDir", os.path.dirname(self.filename))
        QMainWindow.closeEvent(self, ev)



def wait(millisec):
    loop = QEventLoop()
    QTimer.singleShot(millisec, loop.quit)
    loop.exec()


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
