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
            bboxes = [self.paper.itemBoundingBox(item) for item in self._main_items]
            return bbox_of_bboxes(bboxes)
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



class p_Orbital(DrawableObject):
    meta__undo_properties = ("x", "y", "lobe_size", "rotation", "paths",
             "gradient_center", "gradient_size", "layer", "color", "scale_val",)
    meta__scalables = ("scale_val", "x", "y", "lobe_size")

    def __init__(self):
        DrawableObject.__init__(self)
        self.x = 0 # center_x
        self.y = 0
        self.lobe_size = 24 # equals to bond length by default
        self.rotation = 0
        self.layer = -1 # 1=foreground | -1=background
        self.scale_val = 1.0
        #self.paper = None # inherited
        #self.color = (0,0,0) # inherited
        self._main_items = []
        self._focus_item = None
        self._selection_item = None
        self.paths = []
        self.gradient_center = None
        self.gradient_size = None

    @property
    def pos(self):
        return (self.x,self.y)

    def set_pos(self, x,y):
        self.x, self.y = x, y

    def set_rotation(self, angle):
        self.rotation = angle
        self.paths = []

    def set_lobe_size(self, size):
        self.lobe_size = size
        self.paths = []

    def calc_path(self):
        if self.paths:# already calculated
            return
        path = "30,100 15,100 0,48 0,34 0,15 6,0 30,0 54,0 60,15 60,34 60,48 45,100 30,100"
        path = [tuple(map(int, coord.split(","))) for coord in path.split(" ")]
        scale = self.lobe_size/100
        points1 = [(self.x+(x-30)*scale, self.y+(y-100)*scale) for x,y in path]
        points2 = [(x, 2*self.y-y) for x,y in points1]
        self.gradient_center = (self.x-9*scale, self.y-65*scale)
        self.gradient_size = 60*scale
        if self.rotation:
            tfm = geo.Transform()
            tfm.translate(-self.x, -self.y)
            tfm.rotate(self.rotation*PI/180)
            tfm.translate(self.x, self.y)
            points1 = tfm.transform_points(points1)
            points2 = tfm.transform_points(points2)
            self.gradient_center = tfm.transform(*self.gradient_center)
        self.paths = [points1, points2]

    @property
    def chemistry_items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def bounding_box(self):
        if self._main_items:
            return self.paper.itemBoundingBox(self._main_items[0])
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

        self.calc_path()
        gradient = QRadialGradient(*self.gradient_center, self.gradient_size)
        gradient.setColorAt(0.0, QColor("white"))
        gradient.setColorAt(0.4, QColor("#aaaaaa"))
        gradient.setColorAt(1.0, QColor("#aaaaaa").darker())
        item1 = self.paper.addCubicBezier(self.paths[0], fill=gradient)
        item2 = self.paper.addCubicBezier(self.paths[1], fill=(255,255,255))
        self._main_items = [item1,item2]
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


    def set_focus(self, focus):
        if focus:
            self.calc_path()
            path = self.paths[0] + self.paths[1][1:]
            self._focus_item = self.paper.addCubicBezier(path, fill=Settings.focus_color)
            if self.layer==1:
                self.paper.toTopLayer(self._focus_item)
            else:
                App.paper.toBottomLayer(self._focus_item)
        else: # unfocus
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            self.calc_path()
            path = self.paths[0] + self.paths[1][1:]
            self._selection_item = self.paper.addCubicBezier(path, fill=Settings.selection_color)
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
        self.paths = []

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
