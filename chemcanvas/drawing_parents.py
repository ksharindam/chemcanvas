# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>


# any color is denoted by 3 or 4 member tuple (4th is alpha)
class Color:
    black = (0, 0, 0) #2
    white = (255, 255, 255) #3
    darkGray = (128, 128, 128) #4
    gray = (160, 160, 160) #5
    lightGray = (192, 192, 192) #6
    red = (255, 0, 0) #7
    green = (0, 255, 0) #8
    blue = (0, 0, 255) #9
    cyan = (0, 255, 255) #10
    magenta = (255, 0, 255) #11
    yellow = (255, 255, 0) #12
    darkRed = (128, 0, 0) #13
    darkGreen = (0, 128, 0) #14
    darkBlue = (0, 0, 128) #15
    darkCyan = (0, 128, 128) #16
    darkMagenta = (128, 0, 128) #17
    darkYellow = (128, 128, 0) #18
    transparent = (0,0,0,0) #19



class Font:
    def __init__(self, name="Sans Serif", size=10):
        self.name = name# Family
        self.size = size# point size
        self.bold = False
        self.italic = False


# Subclass of this class are ...
# Molecule, Atom, Bond, Mark, Plus, Arrow, Text

class DrawableObject:
    focus_priority = 10 # smaller number have higher priority
    redraw_priority = 10
    is_toplevel = True
    # undo helpers metadata
    meta__undo_properties = () # attribute that dont need coping, eg - int, string, bool etc
    meta__undo_copy = () # attributes that requires copying (e.g - list, set, dict)
    meta__undo_children_to_record = () # must be a list or set
    meta__same_objects = {}

    def __init__(self):
        self.paper = None

    @property
    def class_name(self):
        """ returns the class name """
        return self.__class__.__name__

    @property
    def parent(self):
        return None

    @property
    def children(self):
        return []

    @property
    def items(self):
        """ returns all graphics items """
        return []

    def draw(self):
        """ clears prev drawing, focus, selection. Then draws object, and restore focus and selection """
        pass

    def drawOnPaper(self, paper):
        """ draw on specified paper """
        pass

    def clearDrawings(self):
        """ clears drawing and unfocus and deselect itself"""
        pass

    def boundingBox(self):
        """ bounding box of all graphics items return as [x1,x2,y1,y2]
        reimplementation mandatory. required by ScaleTool """
        return None

#    def transform(self, tr):
#        pass

#   def scale(self, scale):
#       pass

    def moveBy(self, dx, dy):
        """ translate object coordinates by (dx,dy). (does not redraw)"""
        pass

    def deleteFromPaper(self):
        """ unfocus, deselect, unmap focusable, clear graphics"""
        if not self.paper:
            return
        self.paper.unfocusObject(self)
        self.paper.deselectObject(self)
        self.clearDrawings()
        if self.is_toplevel:
            self.paper.removeObject(self)


class Anchor:
    Left = 0x01
    Right = 0x02
    HCenter = 0x04
    Top = 0x20
    Bottom = 0x40
    VCenter = 0x80
    Baseline = 0x100# for text

class BasicPaper:
    """ The Drawing API of a Paper """
    def addLine(self, line, width=1, color=Color.black):
        pass

    # A stroked rectangle has a size of (rectangle size + pen width)
    def addRect(self, rect, width=1, color=Color.black, fill=None):
        pass

    def addPolygon(self, points, width=1, color=Color.black, fill=None):
        pass

    def addPolyline(self, points, width=1, color=Color.black):
        pass

    def addEllipse(self, rect, width=1, color=Color.black, fill=None):
        pass

    def addCubicBezier(self, points, width=1, color=Color.black):
        pass

    def addQuadBezier(self, points, width=1, color=Color.black):
        pass

    def addHtmlText(self, text, pos, font=None, anchor=Anchor.Left|Anchor.Baseline):
        """ Draw Html Text """
        pass

    def addChemicalFormula(self, formula, pos, anchor, font=None):
        """ draw chemical formula """
        pass
