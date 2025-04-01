# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject
import geometry as geo
from app_data import Settings

# FIXME:
# circle inside cyclopropenyl cation not visible
# color not supported

global delocalization_id_no
delocalization_id_no = 1


class Delocalization(DrawableObject):
    """ represents a delocalization curve in a molecule.
    responsible for drawing aromatic rings """
    is_toplevel = False
    meta__undo_properties = ("molecule", "color")
    meta__undo_copy = ("atoms",)

    def __init__(self, atoms=None):
        DrawableObject.__init__(self)
        # sequencial list of atoms. If it is delocalization ring of
        # aromaticity, first and last atom is same object
        self.atoms = atoms or []
        self.molecule = None
        # graphics items
        self._main_item = None
        # generate unique id
        global delocalization_id_no
        self.id = 'deloc' + str(delocalization_id_no)
        delocalization_id_no += 1

    def __str__(self):
        return self.id

    @property
    def parent(self):
        return self.molecule

    @property
    def bonds(self):
        if not self.atoms:
            return []
        bonds = []
        for i,a in enumerate(self.atoms[:-1]):
            b = set(a.bonds) & set(self.atoms[i+1].bonds)
            bonds.append(b.pop())
        return bonds

    def contains_bond(self, bond):
        return bond.atom1 in self.atoms and bond.atom2 in self.atoms

    @property
    def chemistry_items(self):
        return self._main_item and [self._main_item] or []

    @property
    def all_items(self):
        return self._main_item and [self._main_item] or []

    def clear_drawings(self):
        if self._main_item:
            self.paper.removeItem(self._main_item)
            self._main_item = None


    def draw(self):
        self.clear_drawings()
        self.paper = self.molecule.paper
        pts = [(a.x, a.y) for a in self.atoms]

        side = geo.line_get_side_of_point(pts[0]+pts[1], pts[2])
        d = Settings.bond_spacing*1.5*side*self.molecule.scale_val

        ring_pts = []
        parallel_lines = []

        for i,pt in enumerate(pts[:-1]):
            line = [*pt, *pts[i+1]]
            parallel_lines.append( geo.line_get_parallel(line, d))

        parallel_lines.insert(0, parallel_lines[-1])

        for i,line in enumerate(parallel_lines[:-1]):
            xp, yp, parallel = geo.line_get_intersection_of_line(line, parallel_lines[i+1])
            ring_pts.append((xp,yp))

        # make a closed loop
        ring_pts.append(ring_pts[0])
        # append first atom, and prepend last atom to make almost circular and continuous
        ring_pts.append(ring_pts[1])
        ring_pts.insert(0, ring_pts[-3])
        spline = geo.calc_spline_through_points(ring_pts)
        line_width = max(1*self.molecule.scale_val, 1)
        self._main_item = self.paper.addCubicBezier(spline[3:-3],
                            width=line_width, color=self.color)


    def bounding_box(self):
        if self._main_item:
            return self.paper.itemBoundingBox(self._main_item)
        xs = [a.x for a in self.atoms]
        ys = [a.y for a in self.atoms]
        return [min(xs), min(ys), max(xs), max(ys)]


    def copy(self):
        """ new delocalization can not have same atoms and molecule as this """
        return Delocalization()


    def transform(self, tr):
        pass

    def transform_3D(self, tr):
        pass

    def scale(self, scale):
        pass

    def move_by(self, dx, dy):
        pass





