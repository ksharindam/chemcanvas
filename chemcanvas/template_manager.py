# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os
import math
import operator
from functools import reduce
import urllib.request

from PyQt5.QtCore import QRect, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFontMetrics, QPainter
from PyQt5.QtWidgets import (QToolButton, QMenu, QInputDialog, QMessageBox, QDialog,
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGridLayout, QComboBox, QScrollArea,
    QDialogButtonBox, QAction, QCheckBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QStyle, QStyleOption)

from app_data import App, Settings
from document import Document
from fileformats import Ccdx, Molfile
from widgets import FlowLayout, PixmapButton, SearchBox, wait
from paper import Paper
import geometry as geo
from tool_helpers import place_molecule, remove_explicit_hydrogens


def find_template_icon(icon_name):
    """ find and return full path of an icon file. returns empty string if not found """
    template_dir = App.template_manager.APP_TEMPLATES_DIR
    icon_path = template_dir + "/" + icon_name + ".png"
    if os.path.exists(icon_path):
        return icon_path
    return ""




class TemplateManager:
    # molecule categories
    categories = ["Amino Acids", "Aromatics", "Bicyclics", "Bridged Polycyclics", "Crown Ethers", "Heterocycles", "Nucleobases", "Rings", "Sugars", "Others"]

    def __init__(self):
        # dict key is in "name index" format. eg - "cyclohexane", "cyclohexane 1".
        # index is used when two templates have same name
        self.templates = {}
        # ordered list of template names
        self.basic_templates = [] # basic set
        self.extended_templates = [] # all others except basic including user templates
        self.recent_templates = []
        self.templates_usage_count = {}
        # directories
        self.APP_TEMPLATES_DIR = App.SRC_DIR + "/templates"
        self.USER_TEMPLATES_DIR = App.DATA_DIR + "/templates"
        if not os.path.exists(self.USER_TEMPLATES_DIR):
            os.mkdir(self.USER_TEMPLATES_DIR)

        # read all templates
        basic_templates_file = self.APP_TEMPLATES_DIR + "/basic_templates.cctf"
        basic_templates = self.read_templates_file(basic_templates_file)
        self.basic_templates = self.add_templates(basic_templates)

        for template_dir in [self.APP_TEMPLATES_DIR, self.USER_TEMPLATES_DIR]:
            files = os.listdir(template_dir)
            files = [ template_dir+"/"+f for f in files if f.endswith(".cctf") ]
            for templates_file in files:
                if templates_file != basic_templates_file:
                    templates = self.read_templates_file(templates_file)
                    self.add_to_extended_templates(templates)


    def read_templates_file(self, filename):
        """ returns list of template Molecule objects """
        ccdx_reader = Ccdx()
        doc = ccdx_reader.read(filename)
        if not doc:
            return []
        templates = []
        mols = [obj for obj in doc.objects if obj.class_name=="Molecule"]
        for mol in mols:
            if mol.name and mol.template_atom and mol.template_bond:
                templates.append(mol)
        return templates


    def add_templates(self, templates):
        """ adds the templates to self.templates and returns list of template titles """
        titles = []
        for mol in templates:
            title = mol.name
            i = 1
            while title in self.templates:
                title = "%s %i" % (mol.name, i)
                i += 1
            self.templates[title] = mol
            titles.append(title)
        return titles

    def add_to_extended_templates(self, templates):
        """ add new templates to extended templates list """
        titles = self.add_templates(templates)
        self.extended_templates += titles
        return titles


    def get_transformed_template(self, template, coords, align_to="corner"):
        """ transform template copy with align to atom, bond, center or corner """
        template = template.deepcopy()
        scale_ratio = 1
        trans = geo.Transform()

        if align_to in ("Atom", "Bond") and template.template_atom and template.template_bond:
            if align_to == "Bond":
                xt1, yt1 = template.template_bond.atom1.pos
                xt2, yt2 = template.template_bond.atom2.pos
                #find appropriate side of bond to append template to
                atom1, atom2 = template.template_bond.atoms
                atms = atom1.neighbors + atom2.neighbors
                atms = set(atms) - set([atom1,atom2])
                points = [a.pos for a in atms]
                if reduce( operator.add, [geo.line_get_side_of_point( (xt1,yt1,xt2,yt2), xy) for xy in points], 0) < 0:
                    xt1, yt1, xt2, yt2 = xt2, yt2, xt1, yt1
            else:# align_to == "Atom"
                xt1, yt1 = template.template_atom.pos
                xt2, yt2 = template.find_place(template.template_atom, geo.point_distance(template.template_atom.pos, template.template_atom.neighbors[0].pos))
            x1, y1, x2, y2 = coords
            scale_ratio = math.sqrt( ((x1-x2)**2 + (y1-y2)**2) / ((xt1-xt2)**2 + (yt1-yt2)**2) )
            trans.translate( -xt1, -yt1)
            trans.rotate( math.atan2( xt1-xt2, yt1-yt2) - math.atan2( x1-x2, y1-y2))
            trans.scale(scale_ratio)
            trans.translate(x1, y1)
        # place center of template at given coord
        else:
            #xt1, yt1 = template.template_atom.pos
            #xt2, yt2 = template.template_atom.neighbors[0].pos
            #scale_ratio = Settings.bond_length / math.sqrt( (xt1-xt2)**2 + (yt1-yt2)**2)
            place_molecule(template)
            bbox = template.bounding_box()
            if align_to == "center":
                center = geo.rect_get_center(bbox)
                trans.translate( -center[0], -center[1])
            else:# align_to=="corner" (place top-left corner of template at given coord)
                trans.translate( -bbox[0], -bbox[1])
            trans.scale(scale_ratio)
            trans.translate( coords[0], coords[1])

        for a in template.atoms:
            a.x, a.y = trans.transform(a.x, a.y)
            #a.scale_font( scale_ratio)
        #for b in template.bonds:
        #    if b.order != 1:
        #        b.second_line_distance *= scale_ratio
        # update template according to current default values
        #App.paper.applyDefaultProperties( [temp], template_mode=1)
        return template


    def save_template(self, template_mol):
        # check if molecule is template
        if not template_mol.template_atom:
            QMessageBox.warning(App.window, "No Template-Atom !", "Template-Atom not selected. \nRight click on an atom and click 'Set as Template-Atom'")
            return
        if not template_mol.template_bond:
            QMessageBox.warning(App.window, "No Template-Bond !", "Template-Bond not selected. \nRight click on an bond and click 'Set as Template-Bond'")
            return
        # this dialog sets template name, category
        dlg = SaveTemplateDialog(App.window)
        if dlg.exec()==dlg.Accepted:
            name, category, filename = dlg.getValues()
            if not filename: # TODO : should create new template file
                return
            template_mol = template_mol.deepcopy()
            template_mol.name = name
            template_mol.category = category

            ccdx = Ccdx()
            doc = ccdx.read(filename)
            if not doc:
                doc = Document()
            doc.objects.append(template_mol)
            ccdx.write(doc, filename)
            self.add_to_extended_templates([template_mol])



