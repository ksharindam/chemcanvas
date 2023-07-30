# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings, periodic_table
from drawing_parents import DrawableObject, Color, Font
from graph import Vertex
from marks import Charge, Electron
from common import float_to_str

import re

global atom_id_no
atom_id_no = 1


class Atom(Vertex, DrawableObject):
    focus_priority = 3
    redraw_priority = 2
    is_toplevel = False
    meta__undo_properties = ("symbol", "is_group", "molecule", "x", "y", "z", "valency",
            "occupied_valency", "_text", "text_layout", "auto_text_layout", "show_symbol",
            "hydrogens", "auto_hydrogens", "auto_valency", "isotope")
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
        self.auto_valency = True
        self.occupied_valency = 0
        # inherited properties from Vertex
        # self.neighbors = []
        # self.neighbor_edges = [] # connected edges
        # self.edges = [] # all edges
        # Drawing Properties
        self._text = None
        self.text_layout = None # vals - "LTR" | "RTL" (for left-to-right or right-to-left)
        self.auto_text_layout = True
        self.show_symbol = symbol!='C' # invisible Carbon atom
        self.hydrogens = 0
        self.auto_hydrogens = True
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
        if self._text == None:# text not determined
            self._update_text()
        font = Font(Settings.atom_font_name, Settings.atom_font_size*self.molecule.scale_val)
        self._text_offset = self.paper.getCharWidth(self.symbol[0], font)/2
        if self.isotope and self.text_layout=="LTR":
            font.size *= 0.75
            self._text_offset += self.paper.getTextWidth(str(self.isotope), font)
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
        # invisible carbon symbol
        if self._text=="":
            return
        text_anchor = self.text_layout=="RTL" and "end" or "start"# like svg text anchor
        # visible symbol
        font = Font(Settings.atom_font_name, Settings.atom_font_size*self.molecule.scale_val)
        return paper.addChemicalFormula(html_formula(self._text), (self.x, self.y), text_anchor, font=font, offset=self._text_offset)


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
        hydrogens = self.free_valency > 0 and self.free_valency or 0
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

    @property
    def isotope_template(self):
        vals = tuple(str(n) for n in element_get_isotopes(self.symbol) )
        return ("Isotope Number", ("Auto",)+vals)

    @property
    def menu_template(self):
        valency_template = ("Valency", ("Auto", "1", "2", "3", "4", "5", "6", "7", "8"))
        hydrogens_template = ("Hydrogens", ("Auto", "0", "1", "2", "3"))
        layout_template = ("Text Layout", ("Auto", "Left-to-Right", "Right-to-Left"))
        return (valency_template, hydrogens_template, layout_template, self.isotope_template)

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


# (isotope num)(atom symbol)(count)
atom_re = "((\^(\d+))*)([A-Z][a-z]*)(\d*)"

def format_func(match_obj):
    isotope, symbol, count = match_obj.group(3), match_obj.group(4), match_obj.group(5)
    if isotope:
        symbol = "<sup>"+isotope+"</sup>" + symbol
    if count:
        symbol += "<sub>"+count+"</sub>"
    return symbol


def html_formula(formula):
    return re.sub(atom_re, format_func, formula)

def get_reverse_formula(formula):
    parts = re.findall(atom_re, formula)
    parts = [part[0]+part[3]+part[4] for part in reversed(parts)]
    return "".join(parts)


def element_get_isotopes(element):
    try:
        return periodic_table[element]["isotopes"]
    except KeyError:
        return ()
