# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App
from undo_manager import UndoManager
from drawing_parents import Color, Font, Anchor, PenStyle, LineCap
import geometry
from common import float_to_str, bbox_of_bboxes

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsTextItem, QMenu
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import (QColor, QPen, QBrush, QPolygonF, QPainterPath,
        QFontMetricsF, QFont, QImage, QPainter)




# Note :


class Paper(QGraphicsScene):
    """ The canvas on which all items are drawn """
    def __init__(self, x,y,w,h, view):
        QGraphicsScene.__init__(self, x,y,w,h, view)
        self.view = view
        view.setScene(self)

        self.objects = []# top level objects

        # set paper size
        self.paper = self.addRect([x,y, x+w,y+h], fill=(255,255,255))
        self.paper.setZValue(-10)# place it below everything
        # event handling
        self.mouse_pressed = False
        self.dragging = False
        self.modifier_keys = set()
        # these are items which are used to focus it's object.
        # each item contains a 'object' variable, which stores the object
        self.focusable_items = set()
        self.dont_focus = set()
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
        """ get objects intersected by region rectangle. """
        x1,y1,x2,y2 = rect
        gfx_items = set(self.items(QRectF(x1, y1, x2-x1, y2-y1)))
        return [itm.object for itm in gfx_items & self.focusable_items]

    # -------------------- DRAWING COMMANDS -------------------------

    def addLine(self, line, width=1, color=Color.black, style=PenStyle.solid, cap=LineCap.square):
        pen = QPen(QColor(*color), width, style, cap)
        return QGraphicsScene.addLine(self, *line, pen)

    # A stroked rectangle has a size of (rectangle size + pen width)
    def addRect(self, rect, width=1, color=Color.black, style=PenStyle.solid, fill=None):
        x1,y1, x2,y2 = rect
        pen = QPen(QColor(*color), width, style)
        brush = fill and QColor(*fill) or QBrush()
        return QGraphicsScene.addRect(self, x1,y1, x2-x1, y2-y1, pen, brush)

    def addPolygon(self, points, width=1, color=Color.black, fill=None):
        polygon = QPolygonF([QPointF(*p) for p in points])
        pen = QPen(QColor(*color), width)
        brush = fill and QColor(*fill) or QBrush()
        return QGraphicsScene.addPolygon(self, polygon, pen, brush)

    def addPolyline(self, points, width=1, color=Color.black):
        shape = QPainterPath(QPointF(*points[0]))
        [shape.lineTo(QPointF(*pt)) for pt in points[1:]]
        pen = QPen(QColor(*color), width)
        return QGraphicsScene.addPath(self, shape, pen)

    def addEllipse(self, rect, width=1, color=Color.black, fill=None):
        x1,y1, x2,y2 = rect
        pen = QPen(QColor(*color), width)
        brush = fill and QColor(*fill) or QBrush()
        return QGraphicsScene.addEllipse(self, x1,y1, x2-x1, y2-y1, pen, brush)

    def addCubicBezier(self, points, width=1, color=Color.black):
        """ draw single bezier or multiple connected bezier curves.
        for n curves, it requires 1+3n points"""
        pts = [QPointF(*pt) for pt in points]
        shape = QPainterPath(pts[0])
        for i in range( (len(pts)-1)//3 ):
            shape.cubicTo(*pts[3*i+1:3*i+4])
        pen = QPen(QColor(*color), width)
        return QGraphicsScene.addPath(self, shape, pen)

    def addHtmlText(self, text, pos, font=None, anchor=Anchor.Left|Anchor.Baseline, color=(0,0,0)):
        """ Draw Html Text """
        item = QGraphicsTextItem()
        item.setDefaultTextColor(QColor(*color))
        if font:
            _font = QFont(font.name)
            _font.setPixelSize(font.size)
            _font.setBold(font.bold)
            _font.setItalic(font.italic)
            item.setFont(_font)
        item.setHtml(text)
        item.text = text # from this we can get the original text we have set
        self.addItem(item)

        font_metrics = QFontMetricsF(item.font())
        item_w = item.boundingRect().width()
        x, y = pos[0]-self.textitem_margin, pos[1]-self.textitem_margin
        w, h = item_w-2*self.textitem_margin, font_metrics.height()
        # horizontal alignment
        if anchor & Anchor.HCenter:
            x -= w/2
            # text width must be set to enable html text-align property
            item.document().setTextWidth(item_w)
        elif anchor & Anchor.Right:
            x -= w
            item.document().setTextWidth(item_w)
        # vertical alignment
        if anchor & Anchor.Baseline:
            y -= font_metrics.ascent()
        elif anchor & Anchor.Bottom:
            y -= h
        elif anchor & Anchor.VCenter:
            y -= h/2

        item.setPos(x,y)
        return item

    def addChemicalFormula(self, text, pos, anchor, font=None, offset=0, color=(0,0,0)):
        """ draw chemical formula """
        item = QGraphicsTextItem()
        item.setDefaultTextColor(QColor(*color))
        if font:
            _font = QFont(font.name)
            _font.setPixelSize(font.size)
            item.setFont(_font)
        item.setHtml(text)
        item.text = text # from this we can get the original text we have set
        self.addItem(item)
        w, h = item.boundingRect().getRect()[2:]
        x, y, w = pos[0]-self.textitem_margin, pos[1]-h/2, w-2*self.textitem_margin

        if anchor=="start":
            x -= offset
        elif anchor=="end":
            x -= w - offset
        item.setPos(x,y)
        return item

    # ----------------- GRAPHICS ITEMS MANAGEMENT --------------------

    def get_items_of_all_objects(self):
        objs = get_objs_with_all_children(self.objects)
        objs = sorted(objs, key=lambda x : x.redraw_priority)
        items = []
        for obj in objs:
            items += obj.items
        return items

    def setItemColor(self, item, color):# UNUSED
        pen = item.pen()
        pen.setColor(QColor(*color))
        item.setPen(pen)

    def itemBoundingBox(self, item):
        """ return the bounding box of GraphicsItem item """
        x1, y1, x2, y2 = item.sceneBoundingRect().getCoords()
        if isinstance(item, QGraphicsTextItem):
            x1,y1,x2,y2 = x1+self.textitem_margin, y1+self.textitem_margin, x2-self.textitem_margin, y2-self.textitem_margin
        return [x1, y1, x2, y2]

    def allObjectsBoundingBox(self):
        items = self.get_items_of_all_objects()
        bboxes = [self.itemBoundingBox(item) for item in items]
        return bbox_of_bboxes(bboxes)

    def toForeground(self, item):
        item.setZValue(1)

    def toBackground(self, item):
        item.setZValue(-1)

    def moveItemsBy(self, items, dx, dy):
        """ move graphics item by dx, dy """
        [item.moveBy(dx, dy) for item in items]

    def getCharWidth(self, char, font):
        qfont = QFont(font.name)
        qfont.setPixelSize(font.size)
        return QFontMetricsF(qfont).widthChar(char)

    def getTextWidth(self, text, font):
        qfont = QFont(font.name)
        qfont.setPixelSize(font.size)
        return QFontMetricsF(qfont).width(text)

    # --------------------- INTERACTIVE-NESS -----------------------

    def addFocusable(self, graphics_item, obj):
        """ Add drawable objects, e.g bond, atom, arrow etc """
        graphics_item.object = obj
        self.focusable_items.add(graphics_item)

    def removeFocusable(self, graphics_item):
        """ Remove drawable objects, e.g bond, atom, arrow etc """
        if graphics_item in self.focusable_items:
            self.focusable_items.remove(graphics_item)
            graphics_item.object = None

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
        if ev.button() != Qt.LeftButton:
            return QGraphicsScene.mousePressEvent(self, ev)
        self.mouse_pressed = True
        self.dragging = False
        x, y = ev.scenePos().x(), ev.scenePos().y()
        self._mouse_press_pos = (x, y)
        App.tool.onMousePress(x, y)
        QGraphicsScene.mousePressEvent(self, ev)


    def mouseMoveEvent(self, ev):
        pos = ev.scenePos()
        x, y = pos.x(), pos.y()

        if self.mouse_pressed and not self.dragging:
            # to ignore slight movement while clicking mouse
            if not geometry.points_within_range([x,y], self._mouse_press_pos, 2):
                self.dragging = True

        # on mouse hover or mouse dragging, find obj to get focus
        if not self.mouse_pressed or self.dragging:
            objs = self.objectsInRegion([x-3,y-3,x+6,y+6])
            if objs:
                objs = sorted(objs, key=lambda obj : obj.focus_priority)
                under_cursor = [itm.object for itm in set(self.items(QPointF(x,y))) & self.focusable_items]
                under_cursor = sorted(under_cursor, key=lambda obj : obj.focus_priority)
                objs = under_cursor + [o for o in objs if o.class_name!="Atom"]
                objs = [o for o in objs if o not in self.dont_focus]
            focused_obj = objs[0] if len(objs) else None
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


    def mouseDoubleClickEvent(self, ev):
        pos = ev.scenePos()
        App.tool.onMouseDoubleClick(pos.x(), pos.y())
        QGraphicsScene.mouseReleaseEvent(self, ev)


    def contextMenuEvent(self, ev):
        menu = QMenu(self.view)
        App.tool.createContextMenu(menu)
        if not menu.isEmpty():
            menu.exec(ev.screenPos())
        menu.deleteLater()

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
        # finds which atoms are touched by arg atom
        items = self.items(QRectF((atom.x-3), (atom.y-3), 7, 7))
        for item in items:
            obj = item.object if item in self.focusable_items else None
            if obj and obj.class_name=="Atom" and obj is not atom:
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

    def getImage(self):
        x1, y1, w, h = self.sceneRect().getCoords()
        image = QImage(w, h, QImage.Format_RGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.render(painter)
        painter.end()

        x1, y1, x2, y2 = self.allObjectsBoundingBox()
        x1, y1, x2, y2 = max(x1-10, 0), max(y1-10, 0), min(x2+10,w), min(y2+10, h)
        image = image.copy(x1, y1, x2-x1, y2-y1)
        return image

    def createMenu(self, title):
        return QMenu(title, self.view)

    def showMenu(self, menu, pos):
        menu.exec(self.view.mapToGlobal(self.view.mapFromScene(*pos)))



# Some Utility Functions

def get_objs_with_all_children(objs):
    """ returns list of objs and their all children recursively"""
    stack = list(objs)
    result = set()
    while len(stack):
        obj = stack.pop()
        result.add(obj)
        stack += obj.children
    return list(result)


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




# ------------------ SVG PAPER ----------------------

# converts (r,g,b) or (r,g,b,a) color to html hex format
def hex_color(color):
    clr = '#'
    for x in color:
        clr += "%.2x" % x
    return clr

def fill_attr(color):
    return color and 'fill="%s" '%hex_color(color) or 'fill="none" '

def stroke_attrs(width=None, color=None, line_style=None, cap_style=None):
    attrs = ''
    # set stroke width
    if width!=None:
        attrs += 'stroke-width="%s" ' % float_to_str(width)
    # set stroke color
    if color!=None:
        attrs += 'stroke="%s" ' % hex_color(color)
    # set stroke line style
    if line_style!=None:
        if line_style == PenStyle.dotted:
            attrs += 'stroke-dasharray="2" '
            cap_style = LineCap.butt
        elif line_style == PenStyle.dashed:
            attrs += 'stroke-dasharray="4" '
            cap_style = LineCap.butt
    # set line capstyle (butt | square | round)
    # in svg butt is default and in SvgPaper square is defalut capstyle
    if cap_style!=None:
        if cap_style==LineCap.butt:
            attrs += 'stroke-linecap="butt" '
        elif cap_style==LineCap.round:
            attrs += 'stroke-linecap="round" '
    return attrs


def points_str(pts):
    return " ".join(",".join(tuple(map(float_to_str,pt))) for pt in pts)

# converts some basic html4 formattings to svg format
def html_to_svg(text):
    text = text.replace('<sup>', '<tspan baseline-shift="super" font-size="75%">')
    text = text.replace('</sup>', '</tspan>')
    text = text.replace('<sub>', '<tspan baseline-shift="sub" font-size="75%">')
    text = text.replace('</sub>', '</tspan>')
    return text


class SvgPaper:
    def __init__(self):
        self.items = []
        self.x = 0
        self.y = 0
        self.w = 300
        self.h = 300

    def setViewBox(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x,y, w,h

    def getSvg(self):
        svg = '<?xml version="1.0" encoding="UTF-8" ?>'
        # we can also include width and height (unit cm or in) to set actual size or to scale svg
        svg += '<svg viewBox="%i %i %i %i"\n' %(self.x, self.y, self.w, self.h)
        svg += '    version="1.1" xmlns="http://www.w3.org/2000/svg" >\n'
        # for text, fill=none must be mentioned
        svg += '<g fill="none" stroke-linecap="square" font-style="normal" >\n'
        for item in self.items:
            svg += item + '\n'
        svg += '</g>\n</svg>'
        return svg

    def drawLine(self, line, width=1, color=Color.black, style=PenStyle.solid, cap=LineCap.square):
        cmd = '<line x1="%s" y1="%s" x2="%s" y2="%s" ' % tuple(map(float_to_str, line))
        cmd += stroke_attrs(width, color, line_style=style, cap_style=cap)
        cmd += '/>'
        self.items.append(cmd)

    def drawRect(self, rect, width=1, color=Color.black, fill=None):
        cmd = '<rect x1="%s" y1="%s" x2="%s" y2="%s" ' % tuple(map(float_to_str, rect))
        cmd += stroke_attrs(width, color)
        cmd += fill_attr(fill)
        cmd += '/>'
        self.items.append(cmd)

    def drawPolygon(self, points, width=1, color=Color.black, fill=None):
        cmd = '<polygon points="%s" ' % points_str(points)
        cmd += stroke_attrs(width, color)
        cmd += fill_attr(fill)
        cmd += '/>'
        self.items.append(cmd)

    def drawEllipse(self, rect, width=1, color=Color.black, fill=None):
        x1, y1, x2, y2 = rect
        rx, ry = (x2-x1)/2, (y2-y1)/2
        ellipse = (x1+rx, y1+ry, rx, ry)
        cmd = '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" ' % tuple(map(float_to_str, ellipse))
        cmd += stroke_attrs(width, color)
        cmd += fill_attr(fill)
        cmd += '/>'
        self.items.append(cmd)

    def drawCubicBezier(self, points, width=1, color=Color.black):
        cmd = '<path d="M%s C%s" ' % (points_str(points[:1]), points_str(points[1:4]))
        cmd += stroke_attrs(width, color)
        cmd += '/>'
        self.items.append(cmd)

    def drawHtmlText(self, text, pos, font=None, color=(0,0,0)):
        """ Draw Html Text """
        x, y = float_to_str(pos[0]), float_to_str(pos[1])
        cmd = '<text x="%s" y="%s" %s>' % (x, y, fill_attr(color))
        if font:
            cmd = '<g font-family="%s" font-size="%spx">'%(font.name, float_to_str(font.size)) + cmd
        cmd += html_to_svg(text)
        cmd += '</text>'
        if font:
            cmd += '</g>'
        self.items.append(cmd)



# ----------------- GRAPHICS ITEM DRAWING INTERFACE --------------------

def to_native_font(qfont):
    return Font(qfont.family(), qfont.pixelSize())

# converts QColor to (r,g,b) or (r,g,b,a)
def to_native_color(qcolor):
    color = qcolor.getRgb()
    return color[3] == 255 and color[:3] or color

def get_pen_info(qpen):
    color = to_native_color(qpen.color())
    width = qpen.widthF()
    return color, width, qpen.style(), qpen.capStyle()

def get_brush_info(brush):
    # for solid colored brush only
    return to_native_color(brush.color())



def draw_graphicsitem(item, paper):
    # If a QGraphicsLineItem is moved by calling moveBy() method,
    # the item.line() does not change, instead item.pos() changes.
    # So we need to translate (or add) the line coordinates by item pos to get
    # actual coordinates. Thus all other graphics items' coordinates are translated.
    # draw line
    if item.type()==6:# QGraphicsLineItem
        line = item.line().translated(item.scenePos())
        line = line.x1(), line.y1(), line.x2(), line.y2()
        color, width, style, cap = get_pen_info(item.pen())
        paper.drawLine(line, width, color, style, cap)
    # draw rectangle
    elif item.type()==3:# QGraphicsRectItem
        rect = item.rect().translated(item.scenePos()).getCoords()
        color, width, style, cap = get_pen_info(item.pen())
        fill = get_brush_info(item.brush())
        paper.drawRect(rect, width, color, fill)
    # draw polygon
    elif item.type()==5:# QGraphicsPolygonItem
        polygon = item.polygon().translated(item.scenePos())
        points = [polygon.at(i) for i in range(polygon.count())]
        points = [(pt.x(), pt.y()) for pt in points]
        color, width, style, cap = get_pen_info(item.pen())
        fill = get_brush_info(item.brush())
        paper.drawPolygon(points, width, color, fill)
    # draw ellipse
    elif item.type()==4:# QGraphicsEllipseItem
        rect = item.rect().translated(item.scenePos()).getCoords()
        color, width, style, cap = get_pen_info(item.pen())
        fill = get_brush_info(item.brush())
        paper.drawEllipse(rect, width, color, fill)
    # draw path
    elif item.type()==2:# QGraphicsPathItem
        item_x, item_y = item.scenePos().x(), item.scenePos().y()
        color, width, style, cap = get_pen_info(item.pen())
        #fill = get_brush_info(item.brush())

        path = item.path()
        curr_pos = (item_x,item_y)
        last_curve = []
        elm_count = path.elementCount()
        i = 0
        while i < elm_count:
            elm = path.elementAt(i)
            elm_type, x, y = elm.type, elm.x+item_x, elm.y+item_y
            if elm_type == QPainterPath.LineToElement:
                paper.drawLine([*curr_pos, x, y])
            elif elm_type == QPainterPath.CurveToElement:
                pts = [curr_pos, (x,y)]
                while i+1 < elm_count:
                    elm = path.elementAt(i+1)
                    if elm.type == QPainterPath.CurveToDataElement:
                        pts.append((elm.x+item_x, elm.y+item_y))
                        i += 1
                    else:
                        break
                paper.drawCubicBezier(pts, width, color)
                x, y = pts[-1] # used as curr_pos
            curr_pos = (x,y)# for MoveToElement and all other elements
            i += 1
    # draw text
    elif item.type()==8:# QGraphicsTextItem
        text = item.text# not a property of QGraphicsTextItem, but we added it in our paper
        color = to_native_color(item.defaultTextColor())
        font = to_native_font(item.font())
        margin = item.scene().textitem_margin
        font_metrics = QFontMetricsF(item.font())
        w, h = item.boundingRect().getRect()[2:]
        pos = item.scenePos()
        x = pos.x() + margin
        y = pos.y() + h - font_metrics.descent() - margin
        paper.drawHtmlText(text, (x, y), font, color)

