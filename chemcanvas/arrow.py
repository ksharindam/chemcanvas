# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>

from drawing_parents import DrawableObject, Color
from app_data import Settings
import geometry as geo
from common import bbox_of_bboxes, float_to_str


class Arrow(DrawableObject):
    meta__undo_properties = ("type", "_line_width", "head_dimensions", "color")
    meta__undo_copy = ("points",)
    meta__scalables = ("points", "_line_width", "head_dimensions")

    def __init__(self):
        DrawableObject.__init__(self)
        self.type = "normal"#simple, resonance, retro, equililbrium
        self.points = [] # list of points that define the path, eg [(x1,y1), (x2,y2)]
        self.anchor = None# for electron_transfer and fishhook arrows
        self._line_width = 2
        # length is the total length of head from left to right
        # width is half width, i.e from vertical center to top or bottom end
        # depth is how much deep the body is inserted to head, when depth=0 head becomes triangular
        self.head_dimensions = (12,5,4)# [length, width, depth]
        # arrow can have multiple parts which receives focus
        self._main_items = []
        self._head_item = None# what about multi head of resonace arrow??
        self._focus_item = None
        self._selection_item = None
        #self._focusable_items = []


    def setPoints(self, points):
        self.points = list(points)

    def setAnchor(self, obj):
        self.anchor = obj

    @property
    def items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def clearDrawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items = []
        self._head_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def headBoundingBox(self):
        if self._head_item:
            return self.paper.itemBoundingBox(self._head_item)
        else:
            w = self.head_dimensions[1]
            x,y = self.points[-1]
            return [x-w, y-w, x+w, y+w]

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()
        getattr(self, "_draw_"+self.type)()
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)


    def _draw_normal(self):
        l,w,d = self.head_dimensions
        points = self.points[:]

        head_points = arrow_head(*points[-2], *points[-1], l, w, d)
        points[-1] = head_points[0]
        body = self.paper.addPolyline(points, self._line_width, color=self.color)
        self._head_item = self.paper.addPolygon(head_points, color=self.color, fill=self.color)
        self._main_items = [body, self._head_item]
        # add focusable
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def _draw_equilibrium(self):
        width = 3
        points = self.points[:]

        for i in range(2):
            points.reverse()# draw first reverse arrow, then forward arrow
            x1, y1, x2, y2 = geo.line_get_parallel(points[0] + points[1], width)
            xp, yp = geo.line_extend_by([x1,y1,x2,y2], -8)
            xp, yp = geo.line_get_point_at_distance([x1,y1,xp,yp], 5)
            coords = [(x1,y1), (x2,y2), (xp,yp)]
            self._main_items.append( self.paper.addPolyline(coords, color=self.color) )
        [self.paper.addFocusable(item, self) for item in self._main_items]


    # arrow head at 2
    #                    length
    #                   |---|  _
    #                  C\      |
    #                    \     | width
    #   A----------------B\-P  |
    #   1       d |  __R___\|2 -
    #                      /|
    #   D----------------E/-Q
    #                    /
    #                  F/


    def _draw_retrosynthetic(self):
        l, w, d = 8, 8, 3
        x1,y1, x2,y2 = self.points[-2] + self.points[-1]
        # calc head
        r = geo.line_extend_by( [x1,y1,x2,y2], -l)
        c = geo.line_get_point_at_distance ([x1,y1, *r], w)
        f = geo.line_get_point_at_distance ([x1,y1, *r], -w)
        # calc body
        w_ratio = d / w
        dl = w_ratio * l
        h = geo.line_extend_by( [x1,y1,x2,y2], -dl)
        line = [x1,y1, *h]
        line1 = geo.line_get_parallel(line, d)
        line2 = geo.line_get_parallel(line, -d)
        # draw
        item1 = self.paper.addLine(line1, color=self.color)
        item2 = self.paper.addLine(line2, color=self.color)
        head_item = self.paper.addPolyline([c, (x2,y2), f], color=self.color)

        self._main_items = [item1, item2, head_item]
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def _draw_resonance(self):
        l,w,d = self.head_dimensions
        points = self.points[:]

        head_points1 = arrow_head(*points[-2], *points[-1], l, w, d)
        head_points2 = arrow_head(*points[-1], *points[-2], l, w, d)
        points[-1] = head_points1[0]
        points[-2] = head_points2[0]
        body = self.paper.addLine(points[-2]+points[-1], self._line_width, color=self.color)
        head1 = self.paper.addPolygon(head_points1, color=self.color, fill=self.color)
        head2 = self.paper.addPolygon(head_points2, color=self.color, fill=self.color)
        self._main_items = [body, head1, head2]
        self._head_item = head1
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def _calc_spline(self, knots):
        # for three points we use quadratic bezier. because, it creates
        # a parabolic shape, looks more natural for electron shift arrows.
        if len(knots)!=3:
            a, b, c = knots
            cp_x = 2*b[0] - 0.5*a[0] - 0.5*c[0]
            cp_y = 2*b[1] - 0.5*a[1] - 0.5*c[1]
            return geo.quad_to_cubic_bezier([a, (cp_x, cp_y), c])

        # for more than 3 points, we use cubic bezier spline
        elif len(knots) >= 3:
            return geo.calc_spline_through_points(knots)

    def _draw_electron_shift(self):
        """ draw electron shift arrow """
        if len(self.points)==2:
            # draw straight line
            pts = self.points
            body = self.paper.addLine(pts[0]+pts[1], color=self.color)

        elif len(self.points)>=3:
            pts = self._calc_spline(self.points)
            body = self.paper.addSpline(pts, color=self.color)
        else:
            return
        # draw head
        l,w,d = 6, 2.5, 2#self.head_dimensions
        points = arrow_head(*pts[-2], *pts[-1], l, w, d)
        head = self.paper.addPolygon(points, color=self.color, fill=self.color)
        self._main_items = [body, head]
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def _draw_fishhook(self):
        if len(self.points)==2:
            # draw straight line
            pts = self.points
            body = self.paper.addLine(pts[0]+pts[1], color=self.color)
            side = 1

        elif len(self.points)>=3:
            pts = self._calc_spline(self.points)
            body = self.paper.addSpline(pts, color=self.color)
            side = -1*geo.line_get_side_of_point([*pts[-2], *pts[-1]], pts[-4]) or 1
        else:
            return
        # draw head
        l,w,d = 6, 2.5, 2#self.head_dimensions
        points = arrow_head(*pts[-2], *pts[-1], l, w*side, d, one_side=True)
        head = self.paper.addPolygon(points, color=self.color, fill=self.color)
        self._main_items = [body, head]
        [self.paper.addFocusable(item, self) for item in self._main_items]


    def setFocus(self, focus):
        if focus:
            width = 2*self.head_dimensions[1]
            self._focus_item = self.paper.addPolyline(self.points, width, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        elif self._focus_item:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            width = 2*self.head_dimensions[1]
            self._selection_item = self.paper.addPolyline(self.points, width, color=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def boundingBox(self):
        bboxes = []
        for item in self._main_items:
            bboxes.append(self.paper.itemBoundingBox(item))
        if bboxes:
            return bbox_of_bboxes(bboxes)
        return self.points[0] + self.points[1]

    def moveBy(self, dx, dy):
        self.points = [(pt[0]+dx,pt[1]+dy) for pt in self.points]

    def scale(self, scale):
        l,w,d = self.head_dimensions
        self.head_dimensions = [l*scale, w*scale, d*scale]

    def transform(self, tr):
        self.points = tr.transformPoints(self.points)

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("arrow")
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


def arrow_head(x1,y1,x2,y2, l,w,d, one_side=False):
    ''' x1,y1 = arrow tail. x2,y2 = arrow head tip.
    l=length, w=width, d=depth.
    Sign of width determines the side of single sided arrow head. +ve = left side'''
    line1 = [x1,y1,x2,y2]
    a = geo.line_extend_by(line1, d-l)# sharp end
    xp,yp = geo.line_extend_by(line1, -l)
    line2 = [x1,y1,xp,yp]
    b = geo.line_get_point_at_distance(line2, w)# side 1
    if one_side:
        return a, b, (x2,y2)
    return  a, b, (x2,y2), geo.line_get_point_at_distance(line2, -w)# side 2


