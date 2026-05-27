# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2025-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
from math import pi as PI
from PyQt5.QtGui import QRadialGradient, QColor

from drawing_parents import DrawableObject
from app_data import App, Settings
import geometry as geo
from common import bbox_of_bboxes

class Shape(DrawableObject):
    meta__undo_properties = ("layer", "color", "fill", "scale_val")
    meta__undo_copy = ("points",)
    meta__scalables = ("scale_val", "points")

    def __init__(self, points=None):
        DrawableObject.__init__(self)
        self.points = points or []
        self.layer = -1 # 1=foreground | -1=background
        self.line_width = 1.0
        self.scale_val = 1.0
        #self.paper = None # inherited
        #self.color = (0,0,0) # inherited
        self.fill = None

    def set_points(self, points):
        self.points = list(points)

    @property
    def chemistry_items(self):
        return [self._main_item]

    @property
    def all_items(self):
        return filter(None, [self._main_item, self._focus_item, self._selection_item])

    def bounding_box(self):
        if self._main_item:
            return self.paper.itemBoundingBox(self._main_item)
        d = self.line_width/2
        x1,y1, x2,y2 = *self.points[0], *self.points[1]
        return x1-d, y1-d, x2+d, y2+d


    def move_by(self, dx, dy):
        self.points = [(x+dx,y+dy) for x,y in self.points]

    def scale(self, scale):
        self.scale_val *= scale

    def transform(self, tr):
        self.points = tr.transform_points(self.points)

    def transform_3D(self, tr):
        self.points = [tr.transform(*pt,0)[:2] for pt in self.points]

    @property
    def menu_template(self):
        menu = (("Move to", ("Foreground", "Background")),)
        return menu

    def get_property(self, key):
        if key=="Move to":
            val = {1:"Foreground", -1:"Background"}.get(self.layer)
            return val
        else:
            print("Warning ! : Invalid key '%s'"%key)

    def set_property(self, key, val):
        if key=="Move to":
            layer = {"Foreground":1, "Background":-1}.get(val)
            if layer != self.layer:
                self.layer = layer
                self.draw()



