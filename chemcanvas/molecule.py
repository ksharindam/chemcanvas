# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from math import cos, sin, atan2
from math import pi as PI

from drawing_parents import DrawableObject
from atom import Atom
from bond import Bond
from graph import Graph
import common
import geometry as geo
from tool_helpers import find_least_crowded_place_around_atom

global molecule_id_no
molecule_id_no = 1

class Molecule(Graph, DrawableObject):
    redraw_priority = 1

    meta__undo_properties = ("scale_val",)
    meta__undo_copy = ("atoms", "bonds", "delocalizations")
    meta__undo_children_to_record = ("atoms", "bonds", "delocalizations")
    meta__same_objects = {"vertices":"atoms", "edges":"bonds"}
    meta__scalables = ("scale_val",)

    def __init__(self):
        DrawableObject.__init__(self)
        Graph.__init__(self)
        self.name = "" # eg. "cyclohexane"
        # this makes two variable same, when we modify self.atoms, self.vertices gets modified
        self.atoms = self.vertices  # a list()
        self.bonds = self.edges     # a set()
        self.delocalizations = [] # delocalization ring or curves
        self.data = None # a dict of structure data
        # template
        self.template_atom = None
        self.template_bond = None
        self.category = "" # template category eg. 'Amino Acid', 'Sugar'
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

    def new_atom(self, symbol="C"):
        atom = Atom(symbol)
        self.add_atom(atom)
        #print("added atom :", atom)
        return atom

    def new_bond(self):
        bond = Bond()
        self.add_bond(bond)
        #print("added bond :", bond.id)
        return bond

    # whenever an atom or a bond is added or removed, graph cache must be cleared
    def add_atom(self, atom):
        self.atoms.append(atom)
        self.clear_cache()
        atom.molecule = self

    def remove_atom(self, atom):
        self.atoms.remove(atom)
        self.clear_cache()
        atom.molecule = None

    def add_bond(self, bond):
        self.bonds.add(bond)
        self.clear_cache()
        bond.molecule = self

    def remove_bond(self, bond):
        self.bonds.remove(bond)
        self.clear_cache()
        bond.molecule = None


    def add_delocalization(self, delocalization):
        self.delocalizations.append(delocalization)
        delocalization.molecule = self
        # for aromatic bonds, occupied valency can not be calculated correctly
        # from bond order, which gives wrong number of implicit hydrogens (eg. N in indole).
        # So, if any aromatic atom contains hydrogens, set as explicit,
        # otherwise assume that it does not contain any hydrogen
        for atom in delocalization.atoms:
            if atom.show_symbol and atom.hydrogens:
                atom.auto_hydrogens = False
        for bond in delocalization.bonds:
            bond.set_type("delocalized")
            bond.show_delocalization = False
            bond.mark_dirty()


    def destroy_delocalization(self, delocalization):
        """ delete delocalization completely """
        self.delocalizations.remove(delocalization)
        delocalization.molecule = None
        # some bonds of this delocalization may be common to other other delocalizations
        delocalized_bonds = set()
        for deloc in self.delocalizations:
            delocalized_bonds |= set(deloc.bonds)
        # display dashed second line, if it is not part of another delocalizations
        for bond in set(delocalization.bonds) - delocalized_bonds:
            bond.show_delocalization = True
            bond.mark_dirty()
        delocalization.delete_from_paper()


    def eat_molecule(self, food_mol):
        if food_mol is self:
            return
        # move all atoms of food_mol to this molecule
        for atom in food_mol.atoms:
            self.add_atom(atom)
        food_mol.atoms.clear()

        # move all bonds of food_mol to this molecule
        for bond in food_mol.bonds:
            self.add_bond(bond)
        food_mol.bonds.clear()

        # move all delocalizations
        for deloc in food_mol.delocalizations:
            deloc.molecule = self
            self.delocalizations.append(deloc)
        food_mol.delocalizations.clear()

        # remove food_mol from paper
        if food_mol.paper:
            food_mol.paper.removeObject(food_mol)


    def split_fragments(self):
        """ convert each fragments into different molecules if it is broken molecule """
        new_mols = []
        frags = list(self.get_connected_components())
        for frag in frags[1:]:
            new_mol = Molecule()
            self.paper.addObject(new_mol)
            bonds = []
            for atom in frag:
                self.remove_atom(atom)
                new_mol.add_atom(atom)
                bonds += atom.bonds
            for bond in set(bonds):
                self.remove_bond(bond)
                new_mol.add_bond(bond)
            new_mols.append(new_mol)
        # move delocalizations
        for deloc in self.delocalizations:
            if not set(deloc.atoms).issubset(set(self.atoms)):
                for mol in new_mols:
                    if set(deloc.atoms).issubset(set(mol.atoms)):
                        self.delocalizations.remove(deloc)
                        mol.delocalizations.append(deloc)
                        deloc.molecule = mol
                        break
        return new_mols


    def find_place( self, a, distance, added_order=1):
        """tries to find accurate place for next atom around atom 'a',
        returns x,y and list of ids of 'items' found there for overlap, those atoms are not bound to id"""
        neighbors = a.neighbors
        if len( neighbors) == 0:
          x = a.x + cos( PI/6) *distance
          y = a.y - sin( PI/6) *distance
        elif len( neighbors) == 1:
          neigh = neighbors[0]
          if a.bonds[0].order != 3 and added_order != 3:
            # we add a single bond to atom with a single bond
            if a == self._last_used_atom or len( neigh.neighbors) != 2:
              # the user has either deleted the last added bond and wants it to be on the other side
              # or it is simply impossible to define a transoid configuration
              self._sign = -self._sign
              x = a.x + cos( get_angle( a, neighbors[0]) + self._sign*2*PI/3) *distance
              y = a.y + sin( get_angle( a, neighbors[0]) + self._sign*2*PI/3) *distance
            else:
              # we would add the new bond transoid
              neighs2 = neigh.neighbors
              neigh2 = (neighs2[0] == a) and neighs2[1] or neighs2[0]
              x = a.x + cos( get_angle( a, neigh) + self._sign*2*PI/3) *distance
              y = a.y + sin( get_angle( a, neigh) + self._sign*2*PI/3) *distance
              side = geo.line_get_side_of_point( (neigh.x,neigh.y,a.x,a.y), (x,y))
              if side == geo.line_get_side_of_point(  (neigh.x,neigh.y,a.x,a.y), (neigh2.x,neigh2.y)):
                self._sign = -self._sign
                x = a.x + cos( get_angle( a, neigh) + self._sign*2*PI/3) *distance
                y = a.y + sin( get_angle( a, neigh) + self._sign*2*PI/3) *distance
              self._last_used_atom = a
          else:
            x = a.x + cos( get_angle( a, neighbors[0]) + PI) *distance
            y = a.y + sin( get_angle( a, neighbors[0]) + PI) *distance
        # more than one neighbors
        else:
          x, y = find_least_crowded_place_around_atom(a, distance)
        return x, y


    def bounding_box(self):
        bboxes = []
        for atom in self.atoms:
            bboxes.append( atom.bounding_box())
        return common.bbox_of_bboxes( bboxes)

    def deepcopy(self):
        obj_map = {}
        new_mol = Molecule()
        #new_mol.paper = self.paper

        for atom in self.atoms:
            new_atom = atom.copy()
            new_mol.add_atom(new_atom)
            obj_map[atom.id] = new_atom

        for bond in self.bonds:
            new_bond = bond.copy()
            new_mol.add_bond(new_bond)
            new_bond.connect_atoms(obj_map[bond.atom1.id], obj_map[bond.atom2.id])
            obj_map[bond.id] = new_bond

        for deloc in self.delocalizations:
            new_deloc = deloc.copy()
            new_deloc.atoms = [obj_map[atom.id] for atom in deloc.atoms]
            new_deloc.molecule = new_mol
            new_mol.delocalizations.append(new_deloc)

        if self.template_atom:
            new_mol.template_atom = obj_map[self.template_atom.id]
        if self.template_bond:
            new_mol.template_bond = obj_map[self.template_bond.id]
        return new_mol


    def handle_overlap(self):
        """ Merge overlapped atoms and bonds in this molecule.
        To handle overlap with two different molecules,
        call Molecule.eat_molecule() before calling this function """
        to_process = self.atoms[:]
        replacement_dict = {}

        while len(to_process):
            a1 = to_process.pop(0) # the overlapped atom
            i = 0
            while i < len(to_process):
                a2 = to_process[i]
                if abs(a2.x-a1.x)<=2 and abs(a2.y-a1.y)<=2:
                    replacement_dict[a2] = a1
                    to_process.pop(i)
                    # handle bonds
                    for bond in a2.bonds:
                        if bond.atom_connected_to(a2) in a1.neighbors:
                            # two overlapping atoms have same neighbor means
                            # we found overlapping bond
                            bond.disconnect_atoms()
                            self.remove_bond(bond)
                            bond.delete_from_paper()
                        else:
                            # disconnect from overlapping atom, and connect to overlapped atom
                            bond.replace_atom(a2, a1)
                else:
                    i += 1

        # handle delocalizations
        for deloc in self.delocalizations:
            for i,atom in enumerate(deloc.atoms):
                if atom in replacement_dict:
                    deloc.atoms[i] = replacement_dict[atom]

        # delete overlapping atoms
        for atom in replacement_dict.keys():
            self.remove_atom(atom)
            atom.delete_from_paper()

    """def explicit_hydrogens_to_real_atoms( self, v):
        hs = set()
        for i in range( v.explicit_hydrogens):
            h = Atom("H")
            self.add_atom( h)
            b = self.new_bond()
            b.connect_atoms(h,v)
            hs.add( h)
        v.explicit_hydrogens = 0
        return hs"""

    def add_stereochemistry(self, st):
        self.stereochemistry.append(st)

    def remove_stereochemistry(self, st):
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
                                value = StereoChemistry.TRANS
                            else:
                                value = StereoChemistry.CIS
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
                                self.add_stereochemistry( st)
                            if to_remove:
                                self.remove_stereochemistry( to_remove)


    def _get_atoms_possible_aromatic_electrons(self, at, ring):
        out = set()
        accept_cation = {'N', 'P', 'O', 'S', 'Se'}
        if at.charge > 0 and at.symbol not in accept_cation:# can contribute vacant p-orbital
            out.add( 0)
        elif at.charge < 0:# negative charge can contribute lone pair
            out.add( 2)
        if at.symbol in accept_cation and not at.charge > 0:
            out.add( 2)
        if at.symbol in ('B','Al'):# has vacant p-orbital
            out.add( 0)
        for b, a in at.get_neighbor_edge_pairs():
            if b.order > 1 and (a in ring or "delocalized" in b.properties_):
                out.add( 1)
            elif b.order > 1:
                out.add( 0)
        return tuple( out)


    def localize_aromatic_bonds( self):
        """ localizes aromatic bonds (does not relocalize already localized ones) """
        # it helps to check whether it was aromatic before bond type is changed
        for b in self.bonds:
            if b.type=="delocalized":
                b.properties_["delocalized"]=1

        erings = self.get_smallest_independent_cycles_e()
        # filter off rings without aromatic bonds
        erings = filter( lambda x: len( [b for b in x if b.type=="delocalized"]), erings)
        rings = list(map( self.edge_subgraph_to_vertex_subgraph, erings))
        # sort rings
        rings.sort( key=lambda x: len(x)%2, reverse=True) # odd size rings first
        last_rings = []
        while rings:
            # we have to continue with the neighbor rings of the last_ring (or the rings before)
            intersection = None
            if last_rings:
                aring = None
                while last_rings:
                    last_ring = last_rings.pop( -1)
                    for ring in rings:
                        intersection = ring & last_ring
                        if intersection:
                            aring = ring
                            last_rings.append( last_ring)
                            break
                    if aring:
                        break
                if not aring:
                    aring = rings.pop(0)
                else:
                    rings.remove( aring)
            else:
                aring = rings.pop(0)
            last_rings.append( aring)
            # convert ring from set to list
            aring = self.sort_vertices_in_path( aring, start_from=intersection and intersection.pop() or None)
            # taken from mark_aromatic_bonds
            els = [self._get_atoms_possible_aromatic_electrons( a, aring) for a in aring]
            if () in els:
                continue  # misuse of aromatic bonds (e.g. by smiles) or e.g. tetrahydronaphtalene
            for comb in common.gen_combinations_of_series( els):
                if sum( comb) % 4 == 2:
                    aring.append( aring[0])
                    comb.append( comb[0])
                    # at first we process the bonds that are surely single (like C-S-C in thiophene)
                    already_set = None
                    for i in range( len( aring) -1):
                        if comb[i] + comb[i+1] != 2:
                            # these bonds must be single
                            b = aring[i].get_edge_leading_to( aring[i+1])
                            b.type = "single"
                            already_set = i
                    if already_set != None:
                        # we reorder the comb and aring to start from the already set bonds
                        j = already_set + 1
                        aring = aring[j:len(aring)] + aring[1:j]
                        aring.insert( 0, aring[-1])
                        comb = comb[j:len(comb)] + comb[1:j]
                        comb.insert( 0, comb[-1])
                    i = 0
                    while i+1 < len( aring):
                        if comb[i] + comb[i+1] == 2:
                            b = aring[i].get_edge_leading_to( aring[i+1])
                            assert b != None # should be
                            # to assure alternating bonds
                            bs1 = [bo for bo in aring[i].neighbor_edges if bo.type=="double" and "delocalized" in bo.properties_ and bo!=b]
                            bs2 = [bo for bo in aring[i+1].neighbor_edges if bo.type=="double" and "delocalized" in bo.properties_ and bo!=b]
                            if len( bs1) == 0 and len( bs2) == 0:
                                b.type = "double"
                            else:
                                b.type = "single"
                        i += 1
                    break

        # cleanup
        for b in self.bonds:
            try:
                del b.properties_["delocalized"]
            except: pass

        self.localize_fake_aromatic_bonds()


    def localize_fake_aromatic_bonds( self):
        """ for those that are not aromatic but marked as delocalized
        (it is for instance possible to misuse 'cccc' in smiles to create butadiene) """
        to_go = [b for b in self.bonds if b.type == "delocalized"]

        processed = []
        for b in to_go:
            if not min( [a.free_valency for a in b.vertices]):
                b.set_type("single")
                processed.append( b)
        to_go = common.difference( to_go, processed)

        while to_go:
            # find the right bond
            b = None
            for bo in to_go:
                bs1, bs2 = bo.neighbor_edges2
                if not bs1 or len( [e for e in bs1 if e.order < 2]) > 0 and len( [e for e in bs1 if e.order == 2]) == 0 \
                   or not bs2 or len( [e for e in bs2 if e.order < 2]) > 0 and len( [e for e in bs2 if e.order == 2]) == 0:
                    b = bo
                    break
                # new start for iteration
            if not b:
                for bo in self.edges:
                    if not [e for e in bo.neighbor_edges if e.type!="delocalized"]:
                        b = bo
                        break
            if not b:
                b = to_go.pop(0)
            # the code itself
            b.type = "double"
            for bo in b.neighbor_edges:
                if bo.type == "delocalized":
                    bo.type = "single"
            # next turn
            to_go = [b for b in self.bonds if b.type == "delocalized"]




def add_neighbor_double_bonds( bond, path):
    for _e in bond.neighbor_edges:
        if _e.type=="double" and _e not in path:
            path.append( _e)
            add_neighbor_double_bonds( _e, path)



def get_angle(a1, a2):
    """ angle between x-axis and a1-a2 line """
    a = a2.x - a1.x
    b = a2.y - a1.y
    return atan2( b, a)





class StereoChemistry:
    CIS_TRANS = 1
    TETRAHEDRAL = 2
    # for cis-trans
    CIS = 1
    TRANS = -1
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