# ---------------------- Template Manager Dialog -------------------

class TemplateManagerDialog(QDialog):
    """ This dialog allows creation, deletion of template files, and deletion
    of template molecules. New templates option only shows how to add template """
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("User Template Manager")
        self.resize(720, 480)
        topContainer = QWidget(self)
        topContainerLayout = QHBoxLayout(topContainer)
        topContainerLayout.setContentsMargins(0,0,0,0)
        # add Tool Button for file menu
        self.fileMenuBtn = QToolButton(self)
        self.fileMenuBtn.setText("File")
        self.fileMenuBtn.setPopupMode(QToolButton.InstantPopup)
        filemenu = QMenu(self.fileMenuBtn)
        #filemenu.addAction("Add Template File", self.addTemplateFile)
        filemenu.addAction("Delete Template File", self.deleteTemplateFile)
        filemenu.addAction("New Template File", self.newTemplateFile)
        self.fileMenuBtn.setMenu(filemenu)
        topContainerLayout.addWidget(self.fileMenuBtn)
        self.filenameCombo = QComboBox(topContainer)
        topContainerLayout.addWidget(self.filenameCombo)
        topContainerLayout.addStretch()
        # add template menu button
        self.templateBtn = QToolButton(self)
        self.templateBtn.setText("Template")
        self.templateBtn.setPopupMode(QToolButton.InstantPopup)
        templatemenu = QMenu(self.templateBtn)
        templatemenu.addAction("Delete", self.deleteTemplate)
        templatemenu.addAction("New", self.newTemplate)
        self.templateBtn.setMenu(templatemenu)
        topContainerLayout.addWidget(self.templateBtn)
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollWidget.setGeometry(0, 0, 397, 373)
        self.scrollLayout = FlowLayout(self.scrollWidget)
        self.scrollLayout.setContentsMargins(8, 8, 8, 8)
        self.scrollArea.setWidget(self.scrollWidget)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Close, self)
        layout = QVBoxLayout(self)
        layout.addWidget(topContainer)
        layout.addWidget(self.scrollArea)
        layout.addWidget(self.btnBox)

        self.filenameCombo.currentIndexChanged.connect(self.readCurrentTemplatesFile)
        self.btnBox.rejected.connect(self.reject)
        # Init some variables
        self.pressed_keys = []
        self.template_buttons = []
        self.selected_templates = [] # list of template widgets
        self.last_selected_button = None
        # add template file names to filename combo
        for filename in self.getTemplateFilenames():
            self.filenameCombo.addItem(os.path.basename(filename), filename)


    def readCurrentTemplatesFile(self):
        # remove previous template buttons
        for btn in reversed(self.template_buttons):# remove from last to first
            self.scrollLayout.removeWidget(btn)
            btn.deleteLater()
        self.template_buttons = []
        self.selected_templates = []
        self.last_selected_button = None

        filename = self.filenameCombo.itemData(self.filenameCombo.currentIndex())
        templates = App.template_manager.read_templates_file(filename)
        paper = Paper()
        for template in templates:
            thumbnail = paper.renderObjects([template])
            btn = TemplateButton(template.name, thumbnail, self.scrollWidget)
            self.scrollLayout.addWidget(btn)
            btn.clicked.connect(self.onTemplateClick)
            btn.template = template
            self.template_buttons.append(btn)


    def deleteTemplateFile(self):
        if self.filenameCombo.count()==0:
            return
        filename = self.filenameCombo.itemData(self.filenameCombo.currentIndex())
        if QMessageBox.question(self, "Delete ?", "Are you sure to permanently delete template file %s ?" % filename,
            QMessageBox.Yes|QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                os.remove(filename)
                self.filenameCombo.removeItem(self.filenameCombo.currentIndex())
            except:
                QMessageBox.warning(self, "Failed !", "Failed to Delete File !")


    def newTemplateFile(self):
        dlg = NewTemplateFileDialog(self)
        if dlg.exec()==dlg.Accepted:
            self.filenameCombo.addItem(os.path.basename(dlg.filename), dlg.filename)


    def getTemplateFilenames(self):
        template_dir = App.template_manager.USER_TEMPLATES_DIR
        if not os.access(template_dir, os.W_OK | os.X_OK):
            return []
        files = os.listdir(template_dir)
        return [ template_dir+"/"+f for f in files if f.endswith(".cctf") ]


    def newTemplate(self):
        QMessageBox.information(self, "New Template", "Follow these steps :\n"+
            "1. In Main Window, draw a molecule.\n"+
            "2. Right click on an atom and click 'Set as Template-Atom',\n"+
            "3. Right click on a bond and click 'Set as Template-Bond',\n"+
            "4. Right click on that molecule and click 'Save Molecule as Template'")

    def deleteTemplate(self):
        if len(self.selected_templates) == 1:
            title = self.selected_templates[0].template.name
            msg = "Are you sure to permanently delete template %s ?" % title
        elif len(self.selected_templates) > 1:
            msg = "Are you sure to permanently delete %i templates ?" % len(self.selected_templates)
        else: # none selected
            return
        if QMessageBox.question(self, "Delete Template ?", msg,
            QMessageBox.Yes|QMessageBox.No, QMessageBox.No) == QMessageBox.No:
            return

        for btn in self.selected_templates:
            self.template_buttons.remove(btn)
            self.scrollLayout.removeWidget(btn)
            btn.deleteLater()

        doc = Document()
        doc.objects = [btn.template for btn in self.template_buttons]
        filename = self.filenameCombo.itemData(self.filenameCombo.currentIndex())
        ccdx = Ccdx()
        if not ccdx.write(doc, filename):
            QMessageBox.warning(self, "Failed !", "Failed to save changes !")
        self.selected_templates = []
        # TODO : we should remove this template from self.templates, extended_templates
        # and recent_templates but we can not because we dont know correct
        # indexed title key to remove from self.templates


    def keyPressEvent(self, ev):
        self.pressed_keys.append(ev.key())

    def keyReleaseEvent(self, ev):
        try:# in some cases key release event happens without key press event
            self.pressed_keys.remove(ev.key())
        except: pass

    def onTemplateClick(self, btn):
        current_selected = [btn]
        # ctrl+click adds to/removes from selection
        if self.pressed_keys == [Qt.Key_Control]:
            if btn in self.selected_templates:# deselect if already selected
                current_selected = self.selected_templates[:]
                current_selected.remove(btn)
            else:
                current_selected += self.selected_templates
            self.last_selected_button = btn
        # on shift+click
        elif self.pressed_keys == [Qt.Key_Shift]:
            if not self.last_selected_button:# no previous selection
                return
            index1 = self.template_buttons.index(self.last_selected_button)
            index2 = self.template_buttons.index(btn)
            if index1 > index2:
                index1, index2 = index2, index1
            current_selected = [self.template_buttons[i] for i in range(index1, index2+1)]
        else:
            self.last_selected_button = btn
        # deselect
        for btn in set(self.selected_templates) - set(current_selected):
            btn.setSelected(False)
        # select clicked template
        for btn in set(current_selected) - set(self.selected_templates):
            btn.setSelected(True)
        self.selected_templates = current_selected



# ---------------------- Template Chooser Dialog -------------------

class TemplateChooserDialog(QDialog):
    category_index = 0 # to remember current category combo
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Templates")
        self.resize(720, 480)
        topContainer = QWidget(self)
        topContainerLayout = QHBoxLayout(topContainer)
        topContainerLayout.setContentsMargins(0,0,0,0)
        self.categoryCombo = QComboBox(topContainer)
        topContainerLayout.addWidget(self.categoryCombo)
        topContainerLayout.addStretch()
        self.searchBox = SearchBox(self)
        self.searchBox.setPlaceholderText("Search Templates ...")
        topContainerLayout.addWidget(self.searchBox)
        self.categoryCombo.addItems(App.template_manager.categories)
        self.categoryCombo.setCurrentIndex(self.category_index)
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollWidget.setGeometry(0, 0, 397, 373)
        self.scrollLayout = FlowLayout(self.scrollWidget)
        self.scrollLayout.setContentsMargins(6, 6, 6, 6)
        self.scrollArea.setWidget(self.scrollWidget)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel, self)
        self.searchBox.setFocus()
        # layout widgets
        layout = QVBoxLayout(self)
        layout.addWidget(topContainer)
        layout.addWidget(self.scrollArea)
        layout.addWidget(self.btnBox)
        # connect signals
        self.categoryCombo.currentTextChanged.connect(self.showCategory)
        #self.searchBox.returnPressed.connect(self.searchTemplate)
        self.searchBox.textChanged.connect(self.searchTemplate)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)
        # init variables
        self.template_buttons = [] # used to remove buttons later
        self.selected_button = None
        self.showCategory(self.categoryCombo.currentText())


    def showCategory(self, category):
        # to remember selected category
        TemplateChooserDialog.category_index = self.categoryCombo.currentIndex()
        # add template buttons to scrollwidget
        titles = App.template_manager.extended_templates
        titles = list(filter(lambda x:App.template_manager.templates[x].category==category.strip("s"), titles))
        self.showTemplates(titles)

    def searchTemplate(self, text):
        """ search and show templates """
        wait(100)# prevents freezing cursor before loading templates
        if len(text)>2:
            self.showTemplates( search_template(text))
        elif text=="":
            self.showCategory(self.categoryCombo.currentText())

    def showTemplates(self, titles):
        # remove previous category templates
        for btn in reversed(self.template_buttons):# remove from last to first
            self.scrollLayout.removeWidget(btn)
            btn.deleteLater()
        self.template_buttons = []
        self.selected_button = None
        self.btnBox.button(QDialogButtonBox.Ok).setEnabled(False)# can not accept if no template is selected
        paper = Paper()
        #for template in templates:
        for title in titles:
            template = App.template_manager.templates[title]
            thumbnail = paper.renderObjects([template])
            btn = TemplateButton(template.name, thumbnail, self.scrollWidget)
            self.scrollLayout.addWidget(btn)
            btn.clicked.connect(self.onTemplateClick)
            btn.doubleClicked.connect(self.accept)
            btn.data = {"template":title}
            self.template_buttons.append(btn)


    def onTemplateClick(self, btn):
        # deselect previous button
        if self.selected_button:
            self.selected_button.setSelected(False)
        # select the clicked button
        btn.setSelected(True)
        self.selected_button = btn
        self.btnBox.button(QDialogButtonBox.Ok).setEnabled(True)


    def accept(self):
        # in rare case, double click event can occur without single click event,
        # then button is not selected
        if not self.selected_button:
            return
        self.selected_template = self.selected_button.data["template"]
        QDialog.accept(self)



