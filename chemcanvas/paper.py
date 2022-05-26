from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QTransform

from molecule import Molecule


class Paper(QGraphicsScene):
    def __init__(self, x,y,w,h, view):
        QGraphicsScene.__init__(self, x,y,w,h, view)
        view.setScene(self)
        view.setMouseTracking(True)

        self.molecules = []
        self.arrows = []
        self.texts = []
        self.shapes = []
        self.mouse_pressed = False
        self.gfx_item_dict = {}
        self.obj_on_focus = None

    def setTool(self, tool):
        self._tool = tool

    def mousePressEvent(self, ev):
        self.mouse_pressed = True
        self.mouse_press_pos = ev.scenePos().toPoint()
        self._tool.onMousePress(self.mouse_press_pos)
        QGraphicsScene.mousePressEvent(self, ev)

    def mouseMoveEvent(self, ev):
        pos = ev.scenePos().toPoint()
        if not self.mouse_pressed:

            gfx_item = self.itemAt(pos, QTransform()) # get at exact postion
            if not gfx_item: # get items near mouse cursor
                gfx_items = self.items(QRectF(pos.x()-3, pos.y()-3, 7,7))
                gfx_item = gfx_items[0] if len(gfx_items) else 0

            if gfx_item:
                if self.obj_on_focus:
                    if gfx_item is self.obj_on_focus.graphics_item:# cursor on prev obj, nothing to do
                        return
                    # remove focus from prev obj
                    self.obj_on_focus.setFocus(False)
                # set focus to new obj
                self.obj_on_focus = self.gfx_item_dict[gfx_item]
                self.obj_on_focus.setFocus(True)
            # cursor moved to blank position
            elif self.obj_on_focus:
                self.obj_on_focus.setFocus(False)
                self.obj_on_focus = None

            return
        self._tool.onMouseMove(pos)
        QGraphicsScene.mouseMoveEvent(self, ev)

    def mouseReleaseEvent(self, ev):
        if self.mouse_pressed:
            self.mouse_pressed = False
            self._tool.onMouseRelease(ev.scenePos().toPoint())
        QGraphicsScene.mouseReleaseEvent(self, ev)

    def newMolecule(self):
        mol = Molecule(self)
        self.molecules.append(mol)
        return mol

    def addDrawable(self, obj):
        """ Add drawable objects, e.g bond, atom, arrow etc """
        graphics_item = obj.graphicsItem()
        self.gfx_item_dict[graphics_item] = obj
        self.addItem(graphics_item)


