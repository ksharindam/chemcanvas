# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject, Color, Font, Anchor
from app_data import Settings
import geometry as geo
from common import float_to_str, bbox_of_bboxes

class Mark(DrawableObject):
    # the stored 'color' property is not used actually, as it is inherited from atom.
    # but adding this is necessary to update marks color when undo and redoing.
    meta__undo_properties = ("rel_x", "rel_y", "size", "color")
    meta__scalables = ("rel_x", "rel_y", "size")

    focus_priority = 2
    redraw_priority = 4
    is_toplevel = False

    def __init__(self):
        DrawableObject.__init__(self)
        self.atom = None
        self.rel_x, self.rel_y = 0,0
        self.size = 6
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def parent(self):
        return self.atom

    def boundingBox(self):
        r = self.size/2
        return [self.x-r, self.y-r, self.x+r, self.y+r]

    @property
    def x(self):
        return self.atom.x + self.rel_x

    @property
    def y(self):
        return self.atom.y + self.rel_y

    def setPos(self, x, y):
        self.rel_x, self.rel_y = x-self.atom.x, y-self.atom.y

    def transform(self, tr):
        pass

    def moveBy(self, dx,dy):
        self.rel_x, self.rel_y = self.rel_x+dx, self.rel_y+dy

    def scale(self, scale):
        self.rel_x *= scale
        self.rel_y *= scale
        self.size *= scale

    @property
    def items(self):
        return self._main_items

    @property
    def all_items(self):
        return filter(None, self._main_items+[self._focus_item, self._selection_item])

    def add_attributes_to_xml_node(self, elm):
        elm.setAttribute("rel_x", float_to_str(self.rel_x))
        elm.setAttribute("rel_y", float_to_str(self.rel_y))
        elm.setAttribute("size", float_to_str(self.size))

    def readXml(self, elm):
        x = elm.getAttribute("rel_x")
        y = elm.getAttribute("rel_y")
        if x and y:
            self.rel_x, self.rel_y = float(x), float(y)
        size = elm.getAttribute("size")
        if size:
            self.size = float(size)


