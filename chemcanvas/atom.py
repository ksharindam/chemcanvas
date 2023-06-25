# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings, periodic_table
from drawing_parents import DrawableObject, Color, Font
from graph import Vertex
from marks import Charge, Electron
from common import float_to_str

global atom_id_no
atom_id_no = 1


class Atom(Vertex, DrawableObject):
    focus_priority = 3
    redraw_priority = 2
    is_toplevel = False
    meta__undo_properties = ("symbol", "is_group", "molecule", "x", "y", "z", "valency",
            "occupied_valency", "_text", "text_anchor", "show_symbol", "show_hydrogens")
    meta__undo_copy = ("_neighbors", "marks")
    meta__undo_children_to_record = ("marks",)
    meta__scalables = ("x", "y", "z", "font_size")

    def __init__(self, symbol='C'):
        DrawableObject.__init__(self)
        Vertex.__init__(self)
        self.x, self.y, self.z = 0,0,0
        # Properties
        self.molecule = None
        self.marks = []
        self.symbol = symbol
        self.is_group = len(formula_to_atom_list(symbol)) > 1
        self.valency = 0
        self.occupied_valency = 0
        self._update_valency()
        # inherited properties from Vertex
        # self.neighbors = []
        # self.neighbor_edges = [] # connected edges
        # self.edges = [] # all edges
        # Drawing Properties
        self._text = None
        self.text_anchor = None # vals - "start" | "end" (like svg)
        self.show_symbol = symbol!='C' # invisible Carbon atom
        self.show_hydrogens = True
        # generate unique id
        global atom_id_no
        self.id = 'a' + str(atom_id_no)
        atom_id_no += 1
        # drawing related
        self.font_size = 9# default 9pt in Qt
        self._main_item = None
        self._focusable_item = None
        self._focus_item = None
        self._selection_item = None
        #self.paper = None
        # for smiles
        self.isotope = None
        self.charge = 0
        self.multiplicity = 1 # what is this?
        self.explicit_hydrogens = 0

    def __str__(self):
        return self.id

    @property
    def parent(self):
        return self.molecule

    @property
    def children(self):
        return self.marks

    @property
    def bonds(self):
        return self.edges

    @property
    def pos(self):
        return self.x, self.y

    @property
    def pos3d(self):
        return self.x, self.y, self.z

    def setPos(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    def addNeighbor(self, atom, bond):
        # to be called inside Bond class only
        Vertex.add_neighbor(self, atom, bond)
        self.update_occupied_valency()

    def removeNeighbor(self, atom):
        # to be called inside Bond class only
        Vertex.remove_neighbor(self, atom)
        self.update_occupied_valency()

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

    @property
    def items(self):
        return filter(None, [self._main_item, self._focusable_item,
            self._focus_item, self._selection_item])

    def clearDrawings(self):
        if self._main_item:
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._focusable_item:
            self.paper.removeFocusable(self._focusable_item)
            self.paper.removeItem(self._focusable_item)
            self._focusable_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()

        self.paper = self.molecule.paper
        # draw
        self._main_item = self.drawOnPaper(self.paper)

        # add item used to receive focus
        rect = self.x-4, self.y-4, self.x+4, self.y+4
        self._focusable_item = self.paper.addRect(rect, color=Color.transparent)
        self.paper.addFocusable(self._focusable_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        if self._text == None:# text not determined
            self._update_text()
        # invisible carbon symbol
        if not self._text:
            return
        # visible symbol
        font = Font(Settings.atom_font_name, Settings.atom_font_size*self.molecule.scale_val)
        return paper.addChemicalFormula(self._text, (self.x, self.y), self.text_anchor, font=font)


    def boundingBox(self):
        """returns the bounding box of the object as a list of [x1,y1,x2,y2]"""
        if self._main_item:
            return self.paper.itemBoundingBox(self._main_item)
        return [self.x, self.y, self.x, self.y]


    def setFocus(self, focus):
        if focus:
            if self._text:
                self._focus_item = self.paper.addRect(self.boundingBox(), fill=Settings.focus_color)
            else:
                rect = self.x-5, self.y-5, self.x+5, self.y+5
                self._focus_item = self.paper.addEllipse(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            if self._main_item:
                rect = self.paper.itemBoundingBox(self._main_item)
            else:
                rect = self.x-4, self.y-4, self.x+4, self.y+4
            self._selection_item = self.paper.addEllipse(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def setSymbol(self, symbol):
        self.symbol = symbol
        if not self.show_symbol and symbol != "C":
            self.show_symbol = True
        atom_list = formula_to_atom_list(symbol)
        self.is_group = len(atom_list) > 1
        #self.show_hydrogens = not self.is_group
        self._update_valency()
        self._text = None

    def _update_valency(self):
        if self.symbol not in periodic_table:
            self.valency = 0
            return
        valencies = periodic_table[self.symbol]["valency"]
        for val in valencies:
            if val >= self.occupied_valency:
                self.valency = val
                break

    def update_occupied_valency(self):
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
            self._text = None

    @property
    def free_valency(self):
        return self.valency - self.occupied_valency

    def raise_valency( self):
        """used in case where valency < occupied_valency to try to find a higher one"""
        for v in periodic_table[ self.symbol]['valency']:
            if v > self.valency:
                self.valency = v
                return True
        return False

    def raise_valency_to_senseful_value( self):
        """set atoms valency to the lowest possible, so that free_valency
        if non-negative (when possible) or highest possible,
        does not lower valency when set to higher then necessary value"""
        while self.free_valency < 0:
            if not self.raise_valency():
                return

    def _update_text(self):
        if not self.show_symbol:
            self._text = ""
            return
        self._text = self.symbol
        free_valency = self.valency - self.occupied_valency
        if self.show_hydrogens and free_valency>=1:
            self._text += free_valency==1 and "H" or "H%i"%free_valency
        if self.text_anchor==None:
            self._decide_anchor_pos()
        if self.text_anchor == "end":
            self._text = get_reverse_formula(self._text)


    def resetText(self):
        self._text = None

    def resetTextLayout(self):
        self.text_anchor = None
        self._text = None

    def _decide_anchor_pos(self):
        """ decides whether the first or the last atom should be positioned at self.pos """
        #if self.is_part_of_linear_fragment():# TODO
        #    self.text_anchor = "start"
        #    return
        p = 0
        for atom in self.neighbors:
            if atom.x < self.x:
                p -= 1
            elif atom.x > self.x:
                p += 1
        if p > 0:
            self.text_anchor = "end"
        else:
            self.text_anchor = "start"

    def redrawNeeded(self):
        return self._text==None


    def copy(self):
        """ copy all properties except neighbors (atom:bond).
        because new atom can not be attached to same neighbors as this atom """
        new_atom = Atom(self.symbol)
        for attr in self.meta__undo_properties:
            setattr(new_atom, attr, getattr(self, attr))
        return new_atom

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def scale(self, scale):
        pass


    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("atom")
        elm.setAttribute("id", self.id)
        elm.setAttribute("x", float_to_str(self.x))
        elm.setAttribute("y", float_to_str(self.y))
        elm.setAttribute("sym", self.symbol)
        elm.setAttribute("show_C", str(int(self.show_symbol)))
        parent.appendChild(elm)
        # add marks
        for child in self.children:
            child.addToXmlNode(elm)

        return elm

    def readXml(self, elm):
        uid = elm.getAttribute("id")
        if uid:
            App.id_to_object_map[uid] = self
        symbol = elm.getAttribute("sym")
        if symbol:
            self.setSymbol(symbol)
        show_symbol = elm.getAttribute("show_C")
        if show_symbol:
            self.show_symbol = bool(int(show_symbol))
        try:
            self.x = float(elm.getAttribute("x"))
            self.y = float(elm.getAttribute("y"))
            self.z = float(elm.getAttribute("z"))
        except:
            pass
        # create marks
        marks_class_dict = {"charge" : Charge, "electron" : Electron}
        for tagname, MarkClass in marks_class_dict.items():
            elms = elm.getElementsByTagName(tagname)
            for elm in elms:
                mark = MarkClass()
                mark.readXml(elm)
                mark.atom = self
                self.marks.append(mark)



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

