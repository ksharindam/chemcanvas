from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem


class DrawableObject:
    obj_type = 'Drawable' # the object type name (e.g - Atom, Bond, Arrow etc)
    focus_priority = 1 # smaller number have higer priority

    def __init__(self):
        # main graphics item, used to track focus.
        self.graphics_item = None # To remove this item use only Paper.removeObject()

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
        """ draw only the item. Does not clear previous drawings.
        Use only for first time drawing an object."""
        pass

    def redraw(self):
        """ clears prev drawing, focus, selection. Then draws object,
        and restore focus and selection. Use it for subsequent drawing """
        pass

    def clearDrawings(self):
        """ clears drawing and unfocus and deselect itself"""
        pass

    def boundingBox(self):
        """ bounding box of all graphics items return as [x1,x2,y1,y2]"""
        return None
