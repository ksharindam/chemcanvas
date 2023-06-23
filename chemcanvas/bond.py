# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings
from graph import Edge
from drawing_parents import DrawableObject, Color, LineStyle
from arrow import arrow_head
from geometry import *
import common


import operator
from functools import reduce

global bond_id_no
bond_id_no = 1

class Align:#unused
    center = 0
    left = -1
    right = 1

class Bond(Edge, DrawableObject):
    focus_priority = 4
    redraw_priority = 2
    is_toplevel = False
    meta__undo_properties = ("molecule", "type", "second_line_side", "second_line_distance",
                "double_length_ratio")
    meta__undo_copy = ("atoms",)
    meta__same_objects = {"vertices":"atoms"}
    meta__scalables = ("second_line_distance",)

    bond_types = ["normal", "double", "triple", "wedge", "hatch", "dashed", "dotted"]

    def __init__(self):
        DrawableObject.__init__(self)
        Edge.__init__(self)
        # Properties
        self.atoms = self.vertices
        self.molecule = None
        self.type = "normal"
        # unique id
        global bond_id_no
        self.id = 'b' + str(bond_id_no)
        bond_id_no += 1
        # drawing related
        self._main_items = []# includes _focusable_item
        self._focusable_item = None
        self._focus_item = None
        self._selection_item = None
        # double bond's second line placement and gap related
        self.second_line_side = None # None=Unknown, 0=centered, -1=one side, +1=another side
        self.second_line_distance = Settings.bond_width # distance between two parallel lines of a double bond
        self.double_length_ratio = 0.75
        # for smiles
        self.aromatic = False
        self._order = 1# TODO : remove later

    def __str__(self):
        return "%s : %s-%s" % (self.id, self.atoms[0], self.atoms[1])

    @property
    def atom1(self):
        return self.atoms[0]

    @property
    def atom2(self):
        return self.atoms[1]

    @property
    def parent(self):
        return self.molecule

    @property
    def order(self):
        """if self.type == 'double':
            return 2
        elif self.type == 'triple':
            return 3
        return 1"""
        return self._order

    @order.setter
    def order(self, val):
        self._order = val

    def setType(self, bond_type):
        self.type = bond_type
        [atom._update_occupied_valency() for atom in self.atoms]
        if self.type == 'double':
            self._order = 2
        elif self.type == 'triple':
            self._order = 3
        else:
            self._order = 1

    def connectAtoms(self, atom1, atom2):
        atom1.addNeighbor(atom2, self)
        atom2.addNeighbor(atom1, self)
        # to keep self.atoms and self.vertices pointing to same list object,
        # we can not use self.atoms = [atom1, atom2] here
        self.atoms.clear()
        self.atoms += [atom1, atom2]

    def disconnectAtoms(self):
        self.atoms[0].removeNeighbor(self.atoms[1])
        self.atoms[1].removeNeighbor(self.atoms[0])
        self.atoms.clear()

    def atomConnectedTo(self, atom):
        """ used in Molecule.handleOverlap() """
        return self.atoms[0] if atom is self.atoms[1] else self.atoms[1]

    def replaceAtom(self, target, substitute):
        """ disconnects from target, and reconnects to substitute.
        used in Molecule.handleOverlap() and Atom.eatAtom() """
        atom1, atom2 = self.atoms
        self.disconnectAtoms()
        if atom1 is target:
            self.connectAtoms(substitute, atom2)
        elif atom2 is target:
            self.connectAtoms(atom1, substitute)
        else:
            print("warning : trying to replace non existing atom")

    def changeDoubleBondAlignment(self):
        self.second_line_side = self.second_line_side+1 if self.second_line_side<1 else -1

    def setFocus(self, focus: bool):
        """ handle draw or undraw on focus change """
        if focus:
            self._focus_item = self.paper.addLine(self.atoms[0].pos + self.atoms[1].pos, width=self._line_width+8, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            self._selection_item = self.paper.addLine(self.atoms[0].pos + self.atoms[1].pos, self._line_width+4, Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    @property
    def items(self):
        return filter(None, self._main_items + [ self._focus_item, self._selection_item])

    def clearDrawings(self):
        if self._focusable_item:
            self.paper.removeFocusable(self._focusable_item)
            self._focusable_item = None
        for item in  self._main_items:
            self.paper.removeItem(item)
        self._main_items = []
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        mid_line = self._where_to_draw_from_and_to()
        if not mid_line:
            return # the bond is too short to draw it

        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()
        self.paper = self.molecule.paper
        # draw
        self._line_width = max(1*self.molecule.scale_val, 1)
        method = "_draw_%s" % self.type
        getattr(self, method)(mid_line)

        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        mid_line = self._where_to_draw_from_and_to()
        if not mid_line:
            return # the bond is too short to draw it
        method = "_draw_%s_on_paper" % self.type
        getattr(self, method)(paper, mid_line)

    def redraw(self):
        self.second_line_side = None
        self.draw()

    def _where_to_draw_from_and_to(self):
        x1, y1 = self.atoms[0].pos
        x2, y2 = self.atoms[1].pos
        # the bond line should not intersect the boundingbox, so increasing boundingbox
        #  by 2px. But on top side, we have enough space, +2px is not needed
        bbox1 = self.atoms[0].boundingBox()
        bbox1 = [bbox1[0]-2, bbox1[1], bbox1[2]+2, bbox1[3]+1]
        bbox2 = self.atoms[1].boundingBox()
        bbox2 = [bbox2[0]-2, bbox2[1], bbox2[2]+2, bbox2[3]+1]
        # at first check if the bboxes are not overlapping
        if rect_intersects_rect(bbox1, bbox2):
            return None # atoms too close to draw a bond
        # then we continue with computation
        if self.atoms[0].show_symbol:
            x1, y1 = rect_get_intersection_of_line(bbox1, [x1,y1,x2,y2])
        if self.atoms[1].show_symbol:
            x2, y2 = rect_get_intersection_of_line(bbox2, [x1,y1,x2,y2])

        if point_distance((x1,y1), (x2,y2)) <= 1.0:
            return None
        return (x1, y1, x2, y2)


    def _draw_normal_on_paper(self, paper, mid_line):
        return [paper.addLine(mid_line, self._line_width)]

    def _draw_normal(self, mid_line):
        #print("draw normal")
        self._main_items = self._draw_normal_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)


    def _draw_double_on_paper(self, paper, mid_line):
        #print("draw double")
        if self.second_line_side == None:
            self.second_line_side = self._calc_second_line_side()

        item0 = item1 = item2 = None
        # sign and value of 'd' determines side and distance of second line
        if self.second_line_side==0:# centered
            # draw one of two equal parallel lines
            d =  0.5*self.second_line_distance
            line2 = calc_second_line(self, mid_line, -d)
            item2 = paper.addLine(line2, self._line_width)
        else:
            # draw longer mid-line
            d = self.second_line_side * self.second_line_distance
            item0 = paper.addLine(mid_line, self._line_width)

        # draw the other parallel line
        line1 = calc_second_line(self, mid_line, d)
        item1 = paper.addLine(line1, self._line_width)

        return [item0, item1, item2]

    def _draw_double(self, mid_line):
        items = self._draw_double_on_paper(self.paper, mid_line)

        if not items[0]:
            # use this item to receive focus
            items[0] = self.paper.addLine(mid_line, self._line_width, color=Color.transparent)
        self._main_items = list(filter(None, items))# item2 may be None
        self._focusable_item = items[0]
        self.paper.addFocusable(self._focusable_item, self)


    def _draw_triple_on_paper(self, paper, mid_line):
        d = self.second_line_distance * 0.75
        line1 = calc_second_line(self, mid_line, d)
        line2 = calc_second_line(self, mid_line, -d)
        item0 = paper.addLine(mid_line, self._line_width)
        item1 = paper.addLine(line1, self._line_width)
        item2 = paper.addLine(line2, self._line_width)

        return [item0, item1, item2]

    def _draw_triple(self, mid_line):
        self._main_items = self._draw_triple_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)

    def _draw_aromatic_on_paper(self, paper, mid_line):
        #print("draw double")
        if self.second_line_side == None:
            self.second_line_side = self._calc_second_line_side()

        item0 = item1 = item2 = None
        # sign and value of 'd' determines side and distance of second line
        if self.second_line_side==0:# centered
            # draw one of two equal parallel lines
            d =  0.5*self.second_line_distance
            line2 = calc_second_line(self, mid_line, -d)
            item2 = paper.addLine(line2, self._line_width)
        else:
            # draw longer mid-line
            d = self.second_line_side * self.second_line_distance
            item0 = paper.addLine(mid_line, self._line_width)

        # draw the other parallel line
        line1 = calc_second_line(self, mid_line, d)
        item1 = paper.addLine(line1, self._line_width, style=LineStyle.dashed)

        return [item0, item1, item2]

    def _draw_aromatic(self, mid_line):
        items = self._draw_aromatic_on_paper(self.paper, mid_line)

        if not items[0]:
            # use this item to receive focus
            items[0] = self.paper.addLine(mid_line, self._line_width, color=Color.transparent)
        self._main_items = list(filter(None, items))# item2 may be None
        self._focusable_item = items[0]
        self.paper.addFocusable(self._focusable_item, self)

    def _draw_partial_on_paper(self, paper, mid_line):
        return [paper.addLine(mid_line, self._line_width, style=LineStyle.dashed)]

    def _draw_partial(self, mid_line):
        self._main_items = self._draw_partial_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)

    def _draw_hbond_on_paper(self, paper, mid_line):
        return [paper.addLine(mid_line, self._line_width, style=LineStyle.dotted)]

    def _draw_hbond(self, mid_line):
        self._main_items = self._draw_hbond_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)

    def _draw_coordinate_on_paper(self, paper, mid_line):
        l, w, d = 6, 2.5, 2
        head_pts = arrow_head(*mid_line, l,w,d)
        line = mid_line[:2] + head_pts[0]
        item1 = paper.addLine(line, self._line_width)
        item2 = paper.addPolygon(head_pts, fill=Color.black)
        return [item1, item2]

    def _draw_coordinate(self, mid_line):
        #print("draw normal")
        self._main_items = self._draw_coordinate_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)

    # ------------ Stereo Bonds -------------------

    def _draw_wedge_on_paper(self, paper, mid_line):
        d = self.second_line_distance
        p1 = line_get_point_at_distance(mid_line, d)
        p2 = line_get_point_at_distance(mid_line, -d)
        p0 = (mid_line[0], mid_line[1])
        return [ paper.addPolygon([p0,p1,p2], fill=Color.black) ]

    def _draw_bold_on_paper(self, paper, mid_line):
        return [paper.addLine(mid_line, self.second_line_distance)]

    def _draw_bold(self, mid_line):
        self._main_items = self._draw_bold_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)

    def _draw_wedge(self, mid_line):
        self._main_items = self._draw_wedge_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)

    def _draw_hatch_on_paper(self, paper, mid_line):
        d = self.second_line_distance
        p1 = line_get_point_at_distance(mid_line, d)
        p2 = line_get_point_at_distance(mid_line, -d)
        p0 = (mid_line[0], mid_line[1])
        return [ paper.addPolygon([p0,p1,p2], fill=Color.lightGray) ]

    def _draw_hatch(self, mid_line):
        self._main_items = self._draw_hatch_on_paper(self.paper, mid_line)
        self._focusable_item = self._main_items[0]
        self.paper.addFocusable(self._focusable_item, self)

    # here we first check which side has higher number of ring atoms, and put
    # the double bond to that side. If both side has equal or no ring atoms,
    # check which side has higher number of neighbouring atoms.
    # If one atom has no other neighbours, center the double bond.
    # If both side has equal number of atoms, put second bond to the side
    # by atom priority C > non-C > H
    def _calc_second_line_side( self):
        """returns tuple of (sign, center) where sign is the default sign of the self.bond_width"""
        # check if we need to transform 3D before computation
        # /end of check
        line = self.atoms[0].pos + self.atoms[1].pos
        atms = self.atoms[0].neighbors + self.atoms[1].neighbors
        atms = common.difference( atms, self.atoms)
        coords = [(a.x,a.y) for a in atms]
        # searching for circles
        circles = 0 # sum of side value of all ring atoms
        # find all rings in the molecule and choose the rings which contain this bond.
        for ring in self.molecule.get_smallest_independent_cycles_dangerous_and_cached():
          if self.atoms[0] in ring and self.atoms[1] in ring:
            on_which_side = lambda xy: line_get_side_of_point( line, xy)
            circles += reduce( operator.add, map( on_which_side, [a.pos for a in ring if a not in self.atoms]))
        if circles: # left or right side has greater number of ring atoms
          side = circles
        else:
          sides = [line_get_side_of_point( line, xy, threshold=0.1) for xy in coords]
          side = reduce( operator.add, sides, 0)
        # on which side to put the second line
        if side == 0 and (len( self.atoms[0].neighbors) == 1 or
                          len( self.atoms[1].neighbors) == 1):
          # maybe we should center, but this is usefull only when one of the atoms has no other substitution
          ret = 0
        else:
          if not circles:
            # we center when both atoms have visible symbol and are not in circle
            if self.atoms[0].show_symbol and self.atoms[1].show_symbol:
              return 0
            # recompute side with weighting of atom types
            for i in range( len( sides)):
              if sides[i] and atms[i].__class__.__name__ == "atom":
                if atms[i].symbol == 'H':
                  sides[i] *= 0.1 # this discriminates H
                elif atms[i].symbol != 'C':
                  sides[i] *= 0.2 # this makes "non C" less then C but more then H
              side = reduce( operator.add, sides, 0)
          if side < 0:
            ret = -1
          else:
            ret = 1
        # transform back if necessary
        '''if transform:
          inv = transform.get_inverse()
          for n in self.atoms[0].neighbors + self.atoms[1].neighbors:
            n.transform( inv)'''
        # /end of back transform
        return ret


    def copy(self):
        """ copy of a bond can not be linked to same atoms as previous bond.
        So, copy of this bond have same properties except they are not linked to any atom """
        new_bond = Bond()
        for attr in self.meta__undo_properties:
            setattr(new_bond, attr, getattr(self, attr))
        return new_bond

    def boundingBox(self):
        return rect_normalize(self.atom1.pos + self.atom2.pos)

    def scale(self, scale):
        self.second_line_distance *= scale

    def transform(self, tr):
        pass


    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("bond")
        elm.setAttribute("id", self.id)
        elm.setAttribute("atms", " ".join([atom.id for atom in self.atoms]))
        elm.setAttribute("typ", self.type)
        #elm.setAttribute("st", self.stereo)
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        uid = elm.getAttribute("id")
        if uid:
            App.id_to_object_map[uid] = self

        atom_ids = elm.getAttribute("atms")
        atoms = []
        for atom_id in atom_ids.split():
            try:
                atoms.append( App.id_to_object_map[atom_id])
            except KeyError:
                return False
        self.connectAtoms(atoms[0], atoms[1])

        _type = elm.getAttribute("typ")
        if _type:
            self.setType(_type)


