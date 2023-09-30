# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings, periodic_table
from drawing_parents import DrawableObject, Color, Font, Align
from graph import Vertex
from common import find_matching_parentheses

import re

global atom_id_no
atom_id_no = 1


class Atom(Vertex, DrawableObject):
    focus_priority = 3
    redraw_priority = 2
    is_toplevel = False
    meta__undo_properties = ("symbol", "is_group", "molecule", "x", "y", "z", "valency",
            "occupied_valency", "_text", "text_layout", "auto_text_layout", "show_symbol",
            "hydrogens", "auto_hydrogens", "auto_valency", "isotope", "color")
    meta__undo_copy = ("_neighbors", "marks")
    meta__undo_children_to_record = ("marks",)
    meta__scalables = ("x", "y", "z")

    def __init__(self, symbol='C'):
        DrawableObject.__init__(self)
        Vertex.__init__(self)
        self.x, self.y = None, None
        self.z = 0
        # Properties
        self.molecule = None
        self.marks = []
        self.symbol = symbol
        self.is_group = len(formula_to_atom_list(symbol)) > 1
        self.isotope = None
        self.valency = 0
        self.auto_valency = True
        self.occupied_valency = 0
        self.hydrogens = 0
        self.auto_hydrogens = True
        # inherited properties from Vertex
        # self.neighbors = []
        # self.neighbor_edges = [] # connected edges
        # self.edges = [] # all edges
        # Drawing Properties
        self._text = None
        self.text_layout = None # vals - "LTR" | "RTL" (for left-to-right or right-to-left)
        self.auto_text_layout = True
        self.show_symbol = symbol!='C' # invisible Carbon atom
        # generate unique id
        global atom_id_no
        self.id = 'a' + str(atom_id_no)
        atom_id_no += 1
        # drawing related
        self.font_name = Settings.atom_font_name
        self.font_size = Settings.atom_font_size
        self._main_item = None
        self._focusable_item = None
        self._focus_item = None
        self._selection_item = None
        #self.paper = None
        # for smiles
        self.charge = 0
        self.multiplicity = 1 # what is this?
        self.explicit_hydrogens = 0
        # init some values
        self._update_valency()

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
    def pos3d(self):
        return self.x, self.y, self.z

    @property
    def pos(self):
        return self.x, self.y

    def setPos(self, x, y):
        self.x, self.y = x, y

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
        #print("merge %s with %s" % (self, atom2))
        self.molecule.eatMolecule(atom2.molecule)
        # disconnect the bonds from atom2, and reconnect to this atom
        for bond in atom2.bonds:
            bond.replaceAtom(atom2, self)
        # remove atom2
        self.molecule.removeAtom(atom2)
        atom2.deleteFromPaper()

    @property
    def items(self):
        return filter(None, [self._main_item])

    @property
    def all_items(self):
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
        # calculate drawing properties
        if self._text == None:# text not determined
            self._update_text()
        font = Font(self.font_name, self.font_size*self.molecule.scale_val)
        self._text_offset = self.paper.getCharWidth(self.symbol[0], font)/2
        if self.isotope and self.text_layout=="LTR":
            font.size *= 0.75
            self._text_offset += self.paper.getTextWidth(str(self.isotope), font)

        # Draw
        if self._text!="":
            alignment = self.text_layout=="RTL" and Align.Right or Align.Left
            # visible symbol
            font = Font(self.font_name, self.font_size*self.molecule.scale_val)
            self._main_item = self.paper.addChemicalFormula(html_formula(self._text),
                (self.x, self.y), alignment, self._text_offset, font, color=self.color)

        # add item used to receive focus
        rect = self.x-8, self.y-8, self.x+8, self.y+8
        self._focusable_item = self.paper.addRect(rect, color=Color.transparent)
        self.paper.addFocusable(self._focusable_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)


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
        """ Atom type is changed. Text and valency need to be updated """
        self.symbol = symbol
        if not self.show_symbol and symbol != "C":
            self.show_symbol = True
        atom_list = formula_to_atom_list(symbol)
        self.is_group = len(atom_list) > 1
        #self.show_hydrogens = not self.is_group
        self.auto_hydrogens = True
        self.auto_valency = True
        self._update_valency()# also updates hydrogen count but may not reset text
        self.isotope = None
        self.resetText()

    @property
    def free_valency(self):
        return self.valency - self.occupied_valency

    def _update_valency(self):
        """ Valency is updated when Atom symbol is changed or valency is set to auto from
        manual or adding new bond exceeds free valency """
        if not self.auto_valency:
            return
        if self.symbol not in periodic_table:
            self.valency = self.occupied_valency
            self._update_hydrogens()
            return
        valencies = periodic_table[self.symbol]["valency"]
        for val in valencies:
            if val >= self.occupied_valency:
                self.valency = val
                break
        # hydrogens count may be changed
        self._update_hydrogens()

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

    def update_occupied_valency(self):
        """ occupied_valency is updated when new bond is added or removed """
        occupied_valency = 0
        for bond in self.bonds:
            occupied_valency += bond.order
        if occupied_valency == self.occupied_valency:
            return
        # occuped valency changed
        self.occupied_valency = occupied_valency
        if self.occupied_valency > self.valency:
            self._update_valency()
        # hydrogens count may be changed
        self._update_hydrogens()

    def _update_hydrogens(self):
        # do not update if explicit hydrogens is set
        if not self.auto_hydrogens:
            return
        if self.symbol in ("C", "N", "O", "B", "Si", "P", "S", "As"):
            hydrogens = self.free_valency > 0 and self.free_valency or 0
        else:
            hydrogens = 0
        if hydrogens != self.hydrogens:
            self.hydrogens = hydrogens
            self.resetText()

    def toggleHydrogens(self):
        """ toggle hydrogens between auto and off """
        if self.auto_hydrogens:
            # set hydrogen count 0 explicitly
            self.auto_hydrogens = False
            self.hydrogens = 0
            self.resetText()
        else:
            self.auto_hydrogens = True
            self._update_hydrogens()

    def _update_text(self):
        if not self.show_symbol:
            self._text = ""
            return
        self._text = self.symbol
        # add isotope number
        if self.isotope:
            self._text = "^%i"%self.isotope + self._text
        # add hydrogens to text
        if self.hydrogens:
            self._text += self.hydrogens==1 and "H" or "H%i"%self.hydrogens
        # decide text layout, and reverse text direction if required
        if self.text_layout==None:
            self._decide_text_layout()
        if self.text_layout == "RTL":
            self._text = get_reverse_formula(self._text)


    def resetText(self):
        self._text = None

    def resetTextLayout(self):
        if self.auto_text_layout:
            self.text_layout = None
            # text need to be reset, to force recalculate text layout before drawing
            self._text = None

    def _decide_text_layout(self):
        """ decides whether the first or the last atom should be positioned at self.pos """
        #if self.is_part_of_linear_fragment():# TODO
        #    self.text_layout = "LTR"
        #    return
        p = 0
        for atom in self.neighbors:
            if atom.x < self.x:
                p -= 1
            elif atom.x > self.x:
                p += 1
        if p > 0:
            self.text_layout = "RTL"
        else:
            self.text_layout = "LTR"

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
        self.z *= scale

    @property
    def isotope_template(self):
        vals = tuple(str(n) for n in element_get_isotopes(self.symbol) )
        return ("Isotope Number", ("Auto",)+vals)

    @property
    def menu_template(self):
        menu = ()
        if not self.is_group:
            menu += (("Valency", ("Auto", "1", "2", "3", "4", "5", "6", "7", "8")),
                    ("Hydrogens", ("Auto", "0", "1", "2", "3")),
                    self.isotope_template )
        menu += (("Text Layout", ("Auto", "Left-to-Right", "Right-to-Left")),)
        return menu

    def getProperty(self, key):
        if key=="Isotope Number":
            return "Auto" if not self.isotope else str(self.isotope)

        elif key=="Valency":
            return "Auto" if self.auto_valency else str(self.valency)

        elif key=="Hydrogens":
            return "Auto" if self.auto_hydrogens else str(self.hydrogens)

        elif key=="Text Layout":
            val_to_name = {"LTR": "Left-to-Right", "RTL": "Right-to-Left"}
            return "Auto" if self.auto_text_layout else val_to_name[self.text_layout]

        else:
            print("Warning ! : Invalid key '%s'"%key)

    def setProperty(self, key, val):
        if key=="Isotope Number":
            self.isotope = val!="Auto" and int(val) or None
            self.resetText()

        elif key=="Valency":
            if val=="Auto":
                self.auto_valency = True
                self._update_valency()
            else:
                self.valency = int(val)
                self.auto_valency = False
                self._update_hydrogens()

        elif key=="Hydrogens":
            if val=="Auto":
                self.auto_hydrogens = True
                self._update_hydrogens()
            else:
                self.hydrogens = int(val)
                self.auto_hydrogens = False
            self.resetText()

        elif key=="Text Layout":
            layout_dict = {"Auto": (None,True),
                        "Left-to-Right": ("LTR",False), "Right-to-Left": ("RTL",False) }
            self.text_layout, self.auto_text_layout = layout_dict[val]
            self.resetText()


