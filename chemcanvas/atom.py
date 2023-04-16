from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from app_data import App, Settings, periodic_table
from drawable import DrawableObject
from graph import Vertex
import common
from geometry import *
from marks import *

import re

global atom_id_no
atom_id_no = 1


class Atom(Vertex, DrawableObject):
    object_type = 'Atom'
    focus_priority = 3
    redraw_priority = 1
    is_toplevel = False
    meta__undo_properties = ("formula", "is_group", "x", "y", "z", "valency",
            "occupied_valency", "text", "text_center", "show_symbol", "show_hydrogens")
    meta__undo_copy = ("_neighbors",)

    def __init__(self, formula):
        DrawableObject.__init__(self)
        Vertex.__init__(self)
        self.x, self.y, self.z = 0,0,0
        # Properties
        self.molecule = None
        self.marks = []
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
        self.font_size = 9# default 9pt in Qt
        self.font_height = 0
        self._main_item = None
        self._focusable_item = None
        self._focus_item = None
        self._selection_item = None
        #self.paper = None

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
        if self.text == None:# text not determined
            self._update_text()
        # visible symbol
        if self.text:
            text = formatted_formula(self.text)
            alignment = -1 if self.text_center=="last-atom" else 0
            self._main_item = self.paper.addHtmlText(text, [self.x, self.y], alignment)
            self.font_height = QFontMetrics(self._main_item.font()).height()# for calculating bbox
        # add item used to receive focus
        rect = self.x-4, self.y-4, self.x+4, self.y+4
        self._focusable_item = self.paper.addRect(rect, color=Qt.transparent)
        self.paper.addFocusable(self._focusable_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def boundingBox(self):
        """returns the bounding box of the object as a list of [x1,y1,x2,y2]"""
        if self._main_item:
            x,y,w,h = self._main_item.sceneBoundingRect().getRect()
            margin = (h-self.font_height)/2
            return [x+margin, y+margin, x+w-margin, y+h-margin]
        return [self.x, self.y, self.x, self.y]


    def setFocus(self, focus):
        if focus:
            if self.text:
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
                rect = self._main_item.sceneBoundingRect().getCoords()
            else:
                rect = self.x-4, self.y-4, self.x+4, self.y+4
            self._selection_item = self.paper.addEllipse(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy
        items = filter(None, [self._main_item, self._focusable_item, self._focus_item, self._selection_item])
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

    def newMark(self, name):
        mark = mark_class[name]()
        mark.atom = self
        #mark.paper = self.paper
        x, y = self.find_place_for_mark(mark)
        mark.setPos(x,y)
        self.marks.append(mark)# this must be done after setting the pos, otherwise it wont find new place for mark
        return mark

    def find_place_for_mark(self, mark):
        """ find place for new mark """
        # deal with statically positioned marks
        #if mark.meta__mark_positioning == 'righttop':# oxidation_number
        #    bbox = self.boundingBox()
        #    return bbox[2]+2, bbox[1]

        # deal with marks in linear_form
        #if self.is_part_of_linear_fragment():
        #    if mark.object_type == "atom_number":
        #        bbox = self.bbox()
        #        return int( self.x-0.5*self.font_size), bbox[1]-2

        # calculate distance from atom pos
        if not self.show_symbol:
            dist = round(1.5*mark.size)
        else:
            dist = 0.75*self.font_size + round( Settings.mark_size / 2)

        x, y = self.x, self.y

        neighbors = self.neighbors
        # special cases
        if not neighbors:
            # single atom molecule
            if self.show_hydrogens and self.text_center == "first-atom":
                return x -dist, y-3
            else:
                return x +dist, y-3

        # normal case
        coords = [(a.x,a.y) for a in neighbors]
        # we have to take marks into account
        [coords.append( (m.x, m.y)) for m in self.marks]
        # hydrogen positioning is also important
        if self.show_symbol and self.show_hydrogens:
            if self.text_center == 'last-atom':
                coords.append( (x-10,y))
            else:
                coords.append( (x+10,y))

        # now we can compare the angles
        angles = [clockwise_angle_from_east(x1-x, y1-y) for x1,y1 in coords]
        angles.append( 2*pi + min( angles))
        angles.sort(reverse=True)
        diffs = common.list_difference( angles)
        i = diffs.index( max( diffs))
        angle = (angles[i] + angles[i+1]) / 2
        direction = (x+cos(angle), y+sin(angle))

        # we calculate the distance here again as it is anisotropic (depends on direction)
        if self.show_symbol:
            x0, y0 = point_on_circle((x,y), 500, direction)
            x1, y1 = Rect(self.boundingBox()).intersectionOfLine([x,y,x0,y0])
            dist = point_distance((x,y), (x1,y1)) + round( Settings.mark_size / 2)

        return point_on_circle((x,y), dist, direction)


    def findLeastCrowdedPlace(self, distance=10):
        atms = self.neighbors
        if not atms:
          # single atom molecule
          if self.show_hydrogens and self.text_direction == "left-to-right":
            return self.x - distance, self.y
          else:
            return self.x + distance, self.y
        angles = [clockwise_angle_from_east( at.x-self.x, at.y-self.y) for at in atms]
        angles.append( 2*pi + min( angles))
        angles.sort(reverse=True)
        diffs = common.list_difference( angles)
        i = diffs.index( max( diffs))
        angle = (angles[i] +angles[i+1]) / 2
        return self.x + distance*cos( angle), self.y + distance*sin( angle)


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

subscript_text = lambda match_obj : "<sub>"+match_obj.group(0)+"</sub>"

def formatted_formula(formula):
    return re.sub("\d", subscript_text, formula)
