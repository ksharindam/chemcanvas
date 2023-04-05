from PyQt5.QtCore import QLineF, Qt

from app_data import App, Settings
from graph import Edge
from drawable import DrawableObject
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
    object_type = 'Bond'
    focus_priority = 2
    redraw_priority = 2
    meta__undo_properties = ("molecule", "type", "second_line_side", "second_line_distance",
                "double_length_ratio")
    meta__undo_copy = ("atoms",)
    meta__same_objects = {"vertices":"atoms"}
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
        self._main_item = None
        self._second = None # second line of a double/triple bond
        self._third = None
        self._focus_item = None
        self._select_item = None
        # double bond's second line placement and gap related
        self.second_line_side = None # None=Unknown, 0=centered, -1=one side, +1=another side
        self.second_line_distance = Settings.bond_width # distance between two parallel lines of a double bond
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
        if self.type == 'double':
            return 2
        elif self.type == 'triple':
            return 3
        return 1

    def setType(self, bond_type):
        self.type = bond_type
        [atom._update_occupied_valency() for atom in self.atoms]

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
            self._focus_item = self.paper.addLine(self.atoms[0].pos + self.atoms[1].pos, width=10, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            self._select_item = self.paper.addLine(self.atoms[0].pos + self.atoms[1].pos, 5, Settings.selection_color)
            self.paper.toBackground(self._select_item)
        elif self._select_item:
            self.paper.removeItem(self._select_item)
            self._select_item = None

    def clearDrawings(self):
        #if not self.paper:# we have not drawn yet
        #    return
        if self._main_item:
            self.paper.removeFocusable(self._main_item)
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._second:
            self.paper.removeItem(self._second)
            self._second = None
        if self._third:
            self.paper.removeItem(self._third)
            self._third = None
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
        method = "_draw_%s" % self.type
        self.__class__.__dict__[method](self)
        self.paper.addFocusable(self._main_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def redraw(self):
        self.second_line_side = None
        self.draw()

    def _where_to_draw_from_and_to(self):
        x1, y1 = self.atoms[0].pos
        x2, y2 = self.atoms[1].pos
        # at first check if the bboxes are not overlapping
        bbox1 = Rect(self.atoms[0].boundingBox())
        bbox2 = Rect(self.atoms[1].boundingBox())
        if bbox1.intersects(bbox2):
            return None # atoms too close to draw a bond
        # then we continue with computation
        if self.atoms[0].show_symbol:
            x1, y1 = bbox1.intersectionOfLine([x1,y1,x2,y2])
        if self.atoms[1].show_symbol:
            x2, y2 = bbox2.intersectionOfLine([x1,y1,x2,y2])

        if point_distance((x1,y1), (x2,y2)) <= 1.0:
            return None
        return (x1, y1, x2, y2)

    def _draw_normal(self):
        #print("draw normal")
        line = self._where_to_draw_from_and_to()
        if not line:
            return # the bond is too short to draw it
        # more things to consider : decide the capstyle, transformation
        self._main_item = self.paper.addLine(line)

    def _draw_double(self):
        #print("draw double")
        first_line = self._where_to_draw_from_and_to()
        if not first_line:
            return # the bond is too short to draw it
        self._main_item = self.paper.addLine(first_line)
        # more things to consider : decide the capstyle, transformation
        if self.second_line_side == None:
            self.second_line_side = self._calc_second_line_side()
        # sign and value of 'd' determines side and distance of second line
        if self.second_line_side==0:# centered
            d = round(0.4 * self.second_line_distance)
        else:
            d = self.second_line_distance * self.second_line_side

        x, y, x0, y0 = Line(first_line).findParallel(d)
        self._second = self._draw_second_line( [x, y, x0, y0])
        if self.second_line_side==0:
            self.setItemColor(self._main_item, Qt.transparent)
            x1, y1, x2, y2 = first_line
            self._third = self._draw_second_line( [2*x1-x, 2*y1-y, 2*x2-x0, 2*y2-y0])


    def _draw_triple(self):
        first_line = self._where_to_draw_from_and_to()
        if not first_line:
            return # the bond is too short to draw it
        self._main_item = self.paper.addLine(first_line)
        # more things to consider : decide the capstyle, transformation
        x, y, x0, y0 = Line(first_line).findParallel(self.second_line_distance * 0.75)
        self._second = self._draw_second_line( [x, y, x0, y0])
        x1, y1, x2, y2 = first_line
        self._third = self._draw_second_line( [2*x1-x, 2*y1-y, 2*x2-x0, 2*y2-y0])


    # while drawing second line of double bond, the bond length is shortened.
    # bond is shortened to the intersection point of the parallel line
    # (i.e imaginary second bond) of the neighbouring bond of same side.
    # This way, if we convert neighbour bond from single to double bond, the
    # second bonds will just touch at the end and won't cross each other.
    def _draw_second_line( self, coords):
        # center bond coords
        mid_line = self.atoms[0].pos + self.atoms[1].pos
        mid_bond_len = point_distance(self.atoms[0].pos, self.atoms[1].pos)
        # second parallel bond coordinates
        x, y, x0, y0 = coords
        # shortening of the second bond
        dx = x-x0
        dy = y-y0
        _k = 0 if self.second_line_side==0 else (1-self.double_length_ratio)/2

        x, y, x0, y0 = x-_k*dx, y-_k*dy, x0+_k*dx, y0+_k*dy
        # shift according to the bonds arround
        side = on_which_side_is_point( mid_line, (x,y))
        for atom in self.atoms:
          second_atom = self.atoms[1] if atom is self.atoms[0] else self.atoms[0]
          # find all neighbours at the same side of (x,y)
          neighs = [n for n in atom.neighbors if on_which_side_is_point( mid_line, [n.x,n.y])==side and n is not second_atom]
          for n in neighs:
            dist2 = _k * mid_bond_len * on_which_side_is_point((atom.x, atom.y, n.x, n.y), (second_atom.x, second_atom.y))
            xn1, yn1, xn2, yn2 = Line([atom.x, atom.y, n.x, n.y]).findParallel(dist2)
            xp,yp,parallel,online = Line([x,y,x0,y0]).intersectionOfLine([xn1,yn1,xn2,yn2])
            if not parallel:
              if not Line([x,y,x0,y0]).contains([xp,yp]):
                # only shorten the line - do not elongate it
                continue
              if point_distance(atom.pos, (x,y)) < point_distance(atom.pos, (x0,y0)):
                x,y = xp, yp
              else:
                x0,y0 = xp, yp
        return self.paper.addLine([x, y, x0, y0])


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
            on_which_side = lambda xy: on_which_side_is_point( line, xy)
            circles += reduce( operator.add, map( on_which_side, [a.pos for a in ring if a not in self.atoms]))
        if circles: # left or right side has greater number of ring atoms
          side = circles
        else:
          sides = [on_which_side_is_point( line, xy, threshold=0.1) for xy in coords]
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

    def moveBy(self, dx, dy):
        items = filter(None, [self._main_item, self._second, self._third, self._focus_item, self._select_item])
        [item.moveBy(dx,dy) for item in items]

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("bond")
        elm.setAttribute("id", self.id)
        elm.setAttribute("atoms", " ".join([atom.id for atom in self.atoms]))
        elm.setAttribute("type", self.type)
        elm.setAttribute("order", str(self.order))
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        uid = elm.getAttribute("id")
        if uid:
            App.id_to_object_map[uid] = self

        atom_ids = elm.getAttribute("atoms")
        atoms = []
        for atom_id in atom_ids.split():
            try:
                atoms.append( App.id_to_object_map[atom_id])
            except KeyError:
                return False
        self.connectAtoms(atoms[0], atoms[1])

        _type = elm.getAttribute("type")
        if _type:
            self.setType(_type)

        # Bond Order : S/1=single, D/2=double, T/3=triple, hbond=Hydrogen Bond,
        # A=aromatic, partial01=order between 0 & 1, Similarly... partial12, partial23
        #order = elm.getAttribute("order")
        #if order:
        #    self.order = order

    def copy(self):
        """ copy of a bond can not be linked to same atoms as previous bond.
        So, copy of this bond have same properties except they are not linked to any bond """
        new_bond = Bond()
        for attr in self.meta__undo_properties:
            setattr(new_bond, attr, getattr(self, attr))
        return new_bond

