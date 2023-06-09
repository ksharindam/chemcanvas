# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>
from app_data import App, Color
from undo_manager import UndoManager
from molecule import Molecule
from atom import Atom
import geometry

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsTextItem
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QPainterPath, QFontMetricsF, QFont

import re


class BasicPaper:
    AnchorLeft = 0x01
    AnchorRight = 0x02
    AnchorHCenter = 0x04
    AnchorTop = 0x20
    AnchorBottom = 0x40
    AnchorVCenter = 0x80
    AnchorBaseline = 0x100


# Note :
# methods that are mentioned as "For Tool only", must be called from Tool only.
# And must not be called within itself. Because, it uses scaled coordinates.


class Paper(QGraphicsScene, BasicPaper):
    """ The canvas on which all items are drawn """
    def __init__(self, x,y,w,h, view):
        QGraphicsScene.__init__(self, x,y,w,h, view)
        view.setScene(self)
        view.setMouseTracking(True)

        self.objects = []
        self.scale_val = 1.0# scalng factor

        # event handling
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

    # --------------------- OBJECT MANAGEMENT -----------------------

    def addObject(self, obj):
        self.objects.append(obj)
        obj.paper = self

    def removeObject(self, obj):
        obj.paper = None
        self.objects.remove(obj)

    def objectsInRegion(self, rect):
        """ For Tool only : get objects intersected by region rectangle. """
        x1,y1,x2,y2 = rect
        sv = self.scale_val
        gfx_items = self.items(QRectF(x1*sv, y1*sv, (x2-x1)*sv, (y2-y1)*sv))
        return [self.gfx_item_dict[itm] for itm in gfx_items if itm in self.gfx_item_dict]

    # -------------------- DRAWING COMMANDS -------------------------

    def addLine(self, line, width=1, color=Color.black):
        sv = self.scale_val
        line = [it*self.scale_val for it in line]
        pen = QPen(QColor(*color), width*self.scale_val)
        return QGraphicsScene.addLine(self, *line, pen)

    # A stroked rectangle has a size of (rectangle size + pen width)
    def addRect(self, rect, width=1, color=Color.black, fill=None):
        sv = self.scale_val
        x1,y1, x2,y2 = rect[0]*sv, rect[1]*sv, rect[2]*sv, rect[3]*sv
        pen = QPen(QColor(*color), width*sv)
        brush = fill and QColor(*fill) or QBrush()
        return QGraphicsScene.addRect(self, x1,y1, x2-x1, y2-y1, pen, brush)

    def addPolygon(self, points, width=1, color=Color.black, fill=None):
        polygon = QPolygonF([QPointF(*p)*self.scale_val for p in points])
        pen = QPen(QColor(*color), width*self.scale_val)
        brush = fill and QColor(*fill) or QBrush()
        return QGraphicsScene.addPolygon(self, polygon, pen, brush)

    def addPolyline(self, points, width=1, color=Color.black):
        sv = self.scale_val
        shape = QPainterPath(QPointF(*points[0])*sv)
        [shape.lineTo(QPointF(*pt)*sv) for pt in points[1:]]
        pen = QPen(QColor(*color), width*sv)
        return QGraphicsScene.addPath(self, shape, pen)

    def addEllipse(self, rect, width=1, color=Color.black, fill=None):
        sv = self.scale_val
        x1,y1, x2,y2 = rect[0]*sv, rect[1]*sv, rect[2]*sv, rect[3]*sv
        pen = QPen(QColor(*color), width*sv)
        brush = fill and QColor(*fill) or QBrush()
        return QGraphicsScene.addEllipse(self, x1,y1, x2-x1, y2-y1, pen, brush)

    def addCubicBezier(self, points, width=1, color=Color.black):
        pts = [QPointF(*pt)*self.scale_val for pt in points]
        shape = QPainterPath(pts[0])
        shape.cubicTo(pts[1:4])
        pen = QPen(QColor(*color), width*self.scale_val)
        return QGraphicsScene.addPath(self, shape, pen)

    def addQuadBezier(self, points, width=1, color=Color.black):
        pts = [QPointF(*pt)*self.scale_val for pt in points]
        shape = QPainterPath(pts[0])
        shape.quadTo(pts[1], pts[2])
        pen = QPen(QColor(*color), width*self.scale_val)
        return QGraphicsScene.addPath(self, shape, pen)

    def addHtmlText(self, text, pos, font=None, anchor=BasicPaper.AnchorLeft|BasicPaper.AnchorBaseline):
        """ Draw Html Text """
        sv = self.scale_val
        pos = pos[0]*sv, pos[1]*sv
        item = QGraphicsTextItem()
        if font:
            _font = QFont(font.name)
            _font.setPointSize(font.size * sv)
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

    def addChemicalFormula(self, formula, pos, anchor, font=None):
        """ draw chemical formula """
        sv = self.scale_val
        pos = pos[0]*sv, pos[1]*sv
        text = html_formula(formula)# subscript the numbers
        item = QGraphicsTextItem()
        if font:
            _font = QFont(font.name)
            _font.setPointSize(font.size * sv)
            item.setFont(_font)
        item.setHtml(text)
        self.addItem(item)
        w, h = item.boundingRect().getRect()[2:]
        x, y, w = pos[0]-self.textitem_margin, pos[1]-h/2, w-2*self.textitem_margin

        if anchor=="start":
            char_w = QFontMetricsF(item.font()).widthChar(text[0])
            x -= char_w/2
        elif anchor=="end":
            char_w = QFontMetricsF(item.font()).widthChar(text[-1])
            x -= w - char_w/2
        item.setPos(x,y)
        return item

    # ----------------- GRAPHICS ITEMS MANAGEMENT --------------------

    def setItemColor(self, item, color):
        pen = item.pen()
        pen.setColor(QColor(*color))
        item.setPen(pen)

    def itemBoundingBox(self, item):
        """ For Tool Only : return the bounding box of GraphicsItem item """
        x1, y1, x2, y2 = item.sceneBoundingRect().getCoords()
        if isinstance(item, QGraphicsTextItem):
            x1,y1,x2,y2 = x1+self.textitem_margin, y1+self.textitem_margin, x2-self.textitem_margin, y2-self.textitem_margin
        sv = self.scale_val
        return [x1/sv, y1/sv, x2/sv, y2/sv]

    def toForeground(self, item):
        item.setZValue(1)

    def toBackground(self, item):
        item.setZValue(-1)

    def moveItemsBy(self, items, dx, dy):
        """ For Tool Only : move graphics item by dx, dy """
        [item.moveBy(dx*self.scale_val, dy*self.scale_val) for item in items]

    # --------------------- INTERACTIVE-NESS -----------------------

    def addFocusable(self, graphics_item, obj):
        """ Add drawable objects, e.g bond, atom, arrow etc """
        self.gfx_item_dict[graphics_item] = obj

    def removeFocusable(self, graphics_item):
        """ Remove drawable objects, e.g bond, atom, arrow etc """
        if graphics_item in self.gfx_item_dict:
            self.gfx_item_dict.pop(graphics_item)

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


    #-------------------- EVENT HANDLING -----------------

    def mousePressEvent(self, ev):
        self.mouse_pressed = True
        self.dragging = False
        x, y = ev.scenePos().x(), ev.scenePos().y()
        self._mouse_press_pos = (x, y)
        App.tool.onMousePress(x/self.scale_val, y/self.scale_val)
        QGraphicsScene.mousePressEvent(self, ev)

    def mouseMoveEvent(self, ev):
        pos = ev.scenePos()
        x, y = pos.x(), pos.y()

        if self.mouse_pressed and not self.dragging:
            # to ignore slight movement while clicking mouse
            if not geometry.points_within_range([x,y], self._mouse_press_pos, 3):
                self.dragging = True

        # on mouse hover or mouse dragging, find obj to get focus
        if not self.mouse_pressed or self.dragging:
            gfx_items = self.items(QRectF(x-3,y-3, 6,6))
            drawables = [self.gfx_item_dict[itm] for itm in gfx_items if itm in self.gfx_item_dict]
            drawables = sorted(drawables, key=lambda obj : obj.focus_priority) # making atom higher priority than bonds
            focused_obj = drawables[0] if len(drawables) else None
            self.changeFocusTo(focused_obj)

        App.tool.onMouseMove(x/self.scale_val, y/self.scale_val)
        QGraphicsScene.mouseMoveEvent(self, ev)

    def mouseReleaseEvent(self, ev):
        if self.mouse_pressed:
            self.mouse_pressed = False
            pos = ev.scenePos() / self.scale_val
            App.tool.onMouseRelease(pos.x(), pos.y())
            self.dragging = False
        QGraphicsScene.mouseReleaseEvent(self, ev)

    def mouseDoubleClickEvent(self, ev):
        pos = ev.scenePos() / self.scale_val
        App.tool.onMouseDoubleClick(pos.x(), pos.y())
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

    def touchedAtom(self, atom):
        # For Tool only : finds which atoms are touched by arg atom
        sv = self.scale_val
        items = self.items(QRectF((atom.x-3)*sv, (atom.y-3)*sv, 7*sv, 7*sv))
        for item in items:
            obj = self.gfx_item_dict[item] if item in self.gfx_item_dict else None
            if type(obj) is Atom and obj is not atom:
                return obj
        return None


    # ------------------ PAPER STATE CACHE ---------------------

    def save_state_to_undo_stack(self, name=''):
        self.undo_manager.save_current_state(name)

    def undo(self):
        App.tool.clear()
        self.undo_manager.undo()

    def redo(self):
        App.tool.clear()
        self.undo_manager.redo()




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
