# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings, periodic_table
from drawing_parents import DrawableObject, Color, Font, Align
from graph import Vertex
from common import find_matching_parentheses
import geometry as geo
from math import pi

from functools import reduce
import operator
import re

global atom_id_no
atom_id_no = 1


class Atom(Vertex, DrawableObject):
    focus_priority = 3
    redraw_priority = 2
    is_toplevel = False
    meta__undo_properties = ("symbol", "is_group", "molecule", "x", "y", "z", "valency",
            "occupied_valency", "_text", "_hydrogens_text", "hydrogen_pos", "text_layout", "auto_text_layout", "show_symbol",
            "hydrogens", "auto_hydrogens", "isotope", "color")
    meta__undo_copy = ("_neighbors", "marks")
    meta__undo_children_to_record = ("marks",)
    meta__scalables = ("x", "y", "z")

    auto_hydrogen_elements = {"B", "C","Si", "N","P","As", "O","S", "F","Cl","Br","I"}

    def __init__(self, symbol='C'):
        DrawableObject.__init__(self)
        Vertex.__init__(self)
        self.x, self.y = None, None
        self.z = 0
        # Properties
        self.molecule = None
        self.marks = []
        self.symbol = symbol
        self.is_group = symbol not in periodic_table
        self.isotope = None
        self.valency = 0
        self.occupied_valency = 0
        self.hydrogens = 0
        self.auto_hydrogens = True
        # inherited properties from Vertex
        # self.neighbors = []
        # self.neighbor_edges = [] # connected edges
        # self.edges = [] # all edges
        # Drawing Properties
        self.show_symbol = symbol!='C' # Carbon atom visibility
        self._hydrogens_text = ""
        self.hydrogen_pos = None # R|L|T|B for right,left,top,bottom respectively
        # text and layout required for functional groups
        self._text = None
        self.text_layout = None # vals - "LTR" | "RTL" (for left-to-right or right-to-left)
        self.auto_text_layout = True
        # generate unique id
        global atom_id_no
        self.id = 'a' + str(atom_id_no)
        atom_id_no += 1
        # drawing related
        self.font_name = Settings.atom_font_name
        self.font_size = Settings.atom_font_size
        self._main_items = []
        self._focusable_item = None# a invisible _focusable_item is not in _main_items
        self._focus_item = None
        self._selection_item = None
        #self.paper = None # set by draw()
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
    def charge(self):
        charges = [mark for mark in self.marks if mark.class_name=="Charge" and mark.type!="partial"]
        charges = [charge.value for charge in charges]
        return reduce(operator.add, charges, 0)

    @property
    def multiplicity(self):
        """ 0=undefined, 1=singlet(lone pair), 2=doublet(radical), 3=triplet(diradical) """
        marks = [mark for mark in self.marks if mark.class_name=="Electron"]
        if not marks:
            return 0
        multi = 1 # spin multiplicity = 2S+1
        for mark in marks:
            if mark.type=="1":
                multi += 1
        return multi

    @property
    def free_valency(self):
        return self.valency - self.occupied_valency

    @property
    def pos3d(self):
        return self.x, self.y, self.z

    @property
    def pos(self):
        return self.x, self.y

    def set_pos(self, x, y):
        self.x, self.y = x, y

    def set_symbol(self, symbol):
        """ Atom type is changed. Text and valency need to be updated """
        self.symbol = symbol
        self.show_symbol = symbol != "C"
        self.is_group = symbol not in periodic_table
        self._text = None
        self.isotope = None
        self.auto_hydrogens = True
        self._update_valency()# also updates hydrogen count


    def set_hydrogens(self, count):
        """ val is -1 for auto_hydrogens, else explicitly set """
        if count==-1:
            self.auto_hydrogens = True# this change requires update_occupied_valency
        else:
            self.hydrogens = count
            self.auto_hydrogens = False
        self.update_occupied_valency()
        self._update_hydrogens()


    @property
    def items(self):
        return self._main_items

    @property
    def all_items(self):
        if self._main_items:
            return filter(None, self._main_items + [self._focus_item, self._selection_item])
        return filter(None, [self._focusable_item, self._focus_item, self._selection_item])


    def clear_drawings(self):
        if self._focusable_item:
            self.paper.removeFocusable(self._focusable_item)
            if self._focusable_item not in self._main_items:
                self.paper.removeItem(self._focusable_item)
            self._focusable_item = None
        for item in self._main_items:
            self.paper.removeItem(item)
        self._main_items = []
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clear_drawings()
        self.paper = self.molecule.paper

        # hidden carbon atom
        if not self.show_symbol:
            rect = self.x-8, self.y-8, self.x+8, self.y+8
            self._focusable_item = self.paper.addRect(rect, color=Color.transparent)
            self.paper.addFocusable(self._focusable_item, self)
            # restore focus and selection
            if focused:
                self.set_focus(True)
            if selected:
                self.set_selected(True)
            return

        font = Font(self.font_name, self.font_size*self.molecule.scale_val)
        # Draw atom
        if not self.is_group:
            # draw symbol
            symbol_item = self.paper.addChemicalFormula(html_formula(self.symbol),
                (self.x, self.y), Align.HCenter, 0, font, color=self.color)
            self._main_items = [symbol_item]
            # draw hydrogen
            if self.hydrogens:
                self._decide_hydrogen_pos()
                Sx,Sy,Sw,Sh = self.paper.itemBoundingRect(symbol_item)
                H_item = self.paper.addChemicalFormula(self._hydrogens_text,
                    (Sx, self.y), Align.Left, 0, font, color=self.color)
                Hx,Hy,Hw,Hh = self.paper.itemBoundingRect(H_item)
                # for top and bottom position, a fraction of height is used to reduce gap
                offsets = {"R":(Sw,0), "L":(-Hw,0), "T":(0,-Sh*0.8), "B":(0,Hh*0.7)}
                self.paper.moveItemsBy([H_item], *offsets[self.hydrogen_pos])
                self._main_items.append(H_item)
            # draw isotope number
            if self.isotope:
                Sx,Sy,Sw,Sh = self.paper.itemBoundingRect(symbol_item)
                font.size *= 0.7
                iso_item = self.paper.addChemicalFormula(str(self.isotope),
                    (Sx, Sy), Align.Right, 0, font, color=self.color)
                self._main_items.append(iso_item)
        # Draw functional group
        else:
            if self._text == None:
                self._update_text()# reverse text direction if needed
            alignment = self.text_layout=="RTL" and Align.Right or Align.Left
            offset = self.paper.getCharWidth(self.symbol[0], font)/2
            self._main_items = [self.paper.addChemicalFormula(html_formula(self._text),
                (self.x, self.y), alignment, offset, font, color=self.color)]

        self.paper.addFocusable(self._main_items[0], self)
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def bounding_box(self):
        """returns the bounding box of the object as a list of [x1,y1,x2,y2]"""
        if self._main_items:
            return self.paper.itemBoundingBox(self._main_items[0])
        return [self.x, self.y, self.x, self.y]


    def set_focus(self, focus):
        if focus:
            if self._main_items:
                self._focus_item = self.paper.addRect(self.bounding_box(), fill=Settings.focus_color)
            else:
                rect = self.x-5, self.y-5, self.x+5, self.y+5
                self._focus_item = self.paper.addEllipse(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            if self._main_items:
                self._selection_item = self.paper.addRect(self.bounding_box(), fill=Settings.selection_color)
            else:
                rect = self.x-4, self.y-4, self.x+4, self.y+4
                self._selection_item = self.paper.addEllipse(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None


    def move_by(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy


    def update_occupied_valency(self):
        """ occupied_valency is updated when new bond is added or removed,
        bond order is changed or explicit hydrogen count is changed """
        occupied_valency = 0 if self.auto_hydrogens else self.hydrogens
        for bond in self.bonds:
            occupied_valency += bond.order
        if occupied_valency == self.occupied_valency:
            return
        # valency need to be increased or decreased
        self.occupied_valency = occupied_valency
        self._update_valency()

    def _update_valency(self):
        """ Valency is updated when Atom symbol is changed
        or adding new bond exceeds free valency """
        if not self.auto_hydrogens or self.is_group:
            self.valency = self.occupied_valency
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

    def _update_hydrogens(self):
        """ update hydrogens count and text after valency or occupied valency change """
        # first calculate hydrogen count, then update hydrogens text
        if self.auto_hydrogens:
            if self.symbol in self.auto_hydrogen_elements:
                self.hydrogens = self.free_valency > 0 and self.free_valency or 0
            else:
                self.hydrogens = 0
        if self.hydrogens:
            self._hydrogens_text = self.hydrogens==1 and "H" or "H<sub>%i</sub>"%self.hydrogens


    def _update_text(self):
        """ atom text can be empty, forward or reverse """
        self._text = self.symbol
        # decide text layout, and reverse text direction if required
        if self.text_layout==None:
            self._decide_text_layout()
        if self.text_layout == "RTL":
            self._text = get_reverse_formula(self._text)


    def _decide_text_layout(self):
        """ decides whether the first or the last atom should be positioned at self.pos """
        p = 0
        for atom in self.neighbors:
            if atom.x < self.x:
                p -= 1
            elif atom.x > self.x:
                p += 1
        self.text_layout = p > 0 and "RTL" or "LTR"


    def on_bonds_reposition(self):
        self.hydrogen_pos = None
        if self.auto_text_layout:
            self.text_layout = None
            # text need to be reset, to force recalculate text layout before drawing
            self._text = None


    def _decide_hydrogen_pos(self):
        """ hydrogen pos can be right, left, top or bottom """
        if self.hydrogen_pos:# already determined
            return
        if len(self.bonds)==0:# single atom molecule
            # R for CH4, NH3 etc, and L for H2O, HCl etc
            self.hydrogen_pos = self.hydrogens>2 and "R" or "L"
            return
        elif len(self.bonds)==1:
            self.hydrogen_pos = self.neighbors[0].x > self.x+1 and "L" or "R"
            return
        # for more than one bonds
        angles = [geo.line_get_angle_from_east(self.pos+at.pos) for at in self.neighbors]
        angles.sort()
        closest_angles = []
        for i, pos in enumerate(["R", "B", "L", "T"]):
            diff_angles = []
            for angle in angles:
                diff_angle = abs(angle - i*pi/2)
                diff_angles += [diff_angle, 2*pi-diff_angle]
            # add the closest bond
            closest_angles.append((min(diff_angles), pos))
        closest_angles.sort(key=lambda l: l[0])
        self.hydrogen_pos = closest_angles[-1][1]


    def redraw_needed(self):
        return self._text==None


    def eat_atom(self, atom2):
        """ merge src atom (atom2) with this atom, and merges two molecules also. """
        #print("merge %s with %s" % (self, atom2))
        self.molecule.eat_molecule(atom2.molecule)
        # disconnect the bonds from atom2, and reconnect to this atom
        for bond in atom2.bonds:
            bond.replace_atom(atom2, self)
        # remove atom2
        self.molecule.remove_atom(atom2)
        atom2.delete_from_paper()


    def copy(self):
        """ copy all properties except neighbors (atom:bond).
        because new atom can not be attached to same neighbors as this atom """
        new_atom = Atom(self.symbol)
        for attr in self.meta__undo_properties:
            setattr(new_atom, attr, getattr(self, attr))
        return new_atom

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def transform_3D(self, tr):
        self.x, self.y, self.z = tr.transform(self.x, self.y, self.z)

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
            menu += (("Hydrogens", ("Auto", "0", "1", "2", "3", "4")),
                    self.isotope_template )
        menu += (("Text Layout", ("Auto", "Left-to-Right", "Right-to-Left")),)
        return menu

    def get_property(self, key):
        if key=="Isotope Number":
            return "Auto" if not self.isotope else str(self.isotope)

        elif key=="Hydrogens":
            return "Auto" if self.auto_hydrogens else str(self.hydrogens)

        elif key=="Text Layout":
            val_to_name = {"LTR": "Left-to-Right", "RTL": "Right-to-Left"}
            return "Auto" if self.auto_text_layout else val_to_name[self.text_layout]

        else:
            print("Warning ! : Invalid key '%s'"%key)

    def set_property(self, key, val):
        if key=="Isotope Number":
            self.isotope = val!="Auto" and int(val) or None

        elif key=="Hydrogens":
            self.set_hydrogens(val=="Auto" and -1 or int(val))

        elif key=="Text Layout":
            layout_dict = {"Auto": (None,True),
                        "Left-to-Right": ("LTR",False), "Right-to-Left": ("RTL",False) }
            self.text_layout, self.auto_text_layout = layout_dict[val]
            self._text = None


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
