# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from math import degrees
import operator
from functools import reduce

from app_data import App, Settings
from graph import Edge
from drawing_parents import DrawableObject, Color, PenStyle, LineCap, Font, Align
from arrow import arrow_head
import geometry as geo
import common


global bond_id_no
bond_id_no = 1



class Bond(Edge, DrawableObject):
    focus_priority = 4
    redraw_priority = 3
    is_toplevel = False
    meta__undo_properties = ("molecule", "type", "color",
                "second_line_side", "auto_second_line_side", "show_delocalization")
    meta__undo_copy = ("atoms",)
    meta__same_objects = {"vertices":"atoms"}

    types = ("single", "double", "triple", "delocalized", "partial", "hbond", "coordinate",
            "E_or_Z", "wavy", "wedge", "hashed_wedge", "bold", "hashed", "bold2",
            "1_or_2", "1_or_a", "2_or_a", "any")

    def __init__(self):
        DrawableObject.__init__(self)
        Edge.__init__(self)
        # Properties
        self.atoms = self.vertices
        self.molecule = None
        self.type = "single"
        # unique id
        global bond_id_no
        self.id = 'b' + str(bond_id_no)
        bond_id_no += 1
        # drawing related
        self._main_items = []
        self._focus_item = None
        self._selection_item = None
        # whether to show second dashed line of delocalized bond. If False
        # delocalization will be displayed by Delocalization object in molecule.
        self.show_delocalization = True
        # double bond's second line placement and gap related
        self.second_line_side = None # None=Unknown, 0=Middle, -1=Right, +1=Left side
        self.auto_second_line_side = True
        self.line_width = Settings.bond_width
        self.line_spacing = Settings.bond_spacing
        self.coord_head_dimensions = tuple(x*self.line_width for x in Settings.coord_head_dimensions)
        self.double_length_ratio = 0.75

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
        order_dict = {"double":2, "E_or_Z":2, "triple":3,
                    "delocalized":1.5, "partial":0.5, "hbond":0, "bold2":2}
        return order_dict.get(self.type, 1)


    def set_type(self, bond_type):
        if bond_type == self.type:
            return
        # reset double bond side
        self.auto_second_line_side = True
        self.second_line_side = None
        # if delocalization shown as delocalization ring,
        if self.type=="delocalized" and self.molecule:
            for deloc in self.molecule.delocalizations:
                if deloc.contains_bond(self):
                    self.molecule.destroy_delocalization(deloc)
        self.type = bond_type

        # if bond order is changed atoms occupied valency will also be changed
        [atom.update_occupied_valency() for atom in self.atoms]


    def connect_atoms(self, atom1, atom2):
        atom1.add_neighbor(atom2, self)
        atom1.on_bond_count_change()
        atom2.add_neighbor(atom1, self)
        atom2.on_bond_count_change()
        # to keep self.atoms and self.vertices pointing to same list object,
        # we can not use self.atoms = [atom1, atom2] here
        self.atoms.clear()
        self.atoms += [atom1, atom2]

    def disconnect_atoms(self):
        self.atoms[0].remove_neighbor(self.atoms[1])
        self.atoms[0].on_bond_count_change()
        self.atoms[1].remove_neighbor(self.atoms[0])
        self.atoms[1].on_bond_count_change()
        self.atoms.clear()

    def atom_connected_to(self, atom):
        """ used in Molecule.handle_overlap() """
        return self.atoms[0] if atom is self.atoms[1] else self.atoms[1]

    def replace_atom(self, target, substitute):
        """ disconnects from target, and reconnects to substitute.
        used in Molecule.handle_overlap() and Atom.eat_atom() """
        atom1, atom2 = self.atoms
        self.disconnect_atoms()
        if atom1 is target:
            self.connect_atoms(substitute, atom2)
        elif atom2 is target:
            self.connect_atoms(atom1, substitute)
        else:
            print("warning : trying to replace non existing atom")

    def change_double_bond_alignment(self):
        if self.second_line_side==None:# in case when bond with delocalization ring loaded from file
            return
        self.auto_second_line_side = False
        # for delocalized bond it switches between 1 and -1 (left and right)
        if self.type in ("delocalized", "bold2"):
            self.second_line_side = -self.second_line_side
            return
        # for double bond it switches between -1, 0 and 1 (right, center, left)
        self.second_line_side = self.second_line_side+1 if self.second_line_side<1 else -1

    def reverse_direction(self):
        self.atoms.reverse()

    def set_focus(self, focus: bool):
        """ handle draw or undraw on focus change """
        if focus:
            self._focus_item = self.paper.addLine(self.atoms[0].pos + self.atoms[1].pos, width=self._line_width+8, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            self._selection_item = self.paper.addLine(self.atoms[0].pos + self.atoms[1].pos, self._line_width+4, Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    @property
    def chemistry_items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items + [ self._focus_item, self._selection_item])

    def clear_drawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items = []
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        # prev drawings must be cleared even if not redrawn.
        # Because, when midline is None after bond changed its position,
        # if drawings are not cleared, bond remains in older position
        # while attached atoms move to new position.
        self.clear_drawings()

        self._midline = self._where_to_draw_from_and_to()
        if not self._midline:
            return # the bond is too short to draw it
        self.paper = self.molecule.paper
        # draw
        self._line_width = max(self.line_width*self.molecule.scale_val, 1)
        method = "_draw_%s" % self.type
        getattr(self, method)()
        # add all main items as focusable
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def redraw(self):
        if self.auto_second_line_side:
            self.second_line_side = None
        self.draw()

    def _where_to_draw_from_and_to(self):
        x1,y1,x2,y2 = line = self.atoms[0].pos + self.atoms[1].pos
        bbox1 = self.atoms[0].bounding_box()
        bbox2 = self.atoms[1].bounding_box()
        # can not draw bond when atoms are too close
        if geo.rect_intersects_rect(bbox1, bbox2):
            return None
        # there should be fine gap between atom text and the bond line,
        # so increase boundingbox on all sides.
        if self.atoms[0]._main_items:
            bbox1 = [bbox1[0]-2, bbox1[1]+2, bbox1[2]+2, bbox1[3]+1]
            x1,y1 = geo.rect_get_intersection_of_line(bbox1, line)
        if self.atoms[1]._main_items:
            bbox2 = [bbox2[0]-2, bbox2[1]+2, bbox2[2]+2, bbox2[3]+1]
            x2,y2 = geo.rect_get_intersection_of_line(bbox2, line)

        return [x1,y1,x2,y2]


    def _draw_single(self):
        #print("draw single")
        self._main_items = [self.paper.addLine(self._midline, self._line_width, color=self.color)]


    def _draw_double(self):
        #print("draw double")
        if self.second_line_side == None:
            self.second_line_side = self._calc_second_line_side()

        # sign and value of 'd' determines side and distance of second line
        if self.second_line_side==0:# centered
            # draw one of two equal parallel lines
            d =  0.5 * self.line_spacing * self.molecule.scale_val
            line0 = calc_second_line(self, self._midline, -d)
        else:
            d = self.second_line_side * self.line_spacing * self.molecule.scale_val
            line0 = self._midline

        item0 = self.paper.addLine(line0, self._line_width, color=self.color)

        # draw the other parallel line
        line1 = calc_second_line(self, self._midline, d)
        item1 = self.paper.addLine(line1, self._line_width, color=self.color)

        self._main_items = [item0, item1]


    def _draw_triple(self):
        d = 0.75 * self.line_spacing * self.molecule.scale_val
        line1 = calc_second_line(self, self._midline, d)
        line2 = calc_second_line(self, self._midline, -d)
        item0 = self.paper.addLine(self._midline, self._line_width, color=self.color)
        item1 = self.paper.addLine(line1, self._line_width, color=self.color)
        item2 = self.paper.addLine(line2, self._line_width, color=self.color)

        self._main_items = [item0, item1, item2]


    def _draw_delocalized(self):
        # draw longer solid mid-line
        item0 = self.paper.addLine(self._midline, self._line_width, color=self.color)
        self._main_items = [item0]

        if not self.show_delocalization:
            return
        if self.second_line_side == None:
            self.second_line_side = self._calc_second_line_side() or 1

        # draw the dashed parallel line
        # sign and value of 'd' determines side and distance of second line
        d = self.second_line_side * self.line_spacing * self.molecule.scale_val
        line1 = calc_second_line(self, self._midline, d)
        item1 = self.paper.addLine(line1, self._line_width, color=self.color, style=PenStyle.dashed)
        self._main_items.append(item1)


    def _draw_partial(self):
        self._main_items = [ self.paper.addLine(self._midline, self._line_width,
                        color=self.color, style=PenStyle.dashed) ]


    def _draw_hbond(self):
        self._main_items = [ self.paper.addLine(self._midline, self._line_width,
                        color=self.color, style=PenStyle.dotted) ]


    def _draw_coordinate(self):
        """ Coordinate bond or Dative bond """
        l, w, d = self.coord_head_dimensions
        head_pts = arrow_head(*self._midline, l,w,d)
        line = self._midline[:2] + list(head_pts[0])
        item1 = self.paper.addLine(line, self._line_width, color=self.color)
        item2 = self.paper.addPolygon(head_pts, color=self.color, fill=self.color)
        self._main_items = [item1, item2]

    # ------------ Stereo Bonds -------------------

    def _draw_wedge(self):
        d = 0.5 * self.line_spacing * self.molecule.scale_val
        p1 = geo.line_get_point_at_distance(self._midline, d)
        p2 = geo.line_get_point_at_distance(self._midline, -d)
        p0 = (self._midline[0], self._midline[1])
        self._main_items = [ self.paper.addPolygon([p0,p1,p2], color=self.color, fill=self.color) ]


    def _draw_hashed_wedge(self):
        d = 0.5 * self.line_spacing * self.molecule.scale_val
        p1_x, p1_y = geo.line_get_point_at_distance(self._midline, d)
        p2_x, p2_y = geo.line_get_point_at_distance(self._midline, -d)
        p0_x, p0_y = (self._midline[0], self._midline[1])
        line_width = 1.2 * self._line_width
        line_count = int(round(geo.line_length(self._midline) / (3*line_width)))
        if line_count<2:# to avoid zero division error
            return
        lines = []
        for i in range(line_count):
            t = i/(line_count-1)
            x1 = p0_x + (p1_x-p0_x)*t
            y1 = p0_y + (p1_y-p0_y)*t
            x2 = p0_x + (p2_x-p0_x)*t
            y2 = p0_y + (p2_y-p0_y)*t
            lines.append([x1,y1,x2,y2])
        self._main_items = [ self.paper.addLine(line, line_width, self.color) for line in lines ]


    def _draw_bold(self):
        # bold width should be wedge_width/1.5
        width = 0.75 * self.line_spacing * self.molecule.scale_val
        self._main_items = [ self.paper.addLine(self._midline, width,
                            color=self.color, cap=LineCap.square) ]


    def _draw_hashed(self):
        d = (0.75 * self.line_spacing * self.molecule.scale_val)/2
        rev_line = self._midline[2:] + self._midline[:2]
        s1_x, s1_y = geo.line_get_point_at_distance(rev_line, d)
        s2_x, s2_y = geo.line_get_point_at_distance(rev_line, -d)
        e1_x, e1_y = geo.line_get_point_at_distance(self._midline, -d)
        e2_x, e2_y = geo.line_get_point_at_distance(self._midline, d)
        line_width = 1.2 * self._line_width
        line_count = int(round(geo.line_length(self._midline) / (3*line_width)))
        if line_count<2:# to avoid zero division error
            return
        lines = []
        for i in range(line_count):
            t = i/(line_count-1)
            x1 = s1_x + (e1_x-s1_x)*t
            y1 = s1_y + (e1_y-s1_y)*t
            x2 = s2_x + (e2_x-s2_x)*t
            y2 = s2_y + (e2_y-s2_y)*t
            lines.append([x1,y1,x2,y2])
        self._main_items = [ self.paper.addLine(line, line_width, self.color) for line in lines ]


    def _draw_bold2(self):
        """ Bold Double bond """
        width = 0.75 * self.line_spacing * self.molecule.scale_val
        item0 = self.paper.addLine(self._midline, width, color=self.color, cap=LineCap.square)

        if self.second_line_side == None:
            self.second_line_side = self._calc_second_line_side() or 1

        # draw the thin parallel line
        # sign and value of 'd' determines side and distance of second line
        d = self.second_line_side * 1.25*self.line_spacing * self.molecule.scale_val
        line1 = calc_second_line(self, self._midline, d)
        item1 = self.paper.addLine(line1, self._line_width, color=self.color)
        self._main_items = [item0, item1]


    def _draw_wavy(self):
        """ The Up or Down bond """
        d = (0.75 * self.line_spacing * self.molecule.scale_val)/2
        s_x, s_y, e_x, e_y = self._midline
        rev_line = self._midline[2:] + self._midline[:2]
        s1_x, s1_y = geo.line_get_point_at_distance(rev_line, d)
        s2_x, s2_y = geo.line_get_point_at_distance(rev_line, -d)
        e1_x, e1_y = geo.line_get_point_at_distance(self._midline, -d)
        e2_x, e2_y = geo.line_get_point_at_distance(self._midline, d)
        line_width = 1.2 * self._line_width
        line_count = int(round(geo.line_length(self._midline) / (3*line_width)))
        line_count = max(line_count, 2)
        points = []
        for i in range(line_count):
            t = i/(line_count-1)
            x0 = s_x + (e_x-s_x)*t
            y0 = s_y + (e_y-s_y)*t
            x1 = s1_x + (e1_x-s1_x)*t
            y1 = s1_y + (e1_y-s1_y)*t
            x2 = s2_x + (e2_x-s2_x)*t
            y2 = s2_y + (e2_y-s2_y)*t
            if i%2:# even
                points += [(x2,y2), (x0,y0), (x1,y1)]
            else:# odd
                points += [(x1,y1), (x0,y0), (x2,y2)]
        self._main_items = [self.paper.addCubicBezier(points[1:-1], line_width, self.color)]


    # ------------ Ambiguous Bonds -------------------

    def _draw_E_or_Z(self):
        """ draw Either Cis or Trans Bond """
        d =  0.5 * self.line_spacing * self.molecule.scale_val
        self.second_line_side = 0
        line0 = calc_second_line(self, self._midline, -d)
        line1 = calc_second_line(self, self._midline, d)
        # draw two lines crossing each other
        item0 = self.paper.addLine(line0[:2]+line1[2:], self._line_width, color=self.color)
        item1 = self.paper.addLine(line0[2:]+line1[:2], self._line_width, color=self.color)
        self._main_items = [item0, item1]


    def _draw_1_or_2(self):
        """ Draw single or double """
        self._main_items = [self.paper.addLine(self._midline, self._line_width, color=self.color)]
        self._set_label_text("S/D")

    def _draw_1_or_a(self):
        """ Draw single or aromatic """
        self._main_items = [self.paper.addLine(self._midline, self._line_width, color=self.color)]
        self._set_label_text("S/A")

    def _draw_2_or_a(self):
        """ Draw double or aromatic """
        self._main_items = [self.paper.addLine(self._midline, self._line_width, color=self.color)]
        self._set_label_text("D/A")

    def _draw_any(self):
        """ Draw Any bond """
        self._main_items = [self.paper.addLine(self._midline, self._line_width, color=self.color)]
        self._set_label_text("Any")

    def _set_label_text(self, text):
        """ draw a text beside bond for S/D, S/A etc bonds """
        x1,y1,x2,y2 = self._midline
        if x2<x1:
            x2,y2,x1,y1 = self._midline
        midpoint = (x1+x2)/2, (y1+y2)/2
        font = Font(Settings.atom_font_name, 0.75*Settings.atom_font_size*self.molecule.scale_val)
        label = self.paper.addHtmlText(text, midpoint, font, Align.HCenter|Align.VCenter)
        w, h = label.boundingRect().getRect()[2:]
        cx,cy = geo.line_get_point_at_distance((x1,y1)+midpoint, h/3)
        dx,dy = cx-midpoint[0], cy-midpoint[1]
        label.moveBy(dx,dy)
        rotation = geo.line_get_angle_from_east([x1,y1,x2,y2])
        self.paper.setItemRotation(label, degrees(rotation))
        self._main_items.append(label)


    # here we first check which side has higher number of ring atoms, and put
    # the double bond to that side. If both side has equal or no ring atoms,
    # check which side has higher number of neighbouring atoms.
    # If one atom has no other neighbours, center the double bond.
    # If both side has equal number of atoms, put second bond to the side
    # by atom priority C > non-C > H
    def _calc_second_line_side( self):
        """returns 0 for center, -1 for right and +1 for left """
        # for cumulated double bonds, center aligned
        for e in self.neighbor_edges:
            if e.order==2:
                return 0
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
            on_which_side = lambda xy: geo.line_get_side_of_point( line, xy)
            circles += reduce( operator.add, map( on_which_side, [a.pos for a in ring if a not in self.atoms]))
        if circles: # left or right side has greater number of ring atoms
          side = circles
        else:
          sides = [geo.line_get_side_of_point( line, xy, threshold=0.1) for xy in coords]
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

    def bounding_box(self):
        return geo.rect_normalize(self.atom1.pos + self.atom2.pos)

    def scale(self, scale):
        pass

#    def transform(self, tr):
#        pass

    @property
    def menu_template(self):
        menu = ()
        side = {1: "Left", -1: "Right", 0: "Middle"}.get(self.second_line_side)
        auto_side = self.auto_second_line_side and "Auto (%s)"%side or "Auto"
        if self.type == "double":
            menu += (("Double Bond Side", (auto_side, "Left", "Right", "Middle")),)
        elif self.type in ("delocalized", "bold2"):
            menu += (("Double Bond Side", (auto_side, "Left", "Right")),)
        return menu

    def get_property(self, key):
        if key=="Double Bond Side":
            side = {1: "Left", -1: "Right", 0: "Middle"}.get(self.second_line_side)
            return self.auto_second_line_side and "Auto (%s)"%side or side
        else:
            print("Warning ! : Invalid key '%s'"%key)

    def set_property(self, key, val):
        if key=="Double Bond Side":
            if val.startswith("Auto"):
                self.second_line_side = None
                self.auto_second_line_side = True
            else:
                name_to_val = {"Left": 1, "Right": -1, "Middle": 0}
                self.second_line_side = name_to_val[val]
                self.auto_second_line_side = False


# while drawing second line of double bond, the bond length is shortened.
# bond is shortened to the intersection point of the parallel line
# (i.e imaginary second bond) of the neighbouring bond of same side.
# This way, if we convert neighbour bond from single to double bond, the
# second bonds will just touch at the end and won't cross each other.
def calc_second_line( bond, mid_line, distance):
    # center bond coords
    bond_line = bond.atoms[0].pos + bond.atoms[1].pos
    mid_bond_len = geo.point_distance(bond.atoms[0].pos, bond.atoms[1].pos)
    # second parallel bond coordinates
    x, y, x0, y0 = geo.line_get_parallel(mid_line, distance)
    # shortening of the second bond
    dx = x-x0
    dy = y-y0
    _k = 0 if bond.second_line_side==0 else (1-bond.double_length_ratio)/2

    x, y, x0, y0 = x-_k*dx, y-_k*dy, x0+_k*dx, y0+_k*dy
    # shift according to the bonds around
    side = geo.line_get_side_of_point( bond_line, (x,y))
    for atom in bond.atoms:
      second_atom = bond.atoms[1] if atom is bond.atoms[0] else bond.atoms[0]
      # find all neighbours at the same side of (x,y)
      neighs = [n for n in atom.neighbors if geo.line_get_side_of_point( bond_line, [n.x,n.y])==side and n is not second_atom]
      for n in neighs:
        dist2 = _k * mid_bond_len * geo.line_get_side_of_point((atom.x, atom.y, n.x, n.y), (second_atom.x, second_atom.y))
        xn1, yn1, xn2, yn2 = geo.line_get_parallel([atom.x, atom.y, n.x, n.y], dist2)
        xp, yp, parallel = geo.line_get_intersection_of_line([x,y,x0,y0], [xn1,yn1,xn2,yn2])
        if not parallel:
          if not geo.line_contains_point([x,y,x0,y0], (xp,yp)):
            # only shorten the line - do not elongate it
            continue
          if geo.point_distance(atom.pos, (x,y)) < geo.point_distance(atom.pos, (x0,y0)):
            x,y = xp, yp
          else:
            x0,y0 = xp, yp
    return [x, y, x0, y0]
