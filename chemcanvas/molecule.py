# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject
from atom import Atom
from bond import Bond
from graph import Graph
import common
import geometry as geo
from app_data import App
from math import cos, sin, pi, atan2

global molecule_id_no
molecule_id_no = 1

class Molecule(Graph, DrawableObject):
    redraw_priority = 1

    meta__undo_properties = ("scale_val",)
    meta__undo_copy = ("atoms", "bonds")
    meta__undo_children_to_record = ("atoms", "bonds")
    meta__same_objects = {"vertices":"atoms", "edges":"bonds"}
    meta__scalables = ("scale_val",)

    def __init__(self):
        DrawableObject.__init__(self)
        Graph.__init__(self)
        self.name = None
        # this makes two variable same, when we modify self.atoms, self.vertices gets modified
        self.atoms = self.vertices  # a list()
        self.bonds = self.edges     # a set()
        self.delocalizations = [] # delocalization ring or curves
        # template
        self.template_atom = None
        self.template_bond = None
        # set molecule unique id
        global molecule_id_no
        self.id = 'mol' + str(molecule_id_no)
        molecule_id_no += 1
        # drawing related
        self._last_used_atom = None
        self._sign = 1
        self.stereochemistry = []
        # this is used to calculate atom font size, and new bond length
        self.scale_val = 1.0

    @property
    def children(self):
        return self.atoms + list(self.bonds) + self.delocalizations

    def newAtom(self, symbol="C"):
        atom = Atom(symbol)
        self.addAtom(atom)
        #print("added atom :", atom)
        return atom

    def newBond(self):
        bond = Bond()
        self.addBond(bond)
        #print("added bond :", bond.id)
        return bond

    # whenever an atom or a bond is added or removed, graph cache must be cleared
    def addAtom(self, atom):
        self.atoms.append(atom)
        self.clear_cache()
        atom.molecule = self

    def removeAtom(self, atom):
        self.atoms.remove(atom)
        self.clear_cache()
        atom.molecule = None

    def addBond(self, bond):
        self.bonds.add(bond)
        self.clear_cache()
        bond.molecule = self

    def removeBond(self, bond):
        self.bonds.remove(bond)
        self.clear_cache()
        bond.molecule = None

    def add_delocalization(self, delocalization):
        self.delocalizations.append(delocalization)
        delocalization.molecule = self
        for bond in delocalization.bonds:
            bond.setType("aromatic")
            bond.show_delocalization = False
            if self.paper:
                self.paper.dirty_objects.add(bond)

    def remove_delocalization(self, delocalization):
        self.delocalizations.remove(delocalization)
        delocalization.molecule = None
        for bond in delocalization.bonds:
            # display dashed second line, if it is not part of another ring
            bond.show_delocalization = True
            if self.paper:
                self.paper.dirty_objects.add(bond)
        delocalization.deleteFromPaper()

    def eatMolecule(self, food_mol):
        if food_mol is self:
            return
        # move all atoms of food_mol to this molecule
        for atom in food_mol.atoms:
            self.addAtom(atom)
        food_mol.atoms.clear()

        # move all bonds of food_mol to this molecule
        for bond in food_mol.bonds:
            self.addBond(bond)
        food_mol.bonds.clear()
        # remove food_mol from paper
        if food_mol.paper:
            food_mol.paper.removeObject(food_mol)

    def splitFragments(self):
        """ convert each fragments into different molecules if it is broken molecule """
        new_mols = []
        frags = list(self.get_connected_components())
        for frag in frags[1:]:
            new_mol = Molecule()
            self.paper.addObject(new_mol)
            bonds = []
            for atom in frag:
                self.removeAtom(atom)
                new_mol.addAtom(atom)
                bonds += atom.bonds
            for bond in set(bonds):
                self.removeBond(bond)
                new_mol.addBond(bond)
            new_mols.append(new_mol)
        return new_mols


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
            # we add a single bond to atom with a single bond
            if a == self._last_used_atom or len( neigh.neighbors) != 2:
              # the user has either deleted the last added bond and wants it to be on the other side
              # or it is simply impossible to define a transoid configuration
              self._sign = -self._sign
              x = a.x + cos( get_angle( a, neighbors[0]) + self._sign*2*pi/3) *distance
              y = a.y + sin( get_angle( a, neighbors[0]) + self._sign*2*pi/3) *distance
            else:
              # we would add the new bond transoid
              neighs2 = neigh.neighbors
              neigh2 = (neighs2[0] == a) and neighs2[1] or neighs2[0]
              x = a.x + cos( get_angle( a, neigh) + self._sign*2*pi/3) *distance
              y = a.y + sin( get_angle( a, neigh) + self._sign*2*pi/3) *distance
              side = geo.line_get_side_of_point( (neigh.x,neigh.y,a.x,a.y), (x,y))
              if side == geo.line_get_side_of_point(  (neigh.x,neigh.y,a.x,a.y), (neigh2.x,neigh2.y)):
                self._sign = -self._sign
                x = a.x + cos( get_angle( a, neigh) + self._sign*2*pi/3) *distance
                y = a.y + sin( get_angle( a, neigh) + self._sign*2*pi/3) *distance
              self._last_used_atom = a
          else:
            x = a.x + cos( get_angle( a, neighbors[0]) + pi) *distance
            y = a.y + sin( get_angle( a, neighbors[0]) + pi) *distance
        # more than one neighbors
        else:
          x, y = find_least_crowded_place_around_atom(a, distance)
        return x, y


    def boundingBox(self):
        bboxes = []
        for atom in self.atoms:
            bboxes.append( atom.boundingBox())
        return common.bbox_of_bboxes( bboxes)

    def deepcopy(self):
        obj_map = {}
        new_mol = Molecule()
        #new_mol.paper = self.paper

        for atom in self.atoms:
            new_atom = atom.copy()
            new_mol.addAtom(new_atom)
            obj_map[atom.id] = new_atom

        for bond in self.bonds:
            new_bond = bond.copy()
            new_mol.addBond(new_bond)
            new_bond.connectAtoms(obj_map[bond.atom1.id], obj_map[bond.atom2.id])
            obj_map[bond.id] = new_bond

        if self.template_atom:
            new_mol.template_atom = obj_map[self.template_atom.id]
        if self.template_bond:
            new_mol.template_bond = obj_map[self.template_bond.id]
        return new_mol


    def handleOverlap(self):
        """ Merge overlapped atoms and bonds in this molecule.
        To handle overlap with two different molecules,
        call Molecule.eatMolecule() before calling this function """
        to_process = self.atoms[:]
        to_delete = []

        while len(to_process):
            a1 = to_process.pop(0) # the overlapped atom
            i = 0
            while i < len(to_process):
                a2 = to_process[i]
                if abs(a2.x-a1.x)<=2 and abs(a2.y-a1.y)<=2:
                    to_delete.append(a2)
                    to_process.pop(i)
                    # handle bonds
                    for bond in a2.bonds:
                        if bond.atomConnectedTo(a2) in a1.neighbors:
                            # two overlapping atoms have same neighbor means
                            # we found overlapping bond
                            bond.disconnectAtoms()
                            self.removeBond(bond)
                            bond.deleteFromPaper()
                        else:
                            # disconnect from overlapping atom, and connect to overlapped atom
                            bond.replaceAtom(a2, a1)
                else:
                    i += 1

        # delete overlapping atoms
        for atom in to_delete:
            self.removeAtom(atom)
            atom.deleteFromPaper()

    """def explicit_hydrogens_to_real_atoms( self, v):
        hs = set()
        for i in range( v.explicit_hydrogens):
            h = Atom("H")
            self.addAtom( h)
            b = self.newBond()
            b.connectAtoms(h,v)
            hs.add( h)
        v.explicit_hydrogens = 0
        return hs"""

    def addStereoChemistry(self, st):
        self.stereochemistry.append(st)

    def removeStereoChemistry(self, st):
        self.stereochemistry.remove(st)