class TemplateButton(PixmapButton):
    def __init__(self, title, thumbnail, parent):
        PixmapButton.__init__(self, parent)
        font = self.font()
        font.setPointSize(9)
        font_met = QFontMetrics(font)
        text_w, text_h = font_met.width(title), font_met.height()
        btn_w = max(text_w, thumbnail.width())
        btn_h = thumbnail.height() + text_h
        pm = QPixmap(btn_w, btn_h)
        pm.fill()
        painter = QPainter(pm)
        painter.setPen(Qt.blue)
        painter.setFont(font)
        painter.drawImage(int((btn_w-thumbnail.width())/2), 0, thumbnail)
        painter.drawText(QRect(0,thumbnail.height(), pm.width(), text_h), Qt.AlignHCenter, title)
        painter.end()
        PixmapButton.setPixmap(self,pm)



# ---------------------- Save Template Dialog -------------------

class SaveTemplateDialog(QDialog):
    filename_index = 0
    category_index = 0 # to remember current category combo
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Save Template")
        self.resize(320, 100)
        label1 = QLabel("Molecule Name :", self)
        self.nameEdit = QLineEdit(self)
        self.nameEdit.setPlaceholderText("eg. - cyclohexane")
        label3 = QLabel("Category :", self)
        self.categoryCombo = QComboBox(self)
        label4 = QLabel("Save to File :", self)
        self.filenameCombo = QComboBox(self)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel, self)
        # layout widgets
        layout = QGridLayout(self)
        layout.addWidget(label1, 0,0,1,1)
        layout.addWidget(self.nameEdit, 0,1,1,1)
        layout.addWidget(label3, 1,0,1,1)
        layout.addWidget(self.categoryCombo, 1,1,1,1)
        layout.addWidget(label4, 2,0,1,1)
        layout.addWidget(self.filenameCombo, 2,1,1,1)
        layout.addWidget(self.btnBox, 3,0,1,2)
        # connect signals
        self.btnBox.accepted.connect(self.onSaveClick)
        self.btnBox.rejected.connect(self.reject)

        template_dir = App.template_manager.USER_TEMPLATES_DIR
        files = os.listdir(template_dir)
        for templates_file in files:
            self.filenameCombo.addItem(templates_file, template_dir+"/"+templates_file)
        if self.filename_index < len(files):
            self.filenameCombo.setCurrentIndex(self.filename_index)
        self.categoryCombo.addItems([c.strip("s") for c in App.template_manager.categories])
        self.categoryCombo.setCurrentIndex(self.category_index)

    def onSaveClick(self):
        if not self.nameEdit.text():
            QMessageBox.warning(self, "Error !", "Molecule name can not be empty !")
            return
        if self.filenameCombo.count()==0:
            QMessageBox.warning(self, "Error !", "Save to File is empty. \nPlease create an User-Templates File!")
            dlg = NewTemplateFileDialog(self)
            if dlg.exec()!=dlg.Accepted:
                return self.reject()
        SaveTemplateDialog.filename_index = self.filenameCombo.currentIndex()
        SaveTemplateDialog.category_index = self.categoryCombo.currentIndex()
        self.accept()

    def getValues(self):
        name = self.nameEdit.text()
        category = self.categoryCombo.currentText()
        filename = self.filenameCombo.itemData(self.filenameCombo.currentIndex())
        return name, category, filename



