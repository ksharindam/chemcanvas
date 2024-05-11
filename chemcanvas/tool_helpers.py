# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>
import geometry as geo
from app_data import Settings
import common

from math import sqrt
import operator


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


"""
from functools import reduce

def scale_and_reposition_objs(objs):
    mols = list(filter(lambda o: o.class_name=="Molecule", objs))
    bonds = reduce(operator.add, [list(mol.bonds) for mol in mols], [])
    bond_len = calc_average_bond_length(bonds)
    scale = Settings.bond_length/bond_len
    scale_objs(objs, scale)
"""



def reposition_document(doc):
    bboxes = [obj.boundingBox() for obj in doc.objects]
    bbox = common.bbox_of_bboxes(bboxes)
    tx = (doc.page_w-bbox[2]+bbox[0])/2 - bbox[0]# horizontal center
    ty = 30 - bbox[1]
    tr = geo.Transform()
    tr.translate(tx, ty)
    objs = get_objs_with_all_children(doc.objects)
    [o.transform(tr) for o in objs]