def formula_to_atom_list(formula):
    l = list(formula)
    atom_list = [l.pop(0)]
    for item in l:
        if item.isupper():# new atom
            atom_list.append(item)
        else: # part of prev atom
            atom_list[-1] = atom_list[-1]+item
    return atom_list



# regex for finding superscript numbers and plain numbers
formula_num_re = "(\^(\d+))|(\d+)"

def format_num(match):
    sup, sub = match.group(1), match.group(3)
    if sup:
        return "<sup>" + match.group(2) + "</sup>"
    else:
        return "<sub>" + sub + "</sub>"

# converts ^14NH2 to <sup>14</sup>NH<sub>2</sub>
def html_formula(formula):
    return re.sub(formula_num_re, format_num, formula)


# (isotope num)(atom symbol)(count)
atom_re = "((\^(\d+))*)([A-Z][a-z]*)(\d*)"

# effectively reverses formulae like CO(NH2)2 to (NH2)2OC
def get_reverse_formula(formula):
    size = len(formula)
    parts = []
    i = 0
    while i < size:
        # if found a start bracket, find its ending bracket, and add to parts
        if formula[i]=="(":
            end_bracket_pos = find_matching_parentheses(formula, i)
            part = formula[i:end_bracket_pos+1]
            i = end_bracket_pos + 1
            # there may be number after end bracket (eg. CO(NH2)2 )
            while i < size and formula[i].isdigit():
                part += formula[i]
                i += 1
            parts.append( part )
            continue
        # try to find an atom set
        match = re.search(atom_re, formula[i:])
        if match:
            start, end = match.span()
            start, end = i+start, i+end# absolute position in formula
            if i != start:
                # we found something that is not atom symbol
                parts.append(formula[i:start])
        else:
            # not atom set exists, append rest of all characters
            start, end = i, size
        parts.append(formula[start:end])
        i = end

    return "".join(reversed(parts))




def element_get_isotopes(element):
    try:
        return periodic_table[element]["isotopes"]
    except KeyError:
        return ()