# ---------------------- New Template File Dialog -------------------

class NewTemplateFileDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("New Template File")
        self.resize(200, 100)
        # add widgets
        label1 = QLabel("Enter Templates Filename :", self)
        self.filenameEdit = QLineEdit(self)
        extLabel = QLabel(".cctf", self)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel, self)
        # layout widgets
        layout = QGridLayout(self)
        layout.addWidget(label1, 0,0,1,2)
        layout.addWidget(self.filenameEdit, 1,0,1,1)
        layout.addWidget(extLabel, 1,1,1,1)
        layout.addWidget(self.btnBox, 2,0,1,2)
        # connect signals
        self.btnBox.accepted.connect(self.onAccept)
        self.btnBox.rejected.connect(self.reject)


    def onAccept(self):
        filename = self.filenameEdit.text()
        if not filename:
            QMessageBox.warning(self, "Error !", "Filename can not be empty !")
            return
        filename = App.template_manager.USER_TEMPLATES_DIR + "/" + filename + ".cctf"
        if os.path.exists(filename):
            QMessageBox.warning(self, "Error !", "File already exists ! \nUse a different filename")
            return

        ccdx = Ccdx()
        if ccdx.write(Document(), filename):
            self.filename = filename
            self.accept()
        else:# failed to write
            self.reject()




