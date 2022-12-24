from PyQt5.QtCore import Qt, QLineF, QPoint
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem

from app_data import App
from drawable import DrawableObject
from graph import Vertex
from geometry import *

global atom_id_no
atom_id_no = 1

class Atom(Vertex, DrawableObject):
    obj_type = 'Atom'
    focus_priority = 1
    def __init__(self, molecule, pos):
        DrawableObject.__init__(self)
        Vertex.__init__(self)
        self.molecule = molecule
        self.x, self.y = pos
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
        self._select_item = None
        self._focus_item = None

    def __str__(self):
        return self.id

    @property
    def parent(self):
        return self.molecule

    @property
    def bonds(self):
        return self.edges

    @property
    def pos(self):
        return [self.x, self.y]

    @pos.setter
    def pos(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    @property
    def pos3d(self):
        return [self.x, self.y, self.z]

    @pos3d.setter
    def pos3d(self, pos):
        self.x, self.y, self.z = pos

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
        # atom2 may be selected/focused, it must be deselected/unfocused then
        #App.paper.clearFocus()
        #App.paper.clearSelection()
        atom2.clearDrawings()

    def clearDrawings(self):
        if self.graphics_item:
            App.paper.removeObject(self)
        if self._focus_item:
            self.setFocus(False)
        if self._select_item:
            self.setSelected(False)

    def draw(self):
        if self.graphics_item:
            print("Warning drawing atom %s which is already drawn" % self)
            return
        self.graphics_item = App.paper.addEllipse(self.x-4, self.y-4, 9, 9, 1, Qt.transparent)

    def redraw(self):
        focused = bool(self._focus_item)
        selected = bool(self._select_item)
        self.clearDrawings()
        self.draw()
        App.paper.addObject(self)
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            self._focus_item = App.paper.addEllipse(self.x-4, self.y-4, 9, 9, 5, Qt.black)
        else:
            App.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            self._select_item = App.paper.addEllipse(self.x-4, self.y-4, 9, 9, 3, Qt.blue)
            App.paper.toBackground(self._select_item)
        else:
            App.paper.removeItem(self._select_item)
            self._select_item = None

    def boundingBox(self):
        """returns the bounding box of the object as a list of [x1,y1,x2,y2]"""
        #if self.show:
        #   return drawable_chem_vertex.bbox( self, substract_font_descent=substract_font_descent)
        #else:
        if self.graphics_item:
            return self.graphics_item.boundingRect().getCoords()
        else:
            return [self.x, self.y, self.x, self.y]

    def moveTo(self, pos):
        """ move and redraw """
        if pos == [self.x, self.y]:
            return
        self.x, self.y = pos[0], pos[1]

        self.redraw()
        for bond in self.bonds:
            bond.redraw()

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy
        items = filter(None, [self.graphics_item, self._focus_item, self._select_item])
        [item.moveBy(dx,dy) for item in items]
        for bond in self.bonds:
            bond.redraw()

