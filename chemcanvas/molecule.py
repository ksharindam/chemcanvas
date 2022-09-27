from atom import Atom
from bond import Bond
from graph import Graph
import common
from geometry import *
from app_data import App
from math import cos, sin, pi

global molecule_id_no
molecule_id_no = 1

class Molecule(Graph):
    obj_type = 'Molecule'
    def __init__(self, paper):
        Graph.__init__(self)
        self.paper = paper
        # this makes two variable same, when we modify self.atoms, self.vertices gets modified
        self.atoms = self.vertices  # a list of vertices
        self.bonds = self.edges     # a set of edges
        # set molecule unique id
        global molecule_id_no
        self.id = 'molecule' + str(molecule_id_no)
        molecule_id_no += 1
        # drawing related
        self._last_used_atom = None
        self.sign = 1

    # whenever an atom or a bond is added or removed, graph cache must be cleared
    def newAtom(self, pos):
        atom = Atom(self, pos)
        self.atoms.append(atom)
        self.clear_cache()
        print("added atom :", atom)
        return atom

    def newBond(self, atom1, atom2, bond_type="normal"):
        bond = Bond(atom1, atom2, bond_type)
        self.bonds.add(bond)
        self.clear_cache()
        print("added bond :", bond)
        return bond

    def addAtom(self, atom):
        atom.molecule = self
        self.atoms.append(atom)
        self.clear_cache()

    def removeAtom(self, atom):
        self.atoms.remove(atom)
        atom.molecule = None
        self.clear_cache()

    def addBond(self, bond):
        print("added bond :", bond)
        self.bonds.add(bond)
        self.clear_cache()

    def removeBond(self, bond):
        self.bonds.remove(bond)
        self.clear_cache()

    def addAtomTo(self, a1, bond_to_use=None, pos=None):
        """adds new atom (a2) to atom a1 with bond, the position of new atom can be specified in pos or is
        decided calling find_place(), if x, y is specified and matches already existing atom it will be
        used instead of creating new one """
        if pos != None:
          x, y = pos
        else:
          if bond_to_use:
            x, y = self.findPlace( a1, App.bond_length, bond_to_use.order)
          else:
            x, y = self.findPlace( a1, App.bond_length)
        a2 = None # the new atom
        #if pos:
        # try if the coordinates are the same as of another atom
        for at in self.atoms:
          if abs( at.x - x) < 3 and abs( at.y - y) < 3 and not at == a1:
            a2 = at
            break
        if not a2:
          a2 = self.newAtom( QPoint(x, y))
        b = bond_to_use or Bond(a1, a2)
        self.addBond(b)
        return a2, b


    def findPlace( self, a, distance, added_order=1):
        """tries to find accurate place for next atom around atom 'a',
        returns x,y and list of ids of 'items' found there for overlap, those atoms are not bound to id"""
        neighbors = a.neighbors
        if len( neighbors) == 0:
          x = a.x + cos( pi/6) *distance
          y = a.y - sin( pi/6) *distance
        elif len( neighbors) == 1:
          neigh = neighbors[0]
          if a.bonds[0].order != 3 and added_order != 3:
            # we add a single bond to atom with one single bond
            if a == self._last_used_atom or len( neigh.neighbors) != 2:
              # the user has either deleted the last added bond and wants it to be on the other side
              # or it is simply impossible to define a transoid configuration
              self.sign = -self.sign
              x = a.x + cos( self.get_angle( a, neighbors[0]) +self.sign*2*pi/3) *distance
              y = a.y + sin( self.get_angle( a, neighbors[0]) +self.sign*2*pi/3) *distance
            else:
              # we would add the new bond transoid
              neighs2 = neigh.neighbors
              neigh2 = (neighs2[0] == a) and neighs2[1] or neighs2[0]
              x = a.x + cos( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
              y = a.y + sin( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
              side = on_which_side_is_point( (neigh.x,neigh.y,a.x,a.y), (x,y))
              if side == on_which_side_is_point(  (neigh.x,neigh.y,a.x,a.y), (neigh2.x,neigh2.y)):
                self.sign = -self.sign
                x = a.x + cos( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
                y = a.y + sin( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
              self._last_used_atom = a
          else:
            x = a.x + cos( self.get_angle( a, neighbors[0]) + pi) *distance
            y = a.y + sin( self.get_angle( a, neighbors[0]) + pi) *distance
        else:
          x, y = self.find_least_crowded_place_around_atom( a, distance)
        return x, y

    def find_least_crowded_place_around_atom( self, a, range_=10):
        atms = a.neighbors
        if not atms:
          # single atom molecule
          if a.show_hydrogens and a.text_pos == "center-first":
            return a.x - range_, a.y
          else:
            return a.x + range_, a.y
        angles = [clockwise_angle_from_east( at.x-a.x, at.y-a.y) for at in atms]
        angles.append( 2*pi + min( angles))
        angles.sort()
        angles.reverse()
        diffs = common.list_difference( angles)
        i = diffs.index( max( diffs))
        angle = (angles[i] +angles[i+1]) / 2
        return a.x + range_*cos( angle), a.y + range_*sin( angle)

    def get_angle( self, a1, a2):
        """ angle between x-axis and a1-a2 line """
        a = a2.x - a1.x
        b = a2.y - a1.y
        return atan2( b, a)