def search_template(text):
    """ search and show templates """
    if not text:
        return []
    text = text.lower()
    result1 = []# list of (title, priority) tuple
    result2 = []
    for title in App.template_manager.extended_templates:
        name = title.lower()
        if name.startswith(text):
            result1.append((title, len(title)))# shorter names have higher priority
        elif text in name:
            result2.append((title, len(title)))
    # sort the result, according to number of matched words
    result1 = sorted(result1, key=lambda x: x[1])
    result2 = sorted(result2, key=lambda x: x[1])
    return [x[0] for x in result1+result2]



class TemplateSearchWidget(QWidget):
    templateSelected = pyqtSignal(str)
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.setStyleSheet("TemplateSearchWidget{background-color: #cccccc;}")
        self.resize(600,304)
        self.table = QTableWidget(self)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(self.table.SelectRows)# required for table.selectRow()
        self.table.setSelectionMode(self.table.SingleSelection)
        self.table.horizontalHeader().setHidden(True)
        self.table.verticalHeader().setHidden(True)
        self.table.setColumnCount(1)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.viewport().setMouseTracking(True)# to enable hover event
        self.thumbnail = QLabel(self)
        pm = QPixmap(256,256)
        pm.fill()
        self.thumbnail.setPixmap(pm)
        self.statusbar = QLabel(self)
        self.autoPlacementBtn = QCheckBox("Place automatically", self)
        self.autoPlacementBtn.setChecked(True)
        # layout widgets
        layout = QGridLayout(self)
        layout.addWidget(self.table, 0,0,1,1)
        layout.addWidget(self.thumbnail, 0,1,1,1)
        layout.addWidget(self.statusbar, 2,0,1,1)
        layout.addWidget(self.autoPlacementBtn, 2,1,1,1)
        # connect signals
        self.table.entered.connect(self.onHover)
        self.table.itemSelectionChanged.connect(self.updateThumbnail)
        self.table.itemClicked.connect(self.onItemClick)

    def reposition(self):
        """ place just below searchBox """
        x = self.searchBox.pos().x()+self.searchBox.width()-self.width()
        y = self.searchBox.pos().y()+self.searchBox.height()*2
        self.move(x, y)

    def setSearchBox(self, searchBox):
        self.searchBox = searchBox
        searchBox.textChanged.connect(self.searchTemplate)
        searchBox.arrowPressed.connect(self.onArrowPress)
        searchBox.tabPressed.connect(self.useSelectedTemplate)
        searchBox.returnPressed.connect(self.useSelectedTemplate)
        self.reposition()

    def onArrowPress(self, key):
        """ move selection up or down by pressing arrow keys """
        items = self.table.selectedItems()
        if items:
            row = items[0].row()
            if key==Qt.Key_Up and row>0:
                self.table.selectRow(row-1)
            if key==Qt.Key_Down and row<self.table.rowCount()-1:
                self.table.selectRow(row+1)

    def onHover(self, index):
        """ select on hover """
        self.table.setCurrentIndex(index)
        self.table.selectRow(index.row())

    def onItemClick(self, tableitem):
        self.useSelectedTemplate()

    def useSelectedTemplate(self):
        items = self.table.selectedItems()
        if items:
            id = items[0].data(Qt.UserRole+1)
            if not id:
                template = items[0].data(Qt.UserRole)
                id = App.template_manager.add_to_extended_templates([template])[0]
            self.templateSelected.emit(id)

    def searchTemplate(self, text):
        """ search and show templates """
        if not text or len(text)<3:
            self.showTemplates([])# clear list
            return
        templates = search_template(text)
        #self.statusbar.setText("%i results found" % len(templates))
        self.showTemplates( templates)

    def webSearchTemplate(self):
        text = self.searchBox.text()
        if len(text)<3:
            return
        self.showTemplates([])# clear list
        self.statusbar.setText("Searching...")
        wait(100)
        try:
            # tutorial : https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial
            url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/%s/SDF"%text.replace(" ", "-")
            response = urllib.request.urlopen(url)
            result = response.read().decode("utf-8")
        except urllib.error.HTTPError:
            self.statusbar.setText("No result found")
            return
        except:
            self.statusbar.setText("Failed to connect to the internet")
            return
        reader = Molfile()
        doc = reader.readFromString(result)
        if doc:
            objs = doc.objects
            for obj in objs:
                remove_explicit_hydrogens(obj)
                obj.name = obj.data["PUBCHEM_IUPAC_NAME"]
                obj.data = None
            self.showTemplates( doc.objects)

    def showTemplates(self, templates):
        """ add list of templates to table. templates is a list of either te """
        if len(self.searchBox.text())>2:
            self.statusbar.setText("Found %i results" % len(templates))
        else:
            self.statusbar.setText("")
        self.table.setRowCount(len(templates))
        for i,tmpl in enumerate(templates):
            if type(tmpl)==str:# template id
                template = App.template_manager.templates[tmpl]
                template_id = tmpl
            else:# Molecule object
                template = tmpl
                template_id = None
            item = QTableWidgetItem(template.name)
            item.setData(Qt.UserRole, template)
            item.setData(Qt.UserRole+1, template_id)
            self.table.setItem(i, 0, item)
        # select first row
        if len(templates):
            self.table.selectRow(0)
            self.updateThumbnail()

    def updateThumbnail(self):
        pm = QPixmap(256,256)
        pm.fill()
        items = self.table.selectedItems()
        if not items:
            self.thumbnail.setPixmap(pm)
            return
        template = items[0].data(Qt.UserRole)
        paper = Paper()
        img = paper.renderObjects([template])
        if img.width()>pm.width() or img.height()>pm.height():
            img = img.scaled(pm.width(),pm.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter = QPainter(pm)
        painter.drawImage(int((pm.width()-img.width())/2), int((pm.height()-img.height())/2),img)
        painter.end()
        self.thumbnail.setPixmap(pm)

    def paintEvent(self, paint_ev):
        """ this function is needed, otherwise stylesheet is not applied properly """
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)
