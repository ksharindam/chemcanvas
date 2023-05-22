# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>
from app_data import App, Color
from undo_manager import UndoManager
from molecule import Molecule
from atom import Atom
import geometry

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsTextItem
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QPen, QBrush, QPolygonF, QPainterPath, QFontMetricsF, QFont

import re


class BasicPaper:
    AnchorLeft = 0x01
    AnchorRight = 0x02
    AnchorHCenter = 0x04
    AnchorTop = 0x20
    AnchorBottom = 0x40
    AnchorVCenter = 0x80
    AnchorBaseline = 0x100



class Paper(QGraphicsScene, BasicPaper):
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
        self.modifier_keys = set()
        self.gfx_item_dict = {} # maps graphics Items to object
        self.focused_obj = None
        self.selected_objs = []

        # QGraphicsTextItem has a margin on each side, precalculate this
        item = self.addText("")
        self.textitem_margin = item.boundingRect().width()/2
        self.removeItem(item)

        self.undo_manager = UndoManager(self)

    def objectsInRegion(self, x1,y1,x2,y2):
        """ get objects intersected by region rectangle"""
        gfx_items = self.items(QRectF(x1,y1, x2-x1,y2-y1))
        return [self.gfx_item_dict[itm] for itm in gfx_items if itm in self.gfx_item_dict]

    def addFocusable(self, graphics_item, obj):
        """ Add drawable objects, e.g bond, atom, arrow etc """
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
        key = ev.key()
        if key in key_name_map:
            key = key_name_map[key]
            text = ""
        elif ev.text():
            key = text = ev.text()
        else:
            return

        if key in ("Shift", "Ctrl", "Alt"):
            self.modifier_keys.add(key)
            return
        App.tool.onKeyPress(key, text)

    def keyReleaseEvent(self, ev):
        #print("key released", ev.key())
        try:
            key = key_name_map[ev.key()]
            if key in self.modifier_keys:
                self.modifier_keys.remove(key)
        except KeyError:
            return

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

    def addLine(self, line, width=1, color=Color.black):
        pen = QPen(color, width)
        return QGraphicsScene.addLine(self, *line, pen)

    # A stroked rectangle has a size of (rectangle size + pen width)
    def addRect(self, rect, width=1, color=Color.black, fill=QBrush()):
        x1,y1, x2,y2 = rect
        pen = QPen(color, width)
        return QGraphicsScene.addRect(self, x1,y1, x2-x1, y2-y1, pen, fill)

    def addPolygon(self, points, width=1, color=Color.black, fill=QBrush()):
        polygon = QPolygonF([QPointF(*p) for p in points])
        pen = QPen(color, width)
        return QGraphicsScene.addPolygon(self, polygon, pen, fill)

    def addPolyline(self, points, width=1, color=Color.black):
        shape = QPainterPath(QPointF(*points[0]))
        [shape.lineTo(*pt) for pt in points[1:]]
        pen = QPen(color, width)
        return QGraphicsScene.addPath(self, shape, pen)

    def addEllipse(self, rect, width=1, color=Color.black, fill=QBrush()):
        x1,y1, x2,y2 = rect
        pen = QPen(color, width)
        return QGraphicsScene.addEllipse(self, x1,y1, x2-x1, y2-y1, pen, fill)

    def addCubicBezier(self, points, width=1, color=Color.black):
        shape = QPainterPath(QPointF(*points[0]))
        shape.cubicTo(*points[1], *points[2], *points[3])
        pen = QPen(color, width)
        return QGraphicsScene.addPath(self, shape, pen)

    def addQuadBezier(self, points, width=1, color=Color.black):
        shape = QPainterPath(QPointF(*points[0]))
        shape.quadTo(*points[1], *points[2])
        pen = QPen(color, width)
        return QGraphicsScene.addPath(self, shape, pen)

    def addHtmlText(self, text, pos, font=None, anchor=BasicPaper.AnchorLeft|BasicPaper.AnchorBaseline):
        """ Draw Html Text """
        item = QGraphicsTextItem()
        if font:
            _font = QFont(font.name)
            _font.setPointSize(font.size)
            _font.setBold(font.bold)
            _font.setItalic(font.italic)
            item.setFont(_font)
        item.setHtml(text)
        self.addItem(item)

        font_metrics = QFontMetricsF(item.font())
        item_w = item.boundingRect().width()
        x, y = pos[0]-self.textitem_margin, pos[1]-self.textitem_margin
        w, h = item_w-2*self.textitem_margin, font_metrics.height()
        # horizontal alignment
        if anchor & self.AnchorHCenter:
            x -= w/2
            # text width must be set to enable html text-align property
            item.document().setTextWidth(item_w)
        elif anchor & self.AnchorRight:
            x -= w
            item.document().setTextWidth(item_w)
        # vertical alignment
        if anchor & self.AnchorBaseline:
            y -= font_metrics.ascent()
        elif anchor & self.AnchorBottom:
            y -= h
        elif anchor & self.AnchorVCenter:
            y -= h/2

        item.setPos(x,y)
        #item.setTabChangesFocus(False)
        return item

    def addChemicalFormula(self, formula, pos, anchor):
        """ draw chemical formula """
        text = html_formula(formula)# subscript the numbers
        item = QGraphicsTextItem()
        item.setHtml(text)
        self.addItem(item)
        item.margin = self.textitem_margin
        w, h = item.boundingRect().getCoords()[2:]
        x, y, w = pos[0]-item.margin, pos[1]-h/2, w-2*item.margin

        if anchor=="start":
            char_w = QFontMetricsF(item.font()).widthChar(text[0])
            x -= char_w/2
        elif anchor=="end":
            char_w = QFontMetricsF(item.font()).widthChar(text[-1])
            x -= w - char_w/2
        item.setPos(x,y)
        return item

    def setItemColor(self, item, color):
        pen = item.pen()
        pen.setColor(color)
        item.setPen(pen)

    def save_state_to_undo_stack(self, name=''):
        self.undo_manager.save_current_state(name)

    def undo(self):
        self.deselectAll()
        self.undo_manager.undo()

    def redo(self):
        self.deselectAll()
        self.undo_manager.redo()

    def addObject(self, obj):
        self.objects.append(obj)
        obj.paper = self

    def removeObject(self, obj):
        obj.paper = None
        self.objects.remove(obj)

    def moveItemsBy(self, items, dx, dy):
        [item.moveBy(dx, dy) for item in items]

    def itemBoundingBox(self, item):
        return item.sceneBoundingRect().getCoords()



key_name_map = {
    Qt.Key_Shift: "Shift",
    Qt.Key_Control: "Ctrl",
    Qt.Key_Alt: "Alt",
    Qt.Key_Escape: "Esc",
    Qt.Key_Tab: "Tab",
    Qt.Key_Backspace: "Backspace",
    Qt.Key_Insert: "Insert",
    Qt.Key_Delete: "Delete",
    Qt.Key_Home: "Home",
    Qt.Key_End: "End",
    Qt.Key_PageUp: "PageUp",
    Qt.Key_PageDown: "PageDown",
    Qt.Key_Left: "Left",
    Qt.Key_Right: "Right",
    Qt.Key_Up: "Up",
    Qt.Key_Down: "Down",
    Qt.Key_Return: "Return",
    Qt.Key_Enter: "Enter",# on numpad
}

subscript_text = lambda match_obj : "<sub>"+match_obj.group(0)+"</sub>"

def html_formula(formula):
    return re.sub("\d", subscript_text, formula)
