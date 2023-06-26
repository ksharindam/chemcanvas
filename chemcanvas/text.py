# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject, Font, Anchor
from app_data import Settings

from common import float_to_str


# ---------------------------- TEXT --------------------------------

class Text(DrawableObject):
    meta__undo_properties = ("x", "y", "text", "font_name", "font_size")
    meta__undo_copy = ("_formatted_text_parts",)
    meta__scalables = ("x", "y", "font_size")

    def __init__(self):
        DrawableObject.__init__(self)
        #self.paper = None # inherited
        self.x = 0
        self.y = 0
        self.text = ""
        self.font_name = "Sans Serif"
        self.font_size = Settings.text_size
        self._formatted_text_parts = []
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    def setText(self, text):
        self.text = text
        self._formatted_text_parts = []

    def append(self, char):
        self.text += char
        self._formatted_text_parts = []

    def deleteLastChar(self):
        if self.text:
            self.text = self.text[:-1]
        self._formatted_text_parts = []

    @property
    def items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def clearDrawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items.clear()
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()

        self._main_items = self.drawOnPaper(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        if not self._formatted_text_parts:
            # TODO : convert < and > to ;lt and ;gt
            self._formatted_text_parts = ["<br>".join(self.text.split('\n'))]

        _font = Font(self.font_name, self.font_size)
        line_spacing = self.font_size
        x, y = self.x, self.y
        items = []
        for text_part in self._formatted_text_parts:
            if text_part:
                item = paper.addHtmlText(text_part, (x,y), font=_font)
                items.append(item)
            y += line_spacing
        return items


    def setFocus(self, focus):
        if focus:
            rect = self.paper.itemBoundingBox(self._main_items[0])
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            rect = self.paper.itemBoundingBox(self._main_items[0])
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def boundingBox(self):
        if self._main_items:
            return self.paper.itemBoundingBox(self._main_items[0])
        return self.x, self.y-self.font_size, self.x+font_size, self.y # TODO : need replacement

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.font_size *= scale

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("text")
        elm.setAttribute("x", float_to_str(self.x))
        elm.setAttribute("y", float_to_str(self.y))
        elm.setAttribute("text", self.text)
        elm.setAttribute("font", self.font_name)
        elm.setAttribute("size", float_to_str(self.font_size))
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        x = elm.getAttribute("x")
        y = elm.getAttribute("y")
        if x and y:
            self.x, self.y = float(x), float(y)
        text = elm.getAttribute("text")
        if text:
            self.text = text
        font_name = elm.getAttribute("font")
        font_size = elm.getAttribute("size")
        if font_name and font_size:
            self.font_name = font_name
            self.font_size = float(font_size)

#---------------------------- END TEXT ----------------------------------


#------------------------------- PLUS --------------------------------

class Plus(DrawableObject):
    meta__undo_properties = ("x", "y", "font_size")
    meta__scalables = ("x", "y", "font_size")

    def __init__(self):
        DrawableObject.__init__(self)
        #self.paper = None # inherited
        self.x = 0
        self.y = 0
        self.font_name = Settings.atom_font_name
        self.font_size = Settings.plus_size
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    @property
    def items(self):
        return filter(None, [self._main_item, self._focus_item, self._selection_item])

    def clearDrawings(self):
        if self._main_item:
            self.paper.removeFocusable(self._main_item)
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()

        self._main_item = self.drawOnPaper(self.paper)
        self.paper.addFocusable(self._main_item, self)
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        _font = Font(self.font_name, self.font_size)
        return paper.addHtmlText("+", (self.x,self.y), font=_font,
                    anchor = Anchor.HCenter|Anchor.VCenter)


    def setFocus(self, focus):
        if focus:
            rect = self.paper.itemBoundingBox(self._main_item)
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            rect = self.paper.itemBoundingBox(self._main_item)
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def boundingBox(self):
        if self._main_item:
            return self.paper.itemBoundingBox(self._main_item)
        d = self.font_size/2
        return self.x-d, self.y-d, self.x+d, self.y+d

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.font_size *= scale

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("plus")
        elm.setAttribute("x", float_to_str(self.x))
        elm.setAttribute("y", float_to_str(self.y))
        elm.setAttribute("font_size", float_to_str(self.font_size))
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        x = elm.getAttribute("x")
        y = elm.getAttribute("y")
        if x and y:
            self.x, self.y = float(x), float(y)
        font_size = elm.getAttribute("font_size")
        if font_size:
            self.font_size = float(font_size)

#---------------------------- END PLUS ----------------------------------



