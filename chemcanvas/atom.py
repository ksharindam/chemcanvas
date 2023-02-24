from PyQt5.QtCore import Qt

from app_data import App, periodic_table
from drawable import DrawableObject
from graph import Vertex
from geometry import *

global atom_id_no
atom_id_no = 1


class Atom(Vertex, DrawableObject):
    object_type = 'Atom'
    focus_priority = 1
    redraw_priority = 1
    meta__undo_properties = ("formula", "is_group", "x", "y", "z", "valency",
            "occupied_valency", "text", "text_center", "show_symbol", "show_hydrogens")
    meta__undo_copy = ("_neighbors",)

    def __init__(self, formula):
        DrawableObject.__init__(self)
        Vertex.__init__(self)
        self.x, self.y, self.z = 0,0,0
        # Properties
        self.molecule = None
        self.formula = formula
        self.is_group = len(formula_to_atom_list(formula)) > 1
        self.valency = 0
        self.occupied_valency = 0
        self._update_valency()
        # inherited properties from Vertex
        # self.neighbors = []
        # self.neighbor_edges = [] # connected edges
        # self.edges = [] # all edges
        # Drawing Properties
        self.text = None
        self.text_center = None # vals - "first-atom" | "last-atom"
        self.show_symbol = formula!='C' # invisible Carbon atom
        self.show_hydrogens = True
        # generate unique id
        global atom_id_no
        self.id = 'a' + str(atom_id_no)
        atom_id_no += 1
        # drawing related
        self._select_item = None
        self._focus_item = None
        #self.paper = None

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

    @property
    def pos3d(self):
        return [self.x, self.y, self.z]

    def setPos(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    def addNeighbor(self, atom, bond):
        # to be called inside Bond class only
        Vertex.addNeighbor(self, atom, bond)
        self._update_occupied_valency()

    def removeNeighbor(self, atom):
        # to be called inside Bond class only
        Vertex.removeNeighbor(self, atom)
        self._update_occupied_valency()

    def eatAtom(self, atom2):
        """ merge src atom (atom2) with this atom, and merges two molecules also. """
        print("merge %s with %s" % (self, atom2))
        self.molecule.eatMolecule(atom2.molecule)
        # disconnect the bonds from atom2, and reconnect to this atom
        for bond in atom2.bonds:
            bond.replaceAtom(atom2, self)
        # remove atom2
        self.molecule.removeAtom(atom2)
        atom2.deleteFromPaper()

    def clearDrawings(self):
        #if not self.paper:# we have not drawn yet
        #    return
        if self.graphics_item:
            self.paper.removeFocusable(self.graphics_item)
            self.paper.removeItem(self.graphics_item)
            self.graphics_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._select_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._select_item)
        self.clearDrawings()
        self.paper = self.molecule.paper
        # draw
        if self.text == None:
            self._update_text()
        if self.text == "": # hidden symbol for carbon
            self.graphics_item = self.paper.addEllipse(self.x-4, self.y-4, 9, 9, 1, Qt.transparent)
        else:
            self.graphics_item = self.paper.addFormulaText(self.text, [self.x, self.y])
        self.paper.addFocusable(self.graphics_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def boundingBox(self):
        """returns the bounding box of the object as a list of [x1,y1,x2,y2]"""
        #if self.show:
        #   return drawable_chem_vertex.bbox( self, substract_font_descent=substract_font_descent)
        #else:
        if self.graphics_item:
            # QGgraphicsSimpleTextItem.boundingRect() has always x=0, y=0
            x,y = self.graphics_item.pos().x(), self.graphics_item.pos().y()
            x1,y1,x2,y2 = self.graphics_item.boundingRect().getCoords()
            return [x+x1, y+y1, x+x2, y+y2]
        else:
            return [self.x, self.y, self.x, self.y]


    def setFocus(self, focus):
        if focus:
            self._focus_item = self.paper.addEllipse(self.x-4, self.y-4, 9, 9, 5, Qt.black)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            self._select_item = self.paper.addEllipse(self.x-4, self.y-4, 9, 9, 3, Qt.blue)
            self.paper.toBackground(self._select_item)
        else:
            self.paper.removeItem(self._select_item)
            self._select_item = None

    def translateDrawings(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy
        items = filter(None, [self.graphics_item, self._focus_item, self._select_item])
        [item.moveBy(dx,dy) for item in items]

    def setFormula(self, formula):
        self.formula = formula
        if not self.show_symbol and formula != "C":
            self.show_symbol = True
        atom_list = formula_to_atom_list(formula)
        self.is_group = len(atom_list) > 1
        #self.show_hydrogens = not self.is_group
        self._update_valency()
        self.text = None

    def _update_valency(self):
        if self.formula not in periodic_table:
            self.valency = 0
            return
        valencies = periodic_table[self.formula]["valency"]
        for val in valencies:
            if val >= self.occupied_valency:
                self.valency = val
                break

    def _update_occupied_valency(self):
        occupied_valency = 0
        for bond in self.bonds:
            occupied_valency += bond.order
        if occupied_valency == self.occupied_valency:
            return
        # occuped valency changed
        self.occupied_valency = occupied_valency
        if self.occupied_valency > self.valency:
            self._update_valency()
        if self.show_hydrogens: # text needs to be updated
            self.text = None

    @property
    def free_valency(self):
        return self.valency - self.occupied_valency


    def _update_text(self):
        if not self.show_symbol:
            self.text = ""
            return
        self.text = self.formula
        free_valency = self.valency - self.occupied_valency
        if self.show_hydrogens and free_valency>=1:
            self.text += free_valency==1 and "H" or "H%i"%free_valency
        if self.text_center==None:
            self._decide_text_center()
        if self.text_center == "last-atom":
            self.text = get_reverse_formula(self.text)

    def resetText(self):
        self.text = None

    def resetTextLayout(self):
        self.text_center = None
        self.text = None

    def _decide_text_center(self):
        """ decides whether the first or the last atom should be positioned at self.pos """
        #if self.is_part_of_linear_fragment():
        #    self.text_center = "first-atom"
        #    return
        p = 0
        for atom in self.neighbors:
            if atom.x < self.x:
                p -= 1
            elif atom.x > self.x:
                p += 1
        if p > 0:
            self.text_center = "last-atom"
        else:
            self.text_center = "first-atom"

    def redrawNeeded(self):
        return self.text==None

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("atom")
        elm.setAttribute("id", self.id)
        elm.setAttribute("x", str(self.x))
        elm.setAttribute("y", str(self.y))
        elm.setAttribute("formula", self.formula)
        elm.setAttribute("show_symbol", str(self.show_symbol))
        parent.appendChild(elm)
        return elm

    def readXml(self, atom_elm):
        uid = atom_elm.getAttribute("id")
        if uid:
            App.id_to_object_map[uid] = self
        formula = atom_elm.getAttribute("formula")
        if formula:
            self.setFormula(formula)
        show_symbol = atom_elm.getAttribute("show_symbol")
        if show_symbol:
            self.show_symbol = show_symbol=="True"
        try:
            self.x = float(atom_elm.getAttribute("x"))
            self.y = float(atom_elm.getAttribute("y"))
            self.z = float(atom_elm.getAttribute("z"))
        except:
            pass

    def copy(self):
        """ copy all properties except neighbors (atom:bond).
        because new atom can not be attached to same neighbors as this atom """
        new_atom = Atom(self.formula)
        for attr in self.meta__undo_properties:
            setattr(new_atom, attr, getattr(self, attr))
        return new_atom



def formula_to_atom_list(formula):
    l = list(formula)
    atom_list = [l.pop(0)]
    for item in l:
        if item.isupper():# new atom
            atom_list.append(item)
        else: # part of prev atom
            atom_list[-1] = atom_list[-1]+item
    return atom_list

def get_reverse_formula(formula):
    atom_list = formula_to_atom_list(formula)
    atom_list.reverse()
    return "".join(atom_list)

