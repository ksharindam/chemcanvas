# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>

from drawing_parents import DrawableObject
from app_data import Settings

from math import sqrt


class Bracket(DrawableObject):
    meta__undo_properties = ("type", "scale_val")
    meta__undo_copy = ("points",)
    meta__scalables = ("scale_val", "points")

    types = ("square", "curly", "round")

    def __init__(self, type="square"):
        DrawableObject.__init__(self)
        self.type = type
        self.points = []
        self.scale_val = 1.0
        # graphics items
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    def set_points(self, points):
        self.points = list(points)

    @property
    def chemistry_items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def clear_drawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items = []
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clear_drawings()
        getattr(self, "_draw_"+self.type)()
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def _draw_square(self):
        x1, y1, x2, y2 = *self.points[0], *self.points[1]
        dx = 0.08*sqrt( (y2-y1)**2 + (x2-x1)**2)
        self._polyline1 = [(x1+dx,y1), (x1,y1), (x1,y2), (x1+dx,y2)]
        self._polyline2 = [(x2-dx,y1), (x2,y1), (x2,y2), (x2-dx,y2)]

        self._main_items = [self.paper.addPolyline(pts, color=self.color) for pts in (self._polyline1, self._polyline2)]
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def _draw_curly(self):
        x1, y1, x2, y2 = *self.points[0], *self.points[1]
        ch = (y2-y1)/2 # curve height = 1/2 of bracket height
        w = 0.1*sqrt( (y2-y1)**2 + (x2-x1)**2) # curve rect width
        c1 = (x1+w,y1), (x1,y1), (x1+w,y1+ch), (x1,y1+ch)
        c2 = (x1,y1+ch), (x1+w,y1+ch), (x1,y2), (x1+w,y2)
        c3 = (x2-w,y1), (x2,y1), (x2-w,y1+ch), (x2,y1+ch)
        c4 = (x2,y1+ch), (x2-w,y1+ch), (x2,y2), (x2-w,y2)

        self._main_items = [self.paper.addCubicBezier(pts, color=self.color) for pts in (c1, c2, c3, c4)]
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def _draw_round(self):
        x1, y1, x2, y2 = *self.points[0], *self.points[1]
        ch = (y2-y1)/2 # curve height = 1/2 of bracket height
        w = 0.1 * sqrt( (y2-y1)**2 + (x2-x1)**2) # curve rect width
        q = 0.25 * sqrt(w**2 + ch**2)
        c1 = (x1+w,y1), (x1+w,y1), (x1,y1+q), (x1,y1+ch)
        c2 = (x1,y1+ch), (x1,y2-q), (x1+w,y2), (x1+w,y2)
        c3 = (x2-w,y1), (x2-w,y1), (x2,y1+q), (x2,y1+ch)
        c4 = (x2,y1+ch), (x2,y2-q), (x2-w,y2), (x2-w,y2)

        self._main_items = [self.paper.addCubicBezier(pts, color=self.color) for pts in (c1, c2, c3, c4)]
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def set_focus(self, focus):
        if focus:
            self._focus_item = self.paper.addRect(self.points[0]+self.points[1], 3, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        elif self._focus_item:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            self._selection_item = self.paper.addRect(self.points[0]+self.points[1], 3, color=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def bounding_box(self):
        return list(self.points[0] + self.points[1])

    def move_by(self, dx, dy):
        self.points = [(pt[0]+dx,pt[1]+dy) for pt in self.points]

    def scale(self, scale):
        self.scale_val *= scale

    def transform(self, tr):
        self.points = tr.transform_points(self.points)

    def transform_3D(self, tr):
        self.points = [tr.transform(*pt) for pt in self.points]

