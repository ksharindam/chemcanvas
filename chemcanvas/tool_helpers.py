# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from math import sqrt, sin, cos
from math import pi as PI
from functools import reduce
import operator

import common
import geometry as geo
from app_data import Settings



def get_objs_with_all_children(objs):
    """ returns list of objs and their all children recursively"""
    stack = list(objs)
    result = set()
    while len(stack):
        obj = stack.pop()
        result.add(obj)
        stack += obj.children
    return list(result)


def draw_recursively(obj):
    draw_objs_recursively([obj])

def draw_objs_recursively(objs):
    objs = get_objs_with_all_children(objs)
    objs = sorted(objs, key=lambda x : x.redraw_priority)
    [o.draw() for o in objs]

def transform_recursively(obj, tr):
    objs = get_objs_with_all_children([obj])
    [o.transform(tr) for o in objs]

def move_objs(objs, dx, dy):
    tr = geo.Transform()
    tr.translate(dx, dy)
    objs = get_objs_with_all_children(objs)
    [o.transform(tr) for o in objs]


def scale_objs(objs, scale):
    """ Scales the object coordinates. does not scale properties such as atom text size """
    # get objs to scale
    objs = set(filter(lambda o: o.is_toplevel, objs))
    objs |= set([obj.parent for obj in objs if not obj.is_toplevel and obj.parent.is_toplevel])
    objs = get_objs_with_all_children(objs)
    # create transform and scale objs
    tr = geo.Transform3D()
    tr.scale(scale)
    for obj in objs:
        obj.transform_3D(tr)
    return objs



def find_least_crowded_place_around_atom(atom, distance=10):
    atms = atom.neighbors
    if not atms:# single atom molecule
        return atom.x + distance, atom.y
    angles = [geo.line_get_angle_from_east([atom.x, atom.y, at.x, at.y]) for at in atms]
    angles.append( 2*PI + min(angles))
    angles.sort(reverse=True)
    diffs = common.list_difference( angles)
    i = diffs.index( max(diffs))
    angle = (angles[i] +angles[i+1]) / 2
    return atom.x + distance*cos(angle), atom.y + distance*sin(angle)



def calc_average_bond_length(bonds):
    """ get median of bond lengths """
    if len(bonds)==0:
        return Settings.bond_length
    bond_lengths = []
    for b in bonds:
        bond_lengths.append( sqrt( (b.atom1.x-b.atom2.x)**2 + (b.atom1.y-b.atom2.y)**2))
    bond_lengths.sort()
    return bond_lengths[len(bond_lengths)//2]


"""
from functools import reduce

def scale_and_reposition_objs(objs):
    mols = list(filter(lambda o: o.class_name=="Molecule", objs))
    bonds = reduce(operator.add, [list(mol.bonds) for mol in mols], [])
    bond_len = calc_average_bond_length(bonds)
    scale = Settings.bond_length/bond_len
    scale_objs(objs, scale)
"""


def identify_reaction_components(objs):
    """ If single-step reaction detected, returns [reactants, products, arrows, plusses]
    If undetected, returns None """
    reactants, products = [], []
    plusses = [o for o in objs if o.class_name=="Plus"]
    arrows = [o for o in objs if o.class_name=="Arrow" and o.is_reaction_arrow()]
    if len(arrows)!=1:# can not detect multi-step reactions
        return
    arrow = arrows[0]
    # all substances at the front side of arrow are products
    p1 = geo.line_get_point_at_distance(arrow.points[0]+arrow.points[1], 1)
    p2 = geo.line_get_point_at_distance(arrow.points[0]+arrow.points[1], -1)
    line = p1+p2

    mols = [o for o in objs if o.class_name=="Molecule"]
    for mol in mols:
        center = geo.rect_get_center(mol.bounding_box())
        side = geo.line_get_side_of_point(line, center)
        if side<0:
            reactants.append(mol)
        else:
            products.append(mol)

    if reactants and products:
        return reactants, products, arrows, plusses



# FIXME : do not remove third bond of benzyne
def find_aromatic_rings_in_molecule(mol):
    # can not calculate if already have delocalization rings
    if mol.delocalizations:
        return []
    # first find smallest rings
    aromatic_rings = []
    rings = mol.get_smallest_independent_cycles_e()
    for ring_bonds in rings:
        ring_atoms = mol.edge_subgraph_to_vertex_subgraph(ring_bonds)
        pi_electrons = [get_pi_e_contribution(atom) for atom in ring_atoms]
        if None in pi_electrons:
            continue
        pi_e_count = reduce(operator.add, pi_electrons, 0)
        if pi_e_count%4==2:# huckel rule
            atoms = get_ordered_ring_atoms_from_ring_bonds(ring_bonds)
            aromatic_rings.append(atoms)

    return aromatic_rings

def get_pi_e_contribution(atom):
    """ calculate pi electron contribution in conjugation.
    returns number of electrons as integer val or None if has no contribution """
    # check if have pi-bond
    sum_BO = reduce(operator.add, [bond.order for bond in atom.bonds], 0)
    if sum_BO>len(atom.bonds):
        return 1
    # check if it is carbocation or carbanion
    charge = atom.charge
    if atom.symbol=="C":
        if charge==1:
            return 0
        elif charge==-1:
            return 2
    # check if it is heteroatom with lone pair
    VE = {"N":5, "P":5, "As":5, "O":6, "S":6, "Se":6}.get(atom.symbol, 0)
    lp = (VE - charge - sum_BO - atom.hydrogens)//2
    if lp>0:
        return 2
    # can not contribute to aromaticity
    return None


def get_ordered_ring_atoms_from_ring_bonds(ring_bonds):
    ring = set(ring_bonds)
    b = ring.pop()
    a = b.atom1
    bonds = [b]
    atoms = [a]
    while ring:
        a = b.atom_connected_to(a)
        atoms.append(a)
        b = list(filter(lambda b: a in b.atoms, ring))[0]
        bonds.append(b)
        ring.remove(b)
    return atoms


def get_delocalizations_having_atoms(atoms):
    """ return list of delocalizations connected to atoms """
    atoms = set(atoms)
    delocalizations = []
    mols = set(a.molecule for a in atoms)
    for mol in mols:
        for deloc in mol.delocalizations:
            if set(deloc.atoms) & atoms:
                delocalizations.append(deloc)
    return delocalizations
