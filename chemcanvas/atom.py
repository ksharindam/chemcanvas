from PyQt5.QtCore import Qt, QLineF, QPoint
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtWidgets import QGraphicsLineItem

from app_data import App
from graph import Vertex
from geometry import *

global atom_id_no
atom_id_no = 1

class Atom(Vertex):
    obj_type = 'Atom'
    focus_priority = 1
    def __init__(self, molecule, pos):
        Vertex.__init__(self)
        self.molecule = molecule
        self.pos = pos
        self.z = 0
        # Properties
        self.element = 'C'
        self.show = False # invisible Carbon atom
        self.show_hydrogens = False
        self.is_group = False
        self.group_text = ''
        self.text_pos = 'center-first' # center the first letter
        global atom_id_no
        self.id = 'atom' + str(atom_id_no)
        atom_id_no += 1
        # drawing related
        self.graphics_item = None
        self.focus_item = None

    def __str__(self):
        return self.id

    @property
    def bonds(self):
        return self.edges

    @property
    def coords(self):
        return [self.x, self.y]

    @property
    def pos(self):
        return QPoint(self.x, self.y)

    @pos.setter
    def pos(self, val : QPoint):
        self.x = val.x()
        self.y = val.y()

    def moveTo(self, pos):
        """ move and redraw """
        if self.x == pos.x() and self.y == pos.y():
            return
        self.x, self.y = pos.x(), pos.y()
        self.draw()
        for bond in self.bonds:
            bond.redraw()

    def addBond(self, bond):
        if bond in self.bonds:
            print("warning : adding %s to %s which is already added" % (bond, self))
        self.addNeighbor( bond.atomConnectedTo(self), bond)

    def removeBond(self, bond):
        """ remove bond from atom, but dont remove atom from bond """
        self.removeEdge(bond)

    def merge(self, atom2):
        """ merge src atom (atom2) with this atom, and merges two molecules also """
        print("merge %s with %s" % (self, atom2))
        if self.molecule is not atom2.molecule:
            mol2 = atom2.molecule
            # move all atoms of src molecule to dest molecule
            for atom in mol2.atoms:
                self.molecule.addAtom(atom)
            mol2.atoms.clear()

            # move all bonds of src molecule to dest molecule
            self.molecule.bonds |= mol2.bonds
            mol2.bonds.clear()

        # disconnect the bonds from atom2, and connect to this atom
        for bond in atom2.bonds:
            bond.replaceAtom(atom2, self)
        # remove atom2
        self.molecule.removeAtom(atom2)
        atom2.clearDrawings()

    def draw(self):
        self.clearDrawings()
        self.graphics_item = QGraphicsLineItem(QLineF(self.pos, self.pos))
        self.graphics_item.setPen(Qt.transparent)
        #App.paper.setItemColor(self.graphics_item, Qt.transparent)
        App.paper.addItem(self.graphics_item)

    def clearDrawings(self):
        if self.graphics_item:
            App.paper.removeDrawable(self)
        if self.focus_item:
            App.paper.removeItem(self.focus_item)
            self.focus_item = None

    def setFocus(self, focus):
        if focus:
            pen = QPen(Qt.black, 5)
            self.graphics_item.setPen(pen)
        else:
            self.graphics_item.setPen(Qt.transparent)

    def boundingBox(self):
        """returns the bounding box of the object as a list of [x1,y1,x2,y2]"""
        #if self.show:
        #   return drawable_chem_vertex.bbox( self, substract_font_descent=substract_font_descent)
        #else:
        if self.graphics_item:
            return Rect(self.graphics_item.boundingRect().getCoords())
        else:
            return Rect([self.x, self.y, self.x, self.y])