# while drawing second line of double bond, the bond length is shortened.
# bond is shortened to the intersection point of the parallel line
# (i.e imaginary second bond) of the neighbouring bond of same side.
# This way, if we convert neighbour bond from single to double bond, the
# second bonds will just touch at the end and won't cross each other.
def calc_second_line( bond, mid_line, distance):
    # center bond coords
    bond_line = bond.atoms[0].pos + bond.atoms[1].pos
    mid_bond_len = point_distance(bond.atoms[0].pos, bond.atoms[1].pos)
    # second parallel bond coordinates
    x, y, x0, y0 = line_get_parallel(mid_line, distance)
    # shortening of the second bond
    dx = x-x0
    dy = y-y0
    _k = 0 if bond.second_line_side==0 else (1-bond.double_length_ratio)/2

    x, y, x0, y0 = x-_k*dx, y-_k*dy, x0+_k*dx, y0+_k*dy
    # shift according to the bonds arround
    side = line_get_side_of_point( bond_line, (x,y))
    for atom in bond.atoms:
      second_atom = bond.atoms[1] if atom is bond.atoms[0] else bond.atoms[0]
      # find all neighbours at the same side of (x,y)
      neighs = [n for n in atom.neighbors if line_get_side_of_point( bond_line, [n.x,n.y])==side and n is not second_atom]
      for n in neighs:
        dist2 = _k * mid_bond_len * line_get_side_of_point((atom.x, atom.y, n.x, n.y), (second_atom.x, second_atom.y))
        xn1, yn1, xn2, yn2 = line_get_parallel([atom.x, atom.y, n.x, n.y], dist2)
        xp, yp, parallel = line_get_intersection_of_line([x,y,x0,y0], [xn1,yn1,xn2,yn2])
        if not parallel:
          if not line_contains_point([x,y,x0,y0], (xp,yp)):
            # only shorten the line - do not elongate it
            continue
          if point_distance(atom.pos, (x,y)) < point_distance(atom.pos, (x0,y0)):
            x,y = xp, yp
          else:
            x0,y0 = xp, yp
    return [x, y, x0, y0]
