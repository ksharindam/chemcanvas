# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2025-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject
from app_data import App, Settings
import geometry as geo

class Shape(DrawableObject):
    meta__undo_properties = ("layer", "color", "fill", "scale_val")
    meta__undo_copy = ("points",)
    meta__scalables = ("scale_val", "points")

    def __init__(self, points=None):
        DrawableObject.__init__(self)
        self.points = points or []
        self.layer = -1 # 1=foreground | -1=background
        self.line_width = 2.0
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
        x1,y1, x2,y2 = self.points
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

