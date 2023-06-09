# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>
from drawable import DrawableObject
from atom import Atom
from bond import Bond
from graph import Graph
import common
from geometry import *
from app_data import App
from math import cos, sin, pi

global molecule_id_no
molecule_id_no = 1

class Molecule(Graph, DrawableObject):
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
        # template
        self.template_atom = None
        self.template_bond = None
        # set molecule unique id
        global molecule_id_no
        self.id = 'mol' + str(molecule_id_no)
        molecule_id_no += 1
        # drawing related
        self._last_used_atom = None
        self.sign = 1
        self.stereochemistry = []
        # this is used to calculate atom font size, and new bond length
        self.scale_val = 1.0

    @property
    def children(self):
        return self.atoms + list(self.bonds)

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
              self.sign = -self.sign
              x = a.x + cos( self.get_angle( a, neighbors[0]) +self.sign*2*pi/3) *distance
              y = a.y + sin( self.get_angle( a, neighbors[0]) +self.sign*2*pi/3) *distance
            else:
              # we would add the new bond transoid
              neighs2 = neigh.neighbors
              neigh2 = (neighs2[0] == a) and neighs2[1] or neighs2[0]
              x = a.x + cos( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
              y = a.y + sin( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
              side = line_get_side_of_point( (neigh.x,neigh.y,a.x,a.y), (x,y))
              if side == line_get_side_of_point(  (neigh.x,neigh.y,a.x,a.y), (neigh2.x,neigh2.y)):
                self.sign = -self.sign
                x = a.x + cos( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
                y = a.y + sin( self.get_angle( a, neigh) +self.sign*2*pi/3) *distance
              self._last_used_atom = a
          else:
            x = a.x + cos( self.get_angle( a, neighbors[0]) + pi) *distance
            y = a.y + sin( self.get_angle( a, neighbors[0]) + pi) *distance
        else:
          x, y = a.findLeastCrowdedPlace(distance)
        return x, y


    def get_angle( self, a1, a2):
        """ angle between x-axis and a1-a2 line """
        a = a2.x - a1.x
        b = a2.y - a1.y
        return atan2( b, a)

    def boundingBox(self):
        bboxes = []
        for atom in self.atoms:
            bboxes.append( atom.boundingBox())
        return common.bbox_of_bboxes( bboxes)

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("molecule")
        for child in self.children:
            child.addToXmlNode(elm)
        parent.appendChild(elm)
        return elm

    def readXml(self, mol_elm):
        name = mol_elm.getAttribute("name")
        if name:
            self.name = name
        # create atoms
        atom_elms = mol_elm.getElementsByTagName("atom")
        for atom_elm in atom_elms:
            atom = self.newAtom()
            atom.readXml(atom_elm)
        # create bonds
        bond_elms = mol_elm.getElementsByTagName("bond")
        for bond_elm in bond_elms:
            bond = self.newBond()
            bond.readXml(bond_elm)

        template_elms = mol_elm.getElementsByTagName("template")
        if template_elms:
            t_atom = template_elms[0].getAttribute("atom")
            if t_atom:
                self.template_atom = App.id_to_object_map[t_atom]
            t_bond = template_elms[0].getAttribute("bond")
            if t_bond:
                self.template_bond = App.id_to_object_map[t_bond]


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

    def transform(self, tr):
        pass

    def scale(self, scale):
        self.scale_val *= scale


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


class ExplicitHydrogen:
    """this object serves as a placeholder for explicit hydrogen in stereochemistry references"""

    def __eq__(self, other):
        if isinstance(other, ExplicitHydrogen):
            return True
        return False
