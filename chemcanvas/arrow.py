# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>

from drawable import DrawableObject
from app_data import Settings, Color
from geometry import *
import common

from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsItemGroup

class Arrow(DrawableObject):
    meta__undo_properties = ("type", "_line_width", "head_dimensions")
    meta__undo_copy = ("points",)
    meta__scalables = ("points", "_line_width", "head_dimensions")

    def __init__(self):
        DrawableObject.__init__(self)
        self.type = "normal"#simple, resonance, retro, equililbrium
        self.points = [] # list of points that define the path, eg [(x1,y1), (x2,y2)]
        self._line_width = 2
        # length is the total length of head from left to right
        # width is half width, i.e from vertical center to top or bottom end
        # depth is how much deep the body is inserted to head, when depth=0 head becomes triangular
        self.head_dimensions = (12,5,4)# [length, width, depth]
        # arrow can have multiple parts which receives focus
        self._main_items = []
        self.head_item = None
        self._focus_item = None
        self._selection_item = None
        #self._focusable_items = []


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
        self.head_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def headBoundingBox(self):
        if self.head_item:
            return self.head_item.sceneBoundingRect().getCoords()
        else:
            w = self.head_dimensions[1]
            x,y = self.points[-1]
            return [x-w, y-w, x+w, y+w]

    def draw(self):
        focused = bool(self._focus_item)
        self.clearDrawings()
        getattr(self, "_draw_"+self.type)()
        if focused:
            self.setFocus(True)

    def _draw_normal(self):
        l,w,d = self.head_dimensions
        points = self.points[:]

        head_points = arrow_head(*points[-2], *points[-1], l, w, d)
        points[-1] = head_points[0]
        body = self.paper.addPolyline(points, width=self._line_width)
        self.head_item = self.paper.addPolygon(head_points, fill=Color.black)
        self._main_items = [body, self.head_item]
        [self.paper.addFocusable(item, self) for item in self._main_items]

    def _draw_equilibrium_simple(self):
        width = 3
        points = self.points[:]
        #polylines = []
        for i in range(2):
            points.reverse()# draw first reverse arrow, then forward arrow
            x1, y1, x2, y2 = line_get_parallel(points[0] + points[1], width)
            xp, yp = line_extend_by([x1,y1,x2,y2], -8)
            xp, yp = line_get_point_at_distance([x1,y1,xp,yp], 5)
            coords = [(x1,y1), (x2,y2), (xp,yp)]
            item = self.paper.addPolyline(coords)
            self.paper.addFocusable(item, self)
            self._main_items.append(item)

    def _draw_electron_shift(self):
        if len(self.points)==2:
            # for two points, this will be straight line
            a,c = self.points
            cp_x, cp_y = ((c[0]+a[0])/2, (c[1]+a[1])/2)# midpoint
        else:
            a, b, c = self.points[:3]
            cp_x = 2*b[0] - 0.5*a[0] - 0.5*c[0]
            cp_y = 2*b[1] - 0.5*a[1] - 0.5*c[1]
        body = self.paper.addQuadBezier([a, (cp_x, cp_y), c])
        self.paper.addFocusable(body, self)
        # draw head
        l,w,d = 6, 2.5, 2#self.head_dimensions
        points = arrow_head(cp_x,cp_y, *c, l, w, d)
        self.head_item = self.paper.addPolygon(points, fill=Color.black)
        self.paper.addFocusable(self.head_item, self)
        self._main_items = [body, self.head_item]

    def _draw_fishhook(self):
        if len(self.points)==2:
            # for two points, this will be straight line
            a,c = self.points
            cp_x, cp_y = ((c[0]+a[0])/2, (c[1]+a[1])/2)
        else:
            a, b, c = self.points[:3]
            cp_x = 2*b[0] - 0.5*a[0] - 0.5*c[0]
            cp_y = 2*b[1] - 0.5*a[1] - 0.5*c[1]
        body = self.paper.addQuadBezier([a, (cp_x, cp_y), c])
        self.paper.addFocusable(body, self)
        # draw head
        l,w,d = 6, 2.5, 2#self.head_dimensions
        side = -1*line_get_side_of_point([cp_x,cp_y, *c], a) or 1
        points = arrow_head(cp_x,cp_y, *c, l, w*side, d, one_side=True)
        self.head_item = self.paper.addPolygon(points, fill=Color.black)
        self.paper.addFocusable(self.head_item, self)
        self._main_items = [body, self.head_item]


    def setFocus(self, focus):
        if focus:
            width = 2*self.head_dimensions[1]
            self._focus_item = self.paper.addPolyline(self.points, width=width, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        elif self._focus_item:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            width = 2*self.head_dimensions[1]
            self._selection_item = self.paper.addPolyline(self.points, width=width, color=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def boundingBox(self):
        bboxes = []
        for item in self._main_items:
            bboxes.append(self.paper.itemBoundingBox(item))
        if bboxes:
            return common.bbox_of_bboxes(bboxes)
        return self.points[0] + self.points[1]

    def moveBy(self, dx, dy):
        self.points = [(pt[0]+dx,pt[1]+dy) for pt in self.points]

    def scale(self, scale):
        l,w,d = self.head_dimensions
        self.head_dimensions = [l*scale, w*scale, d*scale]

    def transform(self, tr):
        self.points = tr.transformPoints(self.points)


def arrow_head(x1,y1,x2,y2, l,w,d, one_side=False):
    ''' x1,y1 = arrow tail. x2,y2 = arrow head tip.
    l=length, w=width, d=depth.
    Sign of width determines the side of single sided arrow head. +ve = left side'''
    line1 = [x1,y1,x2,y2]
    a = line_extend_by(line1, d-l)# sharp end
    xp,yp = line_extend_by(line1, -l)
    line2 = [x1,y1,xp,yp]
    b = line_get_point_at_distance(line2, w)# side 1
    if one_side:
        return a, b, (x2,y2)
    return  a, b, (x2,y2), line_get_point_at_distance(line2, -w)# side 2

