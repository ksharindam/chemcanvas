# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>
import geometry as geo
from app_data import Settings

from math import sqrt


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
        obj.transform3D(tr)
    return objs


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
        center = geo.rect_get_center(mol.boundingBox())
        side = geo.line_get_side_of_point(line, center)
        if side<0:
            reactants.append(mol)
        else:
            products.append(mol)

    if reactants and products:
        return reactants, products, arrows, plusses

