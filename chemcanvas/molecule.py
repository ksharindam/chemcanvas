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
    object_type = 'Molecule'
    meta__undo_copy = ("atoms", "bonds")
    meta__undo_children_to_record = ("atoms", "bonds")
    meta__same_objects = {"vertices":"atoms", "edges":"bonds"}

    def __init__(self, paper=None):
        DrawableObject.__init__(self)
        Graph.__init__(self)
        self.paper = paper
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

    @property
    def children(self):
        return self.atoms + list(self.bonds)

    def newAtom(self, formula="C"):
        atom = Atom(formula)
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
            new_mol = self.paper.newMolecule()
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

    def find_least_crowded_place_around_atom( self, a, distance=10):
        atms = a.neighbors
        if not atms:
          # single atom molecule
          if a.show_hydrogens and a.text_direction == "left-to-right":
            return a.x - distance, a.y
          else:
            return a.x + distance, a.y
        angles = [clockwise_angle_from_east( at.x-a.x, at.y-a.y) for at in atms]
        angles.append( 2*pi + min( angles))
        angles.sort(reverse=True)
        #angles.reverse()
        diffs = common.list_difference( angles)
        i = diffs.index( max( diffs))
        angle = (angles[i] +angles[i+1]) / 2
        return a.x + distance*cos( angle), a.y + distance*sin( angle)

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


    def drawSelfAndChildren(self):
        for obj in self.children:
            obj.draw()

    def deepcopy(self):
        obj_map = {}
        new_mol = Molecule(self.paper)

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

    def deleteFromPaper(self):
        if len(self.children):
            for child in self.children:
                child.deleteFromPaper()
        self.paper.removeObject(self)
