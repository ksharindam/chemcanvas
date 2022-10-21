from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem


class DrawableObject:
    obj_type = 'Drawable' # the object type name (e.g - Atom, Bond, Arrow etc)
    focus_priority = 1 # smaller number have higer priority

    def __init__(self):
        self.graphics_item = None # main graphics item, used to track focus

    @property
    def parent(self):
        return self

    @property
    def children(self):
        return [self]

    def setItemColor(self, item, color):
        pen = item.pen()
        pen.setColor(color)
        item.setPen(pen)

    def draw(self):
        pass

    def redraw(self):
        pass

    def clearDrawings(self):
        pass

    def boundingBox(self):
        pass
