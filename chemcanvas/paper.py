from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QTransform

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
        self.gfx_item_dict = {} # maps graphics Items to object
        self.focused_obj = None

    def mousePressEvent(self, ev):
        self.mouse_pressed = True
        self.dragging = False
        self.mouse_press_pos = ev.scenePos().toPoint()
        App.tool.onMousePress(self.mouse_press_pos)
        QGraphicsScene.mousePressEvent(self, ev)

    def mouseMoveEvent(self, ev):
        pos = ev.scenePos().toPoint()
        # slight movement while clicking mouse is ignored
        if self.mouse_pressed and not geometry.within_range(pos, self.mouse_press_pos, 3):
            self.dragging = True

        # hover event
        gfx_items = self.items(QRectF(pos.x()-3, pos.y()-3, 7,7))
        drawables = [self.gfx_item_dict[x] for x in gfx_items if x in self.gfx_item_dict]
        drawables = sorted(drawables, key=lambda obj : obj.focus_priority)
        focused_obj = drawables[0] if len(drawables) else None


        if self.focused_obj is not focused_obj:
            # focus is changed, remove focus from prev item and set focus to new item
            if self.focused_obj:
                self.focused_obj.setFocus(False)
            if focused_obj:
                focused_obj.setFocus(True)
            self.focused_obj = focused_obj

        App.tool.onMouseMove(pos)
        QGraphicsScene.mouseMoveEvent(self, ev)

    def mouseReleaseEvent(self, ev):
        if self.mouse_pressed:
            self.mouse_pressed = False
            App.tool.onMouseRelease(ev.scenePos().toPoint())
            self.dragging = False
        QGraphicsScene.mouseReleaseEvent(self, ev)

    def newMolecule(self):
        mol = Molecule(self)
        self.molecules.append(mol)
        return mol

    def addDrawable(self, obj):
        """ Add drawable objects, e.g bond, atom, arrow etc """
        if obj.graphics_item:
            self.gfx_item_dict[obj.graphics_item] = obj

    def removeDrawable(self, obj):
        """ Remove drawable objects, e.g bond, atom, arrow etc """
        if obj.graphics_item in self.gfx_item_dict:
            self.gfx_item_dict.pop(obj.graphics_item)
        self.removeItem(obj.graphics_item)
        obj.graphics_item = None

    '''def toForeground(self, item):
        item.graphics_item.setZValue(1)

    def toBackground(self, item):
        item.graphics_item.setZValue(-1)'''

    def touchedAtom(self, atom):
        items = self.items(QRectF(atom.x-3, atom.y-3, 7,7))
        for item in items:
            obj = self.gfx_item_dict[item] if item in self.gfx_item_dict else None
            if type(obj) is Atom and obj is not atom:
                return obj
        return None

    def setItemColor(self, item, color):
        pen = item.pen()
        pen.setColor(color)
        item.setPen(pen)