class Line(Shape):

    def __init__(self, points=None):
        Shape.__init__(self, points)
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    def clear_drawings(self):
        if self._main_item:
            self.paper.removeFocusable(self._main_item)
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clear_drawings()

        line = self.points[0] + self.points[1]
        self._main_item = self.paper.addLine(line, self.line_width*self.scale_val, color=self.color)
        self.paper.addFocusable(self._main_item, self)
        if self.layer==1:
            self.paper.toTopLayer(self._main_item)
        else:
            self.paper.toBottomLayer(self._main_item)
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def set_focus(self, focus):
        if focus:
            self._focus_item = self.paper.addLine(self.points[0] + self.points[1], width=self.line_width+8, color=Settings.focus_color)
            if self.layer==1:
                self.paper.toTopLayer(self._focus_item)
            else:
                App.paper.toBottomLayer(self._focus_item)
            self._focus_item.stackBefore(self._main_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            self._selection_item = self.paper.addLine(self.points[0] + self.points[1], self.line_width+4, Settings.selection_color)
            if self.layer==1:
                self.paper.toTopLayer(self._selection_item)
            else:
                App.paper.toBottomLayer(self._selection_item)
            self._selection_item.stackBefore(self._main_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None



class Rectangle(Shape):

    def __init__(self, points=None):
        Shape.__init__(self, points)
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    def normalize(self):
        rect = tuple(geo.rect_normalize(self.points[0]+self.points[1]))
        self.points = [rect[:2], rect[2:]]

    def clear_drawings(self):
        if self._main_item:
            self.paper.removeFocusable(self._main_item)
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clear_drawings()

        rect = geo.rect_normalize(self.points[0]+self.points[1])
        self._main_item = self.paper.addRect(rect, self.line_width*self.scale_val,
                            color=self.color, fill=self.fill)
        self.paper.addFocusable(self._main_item, self)
        if self.layer==1:
            self.paper.toTopLayer(self._main_item)
        else:
            self.paper.toBottomLayer(self._main_item)
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def set_focus(self, focus):
        if focus:
            rect = geo.rect_normalize(self.points[0]+self.points[1])
            self._focus_item = self.paper.addRect(rect, width=self.line_width+8, color=Settings.focus_color)
            if self.layer==1:
                self.paper.toTopLayer(self._focus_item)
            else:
                App.paper.toBottomLayer(self._focus_item)
            self._focus_item.stackBefore(self._main_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            rect = geo.rect_normalize(self.points[0]+self.points[1])
            self._selection_item = self.paper.addRect(rect, self.line_width+4, Settings.selection_color)
            if self.layer==1:
                self.paper.toTopLayer(self._selection_item)
            else:
                App.paper.toBottomLayer(self._selection_item)
            self._selection_item.stackBefore(self._main_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None



class Ellipse(Shape):

    def __init__(self, points=None):
        Shape.__init__(self, points)
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    def normalize(self):
        rect = tuple(geo.rect_normalize(self.points[0]+self.points[1]))
        self.points = [rect[:2], rect[2:]]

    def clear_drawings(self):
        if self._main_item:
            self.paper.removeFocusable(self._main_item)
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clear_drawings()

        rect = geo.rect_normalize(self.points[0]+self.points[1])
        self._main_item = self.paper.addEllipse(rect, self.line_width*self.scale_val,
                            color=self.color, fill=self.fill)
        self.paper.addFocusable(self._main_item, self)
        if self.layer==1:
            self.paper.toTopLayer(self._main_item)
        else:
            self.paper.toBottomLayer(self._main_item)
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def set_focus(self, focus):
        if focus:
            rect = geo.rect_normalize(self.points[0]+self.points[1])
            self._focus_item = self.paper.addEllipse(rect, width=self.line_width+8, color=Settings.focus_color)
            if self.layer==1:
                self.paper.toTopLayer(self._focus_item)
            else:
                App.paper.toBottomLayer(self._focus_item)
            self._focus_item.stackBefore(self._main_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            rect = geo.rect_normalize(self.points[0]+self.points[1])
            self._selection_item = self.paper.addEllipse(rect, self.line_width+4, Settings.selection_color)
            if self.layer==1:
                self.paper.toTopLayer(self._selection_item)
            else:
                App.paper.toBottomLayer(self._selection_item)
            self._selection_item.stackBefore(self._main_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None



class Orbital(DrawableObject):
    meta__undo_properties = ("type", "x", "y", "lobe_size", "rotation",
             "layer", "color", "scale_val",)
    meta__scalables = ("scale_val", "x", "y", "lobe_size")
    types = ("p", "dxy", "dz2")
    def __init__(self, type="p"):
        DrawableObject.__init__(self)
        self.type = type
        self.x = 0 # center_x
        self.y = 0
        self.lobe_size = 24 # equals to bond length by default
        self.rotation = 0
        self.layer = 1 # 1=foreground | -1=background
        self.scale_val = 1.0
        #self.paper = None # inherited
        #self.color = (0,0,0) # inherited
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def pos(self):
        return (self.x,self.y)

    def set_pos(self, x,y):
        self.x, self.y = x, y

    @property
    def chemistry_items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def bounding_box(self):
        if self._main_items:
            bboxes = [self.paper.itemBoundingBox(item) for item in self._main_items]
            return bbox_of_bboxes(bboxes)
        d = self.lobe_size
        x,y = self.x, self.y
        return x-d, y-d, x+d, y+d


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

        self._main_items = getattr(self, "_draw_%s" % self.type)()
        for item in self._main_items:
            self.paper.addFocusable(item, self)
            if self.layer==1:
                self.paper.toTopLayer(item)
            else:
                self.paper.toBottomLayer(item)
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)

    def _draw_s(self):
        r = self.lobe_size * self.scale_val
        rect = [self.x-r, self.y-r, self.x+r,self.y+r]
        gradient = self.get_lobe_gradient()
        return [self.paper.addEllipse(rect, 1*self.scale_val, fill=gradient)]

    def _draw_p(self):
        path = "30,100 15,100 0,48 0,34 0,15 6,0 30,0 54,0 60,15 60,34 60,48 45,100 30,100"
        path = [tuple(map(int, coord.split(","))) for coord in path.split(" ")]
        scale = self.lobe_size/100 * self.scale_val
        items = []
        gradient = self.get_lobe_gradient()
        points = [[(self.x+(x-30)*scale, self.y+(y-100)*scale) for x,y in path]]*2
        for i,pts in enumerate(points):
            angle = self.rotation*PI/180 + i*PI
            pts = [geo.rotate_point(*pt, self.x, self.y, angle) for pt in pts]
            fill = (255,255,255) if i%2 else gradient
            item = self.paper.addCubicBezier(pts, 1*self.scale_val, fill=fill)
            items.append(item)
        return items


    def _draw_dxy(self):
        path = "35,100 35,100 0,65 0,33 0,14 10,0 35,0 60,0 70,14 70,33 70,65 35,100 35,100"
        path = [tuple(map(int, coord.split(","))) for coord in path.split(" ")]
        scale = self.lobe_size/100 * self.scale_val
        items = []
        gradient = self.get_lobe_gradient()
        points = [[(self.x+(x-35)*scale, self.y+(y-100)*scale) for x,y in path]]*4
        for i,pts in enumerate(points):
            angle = self.rotation*PI/180 + PI/4 + i*PI/2
            pts = [geo.rotate_point(*pt, self.x, self.y, angle) for pt in pts]
            fill = (255,255,255) if i%2 else gradient
            item = self.paper.addCubicBezier(pts, 1*self.scale_val, fill=fill)
            items.append(item)
        return items

    def _draw_dz2(self):
        scale = self.lobe_size/100 * self.scale_val
        lobe_path = "30,100 15,100 0,48 0,34 0,15 6,0 30,0 54,0 60,15 60,34 60,48 45,100 30,100"
        lobe_path = [tuple(map(int, coord.split(","))) for coord in lobe_path.split(" ")]
        lobe_pts = [(self.x+(x-30)*scale, self.y+(y-100)*scale) for x,y in lobe_path]
        ring_path = "45,0 30,0 0,4 0,14 0,24 30,28 45,28 60,28 90,24 90,14 90,4 60,0 45,0"
        ring_path = [tuple(map(int, coord.split(","))) for coord in ring_path.split(" ")]
        ring_pts = [(self.x+(x-45)*scale, self.y+(y-14)*scale) for x,y in ring_path]
        gradient = self.get_lobe_gradient()
        points = [lobe_pts, ring_pts, lobe_pts]
        items = []
        for i,pts in enumerate(points):
            angle = self.rotation*PI/180
            if i==0:# first lobe will be downward
                angle += PI
            pts = [geo.rotate_point(*pt, self.x, self.y, angle) for pt in pts]
            fill = (255,255,255) if i==1 else gradient
            item = self.paper.addCubicBezier(pts, 1*self.scale_val, fill=fill)
            items.append(item)
        items.reverse()# because set_focus uses path of first item
        return items

    def get_lobe_gradient(self):
        gradient = QRadialGradient(0.35, 0.35, 0.65)
        gradient.setCoordinateMode(gradient.ObjectBoundingMode)
        gradient.setColorAt(0.0, QColor("white"))
        gradient.setColorAt(0.4, QColor("#aaaaaa"))
        gradient.setColorAt(1.0, QColor("#aaaaaa").darker())
        return gradient

    def set_focus(self, focus):
        if focus:
            path = self._main_items[0].shape()
            path.translate(self._main_items[0].scenePos())
            self._focus_item = self.paper.addPath(path, fill=Settings.focus_color)
            if self.layer==1:
                self.paper.toTopLayer(self._focus_item)
            else:
                App.paper.toBottomLayer(self._focus_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            path = self._main_items[0].shape()
            path.translate(self._main_items[0].scenePos())
            self._selection_item = self.paper.addPath(path, fill=Settings.selection_color)
            if self.layer==1:
                self.paper.toTopLayer(self._selection_item)
            else:
                App.paper.toBottomLayer(self._selection_item)
            #self._selection_item.stackBefore(self._main_items[0])
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None


    def move_by(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.scale_val *= scale

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def transform_3D(self, tr):
        self.x, self.y, z = tr.transform(self.x, self.y, 0)

    @property
    def menu_template(self):
        menu = (("Move to", ("Foreground", "Background")),)
        return menu

    def get_property(self, key):
        if key=="Move to":
            val = {1:"Foreground", -1:"Background"}.get(self.layer)
            return val
        else:
            print("Warning ! : Invalid key '%s'"%key)

    def set_property(self, key, val):
        if key=="Move to":
            layer = {"Foreground":1, "Background":-1}.get(val)
            if layer != self.layer:
                self.layer = layer
                self.draw()
