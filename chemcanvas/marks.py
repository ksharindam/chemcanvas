# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject, Color, Font, Align
from app_data import Settings
import geometry as geo
from common import float_to_str, bbox_of_bboxes

class Mark(DrawableObject):
    # the stored 'color' property is not used actually, as it is inherited from atom.
    # but adding this is necessary to update marks color when undo and redoing.
    meta__undo_properties = ("rel_x", "rel_y", "color")
    meta__scalables = ("rel_x", "rel_y")

    focus_priority = 2
    redraw_priority = 4
    is_toplevel = False

    def __init__(self):
        DrawableObject.__init__(self)
        self.atom = None
        self.rel_x, self.rel_y = 0,0
        self._size = 6 # used to calculate position around atom and draw focus item
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def parent(self):
        return self.atom

    def bounding_box(self):
        bboxes = [self.paper.itemBoundingBox(item) for item in self._main_items]
        return bbox_of_bboxes(bboxes)

    @property
    def x(self):
        return self.atom.x + self.rel_x

    @property
    def y(self):
        return self.atom.y + self.rel_y

    @property
    def size(self):
        return self._size * self.atom.molecule.scale_val

    def set_pos(self, x, y):
        self.rel_x, self.rel_y = x-self.atom.x, y-self.atom.y

#    def transform(self, tr):
#        pass

    def move_by(self, dx,dy):
        self.rel_x, self.rel_y = self.rel_x+dx, self.rel_y+dy

    def scale(self, scale):
        self.rel_x *= scale
        self.rel_y *= scale

    @property
    def chemistry_items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items+[self._focus_item, self._selection_item])


# ------------------------- END MARK ------------------------


class Charge(Mark):
    """ Represents various types of charge on atom, eg - +ve, -ve, 2+, 3-, δ+, 2δ+ etc """
    meta__undo_properties = Mark.meta__undo_properties + ("type", "value")

    meta__scalables = Mark.meta__scalables

    types = ("normal", "circled", "partial")

    def __init__(self, type="normal"):
        Mark.__init__(self)
        self.type = type
        self.value = 1 # 2 for 2+, 2δ+ or -2 for 2- or 2δ-
        self.font_name = Settings.atom_font_name
        self.font_size = Settings.atom_font_size * 0.75
        self._focusable_item = None

    def set_type(self, charge_type):
        self.type = charge_type

    def setValue(self, val):
        self.value = val

    @property
    def all_items(self):
        return filter(None, self._main_items+[self._focusable_item, self._focus_item, self._selection_item])

    def clear_drawings(self):
        for item in self._main_items:
            self.paper.removeItem(item)
        self._main_items = []
        if self._focusable_item:
            self.paper.removeFocusable(self._focusable_item)
            self.paper.removeItem(self._focusable_item)
            self._focusable_item = None
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clear_drawings()
        self.paper = self.atom.paper
        # draw
        self.color = self.atom.color
        getattr(self, "_draw_%s" % self.type)()
        self.paper.addFocusable(self._focusable_item, self)
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def _draw_normal(self):
        x,y = self.x, self.y
        text = self.value>0 and "+" or "−"# this minus charater is longer than hyphen
        count = abs(self.value)>1 and ("%i" % abs(self.value)) or ""
        text = count + text
        font_size = self.font_size * self.atom.molecule.scale_val
        font = Font(self.font_name, font_size)
        item1 = self.paper.addHtmlText(text, (x,y), font=font, align=Align.HCenter|Align.VCenter, color=self.color)
        self._main_items = [item1]
        self._focusable_item = self.paper.addRect(self.paper.itemBoundingBox(item1), color=Color.transparent)


    def _draw_circled(self):
        x,y = self.x, self.y
        text = self.value>0 and "⊕" or "⊖"
        count = abs(self.value)>1 and ("%i" % abs(self.value)) or ""
        # ⊕ symbol in the font is smaller than +, so using increased font size
        font_size = self.font_size * self.atom.molecule.scale_val
        font = Font(self.font_name, 1.33*font_size)
        if count:
            item1 = self.paper.addHtmlText(text, (x,y), font=font, align=Align.Left|Align.VCenter, color=self.color)
            font.size = font_size
            item2 = self.paper.addHtmlText(count, (x,y), font=font, align=Align.Right|Align.VCenter, color=self.color)
            self._main_items = [item1, item2]
        else:
            item1 = self.paper.addHtmlText(text, (x,y), font=font, align=Align.HCenter|Align.VCenter, color=self.color)
            self._main_items = [item1]

        self._focusable_item = self.paper.addRect(self.bounding_box(), color=Color.transparent)


    def _draw_partial(self):
        x,y = self.x, self.y
        text = self.value>0 and "δ+" or "δ−"
        count = abs(self.value)>1 and ("%i" % abs(self.value)) or ""
        text = count + text
        font_size = self.font_size * self.atom.molecule.scale_val
        font = Font(self.font_name, font_size)
        item1 = self.paper.addHtmlText(text, (x,y), font=font, align=Align.HCenter|Align.VCenter, color=self.color)
        self._main_items = [item1]
        self._focusable_item = self.paper.addRect(self.paper.itemBoundingBox(item1), color=Color.transparent)



    def set_focus(self, focus):
        if focus:
            rect = self.paper.itemBoundingBox(self._focusable_item)
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, selected):
        if selected:
            rect = self.paper.itemBoundingBox(self._focusable_item)
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def copy(self):
        new_mark = Charge()
        for attr in self.meta__undo_properties:
            setattr(new_mark, attr, getattr(self, attr))
        return new_mark


# ---------------------------- END CHARGE ------------------------------



class Electron(Mark):
    """ represents lone pair or single electron """
    meta__undo_properties = Mark.meta__undo_properties + ("type",)
    meta__scalables = Mark.meta__scalables

    types = ("1", "2")# 1 = radical, 2 = lone pair

    def __init__(self, type="2"):
        Mark.__init__(self)
        self.type = type
        self.dot_size = Settings.electron_dot_size

    def set_type(self, type):
        self.type = type

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
        self.paper = self.atom.paper
        # draw
        self.color = self.atom.color
        self._main_items = getattr(self, "_draw_%s"%self.type)()
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def _draw_1(self):
        """ draw single electron """
        r = self.dot_size/2.0 * self.atom.molecule.scale_val
        x,y = self.x, self.y
        return [self.paper.addEllipse([x-r,y-r,x+r,y+r], color=self.color, fill=self.color)]


    def _draw_2(self):
        """ draw lone pair """
        r = self.dot_size/2.0 * self.atom.molecule.scale_val
        d = r*1.5 + 0.5
        x1, y1, x2, y2 = self.atom.x, self.atom.y, self.x, self.y

        items = []
        for sign in (1,-1):
            x, y = geo.line_get_point_at_distance([x1, y1, x2, y2], sign*d)
            items.append( self.paper.addEllipse([x-r,y-r,x+r,y+r], color=self.color, fill=self.color) )
        return items


    def set_focus(self, focus):
        if focus:
            size = self._size * self.atom.molecule.scale_val
            x,y,s = self.x, self.y, size + 1
            self._focus_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, selected):
        if selected:
            size = self._size * self.atom.molecule.scale_val
            x,y,s = self.x, self.y, size+1
            self._selection_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def copy(self):
        new_mark = Electron()
        for attr in self.meta__undo_properties:
            setattr(new_mark, attr, getattr(self, attr))
        return new_mark
