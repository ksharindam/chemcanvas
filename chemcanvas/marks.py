# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from drawing_parents import DrawableObject, Color
from app_data import Settings
from geometry import *

class Mark(DrawableObject):
    meta__undo_properties = ("x", "y", "size")

    meta__scalables = ("x", "y", "size")

    focus_priority = 2
    focus_priority = 2
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


class PositiveCharge(Mark):
    def __init__(self):
        Mark.__init__(self)
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def pos(self):
        return self.x, self.y

    def setPos(self, x,y):
        self.x = x
        self.y = y

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
        self._main_items = self.drawOnPaper(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        x,y,s = self.x, self.y, self.size/2
        item1 = paper.addLine([x-s, y, x+s, y])
        item2 = paper.addLine([x, y-s, x, y+s])
        return [item1, item2]

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



class NegativeCharge(Mark):
    def __init__(self):
        Mark.__init__(self)
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    @property
    def pos(self):
        return self.x, self.y

    def setPos(self, x,y):
        self.x = x
        self.y = y

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
        self.paper = self.atom.paper
        # draw
        self._main_item = self.drawOnPaper(self.paper)
        self.paper.addFocusable(self._main_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        x,y,s = self.x, self.y, self.size/2
        return paper.addLine([x-s, y, x+s, y])

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


class LonePair(Mark):
    meta__scalables = ("x", "y", "size", "radius")

    def __init__(self):
        Mark.__init__(self)
        self.radius = 1
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def pos(self):
        return self.x, self.y

    def setPos(self, x,y):
        self.x = x
        self.y = y

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
        self._main_items = self.drawOnPaper(self.paper)
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        r, d, s = self.radius, self.radius*1.5+0.5, self.size/2
        x1, y1, x2, y2 = self.atom.x, self.atom.y, self.x, self.y

        items = []
        for sign in (1,-1):
            x, y = line_get_point_at_distance([x1, y1, x2, y2], sign*d)
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


class SingleElectron(Mark):
    meta__scalables = ("x", "y", "size", "radius")

    def __init__(self):
        Mark.__init__(self)
        self.radius = 1
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    @property
    def pos(self):
        return self.x, self.y

    def setPos(self, x,y):
        self.x = x
        self.y = y

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
        self.paper = self.atom.paper
        # draw
        self._main_item = self.drawOnPaper(self.paper)
        self.paper.addFocusable(self._main_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def drawOnPaper(self, paper):
        r, s = self.radius, self.size/2
        x,y = self.x, self.y
        return paper.addEllipse([x-r,y-r,x+r,y+r], fill=Color.black)

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

mark_class = {
    "PositiveCharge" : PositiveCharge,
    "NegativeCharge" : NegativeCharge,
    "LonePair" : LonePair,
    "SingleElectron" : SingleElectron,
}
