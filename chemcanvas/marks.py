# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject, Color
from app_data import Settings
import geometry as geo
from common import float_to_str

class Mark(DrawableObject):
    meta__undo_properties = ("x", "y", "size")
    meta__scalables = ("x", "y", "size")

    focus_priority = 2
    redraw_priority = 4
    is_toplevel = False

    def __init__(self):
        DrawableObject.__init__(self)
        self.atom = None
        self.x, self.y = 0,0
        self.size = 6

    @property
    def parent(self):
        return self.atom

    def boundingBox(self):
        r = self.size/2
        return [self.x-r, self.y-r, self.x+r, self.y+r]

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

    def scale(self, scale):
        self.size *= scale

    def add_attributes_to_xml_node(self, elm):
        elm.setAttribute("x", float_to_str(self.x))
        elm.setAttribute("y", float_to_str(self.y))
        elm.setAttribute("size", float_to_str(self.size))

    def readXml(self, elm):
        x = elm.getAttribute("x")
        y = elm.getAttribute("y")
        if x and y:
            self.x, self.y = float(x), float(y)
        size = elm.getAttribute("size")
        if size:
            self.size = float(size)


class Charge(Mark):
    """ Represents various types of charge on atom, eg - +ve, -ve, 2+, 3-, δ+, δδ+ etc """
    meta__undo_properties = Mark.meta__undo_properties + ("type", "count")

    def __init__(self):
        Mark.__init__(self)
        self.type = "plus"# vals are : plus, minus, (in future : δ+, δ-)
        self.count = 1 # 2 for 2+, 2-, double delta -
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def items(self):
        return filter(None, self._main_items+[self._focus_item, self._selection_item])

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
        self._main_items = getattr(self, "_draw_%s_on_paper"%self.type)(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        getattr(self, "_draw_%s_on_paper"%self.type)(paper)

    def _draw_plus_on_paper(self, paper):
        x,y,s = self.x, self.y, self.size/2
        item1 = paper.addLine([x-s, y, x+s, y])
        item2 = paper.addLine([x, y-s, x, y+s])
        return [item1, item2]

    def _draw_minus_on_paper(self, paper):
        x,y,s = self.x, self.y, self.size/2
        return [paper.addLine([x-s, y, x+s, y])]


    def setFocus(self, focus):
        if focus:
            x,y,s = self.x, self.y, self.size/2+1
            self._focus_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        if selected:
            x,y,s = self.x, self.y, self.size/2+1
            self._selection_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        else:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def moveBy(self, dx,dy):
        self.x, self.y = self.x+dx, self.y+dy

    def addToXmlNode(self, parent):
        elm = parent.ownerDocument.createElement("charge")
        Mark.add_attributes_to_xml_node(self, elm)
        elm.setAttribute("typ", self.type)
        elm.setAttribute("count", str(self.count))
        parent.appendChild(elm)
        return elm

    def readXml(self, elm):
        Mark.readXml(self, elm)
        type = elm.getAttribute("typ")
        if type:
            self.type = type
        count = elm.getAttribute("count")
        if count:
            self.count = int(count)


class Electron(Mark):
    """ represents lone pair or single electron """
    meta__undo_properties = Mark.meta__undo_properties + ("type",)
    meta__scalables = ("x", "y", "size", "radius")

    def __init__(self):
        Mark.__init__(self)
        self.type = "2" # 1 = single, 2 = pair
        self.radius = 1
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def items(self):
        return filter(None, self._main_items+[self._focus_item, self._selection_item])

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
        self._main_items = getattr(self, "_draw_%s_on_paper"%self.type)(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        getattr(self, "_draw_%s_on_paper"%self.type)(paper)

    def _draw_1_on_paper(self, paper):
        """ draw single electron """
        r, s = self.radius, self.size/2
        x,y = self.x, self.y
        return [paper.addEllipse([x-r,y-r,x+r,y+r], fill=Color.black)]

    def _draw_2_on_paper(self, paper):
        """ draw lone pair """
        r, d, s = self.radius, self.radius*1.5+0.5, self.size/2
        x1, y1, x2, y2 = self.atom.x, self.atom.y, self.x, self.y

        items = []
        for sign in (1,-1):
            x, y = geo.line_get_point_at_distance([x1, y1, x2, y2], sign*d)
            items.append( paper.addEllipse([x-r,y-r,x+r,y+r], fill=Color.black) )
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

    def moveBy(self, dx,dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.size *= scale
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


def create_mark_from_type(mark_type):
    if mark_type=="charge_plus":
        mark = Charge()
        mark.type = "plus"
    elif mark_type=="charge_minus":
        mark = Charge()
        mark.type = "minus"
    elif mark_type=="electron_single":
        mark = Electron()
        mark.type = "1"
    elif mark_type=="electron_pair":
        mark = Electron()
        mark.type = "2"
    else:
        raise ValueError("Can not create mark from invalid mark type")
    return mark

