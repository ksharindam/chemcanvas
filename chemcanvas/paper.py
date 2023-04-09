from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsTextItem
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QPen, QBrush, QPolygonF, QPainterPath, QFontMetricsF

from app_data import App
from undo_manager import UndoManager
from molecule import Molecule
from atom import Atom
import geometry



class Paper(QGraphicsScene):
    """ The canvas on which all items are drawn """
    def __init__(self, x,y,w,h, view):
        QGraphicsScene.__init__(self, x,y,w,h, view)
        view.setScene(self)
        view.setMouseTracking(True)

        self.objects = []
        self.arrows = []
        self.texts = []
        self.shapes = []
        self.mouse_pressed = False
        self.dragging = False
        #self.modifer_keys = set()
        self.gfx_item_dict = {} # maps graphics Items to object
        self.focused_obj = None
        self.selected_objs = []

        self.undo_manager = UndoManager(self)

    def objectsInRegion(self, x1,y1,x2,y2):
        """ get objects intersected by region rectangle"""
        gfx_items = self.items(QRectF(x1,y1, x2-x1,y2-y1))
        return [self.gfx_item_dict[itm] for itm in gfx_items if itm in self.gfx_item_dict]

    def addFocusable(self, graphics_item, obj):
        """ Add drawable objects, e.g bond, atom, arrow etc """
        if graphics_item:
            self.gfx_item_dict[graphics_item] = obj

    def removeFocusable(self, graphics_item):
        """ Remove drawable objects, e.g bond, atom, arrow etc """
        if graphics_item in self.gfx_item_dict:
            self.gfx_item_dict.pop(graphics_item)

    def mousePressEvent(self, ev):
        self.mouse_pressed = True
        self.dragging = False
        pos = ev.scenePos()
        self.mouse_press_pos = (pos.x(), pos.y())
        App.tool.onMousePress(*self.mouse_press_pos)
        QGraphicsScene.mousePressEvent(self, ev)

    def mouseMoveEvent(self, ev):
        pos = ev.scenePos()
        x, y = pos.x(), pos.y()

        if self.mouse_pressed and not self.dragging:
            # to ignore slight movement while clicking mouse
            if not geometry.within_range([x,y], self.mouse_press_pos, 3):
                self.dragging = True

        # hover event
        if not self.mouse_pressed or self.dragging:
            drawables = App.paper.objectsInRegion(x-3, y-3, x+3,y+3)
            drawables = sorted(drawables, key=lambda obj : obj.focus_priority) # making atom higher priority than bonds
            focused_obj = drawables[0] if len(drawables) else None
            self.changeFocusTo(focused_obj)

        App.tool.onMouseMove(x, y)
        QGraphicsScene.mouseMoveEvent(self, ev)

    def mouseReleaseEvent(self, ev):
        if self.mouse_pressed:
            self.mouse_pressed = False
            pos = ev.scenePos()
            App.tool.onMouseRelease(pos.x(), pos.y())
            self.dragging = False
        QGraphicsScene.mouseReleaseEvent(self, ev)

    def keyPressEvent(self, ev):
        print("key pressed", ev.key())
        if ev.key()==Qt.Key_Delete and App.tool.name=="MoveTool":
            App.tool.deleteSelected()

    def keyReleaseEvent(self, ev):
        print("key released", ev.key())

    # to remove focus, None should be passed as argument
    def changeFocusTo(self, focused_obj):
        if self.focused_obj is focused_obj:
            return
        # focus is changed, remove focus from prev item and set focus to new item
        if self.focused_obj:
            self.focused_obj.setFocus(False)
        if focused_obj:
            focused_obj.setFocus(True)
        self.focused_obj = focused_obj

    def unfocusObject(self, obj):
        if obj is self.focused_obj:
            obj.setFocus(False)
            self.focused_obj = None

    def selectObject(self, obj):
        if obj not in self.selected_objs:
            obj.setSelected(True)
            self.selected_objs.append(obj)

    def deselectObject(self, obj):
        if obj in self.selected_objs:
            obj.setSelected(False)
            self.selected_objs.remove(obj)

    def deselectAll(self):
        for obj in self.selected_objs:
            obj.setSelected(False)
        self.selected_objs = []

    def newMolecule(self):
        mol = Molecule(self)
        self.objects.append(mol)
        return mol

    def toForeground(self, item):
        item.setZValue(1)

    def toBackground(self, item):
        item.setZValue(-1)

    def touchedAtom(self, atom):
        items = self.items(QRectF(atom.x-3, atom.y-3, 7,7))
        for item in items:
            obj = self.gfx_item_dict[item] if item in self.gfx_item_dict else None
            if type(obj) is Atom and obj is not atom:
                return obj
        return None

    def addLine(self, line, width=1, color=Qt.black):
        pen = QPen(color, width)
        return QGraphicsScene.addLine(self, *line, pen)

    # A stroked rectangle has a size of (rectangle size + pen width)
    def addRect(self, rect, width=1, color=Qt.black, fill=QBrush()):
        x1,y1, x2,y2 = rect
        pen = QPen(color, width)
        return QGraphicsScene.addRect(self, x1,y1, x2-x1, y2-y1, pen, fill)

    def addPolygon(self, points, width=1, color=Qt.black, fill=QBrush()):
        polygon = QPolygonF([QPointF(*p) for p in points])
        pen = QPen(color, width)
        return QGraphicsScene.addPolygon(self, polygon, pen, fill)

    def addPolyline(self, points, width=1, color=Qt.black):
        shape = QPainterPath(QPointF(*points[0]))
        [shape.lineTo(*pt) for pt in points]
        pen = QPen(color, width)
        return QGraphicsScene.addPath(self, shape, pen)

    def addEllipse(self, rect, width=1, color=Qt.black, fill=QBrush()):
        x1,y1, x2,y2 = rect
        pen = QPen(color, width)
        return QGraphicsScene.addEllipse(self, x1,y1, x2-x1, y2-y1, pen, fill)


    def addHtmlText(self, text, pos, alignment=0):
        """ formatted text """
        item = QGraphicsTextItem()
        item.setHtml(text)
        self.addItem(item)
        w,h = item.boundingRect().getCoords()[2:]
        font_metrics = QFontMetricsF(item.font())
        margin = (h-font_metrics.height())/2
        char_w = font_metrics.widthChar(text[alignment])/2
        if not alignment:
            item.setPos(pos[0]-margin-char_w, pos[1]-h/2)
        else:# center last letter
            item.setPos(pos[0]+margin+char_w-w, pos[1]-h/2)
        return item

    def addCubicBezier(self, points, width=1, color=Qt.black):
        shape = QPainterPath(QPointF(*points[0]))
        shape.cubicTo(*points[1], *points[2], *points[3])
        pen = QPen(color, width)
        return QGraphicsScene.addPath(self, shape, pen)

    def addQuadBezier(self, points, width=1, color=Qt.black):
        shape = QPainterPath(QPointF(*points[0]))
        shape.quadTo(*points[1], *points[2])
        pen = QPen(color, width)
        return QGraphicsScene.addPath(self, shape, pen)

    def save_state_to_undo_stack(self, name=''):
        self.undo_manager.save_current_state(name)

    def undo(self):
        self.deselectAll()
        self.undo_manager.undo()

    def redo(self):
        self.deselectAll()
        self.undo_manager.redo()

    def getObjectsOfType(self, obj_type):
        return [o for o in self.objects if o.object_type==obj_type]

    def addObject(self, obj):
        self.objects.append(obj)
        obj.paper = self

    def removeObject(self, obj):
        obj.paper = None
        self.objects.remove(obj)
