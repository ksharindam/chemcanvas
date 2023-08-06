# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>

from drawing_parents import DrawableObject
from app_data import Settings
from common import float_to_str

from math import sqrt


class Bracket(DrawableObject):
    meta__undo_properties = ("type",)
    meta__undo_copy = ("points",)
    meta__scalables = ("points",)

    types = ("square", "curly", "round")

    def __init__(self):
        DrawableObject.__init__(self)
        self.type = "square"
        self.points = []
        # graphics items
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    def setType(self, type):
        self.type = type


    def setPoints(self, points):
        self.points = list(points)

    @property
    def items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def clearDrawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items = []
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()
        getattr(self, "_draw_"+self.type)()
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        getattr(self, "_draw_%s_on_paper"%self.type)(paper)

    def _draw_square(self):
        self._main_items = self._draw_square_on_paper(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]

    def _draw_square_on_paper(self, paper):
        x1, y1, x2, y2 = *self.points[0], *self.points[1]
        dx = 0.08*sqrt( (y2-y1)**2 + (x2-x1)**2)
        self._polyline1 = [(x1+dx,y1), (x1,y1), (x1,y2), (x1+dx,y2)]
        self._polyline2 = [(x2-dx,y1), (x2,y1), (x2,y2), (x2-dx,y2)]

        return [paper.addPolyline(pts) for pts in (self._polyline1, self._polyline2)]


    def _draw_curly(self):
        self._main_items = self._draw_curly_on_paper(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]

    def _draw_curly_on_paper(self, paper):
        x1, y1, x2, y2 = *self.points[0], *self.points[1]
        ch = (y2-y1)/2 # curve height = 1/2 of bracket height
        w = 0.1*sqrt( (y2-y1)**2 + (x2-x1)**2) # curve rect width
        c1 = (x1+w,y1), (x1,y1), (x1+w,y1+ch), (x1,y1+ch)
        c2 = (x1,y1+ch), (x1+w,y1+ch), (x1,y2), (x1+w,y2)
        c3 = (x2-w,y1), (x2,y1), (x2-w,y1+ch), (x2,y1+ch)
        c4 = (x2,y1+ch), (x2-w,y1+ch), (x2,y2), (x2-w,y2)

        return [paper.addCubicBezier(pts) for pts in (c1, c2, c3, c4)]

    def _draw_round(self):
        self._main_items = self._draw_round_on_paper(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]

    def _draw_round_on_paper(self, paper):
        x1, y1, x2, y2 = *self.points[0], *self.points[1]
        ch = (y2-y1)/2 # curve height = 1/2 of bracket height
        w = 0.1 * sqrt( (y2-y1)**2 + (x2-x1)**2) # curve rect width
        q = 0.25 * sqrt(w**2 + ch**2)
        c1 = (x1+w,y1), (x1+w,y1), (x1,y1+q), (x1,y1+ch)
        c2 = (x1,y1+ch), (x1,y2-q), (x1+w,y2), (x1+w,y2)
        c3 = (x2-w,y1), (x2-w,y1), (x2,y1+q), (x2,y1+ch)
        c4 = (x2,y1+ch), (x2,y2-q), (x2-w,y2), (x2-w,y2)

        return [paper.addCubicBezier(pts) for pts in (c1, c2, c3, c4)]


    def setFocus(self, focus):
        if focus:
            self._focus_item = self.paper.addRect(self.points[0]+self.points[1], 3, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        elif self._focus_item:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            self._selection_item = self.paper.addRect(self.points[0]+self.points[1], 3, color=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def boundingBox(self):
        return list(self.points[0] + self.points[1])

    def moveBy(self, dx, dy):
        self.points = [(pt[0]+dx,pt[1]+dy) for pt in self.points]

    def scale(self, scale):
        #self.line_width *= scale
        pass

    def transform(self, tr):
        self.points = tr.transformPoints(self.points)

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("bracket")
        elm.setAttribute("typ", self.type)
        points = ["%s,%s" % (float_to_str(pt[0]), float_to_str(pt[1])) for pt in self.points]
        elm.setAttribute("pts", " ".join(points))
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        type = elm.getAttribute("typ")
        if type:
            self.type = type
        points = elm.getAttribute("pts")
        if points:
            try:
                pt_list = points.split(" ")
                pt_list = [pt.split(",") for pt in pt_list]
                self.points = [(float(pt[0]), float(pt[1])) for pt in pt_list]
            except:
                pass