#    def transform(self, tr):
#        pass

    def scale(self, scale):
        self.scale_val *= scale

    def detect_stereochemistry_from_coords( self, omit_rings=True):
        # double bonds
        # detect clusters of double bonds
        double_paths = []
        processed = set()
        for e in self.edges:
            if e.order == 2 and e not in processed:
                if omit_rings and not self.is_edge_a_bridge( e):
                    continue
                path = [e]
                add_neighbor_double_bonds( e, path)
                if len( path) % 2:# odd
                    double_paths.append( path)
                    processed |= set( path)
        # detect config on these paths
        for path in double_paths:
            vertices = []
            for bond in path:
                vertices.extend( bond.vertices)
            ends = [v for v in vertices if vertices.count(v) == 1]
            if len( ends) != 2: # two ends is the only thing we are prepared to handle
                continue
            end1, end2 = ends
            # set stereochemistry for all neighbors of both ends
            for e1,n1 in end1.get_neighbor_edge_pairs():
                plane1 = geo.plane_normal_from_3_points( (n1.x,n1.y,n1.z),(end1.x,end1.y,end1.z),(end2.x,end2.y,end2.z))
                if plane1 == None:
                    continue # some coords were missing
                if not e1 in path:
                    for e2,n2 in end2.get_neighbor_edge_pairs():
                        if not e2 in path:
                            plane2 = geo.plane_normal_from_3_points( (end1.x,end1.y,end1.z),(end2.x,end2.y,end2.z),(n2.x,n2.y,n2.z))
                            #cos_angle = geo.same_or_oposite_side( plane1, plane2)
                            cos_angle = geo.angle_between_planes( plane1, plane2)
                            if cos_angle < 0:
                                value = StereoChemistry.OPPOSITE_SIDE
                            else:
                                value = StereoChemistry.SAME_SIDE
                            if len( path) == 1:
                                center = path[0]
                            else:
                                center = None
                            refs = [n1,end1,end2,n2]
                            st = StereoChemistry(center, value, refs)
                            to_remove = None
                            to_add = None
                            for st1 in self.stereochemistry:
                                if set( st1.references) == set( st.references):
                                    if st.value == st1.value:
                                        break
                                    else:
                                        to_remove = st1
                                        break
                            else:
                                self.addStereoChemistry( st)
                            if to_remove:
                                self.removeStereoChemistry( to_remove)

