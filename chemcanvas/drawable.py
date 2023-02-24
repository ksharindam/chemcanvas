from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem


class DrawableObject:
    object_type = 'Drawable' # the object type name (e.g - Atom, Bond, Arrow etc)
    focus_priority = 10 # smaller number have higer priority
    redraw_priority = 10
    # undo helpers metadata
    meta__undo_properties = () # attribute that dont need coping, eg - int, string, bool etc
    meta__undo_copy = () # attributes that requires copying (e.g - list, set, dict)
    meta__undo_children_to_record = () # must be a list or set
    meta__same_objects = {}

    def __init__(self):
        # main graphics item, used to track focus.
        self.graphics_item = None
        self.paper = None

    @property
    def parent(self):
        return self

    @property
    def children(self):
        return [self] # why we need self as children ???

    def setItemColor(self, item, color):
        pen = item.pen()
        pen.setColor(color)
        item.setPen(pen)

    def draw(self):
        """ clears prev drawing, focus, selection. Then draws object, and restore focus and selection """
        pass

    def drawSelfAndChildren(self):
        self.draw()

    def clearDrawings(self):
        """ clears drawing and unfocus and deselect itself"""
        pass

    def boundingBox(self):
        """ bounding box of all graphics items return as [x1,x2,y1,y2]"""
        return None

    def deleteFromPaper(self):
        """ unfocus, deselect, unmap focusable, clear graphics"""
        if not self.paper:
            return
        self.paper.unfocusObject(self)
        self.paper.deselectObject(self)
        self.clearDrawings()
