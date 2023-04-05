from app_data import Settings
from PyQt5.QtCore import QRectF, Qt, QPoint
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsItemGroup
from geometry import *


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
        self.paper = None

    @property
    def parent(self):
        return None

    @property
    def children(self):
        return []

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


class Plus(DrawableObject):
    def __init__(self):
        DrawableObject.__init__(self)
        self.paper = None
        self.x = 0
        self.y = 0
        self.font_size = Settings.plus_size
        self._main_item = None
        self._focus_item = None
        self._select_item = None

    def setPos(self, x, y):
        self.x = x
        self.y = y

    def clearDrawings(self):
        if self._main_item:
            self.paper.removeFocusable(self._main_item)
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._select_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._select_item)
        self.clearDrawings()
        font = self.paper.font()
        font.setPointSize(self.font_size)
        self._main_item = self.paper.addText("+", font)
        rect = self._main_item.boundingRect()
        self._main_item.setPos(self.x-rect.width()/2, self.y-rect.height()/2)
        self.paper.addFocusable(self._main_item, self)
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            rect = self._main_item.sceneBoundingRect().getCoords()
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        pass

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy
        items = filter(None, [self._main_item, self._focus_item, self._select_item])
        [item.moveBy(dx,dy) for item in items]


class Arrow(DrawableObject):
    object_type = "Arrow"

    def __init__(self):
        DrawableObject.__init__(self)
        self.type = "normal"#simple, resonance, retro, equililbrium
        self.points = [] # list of points that define the path, eg [(x1,y1), (x2,y2)]
        # length is the total length of head from left to right
        # width is half width, i.e from vertical center to top or bottom end
        # depth is how much deep the body is inserted to head, when depth=0 head becomes triangular
        self._line_width = 2
        self.head_dimensions = [12,5,4]# [length, width, depth]
        self.body = None
        self.head = None
        self._main_item = None
        self._focus_item = None
        self._select_item = None


    def setPoints(self, points):
        self.points = list(points)

    def clearDrawings(self):
        if self._main_item:
            self.paper.removeFocusable(self.body)
            self.paper.removeFocusable(self.head)
            self.paper.removeItem(self._main_item)
            self._main_item = None
            self.head = None
            self.body = None
        if self._focus_item:
            self.setFocus(False)
        if self._select_item:
            self.setSelected(False)

    def headBoundingBox(self):
        if self.head:
            return self.head.sceneBoundingRect().getCoords()
        else:
            w = self.head_dimensions[1]
            x,y = self.points[-1]
            return [x-w, y-w, x+w, y+w]

    def draw(self):
        focused = bool(self._focus_item)
        self.clearDrawings()
        getattr(self, "_draw_"+self.type)()
        if focused:
            self.setFocus(True)

    def _draw_normal(self):
        l,w,d = self.head_dimensions
        points = self.points[:]
        x1, y1 = points[-2]
        x2, y2 = points[-1]
        x2, y2 = Line([x1,y1,x2,y2]).elongate(-l+d)

        points[-1] = [x2, y2]

        self.body = self.paper.addPolyline(points, width=self._line_width)
        points = double_sided_arrow_head(x1,y1, x2,y2, l, w, d)
        self.head = self.paper.addPolygon(points, fill=Qt.black)
        self._main_item = self.paper.createItemGroup([self.body,self.head])
        self.paper.addFocusable(self.body, self)
        self.paper.addFocusable(self.head, self)

    def _draw_equilibrium_simple(self):
        width = 3
        points = self.points[:]
        polylines = []
        for i in range(2):
            points.reverse()# draw first reverse arrow, then forward arrow
            x1, y1, x2, y2 = Line(points[0] + points[1]).findParallel(width)
            xp, yp = Line([x1,y1,x2,y2]).elongate(-8)
            xp, yp = Line([x1,y1,xp,yp]).pointAtDistance(5)
            coords = [(x1,y1), (x2,y2), (xp,yp)]
            polylines.append(self.paper.addPolyline(coords))
        self._main_item = self.paper.createItemGroup(polylines)
        self.paper.addFocusable(self._main_item, self)

    def setFocus(self, focus):
        if focus:
            width = 2*self.head_dimensions[1]
            self._focus_item = self.paper.addPolyline(self.points, width=width, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        elif self._focus_item:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, selected):
        print("select arrow :", selected)

    def moveBy(self, dx, dy):
        self.points = [(pt[0]+dx,pt[1]+dy) for pt in self.points]
        items = filter(None, [self._main_item, self._focus_item, self._select_item])
        [item.moveBy(dx,dy) for item in items]


def double_sided_arrow_head (x1,y1,x2,y2, l,w,d):
    ''' x1,y1 is the point of arrow tail
    x2,y2 is the point where arrow head is connected
    l=length, w=width, d=depth'''
    line1 = Line([x1,y1,x2,y2])
    xc,yc = line1.elongate(l-d)# sharp end
    xp,yp = line1.elongate(-d)
    line2 = Line([x1,y1,xp,yp])
    xb,yb = line2.pointAtDistance(w)# side 1
    xd,yd = line2.pointAtDistance(-w)# side 2
    return (x2,y2), (xb,yb), (xc,yc), (xd,yd)

