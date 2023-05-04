# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2023 Arindam Chaudhuri <ksharindam@gmail.com>

from molecule import Molecule
from app_data import periodic_table
from molecule import StereoChemistry, ExplicitHydrogen
from atom import Atom
from bond import Bond

import re
import operator
from functools import reduce

# TODO :
# implement Atom.explicit_hydrogens, Molecule.explicit_hydrogens_to_real_atoms()

# A little about SMILES
# . -> no bond (dissociation)
# - -> single bond
# = -> double bond
# # -> triple bond
# : -> aromatic bond
# / or \ -> cis or trans single bond attached to a double bond
# @ -> anticlock wise, @@ -> clockwise tetrahedral geometry


class SmilesReader:

    name = "smiles"
    smiles_to_oasa_bond_recode = {'-': 1, '=': 2, '#': 3, ':': 4, ".": 0, "\\": 1, "/": 1}
    oasa_to_smiles_bond_recode = {1: '', 2: '=', 3: '#', 4:''}

    def read( self, text, explicit_hydrogens_to_real_atoms=False):
        self.explicit_hydrogens_to_real_atoms = explicit_hydrogens_to_real_atoms # TODO : remove
        mol = Molecule()#Config.create_molecule()
        text = "".join( text.split())
        is_text = re.compile("^[A-Z][a-z]?$")
        # internally revert \/ bonds before numbers, this makes further processing much easier
        text = re.sub( r"([\\/])([0-9])", lambda m: (m.group(1)=="/" and "\\" or "/")+m.group(2), text)
        # // end
        chunks = re.split( "(\[.*?\]|[A-Z][a-z]?|%[0-9]{1,2}|[^A-Z]|[a-z])", text)
        chunks = self._check_the_chunks( chunks)
        last_atom = None
        last_bond = None
        numbers = {}
        bracket_openings = []
        for c in chunks:
            # atom
            if is_text.match( c) or c.islower() or c[0] == "[":
                a = Atom()#mol.create_vertex()
                if c[0] == "[":
                    # atom spec in square brackets
                    self._parse_atom_spec( c, a)
                else:
                    # just atom symbol
                    if c.islower():
                        symbol = c.upper()
                        a.properties_['aromatic'] = 1
                    else:
                        symbol = c
                    a.setFormula(symbol)#a.symbol = symbol

                mol.addAtom(a)#mol.add_vertex( a)
                if last_bond: # and not (not 'aromatic' in a.properties_ and last_bond.aromatic):
                    mol.addBond(last_bond)#mol.add_edge( last_atom, a, e=last_bond)
                    last_bond = None
                elif last_atom:
                    b = mol.newBond()#mol.add_edge( last_atom, a)
                    b.connectAtoms(last_atom, a)
                    if 'aromatic' in a.properties_:
                        # aromatic bond
                        b.order = 4
                        b.type = 'normal'#'n'
                last_atom = a
                last_bond = None
            # bond
            elif c in r'-=#:.\/':
                order = self.smiles_to_oasa_bond_recode[ c]
                last_bond = Bond()#mol.create_edge()
                last_bond.order = order
                last_bond.type = 'normal'#'n'
                if c in r'\/':
                    last_bond.properties_['stereo'] = c
            # ring closure
            elif c.isdigit():
                if c in numbers:
                    if last_bond:
                        b = last_bond
                    else:
                        b = Bond()#mol.create_edge()
                        if "aromatic" in numbers[c].properties_:
                            b.order = 4
                    mol.addBond(b)#mol.add_edge( last_atom, numbers[c], e=b)
                    b.connectAtoms(last_atom, numbers[c])
                    last_bond = None
                    del numbers[ c]
                else:
                    numbers[c] = last_atom
                    last_bond = None
            elif c == '(':
                bracket_openings.append( last_atom)
            elif c == ')':
                last_atom = bracket_openings.pop(-1)

        ## FINISH
        for a in mol.atoms:#mol.vertices
            if not "explicit_valency" in a.properties_:
                a.raise_valency_to_senseful_value()
            else:
                # detect radicals (but not biradicals - problem of triplet vs. singlet)
                del a.properties_['explicit_valency']
                if a.valency - a.occupied_valency == 1:
                    a.multiplicity += 1
                else:
                    a.valency = a.occupied_valency
            try:
                del a.properties_['aromatic']
            except:
                pass

        # stereochemistry
        self._process_stereochemistry( mol)

        if len(mol.atoms) == 0:#len(mol.vertices)==0
            mol = None
        return mol


    def recode_oasa_to_smiles_bond( self, b):
        if b.aromatic:
            return ''
        elif b in self._stereo_bonds_to_others:
            others = [(e,st) for e,st in self._stereo_bonds_to_others[b] if e in self._stereo_bonds_to_code]
            if not others:
                code = "\\"
            else:
                # other bonds enforce encoding of this one, we select the first one,
                # bacause there is nothing we can do if there are clashing constrains anyway
                other, st = others[0]
                end1,inside1,inside2,end2 = st.references
                if set( other.atoms) == set( [end1,inside1]):
                    v1 = inside1
                    v2 = end1
                else:
                    v1 = inside2
                    v2 = end2
                last_order = self._processed_atoms.index( v2) - self._processed_atoms.index( v1)
                last_code = self._stereo_bonds_to_code[ other] == "\\" and 1 or -1
                relation = st.value == st.OPPOSITE_SIDE and -1 or 1
                if relation*last_code*last_order < 0:
                    code = "/"
                else:
                    code = "\\"
            self._stereo_bonds_to_code[ b] = code
            return code
        else:
            if b.order == 1:
                a1, a2 = b.atoms#b.vertices
                if 'aromatic' in a1.properties_ and 'aromatic' in a2.properties_:
                    # non-aromatic bond connecting two aromatic rings, we need to return -
                    return '-'
            return self.oasa_to_smiles_bond_recode[ b.order]


    def _parse_atom_spec( self, c, a):
        """c is the text spec,
        a is an empty prepared vertex (atom) instance"""
        bracketed_atom = re.compile("^\[(\d*)([A-z][a-z]?)(.*?)\]")
        m = bracketed_atom.match( c)
        if m:
            isotope, symbol, rest = m.groups()
        else:
            raise ValueError( "unparsable square bracket content '%s'" % c)
        if symbol.islower():
            symbol = symbol.upper()
            a.properties_['aromatic'] = 1
        a.symbol = symbol
        if isotope:
            a.isotope = int( isotope)
        # hydrogens
        _hydrogens = re.search( "H(\d*)", rest)
        h_count = 0
        if _hydrogens:
            if _hydrogens.group(1):
                h_count = int( _hydrogens.group(1))
            else:
                h_count = 1
        a.explicit_hydrogens = h_count
        # charge
        charge = 0
        # one possible spec of charge
        _charge = re.search( "[-+]{2,10}", rest)
        if _charge:
            charge = len( _charge.group(0))
            if _charge.group(0)[0] == "-":
                charge *= -1
        # second one, only if the first one failed
        else:
            _charge = re.search( "([-+])(\d?)", rest)
            if _charge:
                if _charge.group(2):
                    charge = int( _charge.group(2))
                else:
                    charge = 1
                if _charge.group(1) == "-":
                    charge *= -1
        a.charge = charge
        # stereo
        _stereo = re.search( "@+", rest)
        if _stereo:
            stereo = _stereo.group(0)
            a.properties_['stereo'] = stereo
        # using [] means valency is explicit
        a.properties_['explicit_valency'] = True


    def _check_the_chunks( self, chunks):
        is_text = re.compile("^[A-Z][a-z]?$")
        is_long_num = re.compile( "^%[0-9]{1,2}$")
        ret = []
        for c in chunks:
            if not c:
                continue
            if is_text.match( c):
                if (not c in periodic_table and len(c)==2) or c == "Sc": # Sc is S-c not scandium
                    a,b = c
                    ret.append( a)
                    ret.append( b)
                else:
                    ret.append( c)
            elif is_long_num.match( c):
                ret.append( str( int( c[1:])))
            else:
                ret.append( c)
        return ret


    def _process_stereochemistry( self, mol):
        ## process stereochemistry
        ## double bonds
        def get_stereobond_direction( end_atom, inside_atom, bond, init):
            position = mol.atoms.index( end_atom) - mol.atoms.index( inside_atom)
            char = bond.properties_['stereo'] == "\\" and 1 or -1
            direction = (position * char * init) < 0 and "up" or "down"
            return direction
        def get_end_and_inside_vertex_from_edge_path( edge, path):
            a1,a2 = edge.atoms#edge.vertices
            if len( [e for e in a1.neighbor_edges if e in path]) == 1:
                return a1, a2
            return a2, a1

        stereo_edges = [e for e in mol.edges if "stereo" in e.properties_]
        paths = []
        for i,e1 in enumerate( stereo_edges):
            for e2 in stereo_edges[i+1:]:
                path = mol.get_path_between_edges( e1, e2)
                path2 = path[1:-1]
                if len( path2)%2 and not [_e for _e in path2 if _e.order != 2]:
                    # only odd number of double bonds, double bonds only
                    for _e in path[1:-1]:
                        if not mol.is_edge_a_bridge_fast_and_dangerous( _e):
                            break
                    else:
                        # only stereo related to non-cyclic bonds
                        paths.append( path)

        for path in paths:
            bond1 = path[0]
            end_atom1,inside_atom1 = get_end_and_inside_vertex_from_edge_path( bond1, path)
            bond2 = path[-1]
            end_atom2,inside_atom2 = get_end_and_inside_vertex_from_edge_path( bond2, path)
            d1 = get_stereobond_direction( end_atom1, inside_atom1, bond1, -1)
            d2 = get_stereobond_direction( end_atom2, inside_atom2, bond2, -1)
            if d1 == d2:
                value = StereoChemistry.SAME_SIDE
            else:
                value = StereoChemistry.OPPOSITE_SIDE
            if len( path) == 3:
                center = path[1]
            else:
                center = None
            refs = [end_atom1,inside_atom1,inside_atom2,end_atom2]
            st = StereoChemistry(center, value, refs)
            mol.addStereoChemistry( st)

        # tetrahedral stereochemistry
        for v in mol.atoms:#mol.vertices
            refs = None
            if 'stereo' in v.properties_:
                idx = [mol.atoms.index( n) for n in v.neighbors]
                idx.sort()
                if len( idx) < 3:
                    pass # no stereochemistry with less then 3 neighbors
                elif len( idx) == 3:
                    if v.explicit_hydrogens == 0:
                        pass # no stereochemistry without adding hydrogen here
                    else:
                        if self.explicit_hydrogens_to_real_atoms:
                            hs = mol.explicit_hydrogens_to_real_atoms( v)
                            h = hs.pop()
                        else:
                            h = ExplicitHydrogen()
                        v_idx = mol.atoms.index( v)
                        idx1 = [i for i in idx if i < v_idx]
                        idx2 = [i for i in idx if i > v_idx]
                        refs = [mol.atoms[i] for i in idx1] + [h] + [mol.atoms[i] for i in idx2]
                elif len( idx) == 4:
                    refs = [mol.atoms[i] for i in idx]
                else:
                    pass # unhandled stereochemistry
            if refs:
                if v.properties_["stereo"] == "@":
                    val = StereoChemistry.ANTICLOCKWISE
                elif v.properties_['stereo'] == "@@":
                    val = StereoChemistry.CLOCKWISE
                else:
                    continue # no meaning
                st = StereoChemistry(v, val, refs)
                mol.addStereochemistry( st)

        # delete the data after processing
        for e in mol.edges:
            if 'stereo' in e.properties_:
                del e.properties_['stereo']
        for v in mol.atoms:
            if 'stereo' in v.properties_:
                del v.properties_['stereo']