def add_neighbor_double_bonds( bond, path):
    for _e in bond.neighbor_edges:
        if _e.order == 2 and _e not in path:
            path.append( _e)
            add_neighbor_double_bonds( _e, path)



def find_least_crowded_place_around_atom(atom, distance=10):
    atms = atom.neighbors
    if not atms:
      # single atom molecule
      if atom.hydrogens and atom.text_layout == "LTR":
        return atom.x - distance, atom.y
      else:
        return atom.x + distance, atom.y
    angles = [geo.line_get_angle_from_east([atom.x, atom.y, at.x, at.y]) for at in atms]
    angles.append( 2*pi + min( angles))
    angles.sort(reverse=True)
    diffs = common.list_difference( angles)
    i = diffs.index( max( diffs))
    angle = (angles[i] +angles[i+1]) / 2
    return atom.x + distance*cos( angle), atom.y + distance*sin( angle)


def get_angle(a1, a2):
    """ angle between x-axis and a1-a2 line """
    a = a2.x - a1.x
    b = a2.y - a1.y
    return atan2( b, a)





class StereoChemistry:
    CIS_TRANS = 1
    TETRAHEDRAL = 2
    # for cis-trans
    SAME_SIDE = 1
    OPPOSITE_SIDE = -1
    # for tetrahedral
    CLOCKWISE = 2
    ANTICLOCKWISE = -2

    def __init__(self, center, value, references):
        self.type = abs(value)
        self.value = value
        self.center = center
        self.references = references

    def get_other_end( self, ref):
        if not ref in self.references:
            raise ValueError("submitted object is not referenced in this stereochemistry object.")
        ref1, _r1, _r2, ref2 = self.references
        return ref is ref1 and ref2 or ref1


