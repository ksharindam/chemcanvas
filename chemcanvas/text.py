# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject, Font, Align
from app_data import Settings


# ---------------------------- TEXT --------------------------------

class Text(DrawableObject):
    meta__undo_properties = ("x", "y", "text", "font_name", "font_size", "color", "scale_val")
    meta__undo_copy = ("_formatted_text_parts",)
    meta__scalables = ("scale_val", "x", "y")

    def __init__(self):
        DrawableObject.__init__(self)
        #self.paper = None # inherited
        self.x = 0
        self.y = 0
        self.text = ""
        self.font_name = "Sans Serif"
        self.font_size = Settings.text_size
        self.scale_val = 1.0

        self._formatted_text_parts = []
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    def set_text(self, text):
        self.text = text
        self._formatted_text_parts = []

    def append(self, char):
        self.text += char
        self._formatted_text_parts = []

    #def delete_last_char(self):
    #    if self.text:
    #        self.text = self.text[:-1]
    #    self._formatted_text_parts = []

    @property
    def items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def clear_drawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items.clear()
        if self._focus_item:
            self.set_focus(False)
        if self._selection_item:
            self.set_selected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clear_drawings()

        if not self._formatted_text_parts:
            # TODO : convert < and > to ;lt and ;gt
            self._formatted_text_parts = ["<br>".join(self.text.split('\n'))]

        font_size = self.font_size * self.scale_val
        _font = Font(self.font_name, font_size)
        line_spacing = font_size
        x, y = self.x, self.y
        for text_part in self._formatted_text_parts:
            if text_part:
                item = self.paper.addHtmlText(text_part, (x,y), font=_font, color=self.color)
                self._main_items.append(item)
            y += line_spacing
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def set_focus(self, focus):
        if focus:
            rect = self.paper.item_bounding_box(self._main_items[0])
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            rect = self.paper.item_bounding_box(self._main_items[0])
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def bounding_box(self):
        if self._main_items:
            return self.paper.item_bounding_box(self._main_items[0])
        d = self.font_size * self.scale_val
        return self.x, self.y-d, self.x+d, self.y # TODO : need replacement

    def set_pos(self, x, y):
        self.x, self.y = x, y

    def move_by(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.scale_val *= scale

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def transform_3D(self, tr):
        self.x, self.y, z = tr.transform(self.x, self.y, 0)

#---------------------------- END TEXT ----------------------------------


#------------------------------- PLUS --------------------------------

class Plus(DrawableObject):
    meta__undo_properties = ("x", "y", "font_size", "color", "scale_val")
    meta__scalables = ("scale_val", "x", "y")

    def __init__(self):
        DrawableObject.__init__(self)
        #self.paper = None # inherited
        self.x = 0
        self.y = 0
        self.font_name = Settings.atom_font_name
        self.font_size = Settings.plus_size
        self.scale_val = 1.0

        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    @property
    def items(self):
        return filter(None, [self._main_item])

    @property
    def all_items(self):
        return filter(None, [self._main_item, self._focus_item, self._selection_item])

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

        font_size = self.font_size * self.scale_val
        _font = Font(self.font_name, font_size)
        self._main_item = self.paper.addHtmlText("+", (self.x,self.y), font=_font,
                    align=Align.HCenter|Align.VCenter, color=self.color)

        self.paper.addFocusable(self._main_item, self)
        # restore focus and selection
        if focused:
            self.set_focus(True)
        if selected:
            self.set_selected(True)


    def set_focus(self, focus):
        if focus:
            rect = self.paper.item_bounding_box(self._main_item)
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def set_selected(self, select):
        if select:
            rect = self.paper.item_bounding_box(self._main_item)
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def bounding_box(self):
        if self._main_item:
            return self.paper.item_bounding_box(self._main_item)
        d = self.font_size/2 * self.scale_val
        return self.x-d, self.y-d, self.x+d, self.y+d

    def set_pos(self, x, y):
        self.x, self.y = x, y

    def move_by(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.scale_val *= scale

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def transform_3D(self, tr):
        self.x, self.y, z = tr.transform(self.x, self.y, 0)

#---------------------------- END PLUS ----------------------------------