class SmilesGenerator:
    organic_subset = ['B', 'C', 'N', 'O', 'P', 'S', 'F', 'Cl', 'Br', 'I']

    def generate( self, mol):
        if not mol.is_connected():
            raise Exception("SMILES : Cannot encode disconnected compounds")
        #mol = molec.copy()
        self.molecule = mol
        self.ring_joins = []
        self._processed_atoms = []
        self.branches = {}
        self._stereo_bonds_to_code = {} # for bond it will contain character it uses
        self._stereo_bonds_to_others = {} # for bond it will contain the other bonds
        self._stereo_centers = {}
        # at first we mark all the atoms with aromatic bonds
        # it is much simple to do it now when all the edges are present
        # we can make use of the properties attribute of the vertex
        for b in mol.bonds:
            if b.aromatic:
                for a in b.atoms:
                    a.properties_[ 'aromatic'] = 1
        # stereochemistry information preparation # TODO : uncomment this
        """for st in mol.stereochemistry:
            if st.type == StereoChemistry.CIS_TRANS:
                end1, inside1, inside2, end2 = st.references
                e1 = end1.get_edge_leading_to( inside1)
                e2 = end2.get_edge_leading_to( inside2)
                self._stereo_bonds_to_others[ e1] = self._stereo_bonds_to_others.get( e1, []) + [(e2, st)]
                self._stereo_bonds_to_others[ e2] = self._stereo_bonds_to_others.get( e2, []) + [(e1, st)]
            elif isinstance( st, stereochemistry.tetrahedral_stereochemistry):
                self._stereo_centers[st.center] = st
            else:
                pass # we cannot handle this"""

        ret = ''.join( [i for i in self._get_smiles( mol)])
        mol.reconnect_temporarily_disconnected_edges()
        # this is needed because the way temporarily_disconnected edges are handled is not compatible with the way smiles
        # generation works - it splits the molecule while reusing the same atoms and bonds and thus disconnected bonds accounting fails
        for e in mol.edges:
            e.disconnected = False
        # here tetrahedral stereochemistry is added
        for v, st in self._stereo_centers.items():
            processed_neighbors = []
            for n in self._processed_atoms:
                if n in v.neighbors:
                    processed_neighbors.append( n)
                elif v.explicit_hydrogens and n is v:
                    processed_neighbors.append( ExplicitHydrogen())
            count = match_atom_lists( st.references, processed_neighbors)
            clockwise = st.value == st.CLOCKWISE
            if count % 2 == 1:
                clockwise = not clockwise
            ch_symbol = clockwise and "@@" or "@"
            ret = ret.replace( "{{stereo%d}}" % mol.atoms.index(v), ch_symbol)
        return ret



    def _get_smiles( self, mol, start_from=None):
        # single atoms
        if len( mol.atoms) == 1:
            v = mol.atoms[0]
            yield self._create_atom_smiles( v)
            for e in self.ring_joins:
                if v in e.atoms:
                    yield self.recode_oasa_to_smiles_bond( e)
                    yield create_ring_join_smiles( self.ring_joins.index( e))
            return
        while not (is_line( mol) and (not start_from or start_from.degree <= 1)):
            if is_pure_ring( mol):
                self.ring_joins.append( mol.temporarily_disconnect_edge( list( mol.edges)[0]))
            else:
                e, mol, branch_vertex, branch = self.disconnect_something( mol, start_from=start_from)
                if branch_vertex:
                    if branch_vertex in self.branches:
                        self.branches[ branch_vertex].append((e, branch))
                    else:
                        self.branches[ branch_vertex] = [(e, branch)]
                else:
                    self.ring_joins.append( e)
        try:
            start, end = filter( lambda x: x.degree == 1, mol.atoms)
        except:
            #print filter( lambda x: x.get_degree() == 1, mol.atoms)
            raise Exception("shit")
        if start_from == end:
            start, end = end, start
        v = start
        last = None
        was_end = False
        while True:
            yield self._create_atom_smiles( v)
            # the atom
            for e in self.ring_joins:
                if v in e.atoms:
                    _b = self.recode_oasa_to_smiles_bond( e)
                    if _b not in "/\\":
                        yield _b
                    yield create_ring_join_smiles( self.ring_joins.index( e))
            # branches
            if v in self.branches:
                for edg, branch in self.branches[ v]:
                    yield '('
                    yield self.recode_oasa_to_smiles_bond( edg)
                    v1, v2 = edg.atoms
                    vv = (v1 != v) and v1 or v2
                    for i in self._get_smiles( branch, start_from=vv):
                        yield i
                    yield ')'
            # bond leading to the neighbor
            for e, neighbor in v.get_neighbor_edge_pairs():
                if neighbor != last:
                    yield self.recode_oasa_to_smiles_bond( e)
                    last = v
                    v = neighbor
                    break
            if was_end:
                break
            if v == end:
                was_end = True


    def _create_atom_smiles( self, v):
        self._processed_atoms.append( v)
        if 'aromatic' in v.properties_:
            symbol = v.symbol.lower()
        else:
            symbol = v.symbol

        stereo = self._stereo_centers.get( v, None)

        if (v.symbol not in self.organic_subset) or (v.isotope) or (v.charge != 0) or (v.valency != periodic_table[ v.symbol]['valency'][0]) or (stereo) or (v.multiplicity != 1):
            # we must use square bracket
            isotope = v.isotope and str( v.isotope) or ""
            # charge
            if v.charge:
                sym = v.charge < 0 and "-" or "+"
                charge = sym + (abs( v.charge) > 1 and str( abs( v.charge)) or "")
            else:
                charge = ""
            # explicit hydrogens
            num_h = v.valency - v.occupied_valency + v.explicit_hydrogens
            h_spec = (num_h and "H" or "") + (num_h > 1 and str( num_h) or "")
            # stereo
            if stereo:
                stereo = "{{stereo%d}}" % self.molecule.atoms.index( v)
            else:
                stereo = ""
            return "[%s%s%s%s%s]" % (isotope, symbol, stereo, h_spec, charge)
        else:
            # no need to use square brackets
            return symbol


    def disconnect_something( self, mol, start_from=None):
        """returns (broken edge, resulting mol, atom where mol was disconnected, disconnected branch)"""
        # we cannot do much about this part
        if start_from and start_from.degree != 1:
            for e,n in start_from.get_neighbor_edge_pairs():
                if n.degree > 2:
                    mol.temporarily_disconnect_edge( e)
                    return e, mol, None, None
            mol.temporarily_disconnect_edge( e)
            return e, mol, None, None
        # at first try to find edges for which degree of neighbors is bigger
        # than [2,2] and at best they are not bridges
        # when no non-bridges are present use the other ones
        #
        # the edges with crowded atoms
        for e in mol.edges:
            d1, d2 = [x.degree for x in e.atoms]
            if d1 > 2 and d2 > 2 and not mol.is_edge_a_bridge_fast_and_dangerous( e):
                mol.temporarily_disconnect_edge( e)
                return e, mol, None, None
        # the other valuable non-bridge edges
        for e in mol.edges:
            d1, d2 = [x.degree for x in e.atoms]
            if (d1 > 2 or d2 > 2) and not mol.is_edge_a_bridge_fast_and_dangerous( e):
                mol.temporarily_disconnect_edge( e)
                return e, mol, None, None
        # there are no non-bridges
        # we want to split off the smallest possible chunks
        min_size = None
        the_right_edge = None
        the_right_mol = None
        the_right_branch = None
        the_right_branch_atom = None
        ring_joints_in_branch = 1000
        ring_join_vertices = set( reduce( operator.add, [e.atoms for e in self.ring_joins], []))
        for e in mol.edges:
            d1, d2 = [x.degree for x in e.atoms]
            if d1 > 2 or d2 > 2:
                ps = mol.get_pieces_after_edge_removal( e)
                if len( ps) == 1:
                    print("impossible")
                    continue
                lenghts = map( len, ps)
                ms = min( lenghts)
                p1, p2 = ps
                the_mol = (len( p1) < len( p2)) and p2 or p1
                the_branch = (p1 == the_mol) and p2 or p1
                ring_joints = len( [i for i in the_branch if i in ring_join_vertices])
                if not min_size or ms < min_size or ring_joints_in_branch > ring_joints:
                    min_size = ms
                    the_right_edge = e
                    the_right_mol = the_mol
                    the_right_branch = the_branch
                    ring_joints_in_branch = ring_joints
        if the_right_edge:
            # what is possible to make here instead in the loop is made here
            # it saves time
            v1, v2 = the_right_edge.atoms
            mol.temporarily_disconnect_edge( the_right_edge)
            the_right_branch_atom = (v1 in the_right_mol) and v1 or v2
            the_right_mol = mol.get_induced_subgraph_from_vertices( the_right_mol)
            the_right_branch = mol.get_induced_subgraph_from_vertices( the_right_branch)
            return (the_right_edge,
                    the_right_mol,
                    the_right_branch_atom,
                    the_right_branch)
        #print mol, mol.is_connected()
        raise Exception("shit, how comes!?")


def create_ring_join_smiles( index):
    i = index +1
    if i > 9:
        return "%%%d" % i
    else:
        return str( i)



def is_line( mol):
    """all degrees are 2 except of two with degree 1"""
    if len( mol.atoms) == 1:
        return True
    ones = 0
    for v in mol.atoms:
        d = v.degree
        if d == 1:
            if ones == 2:
                return False
            ones += 1
        elif d != 2:
            return False
    if ones == 2:
        return True
    return False

def is_pure_ring( mol):
    return filter( lambda x: x.degree != 2, mol.atoms) == []

def match_atom_lists( l1, l2):
    """sort of bubble sort with counter"""
    count = 0
    for i1, v1 in enumerate( l1):
        for i2 in range( i1, len( l2)):
            v2 = l2[i2]
            if v2 == v1:
                if i1 != i2:
                    l2[i1],l2[i2] = l2[i2],l2[i1]
                    count += 1
                break
    assert l1 == l2
    return count
