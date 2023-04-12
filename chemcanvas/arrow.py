
from drawable import DrawableObject
from app_data import Settings
from geometry import *

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsItemGroup

class Arrow(DrawableObject):
    object_type = "Arrow"

    def __init__(self):
        DrawableObject.__init__(self)
        self.type = "normal"#simple, resonance, retro, equililbrium
        self.points = [] # list of points that define the path, eg [(x1,y1), (x2,y2)]
        self._line_width = 2
        # length is the total length of head from left to right
        # width is half width, i.e from vertical center to top or bottom end
        # depth is how much deep the body is inserted to head, when depth=0 head becomes triangular
        self.head_dimensions = [12,5,4]# [length, width, depth]
        self.head = None
        # arrow can have multiple parts which receives focus
        self._main_items = []
        self._focus_item = None
        self._selection_item = None
        self._focusable_items = []


    def setPoints(self, points):
        self.points = list(points)

    def clearDrawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items = []
        self.head = None
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
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

        body = self.paper.addPolyline(points, width=self._line_width)
        points = double_sided_arrow_head(x1,y1, x2,y2, l, w, d)
        self.head = self.paper.addPolygon(points, fill=Qt.black)
        self._main_items = [body, self.head]
        [self.paper.addFocusable(item, self) for item in self._main_items]

    def _draw_equilibrium_simple(self):
        width = 3
        points = self.points[:]
        #polylines = []
        for i in range(2):
            points.reverse()# draw first reverse arrow, then forward arrow
            x1, y1, x2, y2 = Line(points[0] + points[1]).findParallel(width)
            xp, yp = Line([x1,y1,x2,y2]).elongate(-8)
            xp, yp = Line([x1,y1,xp,yp]).pointAtDistance(5)
            coords = [(x1,y1), (x2,y2), (xp,yp)]
            item = self.paper.addPolyline(coords)
            self.paper.addFocusable(item, self)
            self._main_items.append(item)

    def _draw_electron_shift(self):
        if len(self.points)==2:
            # for two points, this will be straight line
            a,c = self.points
            cp_x, cp_y = ((c[0]+a[0])/2, (c[1]+a[1])/2)
        else:
            a, b, c = self.points[:3]
            cp_x = 2*b[0] - 0.5*a[0] - 0.5*c[0]
            cp_y = 2*b[1] - 0.5*a[1] - 0.5*c[1]
        body = self.paper.addQuadBezier([a, (cp_x, cp_y), c])
        self.paper.addFocusable(body, self)
        # draw head
        l,w,d = 6,2.5,2#self.head_dimensions
        x2, y2 = Line([cp_x,cp_y,*c]).elongate(-l+d)
        points = double_sided_arrow_head(cp_x,cp_y, x2,y2, l, w, d)
        self.head = self.paper.addPolygon(points, fill=Qt.black)
        self.paper.addFocusable(self.head, self)
        self._main_items = [body, self.head]

    def setFocus(self, focus):
        if focus:
            width = 2*self.head_dimensions[1]
            self._focus_item = self.paper.addPolyline(self.points, width=width, color=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        elif self._focus_item:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            width = 2*self.head_dimensions[1]
            self._selection_item = self.paper.addPolyline(self.points, width=width, color=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def moveBy(self, dx, dy):
        self.points = [(pt[0]+dx,pt[1]+dy) for pt in self.points]
        items = filter(None, self._main_items + [self._focus_item, self._selection_item])
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

