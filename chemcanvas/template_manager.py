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
    QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QScrollArea, QDialogButtonBox, QAction)

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


def get_template_title(template):
    ''' returns title in "name(variant)" format . eg - "cyclohexane(chair)", "cyclohexane" '''
    return template.variant and template.name+"("+template.variant+")" or template.name


class TemplateManager:
    def __init__(self):
        # key format "name(variant) index" . eg - "cyclohexane(chair)", "cyclohexane(chair) 1"
        # index is used when two templates have same name and variant
        self.templates = {}
        self.current = None # current selected template
        # ordered list of template names
        self.basic_templates = [] # basic set
        self.recent_templates = []
        # directories
        self.APP_TEMPLATES_DIR = App.SRC_DIR + "/templates"
        self.USER_TEMPLATES_DIR = App.DATA_DIR + "/templates"
        if not os.path.exists(self.USER_TEMPLATES_DIR):
            os.mkdir(self.USER_TEMPLATES_DIR)

        # read all templates
        basic_templates_file = self.APP_TEMPLATES_DIR + "/templates.cctf"
        basic_templates = self.readTemplatesFile(basic_templates_file)
        self.basic_templates = self.addTemplates(basic_templates)

        for template_dir in [self.APP_TEMPLATES_DIR, self.USER_TEMPLATES_DIR]:
            files = os.listdir(template_dir)
            files = [ template_dir+"/"+f for f in files if f.endswith(".cctf") ]
            for templates_file in files:
                if templates_file != basic_templates_file:
                    templates = self.readTemplatesFile(templates_file)
                    self.addTemplates(templates)


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
            title = get_template_title(mol)
            key = title
            i = 1
            while key in self.templates:
                key = "%s %i" % (title, i)
                i += 1
            self.templates[key] = mol
            titles.append(key)
        return titles


    def getTransformedTemplate(self, coords, place_on="Paper"):
        current = self.current.deepcopy()
        scale_ratio = 1
        trans = geo.Transform()
        # just place the template on paper
        if place_on == "Paper":
            xt1, yt1 = current.template_atom.pos
            xt2, yt2 = current.template_atom.neighbors[0].pos
            scale_ratio = Settings.bond_length / math.sqrt( (xt1-xt2)**2 + (yt1-yt2)**2)
            trans.translate( -xt1, -yt1)
            trans.scale(scale_ratio)
            trans.translate( coords[0], coords[1])
        else:
            if place_on == "Bond":
                xt1, yt1 = current.template_bond.atom1.pos
                xt2, yt2 = current.template_bond.atom2.pos
                #find appropriate side of bond to append template to
                atom1, atom2 = current.template_bond.atoms
                atms = atom1.neighbors + atom2.neighbors
                atms = set(atms) - set([atom1,atom2])
                points = [a.pos for a in atms]
                if reduce( operator.add, [geo.line_get_side_of_point( (xt1,yt1,xt2,yt2), xy) for xy in points], 0) < 0:
                    xt1, yt1, xt2, yt2 = xt2, yt2, xt1, yt1
            else:# place_on == "Atom"
                xt1, yt1 = current.template_atom.pos
                xt2, yt2 = current.findPlace(current.template_atom, geo.point_distance(current.template_atom.pos, current.template_atom.neighbors[0].pos))
            x1, y1, x2, y2 = coords
            scale_ratio = math.sqrt( ((x1-x2)**2 + (y1-y2)**2) / ((xt1-xt2)**2 + (yt1-yt2)**2) )
            trans.translate( -xt1, -yt1)
            trans.rotate( math.atan2( xt1-xt2, yt1-yt2) - math.atan2( x1-x2, y1-y2))
            trans.scale(scale_ratio)
            trans.translate(x1, y1)

        for a in current.atoms:
            a.x, a.y = trans.transform(a.x, a.y)
            #a.scale_font( scale_ratio)
        #for b in current.bonds:
        #    if b.order != 1:
        #        b.second_line_distance *= scale_ratio
        # update template according to current default values
        #App.paper.applyDefaultProperties( [temp], template_mode=1)
        return current

    def selectTemplate(self, name):
        self.current = self.templates[name]

    def getTemplateValency(self):
        return self.current.template_atom.occupied_valency



# ---------------------- Template Manager Dialog -------------------

class TemplateManagerDialog(QDialog):
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
        self.selected_templates = []
        self.last_selected_button = None
        # add template file names to filename combo
        for filename in self.getTemplateFilenames():
            self.filenameCombo.addItem(os.path.basename(filename), filename)


    def readCurrentTemplatesFile(self):
        # remove previous template buttons
        for btn in self.template_buttons:
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
        filename, ok = QInputDialog.getText(self, "New Template File", "Enter Template Filename :")
        if not ok or not filename:
            return
        # find a writable template path
        dest_dir = App.template_manager.USER_TEMPLATES_DIR

        filename = dest_dir + "/" + filename + ".cctf"
        ccdx = Ccdx()
        if ccdx.write(Document(), filename):
            self.filenameCombo.addItem(os.path.basename(filename), filename)


    def getTemplateFilenames(self):
        template_dir = App.template_manager.USER_TEMPLATES_DIR
        if not os.access(template_dir, os.W_OK | os.X_OK):
            return []
        files = os.listdir(template_dir)
        return [ template_dir+"/"+f for f in files if f.endswith(".cctf") ]


    def newTemplate(self):
        QMessageBox.warning(self, "Not Implemented !", "Feature not implemented !")

    def deleteTemplate(self):
        if len(self.selected_templates) == 1:
            title = get_template_title(self.selected_templates[0].template)
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


    def keyPressEvent(self, ev):
        self.pressed_keys.append(ev.key())

    def keyReleaseEvent(self, ev):
        try:# in some cases key release event happens without key press event
            self.pressed_keys.remove(ev.key())
        except: pass

    def onTemplateClick(self):
        btn = self.sender()
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
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Templates")
        self.resize(500, 350)
        topContainer = QWidget(self)
        topContainerLayout = QHBoxLayout(topContainer)
        topContainerLayout.setContentsMargins(0,0,0,0)
        self.typeCombo = QComboBox(topContainer)
        topContainerLayout.addWidget(self.typeCombo)
        topContainerLayout.addStretch()
        #categories = ["Amino Acids", "Sugars", "Nitrogen Base", "Heterocyles"]
        self.typeCombo.addItems(["All"])
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollWidget.setGeometry(0, 0, 397, 373)
        scrollLayout = FlowLayout(self.scrollWidget)#QHBoxLayout(self.scrollWidget)
        #scrollLayout.setContentsMargins(6, 6, 6, 6)
        self.scrollArea.setWidget(self.scrollWidget)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel, self)
        layout = QVBoxLayout(self)
        layout.addWidget(topContainer)
        layout.addWidget(self.scrollArea)
        layout.addWidget(self.btnBox)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)

        # add template buttons here

