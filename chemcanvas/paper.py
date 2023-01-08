from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QGuiApplication, QPen

from app_data import App
from molecule import Molecule
from atom import Atom
import geometry



class Paper(QGraphicsScene):
    """ The canvas on which all items are drawn """
    def __init__(self, x,y,w,h, view):
        QGraphicsScene.__init__(self, x,y,w,h, view)
        view.setScene(self)
        view.setMouseTracking(True)

        self.molecules = []
        self.arrows = []
        self.texts = []
        self.shapes = []
        self.mouse_pressed = False
        self.dragging = False
        #self.modifer_keys = set()
        self.gfx_item_dict = {} # maps graphics Items to object
        self.focused_obj = None
        self.selected_objs = []

    def objectsInRegion(self, x,y,w,h):
        """ get objects intersected by region rectangle"""
        gfx_items = self.items(QRectF(x, y, w,h))
        return [self.gfx_item_dict[itm] for itm in gfx_items if itm in self.gfx_item_dict]

    def addObject(self, obj):
        """ Add drawable objects, e.g bond, atom, arrow etc """
        if obj.graphics_item:
            self.gfx_item_dict[obj.graphics_item] = obj

    def removeObject(self, obj):
        """ Remove drawable objects, e.g bond, atom, arrow etc """
        if obj.graphics_item in self.gfx_item_dict:
            self.gfx_item_dict.pop(obj.graphics_item)
        self.removeItem(obj.graphics_item)
        obj.graphics_item = None

    def mousePressEvent(self, ev):
        self.mouse_pressed = True
        self.dragging = False
        pos = ev.scenePos()
        self.mouse_press_pos = [pos.x(), pos.y()]
        App.tool.onMousePress(*self.mouse_press_pos)
        QGraphicsScene.mousePressEvent(self, ev)

    def mouseMoveEvent(self, ev):
        pos = ev.scenePos()
        x, y = pos.x(), pos.y()
        # to ignore slight movement while clicking mouse
        if self.mouse_pressed and not geometry.within_range([x,y], self.mouse_press_pos, 3):
            self.dragging = True

        # hover event
        drawables = App.paper.objectsInRegion(x-3, y-3, 7,7)
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

#    def keyPressEvent(self, ev):
#        print("key pressed")

#    def keyReleaseEvent(self, ev):
#        print("key released")

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

    def clearFocus(self):
        self.changeFocusTo(None)

    def selectObjects(self, objs):
        for obj in self.selected_objs:
            obj.setSelected(False)
        self.selected_objs = objs
        for obj in self.selected_objs:
            obj.setSelected(True)

    def clearSelection(self):
        self.selectObjects([])

    def newMolecule(self):
        mol = Molecule(self)
        self.molecules.append(mol)
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
    def addRect(self, x,y,w,h, width=1, color=Qt.black):
        pen = QPen(color, width)
        return QGraphicsScene.addRect(self, x,y,w,h, pen)

    def addEllipse(self, x, y, w, h, width=1, color=Qt.black):
        pen = QPen(color, width)
        return QGraphicsScene.addEllipse(self, x,y,w,h, pen)

    def addFormulaText(self, formula, pos):
        item = QGraphicsScene.addSimpleText(self, formula)
        rect = item.boundingRect()
        item.setPos(pos[0]-rect.width()/2, pos[1]-rect.height()/2)
        return item

