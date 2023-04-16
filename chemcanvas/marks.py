from drawable import DrawableObject
from app_data import Settings
from geometry import *
from PyQt5.QtCore import Qt

class Mark(DrawableObject):
    object_type = 'Mark'
    focus_priority = 2
    is_toplevel = False

    def __init__(self):
        DrawableObject.__init__(self)
        self.atom = None
        self.size = 6

    @property
    def parent(self):
        return self.atom


class Plus(Mark):
    object_type = 'Plus'
    def __init__(self):
        Mark.__init__(self)
        self.x, self.y = 0,0
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    @property
    def pos(self):
        return self.x, self.y

    def setPos(self, x,y):
        self.x = x
        self.y = y

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
        x,y,s = self.x, self.y, self.size/2
        item1 = self.paper.addLine([x-s, y, x+s, y])
        item2 = self.paper.addLine([x, y-s, x, y+s])
        self._main_items = [item1, item2]
        self.paper.addFocusable(item1, self)
        self.paper.addFocusable(item2, self)
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            x,y,s = self.x, self.y, self.size/2+1
            self._focus_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        pass

    def moveBy(self, dx,dy):
        self.x, self.y = self.x+dx, self.y+dy
        items = filter(None, self._main_items+[self._focus_item, self._selection_item])
        [item.moveBy(dx,dy) for item in items]


class Minus(Mark):
    object_type = 'Minus'
    def __init__(self):
        Mark.__init__(self)
        self.x, self.y = 0,0
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    @property
    def pos(self):
        return self.x, self.y

    def setPos(self, x,y):
        self.x = x
        self.y = y

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
        x,y,s = self.x, self.y, self.size/2
        self._main_item = self.paper.addLine([x-s, y, x+s, y])
        self.paper.addFocusable(self._main_item, self)
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            x,y,s = self.x, self.y, self.size/2+1
            self._focus_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        pass

    def moveBy(self, dx,dy):
        self.x, self.y = self.x+dx, self.y+dy
        items = filter(None, [self._main_item, self._focus_item, self._selection_item])
        [item.moveBy(dx,dy) for item in items]


class LonePair(Mark):
    object_type = 'LonePair'
    def __init__(self):
        Mark.__init__(self)
        self.x, self.y = 0,0
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
        r, d, s = self.radius, self.radius*1.5+0.5, self.size/2
        x1, y1, x2, y2 = self.atom.x, self.atom.y, self.x, self.y

        for sign in (1,-1):
            x, y = Line([x1, y1, x2, y2]).pointAtDistance(sign*d)
            self._main_items.append(self.paper.addEllipse([x-r,y-r,x+r,y+r], fill=Qt.black))
        [self.paper.addFocusable(item, self) for item in self._main_items]
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            x,y,s = self.x, self.y, self.size+1
            self._focus_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        pass

    def moveBy(self, dx,dy):
        self.x, self.y = self.x+dx, self.y+dy
        self.draw()

class SingleElectron(Mark):
    object_type = 'SingleElectron'
    def __init__(self):
        Mark.__init__(self)
        self.x, self.y = 0,0
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
        r, s = self.radius, self.size/2
        x,y = self.x, self.y

        self._main_item = self.paper.addEllipse([x-r,y-r,x+r,y+r], fill=Qt.black)
        self.paper.addFocusable(self._main_item, self)
        # restore focus and selection
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            x,y,s = self.x, self.y, self.size+1
            self._focus_item = self.paper.addRect([x-s,y-s,x+s,y+s], fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        pass

    def moveBy(self, dx,dy):
        self.x, self.y = self.x+dx, self.y+dy
        self.draw()


mark_class = {
    "Plus" : Plus,
    "Minus" : Minus,
    "LonePair" : LonePair,
    "SingleElectron" : SingleElectron,
}
