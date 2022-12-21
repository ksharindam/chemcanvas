from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen
#from PyQt5.QtWidgets import QGraphicsLineItem

from functools import reduce

from app_data import App
from graph import Edge
from geometry import *
from drawable import DrawableObject
import common, operator

global bond_id_no
bond_id_no = 1

class Bond(Edge, DrawableObject):
    obj_type = 'Bond'
    focus_priority = 2
    bond_types = ['normal', 'double', 'triple', 'wedge_near', 'wedge_far', 'dashed', 'dotted']

    def __init__(self, atom1, atom2, bond_type='normal'):
        DrawableObject.__init__(self)
        Edge.__init__(self, [atom1, atom2])
        self.atom1 = atom1
        self.atom2 = atom2
        self.atom1.addBond(self)
        self.atom2.addBond(self)
        #self.order = order # 1,2 or 3 for single, double or triple bond
        self.type = bond_type
        global bond_id_no
        self.id = 'bond' + str(bond_id_no)
        bond_id_no += 1
        # drawing related
        self._second = None # second line of a double/triple bond
        self._third = None
        self._focus_item = None
        self._select_item = None
        self.center = None
        self.bond_width = None  # distance between two parallel lines of a double bond
        self.auto_bond_sign = 1 # used to manually change the sign of bond_width, values are 1 and -1
        self.double_length_ratio = 0.75

    def __str__(self):
        return "%s : %s-%s" % (self.id, self.atom1, self.atom2)

    @property
    def molecule(self):
        return self.atom1.molecule

    @property
    def parent(self):
        return self.atom1.molecule

    @property
    def order(self):
        if self.type == 'double':
            return 2
        elif self.type == 'triple':
            return 3
        return 1

    @property
    def atoms(self):
        return self.vertices

    def atomConnectedTo(self, atom):
        return self.atom1 if atom is self.atom2 else self.atom2

    def replaceAtom(self, target, substitute):
        """ disconnects from target, and reconnects to substitute """
        if self.atom1 is target:
            self.atom1, common_atom = substitute, self.atom2
        elif self.atom2 is target:
            self.atom2, common_atom = substitute, self.atom1
        else:
            print("warning : trying to replace non existing atom")
            return
        self.vertices = [self.atom1, self.atom2]
        target.removeBond(self)
        common_atom.removeBond(self) # because target must be removed from neighbors list
        common_atom.addBond(self)
        substitute.addBond(self)

    def setFocus(self, focus: bool):
        """ Focus or unfocus when mouse is hovered """
        if focus:
            self._focus_item = App.paper.addLine(self.atom1.pos + self.atom2.pos, 3)
        else: # unfocus
            App.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            self._select_item = App.paper.addLine(self.atom1.pos + self.atom2.pos, 5, Qt.blue)
            App.paper.toBackground(self._select_item)
        elif self._select_item:
            App.paper.removeItem(self._select_item)
            self._select_item = None

    def clearDrawings(self):
        if self.graphics_item:
            App.paper.removeObject(self)
        if self._second:
            App.paper.removeItem(self._second)
            self._second = None
        if self._third:
            App.paper.removeItem(self._third)
            self._third = None
        if self._focus_item:
            self.setFocus(False)
        if self._select_item:
            self.setSelected(False)

    def draw(self):
        if self.graphics_item:
            print("Warning : drawing bond which is already drawn")
            return
        method = "_draw_%s" % self.type
        self.__class__.__dict__[method](self)

    def redraw(self):
        self.center = None
        self.bond_width = None
        focused = bool(self._focus_item)
        selected = bool(self._select_item)
        self.clearDrawings()
        self.draw()
        App.paper.addObject(self)
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)


    def _where_to_draw_from_and_to(self):
        x1, y1 = self.atom1.x, self.atom1.y
        x2, y2 = self.atom2.x, self.atom2.y
        # at first check if the bboxes are not overlapping
        bbox1 = Rect(self.atom1.boundingBox())
        bbox2 = Rect(self.atom2.boundingBox())
        if bbox1.intersects(bbox2):
            return None # atoms too close to draw a bond
        # then we continue with computation
        if self.atom1.show:
            x1, y1 = bbox1.intersectionOfLine([x1,y1,x2,y2])
        if self.atom2.show:
            x2, y2 = bbox2.intersectionOfLine([x1,y1,x2,y2])

        if point_distance( x1, y1, x2, y2) <= 1.0:
            return None
        return (x1, y1, x2, y2)

    def _draw_normal(self):
        #print("draw normal")
        line = self._where_to_draw_from_and_to()
        if not line:
            return # the bond is too short to draw it
        # more things to consider : decide the capstyle, transformation
        self.graphics_item = App.paper.addLine(line)

    def _draw_double(self):
        #print("draw double")
        first_line = self._where_to_draw_from_and_to()
        if not first_line:
            return # the bond is too short to draw it
        self.graphics_item = App.paper.addLine(first_line)
        # more things to consider : decide the capstyle, transformation
        if self.center == None or self.bond_width == None:
            self._decide_distance_and_center()
        d = self.bond_width
        # double
        if self.center:
            d = round(d*0.4)
            self.setItemColor(self.graphics_item, Qt.transparent)
        x, y, x0, y0 = Line(first_line).findParallel(d)
        self._second = self._draw_second_line( [x, y, x0, y0])
        if self.center:
            x1, y1, x2, y2 = first_line
            self._third = self._draw_second_line( [2*x1-x, 2*y1-y, 2*x2-x0, 2*y2-y0])


    def _draw_triple(self):
        first_line = self._where_to_draw_from_and_to()
        if not first_line:
            return # the bond is too short to draw it
        self.graphics_item = App.paper.addLine(first_line)
        # more things to consider : decide the capstyle, transformation
        if self.bond_width == None:
            self._decide_distance_and_center()

        x, y, x0, y0 = Line(first_line).findParallel(self.bond_width * 0.75)
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
        mid_line = (self.atom1.x, self.atom1.y, self.atom2.x, self.atom2.y)
        mid_bond_len = point_distance(*mid_line)
        # second parallel bond coordinates
        x, y, x0, y0 = coords
        # shortening of the second bond
        dx = x-x0
        dy = y-y0
        _k = 0 if self.center else (1-self.double_length_ratio)/2

        x, y, x0, y0 = x-_k*dx, y-_k*dy, x0+_k*dx, y0+_k*dy
        # shift according to the bonds arround
        side = on_which_side_is_point( mid_line, (x,y))
        for atom in (self.atom1, self.atom2):
          second_atom = self.atom2 if atom is self.atom1 else self.atom1
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
              if point_distance( atom.x,atom.y,x,y) < point_distance( atom.x,atom.y,x0,y0):
                x,y = xp, yp
              else:
                x0,y0 = xp, yp
        return App.paper.addLine([x, y, x0, y0])


    def _decide_distance_and_center( self):
        """ calculate Bond.center and Bond.bond_width should be from molecular geometry """
        if not self.bond_width:
            self.bond_width = App.bond_width
            #line = [self.atom1.x, self.atom1.y, self.atom2.x, self.atom2.y]
            #length = sqrt((line[0]-line[2])**2  + (line[1]-line[3])**2)
            #self.bond_width = round( length / 5, 1)
        # does not need to go further if the bond is not double
        if self.order != 2:
            return
        sign, center = self._compute_sign_and_center()
        self.bond_width = self.auto_bond_sign * sign * abs( self.bond_width)
        self.center = center

    # here we first check which side has higher number of ring atoms, and put
    # the double bond to that side. If both side has equal or no ring atoms,
    # check which side has higher number of neighbouring atoms.
    # If one atom has no other neighbours, center the double bond.
    # If both side has equal number of atoms, put second bond to the side
    # by atom priority C > non-C > H
    def _compute_sign_and_center( self):
        """returns tuple of (sign, center) where sign is the default sign of the self.bond_width"""
        # check if we need to transform 3D before computation
        # /end of check
        line = [self.atom1.x, self.atom1.y, self.atom2.x, self.atom2.y]
        atms = self.atom1.neighbors + self.atom2.neighbors
        atms = common.difference( atms, [self.atom1, self.atom2])
        coords = [(a.x,a.y) for a in atms]
        # searching for circles
        circles = 0 # sum of side value of all ring atoms
        # find all rings in the molecule and choose the rings which contain this bond.
        for ring in self.molecule.get_smallest_independent_cycles_dangerous_and_cached():
          if self.atom1 in ring and self.atom2 in ring:
            on_which_side = lambda xy: on_which_side_is_point( line, xy)
            circles += reduce( operator.add, map( on_which_side, [a.pos for a in ring if a not in self.atoms]))
        if circles: # left or right side has greater number of ring atoms
          side = circles
        else:
          sides = [on_which_side_is_point( line, xy, threshold=0.1) for xy in coords]
          side = reduce( operator.add, sides, 0)
        # on which side to put the second line
        if side == 0 and (len( self.atom1.neighbors) == 1 or
                          len( self.atom2.neighbors) == 1):
          # maybe we should center, but this is usefull only when one of the atoms has no other substitution
          ret = (1 ,1)
        else:
          if not circles:
            # we center when both atoms have visible symbol and are not in circle
            if self.atom1.show and self.atom2.show:
              return (1, 1)
            # recompute side with weighting of atom types
            for i in range( len( sides)):
              if sides[i] and atms[i].__class__.__name__ == "atom":
                if atms[i].symbol == 'H':
                  sides[i] *= 0.1 # this discriminates H
                elif atms[i].symbol != 'C':
                  sides[i] *= 0.2 # this makes "non C" less then C but more then H
              side = reduce( operator.add, sides, 0)
          if side < 0:
            ret = (-1, 0)
          else:
            ret = (1, 0)
        # transform back if necessary
        '''if transform:
          inv = transform.get_inverse()
          for n in self.atom1.neighbors + self.atom2.neighbors:
            n.transform( inv)'''
        # /end of back transform
        return ret

#    def moveBy(self, dx, dy):
#        items = filter(None, [self.graphics_item, self._second, self._third, self._focus_item, self._select_item])
#        [item.moveBy(dx,dy) for item in items]

