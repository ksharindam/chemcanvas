# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>


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


# converts (r,g,b) or (r,g,b,a) color to html hex format
def hex_color(color):
    clr = '#'
    for x in color:
        clr += "%.2x" % x
    return clr

def hex_to_color(hexcolor):
    color = hexcolor.strip("#")
    return tuple(int(color[i:i+2],16) for i in range(0,len(hexcolor)-2,2))

# values are same as Qt.PenStyle
class PenStyle:
    no_line = 0
    solid = 1
    dashed = 2
    dotted = 3

# values are same as Qt.PenCapStyle
class LineCap:
    butt = 0x00
    square = 0x10
    round = 0x20

class Font:
    def __init__(self, name="Sans Serif", size=10):
        self.name = name# Family
        self.size = size# pixel size
        self.bold = False
        self.italic = False


# Subclass of this class are ...
# Molecule
#        |- Atom
#              |- Mark
#        |- Bond
#        |- Delocalization
# Plus
# Arrow
# Text
# Bracket

class DrawableObject:
    focus_priority = 10 # smaller number have higher priority
    redraw_priority = 10
    is_toplevel = True
    # undo helpers metadata
    meta__undo_properties = () # attribute that dont need coping, eg - int, string, bool etc
    meta__undo_copy = () # attributes that requires copying (e.g - list, set, dict)
    meta__undo_children_to_record = () # must be a list or set
    meta__same_objects = {}
    meta__scalables = ()# list of objects which are affected by scaling

    def __init__(self):
        self.paper = None
        self.color = (0,0,0)
        # Top level objects will have scale value, and children will
        # use their parent's scale value.
        #self.scale_val = 1.0 # must be implemented in subclasses

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
    def chemistry_items(self):
        """ items which are drawn while exporting to SVG"""
        return []

    @property
    def all_items(self):
        """ returns all graphics items """
        return []

    def draw(self):
        """ clears prev drawing, focus, selection. Then draws object, and restore focus and selection """
        pass

    def clear_drawings(self):
        """ clears drawing and unfocus and deselect itself"""
        pass

    def bounding_box(self):
        """ bounding box of all graphics items return as [x1,x2,y1,y2]
        reimplementation mandatory. required by ScaleTool """
        return None

    def transform(self, tr):
        """ 2D Transform coordinates of object (Atom, Plus, Text, Arrow, Bracket).
        Molecule, Bond and Mark has no effect of this """
        pass

    def transform_3D(self, tr):
        """ 3D Transform coordinates of object """
        pass

#   def scale(self, scale):
        """ changes the scale properties, such as scale_val """
#       pass

    def move_by(self, dx, dy):
        """ translate object coordinates by (dx,dy). (does not redraw)"""
        pass

    def mark_dirty(self):
        """ mark as redraw needed """
        if self.paper:
            self.paper.dirty_objects.add(self)

    def delete_from_paper(self):
        """ unfocus, deselect, unmap focusable, clear graphics"""
        if not self.paper:
            return
        if self in self.paper.dirty_objects:
            self.paper.dirty_objects.remove(self)
        self.paper.unfocusObject(self)
        self.paper.deselectObject(self)
        self.clear_drawings()
        if self.is_toplevel:
            self.paper.removeObject(self)


class Align:
    Left = 0x01
    Right = 0x02
    HCenter = 0x04
    Top = 0x20
    Bottom = 0x40
    VCenter = 0x80
    Baseline = 0x100# for text

