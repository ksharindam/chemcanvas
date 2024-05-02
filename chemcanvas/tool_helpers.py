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
