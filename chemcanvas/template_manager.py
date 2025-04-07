# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os
import math
import operator
from functools import reduce

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QToolButton, QMenu, QInputDialog, QMessageBox, QDialog,
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGridLayout, QComboBox, QScrollArea, QDialogButtonBox, QAction,
    QLineEdit)

from app_data import App, Settings
from fileformat import Document, Ccdx
from widgets import FlowLayout, PixmapButton
from paper import Paper
import geometry as geo


def find_template_icon(icon_name):
    """ find and return full path of an icon file. returns empty string if not found """
    template_dir = App.template_manager.APP_TEMPLATES_DIR
    icon_path = template_dir + "/" + icon_name + ".png"
    if os.path.exists(icon_path):
        return icon_path
    return ""




class TemplateManager:
    # molecule categories
    categories = ["Hydrocarbon", "Heterocycle", "Amino Acid", "Sugar", "Nitrogen Base", "Other"]

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
        basic_templates = self.readTemplatesFile(basic_templates_file)
        self.basic_templates = self.addTemplates(basic_templates)

        for template_dir in [self.APP_TEMPLATES_DIR, self.USER_TEMPLATES_DIR]:
            files = os.listdir(template_dir)
            files = [ template_dir+"/"+f for f in files if f.endswith(".cctf") ]
            for templates_file in files:
                if templates_file != basic_templates_file:
                    templates = self.readTemplatesFile(templates_file)
                    titles = self.addTemplates(templates)
                    self.extended_templates += titles


    def readTemplatesFile(self, filename):
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


    def addTemplates(self, templates):
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


    def getTransformedTemplate(self, template, coords, place_on="Paper"):
        template = template.deepcopy()
        scale_ratio = 1
        trans = geo.Transform()
        # just place the template on paper
        if place_on == "Paper":
            xt1, yt1 = template.template_atom.pos
            xt2, yt2 = template.template_atom.neighbors[0].pos
            scale_ratio = Settings.bond_length / math.sqrt( (xt1-xt2)**2 + (yt1-yt2)**2)
            trans.translate( -xt1, -yt1)
            trans.scale(scale_ratio)
            trans.translate( coords[0], coords[1])
        else:
            if place_on == "Bond":
                xt1, yt1 = template.template_bond.atom1.pos
                xt2, yt2 = template.template_bond.atom2.pos
                #find appropriate side of bond to append template to
                atom1, atom2 = template.template_bond.atoms
                atms = atom1.neighbors + atom2.neighbors
                atms = set(atms) - set([atom1,atom2])
                points = [a.pos for a in atms]
                if reduce( operator.add, [geo.line_get_side_of_point( (xt1,yt1,xt2,yt2), xy) for xy in points], 0) < 0:
                    xt1, yt1, xt2, yt2 = xt2, yt2, xt1, yt1
            else:# place_on == "Atom"
                xt1, yt1 = template.template_atom.pos
                xt2, yt2 = template.find_place(template.template_atom, geo.point_distance(template.template_atom.pos, template.template_atom.neighbors[0].pos))
            x1, y1, x2, y2 = coords
            scale_ratio = math.sqrt( ((x1-x2)**2 + (y1-y2)**2) / ((xt1-xt2)**2 + (yt1-yt2)**2) )
            trans.translate( -xt1, -yt1)
            trans.rotate( math.atan2( xt1-xt2, yt1-yt2) - math.atan2( x1-x2, y1-y2))
            trans.scale(scale_ratio)
            trans.translate(x1, y1)

        for a in template.atoms:
            a.x, a.y = trans.transform(a.x, a.y)
            #a.scale_font( scale_ratio)
        #for b in template.bonds:
        #    if b.order != 1:
        #        b.second_line_distance *= scale_ratio
        # update template according to current default values
        #App.paper.applyDefaultProperties( [temp], template_mode=1)
        return template


    def saveTemplate(self, template_mol):
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
            titles = self.addTemplates([template_mol])
            self.extended_templates += titles



# ---------------------- Template Manager Dialog -------------------

class TemplateManagerDialog(QDialog):
    """ This dialog allows creation, deletion of template files, and deletion
    of template molecules. New templates option only shows how to add template """
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Template Manager")
        self.resize(500, 350)
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
        templates = App.template_manager.readTemplatesFile(filename)
        paper = Paper()
        for template in templates:
            btn = PixmapButton(self.scrollWidget)
            thumbnail = paper.renderObjects([template])
            btn.setPixmap(QPixmap.fromImage(thumbnail))
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
        self.resize(500, 350)
        topContainer = QWidget(self)
        topContainerLayout = QHBoxLayout(topContainer)
        topContainerLayout.setContentsMargins(0,0,0,0)
        self.categoryCombo = QComboBox(topContainer)
        topContainerLayout.addWidget(self.categoryCombo)
        topContainerLayout.addStretch()
        self.categoryCombo.addItems(["All"] + App.template_manager.categories)
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollWidget.setGeometry(0, 0, 397, 373)
        self.scrollLayout = FlowLayout(self.scrollWidget)
        self.scrollLayout.setContentsMargins(6, 6, 6, 6)
        self.scrollArea.setWidget(self.scrollWidget)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel, self)
        # layout widgets
        layout = QVBoxLayout(self)
        layout.addWidget(topContainer)
        layout.addWidget(self.scrollArea)
        layout.addWidget(self.btnBox)
        # connect signals
        self.categoryCombo.currentTextChanged.connect(self.onCategoryChange)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)
        # init variables
        self.template_buttons = [] # used to remove buttons later
        self.selected_button = None
        # if total number of templates are less, then 'All' templates should be shown.
        # else first non empty category should be shown
        if self.category_index==0:
            self.onCategoryChange("All")
        else:
            self.categoryCombo.setCurrentIndex(self.category_index)


    def onCategoryChange(self, category):
        # to remember selected category
        TemplateChooserDialog.category_index = self.categoryCombo.currentIndex()
        # remove previous category templates
        for btn in reversed(self.template_buttons):# remove from last to first
            self.scrollLayout.removeWidget(btn)
            btn.deleteLater()
        self.template_buttons = []
        self.selected_button = None
        self.btnBox.button(QDialogButtonBox.Ok).setEnabled(False)# can not accept if no template is selected
        # add template buttons to scrollwidget
        titles = App.template_manager.extended_templates
        if category!="All":
            titles = list(filter(lambda x:App.template_manager.templates[x].category==category, titles))

        paper = Paper()
        #for template in templates:
        for title in titles:
            template = App.template_manager.templates[title]
            btn = PixmapButton(self.scrollWidget)
            thumbnail = paper.renderObjects([template])
            btn.setPixmap(QPixmap.fromImage(thumbnail))
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
        self.selected_template = self.selected_button.data["template"]
        QDialog.accept(self)



# ---------------------- Save Template Dialog -------------------

class SaveTemplateDialog(QDialog):
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
        self.categoryCombo.addItems(App.template_manager.categories)
        # select other category by default
        self.categoryCombo.setCurrentIndex(self.categoryCombo.count()-1)


    def onSaveClick(self):
        if not self.nameEdit.text():
            QMessageBox.warning(self, "Error !", "Molecule name can not be empty !")
            return
        if self.filenameCombo.count()==0:
            QMessageBox.warning(self, "Error !", "Save to File is empty. \nPlease create an User-Templates File!")
            dlg = NewTemplateFileDialog(self)
            if dlg.exec()!=dlg.Accepted:
                return self.reject()
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
