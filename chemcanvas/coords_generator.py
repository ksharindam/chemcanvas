# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2023-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>

from math import sqrt, sin, cos, radians
from math import pi as PI
import warnings

import common
import geometry as geo
from molecule import StereoChemistry
from tool_helpers import place_molecule



def calculate_coords( mol, bond_length=0, force=0):
    g = CoordsGenerator()
    g.calculate_coords( mol, bond_length=bond_length, force=force)
    place_molecule(mol)


class CoordsGenerator:

    def __init__(self):
        self.bond_length = 1

    def calculate_coords( self, mol, bond_length=0, force=0):
        """the bond_length (when given) sets the self.bond_length,
        if bond_length == -1 we suppose that there is already part of the molecule containing
        coords and we calculate the bond_length from it;
        force says if we should recalc all coords"""
        processed = []
        self.mol = mol
        # stereochemistry info
        self.stereo = {}
        for st in self.mol.stereochemistry:
            if st.type == StereoChemistry.CIS_TRANS:
                for a in (st.references[0],st.references[-1]):
                    self.stereo[a] = self.stereo.get( a, []) + [st]
            elif st.type == StereoChemistry.TETRAHEDRAL:
                self.stereo[st.center] = self.stereo.get( st.center, []) + [st]
        # regenerate all the coords if force
        if force:
            for a in self.mol.atoms:
                a.x = None
                a.y = None
        # at first we have a look if there is already something with coords
        atms = set( [a for a in mol.atoms if a.x != None and a.y != None])
        # then we check if they are in a continuous block but not the whole molecule
        if atms:
            if len( atms) == len( mol.atoms):
                return
            # this is here just to setup the molecule well
            self.rings = mol.get_smallest_independent_cycles()
            # it is - we can use it as backbone
            sub = mol.get_new_induced_subgraph( atms, mol.vertex_subgraph_to_edge_subgraph( atms))
            subs = [comp for comp in sub.get_connected_components()]
            if len( subs) == 1:
                backbone = atms
            else:
                # we should not be here, but when yes than we have to solve it
                maxlength = max( map( len, subs))
                backbone = [su for su in subs if len( su) == maxlength][0]
                # we have to set the coords to None (for sure)
                for sub in subs:
                    if sub != backbone:
                        for a in sub:
                            a.x = None
                            a.y = None
            # now we check if we have to calculate bond_length from the backbone
            if bond_length < 0:
                bls = []
                for b in mol.vertex_subgraph_to_edge_subgraph( backbone):
                    a1, a2 = b.atoms
                    bls.append( sqrt( (a1.x-a2.x)**2 + (a1.y-a2.y)**2))
                self.bond_length = sum( bls) / len( bls)
            elif bond_length > 0:
                self.bond_length = bond_length
            # at last we have to remove rings that have coords from the self.rings
            for ring in self.rings[:]:
                if backbone >= ring:
                    self.rings.remove( ring)
        else:
            if bond_length > 0:
                # here we must have bond_length > 0
                self.bond_length = bond_length
            # we create a backbone, it is either one of the rings or
            # the longest chain in case of acyclic molecule
            if mol.contains_cycle():
                # ring
                self.rings = mol.get_smallest_independent_cycles()
                # find the most crowded ring
                jmax = 0
                imax = 0
                for i, ring in enumerate( self.rings):
                    j = 0
                    for r in self.rings:
                        if r != ring and r & ring:
                            j += 1
                    if j > jmax:
                        jmax = j
                        imax = i

                backbone = self.rings.pop(imax)
                gcoords = gen_ring_coords( len( backbone), side_length=self.bond_length)
                for v in mol.sort_vertices_in_path( backbone):
                    v.x, v.y = next(gcoords)
                processed += backbone
                processed += self.process_all_anelated_rings( backbone)
            elif len( mol.atoms) == 1:
                a = mol.atoms[0]
                a.x, a.y, a.z = 0, 0, 0
                backbone = [a]
            else:
                # chain - we process 2 atoms as backbone and leave the rest for the code
                a1 = self.mol.atoms[0]
                a2 = a1.neighbors[0]
                a1.x, a1.y = 0, 0
                a2.x, a2.y = self.bond_length, 0
                backbone = [a1,a2]
                self.rings = []
        processed += backbone
        self._continue_with_the_coords( mol, processed=processed)
        for v in mol.atoms:
            if v.z == None:
                v.z = 0

    def _continue_with_the_coords( self, mol, processed=[]):
        """processes the atoms in circles around the backbone (processed) until all is done"""
        while processed:
            new_processed = []
            for v in processed:
                if len( [o for o in self.mol.atoms if o.x == None]) == 0:
                    # its all done
                    return
                # look if v is part of a ring
                ring = None
                for r in self.rings:
                    if v in r:
                        ring = r
                        break
                if not ring:
                    # v is not in a ring - we can continue
                    new_processed += self.process_atom_neigbors( v)
                else:
                    # v is in ring so we process the ring
                    if len( processed) > 1 and mol.defines_connected_subgraph_v( processed) and set( processed) <= ring:
                        new_processed += self.process_all_anelated_rings( processed)
                    else:
                        self.rings.remove( ring)
                        ring = mol.sort_vertices_in_path( ring, start_from=v)
                        ring.remove( v)
                        d = [a for a in v.neighbors if a.x != None and a.y != None][0] # should always work
                        ca = geo.line_get_angle_from_east( [d.x, d.y, v.x, v.y])
                        size = len( ring)+1
                        da = radians( 180 -180*(size-2)/size)
                        gcoords = gen_angle_stream( da, start_from=ca-PI/2+da/2)
                        # here we generate the coords
                        self.apply_gen_to_atoms( gcoords, ring, v)
                        ring.append( v)
                        new_processed += ring
                        new_processed += self.process_all_anelated_rings( ring)
            processed = new_processed

    def process_all_anelated_rings( self, base):
        out = []
        to_go = []
        b = set( base)
        for r in self.rings:
            if r & b:
                to_go.append( r)
        for r in to_go:
            out += self.process_one_anelated_ring( base)
        if out:
            for b in to_go:
                out += self.process_all_anelated_rings( b)
        return out


    def process_one_anelated_ring( self, base):
        mol = self.mol
        out = []
        ring = None
        b = set( base)
        for r in self.rings:
            if r & b:
                ring = r
                break
        if ring:
            self.rings.remove( ring)
            inter = b & ring
            to_go = [a for a in ring if a.x == None or a.y == None]
            if len( ring) - len( to_go) == len( inter):
                out += self._process_simply_anelated_ring( ring, base)
            else:
                out += self._process_multi_anelated_ring( ring)
        return out


    def process_atom_neigbors( self, v):
        def get_angle_at_side( v, d, d2, relation, attach_angle):
            if attach_angle == 180:
                # shortcut
                return attach_angle
            side = geo.line_get_side_of_point( (d.x,d.y,v.x,v.y), (d2.x,d2.y))
            an = angle + radians( attach_angle)
            x = v.x + self.bond_length*cos( an)
            y = v.y + self.bond_length*sin( an)
            if relation*side == geo.line_get_side_of_point( (d.x,d.y,v.x,v.y), (x,y)):
                return attach_angle
            else:
                return -attach_angle

        to_go = [a for a in v.neighbors if a.x == None or a.y == None]
        done = [a for a in v.neighbors if a not in to_go]
        if len( done) == 1 and (len( to_go) == 1 or len( to_go) == 2 and [1 for _t in to_go if _t in self.stereo]):
            # only simple non-branched chain or branched with stereo
            d = done[0]
            if len( to_go) == 1:
                t = to_go[0]
            else:
                t = [_t for _t in to_go if _t in self.stereo][0]
            # decide angle
            angle_to_add = 120
            bond = v.get_edge_leading_to( t)
            # triple bonds
            if 3 in [_e.order for _e in v.neighbor_edges]:
                angle_to_add = 180
            # cumulated double bonds
            if bond.order == 2:
                _b = v.get_edge_leading_to( d)
                if _b.order == 2:
                    angle_to_add = 180
            angle = geo.line_get_angle_from_east( [v.x, v.y, d.x, d.y])
            dns = d.neighbors
            placed = False
            # stereochemistry (E/Z)
            if t in self.stereo:
                ss = [st for st in self.stereo[t] if st.type==st.CIS_TRANS]
                ss = [st for st in ss if not None in st.get_other_end( t).pos]
                if ss:
                    st = ss[0] # we choose the first one if more are present
                    d2 = st.get_other_end( t)
                    # other is processed, we need to adapt
                    relation = st.value == st.TRANS and -1 or 1
                    angle_to_add = get_angle_at_side( v, d, d2, relation, angle_to_add)
                    placed = True
            if not placed and len( dns) == 2:
                # to support the all trans of simple chains without stereochemistry
                d2 = (dns[0] == v) and dns[1] or dns[0]
                if d2.x != None and d2.y != None:
                    angle_to_add = get_angle_at_side( v, d, d2, -1, angle_to_add)
            an = angle + radians( angle_to_add)
            t.x = v.x + self.bond_length*cos( an)
            t.y = v.y + self.bond_length*sin( an)
            if len( to_go) > 1:
                self.process_atom_neigbors( v)
        else:
            # branched chain
            angles = [geo.line_get_angle_from_east( [v.x, v.y, at.x, at.y]) for at in done]
            angles.append( 2*PI + min( angles))
            angles.sort()
            angles.reverse()
            diffs = common.list_difference( angles)
            i = diffs.index( max( diffs))
            angle = (angles[i] -angles[i+1]) / (len( to_go)+1)
            gcoords = gen_coords_from_stream( gen_angle_stream( angle, start_from=angles[i+1]+angle),
                                              length = self.bond_length)
            for a in to_go:
                dx, dy = next(gcoords)
                a.x = v.x + dx
                a.y = v.y + dy
            # tetrahedral stereo
            if v in self.stereo:
                ss = [st for st in self.stereo[v] if st.type==StereoChemistry.TETRAHEDRAL]
                if ss:
                    st = ss[0] # we choose the first one if more are present
                    e = v.get_edge_leading_to(st.references[0])
                    e.type = "wedge" if st.value==StereoChemistry.CLOCKWISE else "hashed_wedge"
                    if e.atoms[0]!=v:
                        e.reverse_direction()
        return to_go


    def apply_gen_to_atoms( self, gen, atoms, start, bond_length=None):
        bl = bond_length or self.bond_length
        x, y = start.x, start.y
        for v in atoms:
            a = next(gen)
            x += bl*cos( a)
            y += bl*sin( a)
            v.x, v.y = x, y


    def _process_simply_anelated_ring( self, ring, base):
        out = []
        inter = [v for v in ring if v.x != None and v.y != None]
        if len( inter) == 1:
            # rings are connected via one atom
            v = inter.pop() # the atom of concatenation
            ring = self.mol.sort_vertices_in_path( ring, start_from=v)
            base_neighs = [a for a in v.neighbors if a in base]
            if len( base_neighs) < 2:
                raise Exception("this should not happen")
            d1 = base_neighs[0]
            d2 = base_neighs[1]
            ca1 = geo.line_get_angle_from_east( [d1.x, d1.y, v.x, v.y])
            ca2 = geo.line_get_angle_from_east( [d2.x, d2.y, v.x, v.y])
            ca = (ca1+ca2)/2
            if abs( ca1-ca2) < PI:
                ca += -PI/2
            else:
                ca += PI/2
            size = len( ring)
            da = radians(180 -180.0*(size-2)/size)
            gcoords = gen_angle_stream( da, start_from=ca + da/2)
            ring.remove( v)
            # here we generate the coords
            self.apply_gen_to_atoms( gcoords, ring, v)
            ring.append( v)
            out += ring
        elif len( inter) == 2:
            # there are two atoms common to the rings
            v1, v2 = inter # the atoms of concatenation
            ring = self.mol.sort_vertices_in_path( ring, start_from=v1)
            ring.remove( v1)
            ring.remove( v2)
            if not v1 in ring[0].neighbors:
                v1, v2 = v2, v1
            side = sum( [geo.line_get_side_of_point((v1.x,v1.y,v2.x,v2.y),(v.x,v.y)) for v in base])
            if not side:
                warnings.warn( "this should not happen")
            ca = geo.line_get_angle_from_east( [v2.x, v2.y, v1.x, v1.y])
            size = len( ring)+2
            da = radians(180 -180.0*(size-2)/size)
            if side > 0:
                da = -da
            gcoords = gen_angle_stream( da, start_from=ca+da)
            self.apply_gen_to_atoms( gcoords, ring, v1)
            ring.append( v1)
            ring.append( v2)
            out += ring
        else:
            # there are more than 2 atoms common
            if len( ring) == len( base):
                out += self._process_multi_anelated_ring( ring, angle_shift=15)
                #raise Exception( "i don't how to handle this yet")
            else:
                out += self._process_multi_anelated_ring( ring)
        return out

    def _process_multi_anelated_ring( self, ring, angle_shift=0):
        out = []
        to_go = [v for v in ring if v.x == None or v.y == None]
        if not to_go:
            # it was all already done
            return []
        back = [v for v in ring if v.x != None and v.y != None]
        sorted_back = self.mol.sort_vertices_in_path( back)
        if not sorted_back:
            # the already set atoms are not in one path - we have to process it "per partes"
            # it should not happen with the construction method we use
            raise Exception( "i am not able to handle this, it should normaly not happen. please send me the input.")
        else:
            v1 = sorted_back[0]
            v2 = sorted_back[-1]
            v3 = sorted_back[1]
            to_go = self.mol.sort_vertices_in_path( to_go)
            if v1 not in to_go[0].neighbors:
                v1, v2 = v2, v1
            blocked_angle = sum_of_ring_internal_angles( len( back))
            overall_angle = sum_of_ring_internal_angles( len( ring))
            da = optimal_ring_internal_angle( len( ring))  # internal angle
            # if there are 2 rings of same size inside each other, we need to use the angle_shift
            if angle_shift:
                da += 2*angle_shift/(len( to_go))
            ca = radians( 180-(overall_angle - blocked_angle - len( to_go) * da + angle_shift)/2)  # connection angle
            side = sum( [geo.line_get_side_of_point( (v1.x,v1.y,v2.x,v2.y),(v.x,v.y)) for v in back if v != v1 and v != v2])
            # we need to make sure that the ring is drawn on the right side
            if side > 0:
                ca = -ca
            ca += geo.line_get_angle_from_east( [v2.x, v2.y, v1.x, v1.y])
            da = 180-da  # for drawing we use external angle
            # we must ensure that the ring will progress towards the second end
            if geo.line_get_side_of_point( (v1.x,v1.y,v3.x,v3.y),(v2.x,v2.y)) < 0:
                da = -da
            # dry run to see where we get
            gcoords = gen_angle_stream( radians( da), start_from= ca)
            x, y = v1.x, v1.y
            for i in range( len( to_go) +1):
                a = next(gcoords)
                x += self.bond_length*cos( a)
                y += self.bond_length*sin( a)
            # end of dry run, we can scale the bond_length now
            length = geo.point_distance((v1.x,v1.y), (v2.x,v2.y))
            real_length = geo.point_distance( (v1.x,v1.y), (x,y))
            bl = self.bond_length * length / real_length
            gcoords = gen_angle_stream( radians( da), start_from= ca)
            # and here we go
            self.apply_gen_to_atoms( gcoords, to_go, v1, bond_length=bl)
            out += to_go
        return out

def sum_of_ring_internal_angles( size):
    return (size-2)*180

def optimal_ring_internal_angle( size, angle_shift=0):
    return sum_of_ring_internal_angles( size)/size

def gen_ring_coords( size, side_length=1):
    coords = gen_coords_from_deg_stream( gen_angle_stream( 180 -180.0*(size-2)/size),
                                         length=side_length)
    x , y = 0, 0
    for i in range( size):
        dx, dy = next(coords)
        x += dx
        y += dy
        yield x,y


def gen_angle_stream( angle, start_from=0, alternate=0):
    yield start_from
    if alternate:
        while 1:
            yield angle
            yield -angle
    else:
        a = start_from
        while 1:
            a += angle
            yield a

def gen_coords_from_deg_stream( stream, length=1):
    for a in stream:
        ang = radians( a)
        yield ( length*cos( ang), length*sin( ang))

def gen_coords_from_stream( stream, length=1):
    for a in stream:
        yield ( length*cos( a), length*sin( a))




##################################################
# TODO

# when an atom with degree 4 is created not as part of the backbone the neighbors are
#   organized in a square instead of the usual 120 deg between 2 and the rest on the other side

# triple bond should be linear

##################################################