class Charge(Mark):
    """ Represents various types of charge on atom, eg - +ve, -ve, 2+, 3-, δ+, 2δ+ etc """
    meta__undo_properties = Mark.meta__undo_properties + ("type", "value", "font_name", "font_size")

    meta__scalables = Mark.meta__scalables + ("font_size",)

    types = ("normal", "circled", "partial")

    def __init__(self):
        Mark.__init__(self)
        self.type = "normal"
        self.value = 1 # 2 for 2+, 2δ+ or -2 for 2- or 2δ-
        self.font_name = Settings.atom_font_name
        self.font_size = Settings.atom_font_size * 0.75
        self._focusable_item = None

    def setType(self, charge_type):
        self.type = charge_type

    def setValue(self, val):
        self.value = val

    def clearDrawings(self):
        for item in self._main_items:
            self.paper.removeItem(item)
        self._main_items = []
        if self._focusable_item:
            self.paper.removeFocusable(self._focusable_item)
            self._focusable_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()
        self.paper = self.atom.paper
        # draw
        self.color = self.atom.color
        getattr(self, "_draw_%s" % self.type)()
        self.paper.addFocusable(self._focusable_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)


    def _draw_normal(self):
        x,y = self.x, self.y
        text = self.value>0 and "+" or "−"# this minus charater is longer than hyphen
        count = abs(self.value)>1 and ("%i" % abs(self.value)) or ""
        text = count + text
        font = Font(self.font_name, self.font_size)
        item1 = self.paper.addHtmlText(text, (x,y), font=font, anchor=Anchor.HCenter|Anchor.VCenter)
        self._main_items = [item1]
        self._focusable_item = self.paper.addRect(self.paper.itemBoundingBox(item1), color=Color.transparent)


    def _draw_circled(self):
        x,y = self.x, self.y
        text = self.value>0 and "⊕" or "⊖"
        count = abs(self.value)>1 and ("%i" % abs(self.value)) or ""
        # ⊕ symbol in the font is smaller than +, so using increased font size
        font = Font(self.font_name, 1.33*self.font_size)
        if count:
            item1 = self.paper.addHtmlText(text, (x,y), font=font, anchor=Anchor.Left|Anchor.VCenter)
            font.size = self.font_size
            item2 = self.paper.addHtmlText(count, (x,y), font=font, anchor=Anchor.Right|Anchor.VCenter)
            self._main_items = [item1, item2]
        else:
            item1 = self.paper.addHtmlText(text, (x,y), font=font, anchor=Anchor.HCenter|Anchor.VCenter)
            self._main_items = [item1]
        bbox = bbox_of_bboxes([self.paper.itemBoundingBox(it) for it in self._main_items])
        self._focusable_item = self.paper.addRect(bbox, color=Color.transparent)


    def _draw_partial(self):
        x,y = self.x, self.y
        text = self.value>0 and "δ+" or "δ−"
        count = abs(self.value)>1 and ("%i" % abs(self.value)) or ""
        text = count + text
        font = Font(self.font_name, self.font_size)
        item1 = self.paper.addHtmlText(text, (x,y), font=font, anchor=Anchor.HCenter|Anchor.VCenter)
        self._main_items = [item1]
        self._focusable_item = self.paper.addRect(self.paper.itemBoundingBox(item1), color=Color.transparent)



    def setFocus(self, focus):
        if focus:
            rect = self.paper.itemBoundingBox(self._focusable_item)
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        if selected:
            rect = self.paper.itemBoundingBox(self._focusable_item)
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None


    def scale(self, scale):
        Mark.scale(self, scale)
        self.font_size *= scale

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("charge")
        Mark.add_attributes_to_xml_node(self, elm)
        elm.setAttribute("typ", self.type)
        elm.setAttribute("val", str(self.value))
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        Mark.readXml(self, elm)
        type = elm.getAttribute("typ")
        if type:
            self.type = type
        val = elm.getAttribute("val")
        if val:
            self.value = int(val)


class Electron(Mark):
    """ represents lone pair or single electron """
    meta__undo_properties = Mark.meta__undo_properties + ("type", "radius")
    meta__scalables = Mark.meta__scalables + ("radius",)

    def __init__(self):
        Mark.__init__(self)
        self.type = "2" # 1 = single, 2 = pair
        self.radius = 1 # dot size

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
        self.paper = self.atom.paper
        # draw
        self.color = self.atom.color
        self._main_items = getattr(self, "_draw_%s"%self.type)()
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)


    def _draw_1(self):
        """ draw single electron """
        r = self.radius
        x,y = self.x, self.y
        return [self.paper.addEllipse([x-r,y-r,x+r,y+r], color=self.color, fill=self.color)]


    def _draw_2(self):
        """ draw lone pair """
        self.dot_distance = self.radius*1.5+0.5
        r, d = self.radius, self.dot_distance
        x1, y1, x2, y2 = self.atom.x, self.atom.y, self.x, self.y

        items = []
        for sign in (1,-1):
            x, y = geo.line_get_point_at_distance([x1, y1, x2, y2], sign*d)
            items.append( self.paper.addEllipse([x-r,y-r,x+r,y+r], color=self.color, fill=self.color) )
        return items


    def setFocus(self, focus):
        if focus:
            x,y,s = self.x, self.y, self.size+1
            self._focus_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        if selected:
            x,y,s = self.x, self.y, self.size+1
            self._selection_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def scale(self, scale):
        Mark.scale(self, scale)
        self.radius *= scale

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("electron")
        Mark.add_attributes_to_xml_node(self, elm)
        elm.setAttribute("type", self.type)
        elm.setAttribute("radius", float_to_str(self.radius))
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        Mark.readXml(self, elm)
        type = elm.getAttribute("type")
        if type:
            self.type = type
        radius = elm.getAttribute("radius")
        if radius:
            self.radius = float(radius)




