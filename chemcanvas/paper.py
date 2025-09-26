# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings
from undo_manager import UndoManager
from drawing_parents import Color, Font, Align, PenStyle, LineCap, hex_color
import geometry as geo
from common import float_to_str, bbox_of_bboxes
from tool_helpers import get_objs_with_all_children, draw_objs_recursively, move_objs
from document import Document

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsTextItem, QMenu
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import (QColor, QPen, QBrush, QPolygonF, QPainterPath,
        QFontMetricsF, QFont, QImage, QPainter)




# Note :


class Paper(QGraphicsScene):
    """ The canvas on which all items are drawn """
    def __init__(self, view=None):
        QGraphicsScene.__init__(self, view)
        self.view = view
        if view:
            view.setScene(self)
        self.paper = None # the background item

        self.objects = []# top level objects
        self.dirty_objects = set() # redraw_needed

        # event handling
        self.mouse_pressed = False
        self.dragging = False
        self.modifier_keys = set() # set of "Shift", "Ctrl" and "Alt"
        # these are items which are used to focus it's object.
        # each item contains a 'object' variable, which stores the object
        self.focusable_items = set()
        self.do_not_focus = set()
        self.focused_obj = None
        self.selected_objs = []

        # QGraphicsTextItem has a margin on each side, precalculate this
        item = self.addText("")
        self.textitem_margin = item.boundingRect().width()/2
        self.removeItem(item)

        self.undo_manager = UndoManager(self)



    def setSize(self, w, h):
        self.setSceneRect(0,0,w,h)
        if self.paper:
            self.removeItem(self.paper)
        self.paper = self.addRect([0,0, w,h], style=PenStyle.no_line, fill=(255,255,255))
        self.paper.setZValue(-10)# place it below everything

    def getDocument(self):
        doc = Document()
        x,y, doc.page_w, doc.page_h = self.sceneRect().getRect()
        doc.objects = self.objects[:]
        return doc

    def setDocument(self, doc):
        """ Return True if document is new, and False if objects are added to existing """
        bboxes = [obj.bounding_box() for obj in doc.objects]
        bbox = bbox_of_bboxes(bboxes)
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]

        # if page already have objects, add objects to already existing document.
        # if page is empty, set page size, and load objects
        is_new = False
        reposition = True
        if not self.objects:# new document
            is_new = True
            if doc.page_w and doc.page_h:# use page size from document
                reposition = False
            else:# new document does not have page size
                w_pt, h_pt = w*72.0/Settings.render_dpi, h*72.0/Settings.render_dpi
                if w_pt<595.0:# prefer A4 portrait
                    doc.set_page_size(595, 842)
                else:
                    # A4 landscape if fits or objects bbox + margin
                    margin = 1/2.54*Settings.render_dpi # 1 cm
                    doc.page_w = max(w+2*margin, 842/72*Settings.render_dpi)
                    doc.page_h = max(h+2*margin, 595/72*Settings.render_dpi)
            self.setSize(doc.page_w, doc.page_h)

        if reposition:
            x, y = self.find_place_for_obj_size(w, h)
            move_objs(doc.objects, x-bbox[0], y-bbox[1])

        for obj in doc.objects:
            self.addObject(obj)
            draw_objs_recursively([obj])
        return is_new


    def find_place_for_obj_size(self, w, h):
        """ find place for new object. return new object position."""
        # It works by first placing rect beside the object in lowest position.
        # If does not fit there, then find the object just above rect
        # and place just beside it. Continue the loop until either
        # fit properly or reaches right edge of page.
        margin = 1/2.54*Settings.render_dpi # 1 cm
        spacing = 0.75/2.54*Settings.render_dpi # 0.75 cm
        if not self.objects:# page empty
            x = min(margin, (self.width()-w)/2)
            y = min(margin, (self.height()-h)/2)
            return (x,y)
        rects = [o.bounding_box() for o in self.objects]
        lowest_rect = max(rects, key=lambda r : r[3])
        baseline = (lowest_rect[3]+lowest_rect[1])/2
        prev_rect = lowest_rect
        while 1:
            # try to place beside previous rect
            x1, x2 = prev_rect[2]+spacing, prev_rect[2]+spacing+w
            rects_above = list(filter(lambda r : x1<r[2] and r[0]<x2, rects))
            if not rects_above:# found place or reached end
                break
            above_rect = max(rects_above, key=lambda r : r[3])
            # check if fits
            if baseline-above_rect[3] > h/2 :# found place
                break
            prev_rect = above_rect
        # try to place object next to previous rect.
        x = x1
        y = baseline - h/2
        # if can not, then place in next line
        if x+w>self.width():
            x = min(margin, (self.width()-w)/2)
            y = lowest_rect[3] + spacing
        # adjust pos when object is outside of page
        x = max(x, 10)
        y = max(min(y, self.height()-h), 10)
        return (x,y)

    # --------------------- OBJECT MANAGEMENT -----------------------

    def addObject(self, obj):
        self.objects.append(obj)
        obj.paper = self

    def removeObject(self, obj):
        obj.paper = None
        self.objects.remove(obj)

    def objectsInRect(self, rect):
        """ get objects intersected by region rectangle. """
        x1,y1,x2,y2 = rect
        gfx_items = set(self.items(QRectF(x1, y1, x2-x1, y2-y1)))
        return [itm.object for itm in gfx_items & self.focusable_items]

    def objectsInPolygon(self, polygon):
        """ get objects intersected by region rectangle. """
        gfx_items = set(self.items(QPolygonF([QPointF(*pt) for pt in polygon])))
        return [itm.object for itm in gfx_items & self.focusable_items]

    def redraw_dirty_objects(self):
        draw_objs_recursively(self.dirty_objects)
        self.dirty_objects.clear()

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

    def addPolygon(self, points, width=1, color=Color.black, style=PenStyle.solid, fill=None):
        polygon = QPolygonF([QPointF(*p) for p in points])
        pen = QPen(QColor(*color), width, style)
        brush = fill and QColor(*fill) or QBrush()
        return QGraphicsScene.addPolygon(self, polygon, pen, brush)

    def addPolyline(self, points, width=1, color=Color.black, style=PenStyle.solid):
        shape = QPainterPath(QPointF(*points[0]))
        [shape.lineTo(QPointF(*pt)) for pt in points[1:]]
        pen = QPen(QColor(*color), width, style)
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

    def addArc(self, rect, start_ang, span_ang, width=1, color=Color.black):
        """ draw arc """
        x1,y1,x2,y2 = rect
        path = QPainterPath()
        path.arcMoveTo(x1,y1,x2-x1,y2-y1, start_ang)
        path.arcTo(x1,y1,x2-x1,y2-y1, start_ang, span_ang)
        pen = QPen(QColor(*color), width)
        return QGraphicsScene.addPath(self, path, pen)

    def addHtmlText(self, text, pos, font=None, align=Align.Left|Align.Baseline, color=(0,0,0)):
        """ Draw Html Text """
        item = QGraphicsTextItem()
        item.setDefaultTextColor(QColor(*color))
        if font:
            _font = QFont(font.name)
            _font.setPixelSize(int(round(font.size)))
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
        if align & Align.HCenter:
            x -= w/2
            # text width must be set to enable html text-align property
            item.document().setTextWidth(item_w)
        elif align & Align.Right:
            x -= w
            item.document().setTextWidth(item_w)
        # vertical alignment
        if align & Align.Baseline:
            y -= font_metrics.ascent()
        elif align & Align.Bottom:
            y -= h
        elif align & Align.VCenter:
            y -= h/2

        item.setPos(x,y)
        return item

    def addChemicalFormula(self, text, pos, align, offset, font, color=(0,0,0)):
        """ draw chemical formula """
        item = QGraphicsTextItem()
        item.setDefaultTextColor(QColor(*color))
        if font:
            _font = QFont(font.name)
            _font.setPixelSize(int(round(font.size)))
            item.setFont(_font)
        item.setHtml(text)
        item.text = text # from this we can get the original text we have set
        self.addItem(item)
        w, h = item.boundingRect().getRect()[2:]
        x, y, w = pos[0]-self.textitem_margin, pos[1]-h/2, w-2*self.textitem_margin

        if align == Align.HCenter:
            x -= w/2
        elif align == Align.Left:
            x -= offset
        elif align == Align.Right:
            x -= w - offset
        item.setPos(x,y)
        return item

    # ----------------- GRAPHICS ITEMS MANAGEMENT --------------------

    def get_items_of_all_objects(self):
        objs = get_objs_with_all_children(self.objects)
        objs = sorted(objs, key=lambda x : x.redraw_priority)
        items = []
        for obj in objs:
            items += obj.chemistry_items
        return items

    def setItemColor(self, item, color, fill=None):
        pen = item.pen()
        pen.setColor(QColor(*color))
        item.setPen(pen)
        if fill:
            item.setBrush(QBrush(QColor(*fill)))

    def setItemRotation(self, item, rotation):
        """ rotate item by degree """
        # this can be done also with QTransform by
        # first translate(w/2,h/2), then rotate then translate(-w/2,-h/2)
        item.original_pos = item.scenePos()
        item.setTransformOriginPoint(item.boundingRect().center())
        item.setRotation(rotation)


    def itemBoundingRect(self, item):
        x, y, w, h = item.sceneBoundingRect().getRect()
        if isinstance(item, QGraphicsTextItem):
            return x+self.textitem_margin, y+self.textitem_margin, w-2*self.textitem_margin, h-2*self.textitem_margin
        return x,y,w,h

    def itemBoundingBox(self, item):
        """ return the bounding box of GraphicsItem item """
        x1, y1, x2, y2 = item.sceneBoundingRect().getCoords()
        if isinstance(item, QGraphicsTextItem):
            return [x1+self.textitem_margin, y1+self.textitem_margin,
                    x2-self.textitem_margin, y2-self.textitem_margin]
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
        qfont.setPixelSize(int(round(font.size)))
        return QFontMetricsF(qfont).widthChar(char)

    def getTextWidth(self, text, font):
        qfont = QFont(font.name)
        qfont.setPixelSize(int(round(font.size)))
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

    def changeFocusTo(self, focused_obj):
        """ to remove focus, None should be passed as argument """
        if self.focused_obj is focused_obj:
            return
        # focus is changed, remove focus from prev item and set focus to new item
        if self.focused_obj:
            self.focused_obj.set_focus(False)
        if focused_obj:
            focused_obj.set_focus(True)
        self.focused_obj = focused_obj

    def unfocusObject(self, obj):
        """ called by DrawableObject.delete_from_paper() """
        if obj is self.focused_obj:
            obj.set_focus(False)
            self.focused_obj = None

    def selectObject(self, obj):
        if obj not in self.selected_objs:
            obj.set_selected(True)
            self.selected_objs.append(obj)

    def deselectObject(self, obj):
        if obj in self.selected_objs:
            obj.set_selected(False)
            self.selected_objs.remove(obj)

    def deselectAll(self):
        for obj in self.selected_objs:
            obj.set_selected(False)
        self.selected_objs = []


    #-------------------- EVENT HANDLING -----------------

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return QGraphicsScene.mousePressEvent(self, ev)
        self.mouse_pressed = True
        self.dragging = False
        x, y = ev.scenePos().x(), ev.scenePos().y()
        self._mouse_press_pos = (x, y)
        App.tool.on_mouse_press(x, y)
        QGraphicsScene.mousePressEvent(self, ev)


    def mouseMoveEvent(self, ev):
        pos = ev.scenePos()
        x, y = pos.x(), pos.y()

        if self.mouse_pressed and not self.dragging:
            # to ignore slight movement while clicking mouse
            if not geo.points_within_range([x,y], self._mouse_press_pos, 2):
                self.dragging = True

        # on mouse hover or mouse dragging, find obj to get focus
        if not self.mouse_pressed or self.dragging:
            objs = self.objectsInRect([x-3,y-3,x+3,y+3])
            if objs:
                objs = sorted(objs, key=lambda obj : obj.focus_priority)
                under_cursor = [itm.object for itm in set(self.items(QPointF(x,y))) & self.focusable_items]
                under_cursor = sorted(under_cursor, key=lambda obj : obj.focus_priority)
                objs = under_cursor + [o for o in objs if o.class_name!="Atom"]
                objs = [o for o in objs if o not in self.do_not_focus]
            focused_obj = objs[0] if len(objs) else None
            self.changeFocusTo(focused_obj)

        App.tool.on_mouse_move(x, y)
        QGraphicsScene.mouseMoveEvent(self, ev)


    def mouseReleaseEvent(self, ev):
        if self.mouse_pressed:
            self.mouse_pressed = False
            pos = ev.scenePos()
            App.tool.on_mouse_release(pos.x(), pos.y())
            self.dragging = False
        QGraphicsScene.mouseReleaseEvent(self, ev)


    def mouseDoubleClickEvent(self, ev):
        pos = ev.scenePos()
        App.tool.on_mouse_double_click(pos.x(), pos.y())
        QGraphicsScene.mouseReleaseEvent(self, ev)


    def contextMenuEvent(self, ev):
        pos = ev.scenePos()
        App.tool.on_right_click(pos.x(), pos.y())


    def keyPressEvent(self, ev):
        key = ev.key()
        if key in key_name_map:# non-printable keys
            key = key_name_map[key]
            text = ""
            if key in ("Shift", "Ctrl", "Alt"):
                self.modifier_keys.add(key)
                return
        elif ev.text():
            if 33<=key<=126:# printable ASCII characters
                key = chr(key)
            else:
                key = ev.text()
            text = ev.text()
        else:
            return

        App.tool.on_key_press(key, text)


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
        App.window.enableSaveButton(True)

    def undo(self):
        App.tool.clear()
        self.undo_manager.undo()
        App.window.enableSaveButton(self.undo_manager.has_unsaved_changes())

    def redo(self):
        App.tool.clear()
        self.undo_manager.redo()
        App.window.enableSaveButton(self.undo_manager.has_unsaved_changes())


    # ------------------------ OTHERS --------------------------

    def getImage(self, margin=10):
        x1, y1, w, h = map(int, self.sceneRect().getCoords())
        image = QImage(w, h, QImage.Format_RGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.render(painter)
        painter.end()

        x1, y1, x2, y2 = map(int, self.allObjectsBoundingBox())
        x1, y1 = max(x1-margin, 0), max(y1-margin, 0)
        x2, y2 = min(x2+margin,w), min(y2+margin, h)
        image = image.copy(x1, y1, x2-x1, y2-y1)
        return image


    def getSvg(self):
        items = self.get_items_of_all_objects()
        svg_paper = SvgPaper()
        for item in items:
            draw_graphicsitem(item, svg_paper)
        x1,y1, x2,y2 = self.allObjectsBoundingBox()
        x1, y1, x2, y2 = x1-6, y1-6, x2+6, y2+6
        svg_paper.setViewBox(x1,y1, x2-x1, y2-y1)
        return svg_paper.getSvg()


    def createMenu(self, title=''):
        # title is only meaningful for submenu. for root menu it must be empty
        return QMenu(title, self.view)

    def showMenu(self, menu, pos):
        if not menu.isEmpty():
            screen_pos = self.view.mapToGlobal(self.view.mapFromScene(*pos))
            menu.exec(screen_pos)
        menu.deleteLater()

    def renderObjects(self, objects):
        """ this is for generating thumbnails """
        bboxes = [obj.bounding_box() for obj in objects]
        bbox = bbox_of_bboxes(bboxes)
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        page_w, page_h = w+50, h+50

        self.setSize(page_w, page_h)

        move_objs(objects, 25-bbox[0], 25-bbox[1])

        for obj in objects:
            self.addObject(obj)
            draw_objs_recursively([obj])

        image = self.getImage(margin=0)
        objs = get_objs_with_all_children(objects)
        for obj in objs:
            obj.delete_from_paper()
        return image


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
    # in svg butt is default and in SvgPaper square is default capstyle
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
    # < and > characters already replaced with &lt; and &gt; in Text obj.
    # replacing & character also replaces & character of &lt; and &gt;
    text = text.replace("&", "&amp;").replace("&amp;lt;", "&lt;").replace("&amp;gt;", "&gt;")
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

    def drawPolygon(self, points, width=1, color=Color.black, style=PenStyle.solid, fill=None):
        cmd = '<polygon points="%s" ' % points_str(points)
        cmd += stroke_attrs(width, color, line_style=style)
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

    def drawCubicBezier(self, points, width=1, color=Color.black, style=PenStyle.solid):
        cmd = '<path d="M%s C%s" ' % (points_str(points[:1]), points_str(points[1:4]))
        cmd += stroke_attrs(width, color, line_style=style)
        cmd += '/>'
        self.items.append(cmd)

    def drawHtmlText(self, text, pos, font=None, color=(0,0,0), transform=None):
        """ Draw Html Text """
        x, y = float_to_str(pos[0]), float_to_str(pos[1])
        cmd = '<text x="%s" y="%s" %s' % (x, y, fill_attr(color))
        if transform:
            cmd += ' transform="%s"'%transform
        cmd += '>'
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
        paper.drawPolygon(points, width, color, style, fill)
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
                paper.drawLine([*curr_pos, x, y], width, color, style)
            elif elm_type == QPainterPath.CurveToElement:
                pts = [curr_pos, (x,y)]
                while i+1 < elm_count:
                    elm = path.elementAt(i+1)
                    if elm.type == QPainterPath.CurveToDataElement:
                        pts.append((elm.x+item_x, elm.y+item_y))
                        i += 1
                    else:
                        break
                paper.drawCubicBezier(pts, width, color, style)
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
        if item.rotation()==0:
            pos = item.scenePos()
        else:
            # rotation changes scenePos(). retrieve scenePos() before rotation
            tfm = item.transform()
            tfm.translate(item.transformOriginPoint().x(), item.transformOriginPoint().y())
            tfm.rotate(item.rotation())
            tfm.translate(-item.transformOriginPoint().x(), -item.transformOriginPoint().y())
            pos = item.scenePos() - tfm.map(QPointF(0,0))

        x = pos.x() + margin
        y = pos.y() + margin + font_metrics.ascent()# top alignment to baseline alignment
        for line in text.split("<br>"):
            if item.rotation()!=0:# this works for single line text only
                c = pos + item.transformOriginPoint()# rotation center
                transform = "rotate(%f,%f,%f)" % (item.rotation(), c.x(), c.y())
            else:
                transform = None
            paper.drawHtmlText(line, (x, y), font, color, transform)
            y += font_metrics.height()

