# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings
from undo_manager import UndoManager
from drawing_parents import Color, Font, Align, PenStyle, LineCap, hex_color
import geometry as geo
from common import float_to_str, bbox_of_bboxes
from tool_helpers import get_objs_with_all_children, draw_objs_recursively, move_objs
from document import Document, Page

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsTextItem, QMenu
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import (QColor, QPen, QBrush, QPolygonF, QPainterPath,
        QFontMetricsF, QFont, QImage, QPainter, QTransform)




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
        self.show_canvas_grid = False
        self.canvas_grid_spacing = 20
        self.canvas_grid_major_every = 5
        self._canvas_grid_items = []
        self.pages = []
        self.page_origins = []  # list[(x,y)] per page
        self.active_page_index = 0
        self.show_page_boundaries = True
        self._page_backgrounds = []
        self._printable_backgrounds = []
        self._page_guides = []
        self._margin_guides = []
        self._limit_warning_item = None
        self._limit_feedback_status_active = False
        self._page_gutter = 40  # default gutter (px)
        self._page_layout_padding = 20
        self.page_layout_mode = "stacked"  # or "grid"
        self.grid_columns = 2
        self.grid_gutter = self._page_gutter
        self._active_page_guide = None

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
        self.show_carbon = "None"
        self.workspace_color = (128, 128, 128)
        self.page_area_color = (232, 236, 241)
        self.printable_area_color = (255, 255, 255)
        self.margin_warning_color = (220, 125, 0, 220)
        self.outside_page_warning_color = (220, 35, 35, 230)



    def setSize(self, w, h, reset_initial_undo=False):
        self.setSceneRect(0,0,w,h)
        if self.paper:
            self.removeItem(self.paper)
        self.paper = self.addRect([0,0, w,h], style=PenStyle.no_line, fill=(255,255,255))
        self.paper.setZValue(-10)# place it below everything
        self._rebuild_canvas_grid()
        if reset_initial_undo and len(self.undo_manager._stack)==1:
            self.undo_manager._stack[0].page_rect = self.sceneRect().getRect()

    def _clear_canvas_grid(self):
        for item in self._canvas_grid_items:
            try:
                self.removeItem(item)
            except Exception:
                pass
        self._canvas_grid_items = []

    def _grid_rects(self):
        if self.pages and self.page_origins:
            return [self.page_rect(i) for i in range(len(self.pages))]
        return [(0, 0, self.width(), self.height())]

    def _rebuild_canvas_grid(self):
        self._clear_canvas_grid()
        if not self.show_canvas_grid:
            return
        spacing = max(4, int(self.canvas_grid_spacing))
        major_every = max(1, int(self.canvas_grid_major_every))
        minor_color = (225, 225, 225)
        major_color = (205, 205, 205)
        for x1, y1, x2, y2 in self._grid_rects():
            start_x = int(x1 // spacing) * spacing
            start_y = int(y1 // spacing) * spacing
            index = 0
            x = start_x
            while x <= x2:
                color = major_color if index % major_every == 0 else minor_color
                line = self.addLine((x, y1, x, y2), width=1, color=color)
                line.setZValue(-9.8)
                self._canvas_grid_items.append(line)
                x += spacing
                index += 1
            index = 0
            y = start_y
            while y <= y2:
                color = major_color if index % major_every == 0 else minor_color
                line = self.addLine((x1, y, x2, y), width=1, color=color)
                line.setZValue(-9.8)
                self._canvas_grid_items.append(line)
                y += spacing
                index += 1

    def _clear_page_guides(self):
        for bg in self._page_backgrounds:
            try:
                self.removeItem(bg)
            except Exception:
                pass
        self._page_backgrounds = []
        for bg in self._printable_backgrounds:
            try:
                self.removeItem(bg)
            except Exception:
                pass
        self._printable_backgrounds = []
        for g in self._page_guides:
            try:
                self.removeItem(g)
            except Exception:
                pass
        self._page_guides = []
        for g in self._margin_guides:
            try:
                self.removeItem(g)
            except Exception:
                pass
        self._margin_guides = []
        if self._active_page_guide:
            try:
                self.removeItem(self._active_page_guide)
            except Exception:
                pass
            self._active_page_guide = None
        self.clear_limit_feedback(clear_status=False)

    def _rebuild_page_layout(self):
        self._clear_page_guides()
        self.page_origins = []
        if not self.pages:
            return
        x0, y0 = self._page_layout_padding, self._page_layout_padding
        gutter = self.grid_gutter if self.page_layout_mode == "grid" else self._page_gutter
        cols = max(1, int(self.grid_columns)) if self.page_layout_mode == "grid" else 1
        max_w = max((p.page_w or 0) for p in self.pages)
        max_h = max((p.page_h or 0) for p in self.pages)
        rows = (len(self.pages) + cols - 1) // cols
        total_w = cols * max_w + (cols - 1) * gutter + 2*self._page_layout_padding
        total_h = rows * max_h + (rows - 1) * gutter + 2*self._page_layout_padding
        if self.paper:
            self.removeItem(self.paper)
            self.paper = None
        self.setSceneRect(0, 0, total_w, total_h)
        for i, page in enumerate(self.pages):
            if self.page_layout_mode == "grid":
                col = i % cols
                row = i // cols
                x = x0 + col * (max_w + gutter)
                y = y0 + row * (max_h + gutter)
            else:
                x = x0
                y = y0 + i * (max_h + gutter)
            self.page_origins.append((x, y))
            bg = self.addRect([x, y, x + page.page_w, y + page.page_h],
                              style=PenStyle.no_line, fill=self.page_area_color)
            bg.setZValue(-10)
            bg.setFlag(QGraphicsItem.ItemIsSelectable, False)
            bg.setFlag(QGraphicsItem.ItemIsMovable, False)
            self._page_backgrounds.append(bg)
            mx1, my1, mx2, my2 = self.page_printable_rect(i)
            if mx2 > mx1 and my2 > my1:
                printable_bg = self.addRect([mx1, my1, mx2, my2],
                                            style=PenStyle.no_line,
                                            fill=self.printable_area_color)
                printable_bg.setZValue(-9.9)
                printable_bg.setFlag(QGraphicsItem.ItemIsSelectable, False)
                printable_bg.setFlag(QGraphicsItem.ItemIsMovable, False)
                self._printable_backgrounds.append(printable_bg)
            if self.show_page_boundaries:
                rect = self.addRect([x, y, x + page.page_w, y + page.page_h], style=PenStyle.dashed, color=(150, 150, 150, 170))
                rect.setZValue(-9)
                rect.setFlag(QGraphicsItem.ItemIsSelectable, False)
                rect.setFlag(QGraphicsItem.ItemIsMovable, False)
                self._page_guides.append(rect)
                if any(page.margins):
                    if mx2 > mx1 and my2 > my1:
                        margin_rect = self.addRect([mx1, my1, mx2, my2], style=PenStyle.dotted,
                                                   color=(70, 130, 180, 180))
                        margin_rect.setZValue(-8.8)
                        margin_rect.setFlag(QGraphicsItem.ItemIsSelectable, False)
                        margin_rect.setFlag(QGraphicsItem.ItemIsMovable, False)
                        self._margin_guides.append(margin_rect)
        # Active page highlight
        self._rebuild_active_page_guide()
        self._rebuild_canvas_grid()

    def _rebuild_active_page_guide(self):
        if not self.pages or not self.show_page_boundaries:
            return
        i = max(0, min(self.active_page_index, len(self.pages)-1))
        x1, y1, x2, y2 = self.page_rect(i)
        rect = self.addRect([x1 - 3, y1 - 3, x2 + 3, y2 + 3], width=1, color=(40, 120, 240, 180), style=PenStyle.solid)
        rect.setZValue(-8)
        rect.setFlag(QGraphicsItem.ItemIsSelectable, False)
        rect.setFlag(QGraphicsItem.ItemIsMovable, False)
        self._active_page_guide = rect

    def page_rect(self, index=None):
        if not self.pages:
            return (0, 0, self.width(), self.height())
        if index is None:
            index = self.active_page_index
        index = max(0, min(index, len(self.pages)-1))
        ox, oy = self.page_origins[index]
        p = self.pages[index]
        return (ox, oy, ox + p.page_w, oy + p.page_h)

    def _clamped_page_margins(self, page):
        top, right, bottom, left = [max(0, float(v)) for v in page.margins]
        page_w, page_h = max(0, float(page.page_w)), max(0, float(page.page_h))
        left = min(left, page_w)
        right = min(right, max(0, page_w-left))
        top = min(top, page_h)
        bottom = min(bottom, max(0, page_h-top))
        return top, right, bottom, left

    def page_printable_rect(self, index=None):
        """Return the printable page rectangle in scene coordinates."""
        x1, y1, x2, y2 = self.page_rect(index)
        if not self.pages:
            return (x1, y1, x2, y2)
        if index is None:
            index = self.active_page_index
        index = max(0, min(index, len(self.pages)-1))
        top, right, bottom, left = self._clamped_page_margins(self.pages[index])
        return (x1 + left, y1 + top, x2 - right, y2 - bottom)

    def page_printable_rect_local(self, index=None):
        """Return the printable page rectangle in page-local coordinates."""
        if not self.pages:
            return (0, 0, self.width(), self.height())
        if index is None:
            index = self.active_page_index
        index = max(0, min(index, len(self.pages)-1))
        page = self.pages[index]
        top, right, bottom, left = self._clamped_page_margins(page)
        return (left, top, page.page_w - right, page.page_h - bottom)

    def objects_outside_margins(self, page_index=None):
        """Return top-level objects whose bounds extend outside printable margins."""
        if not self.pages:
            return []
        indices = [page_index] if page_index is not None else range(len(self.pages))
        outside = []
        for i in indices:
            i = max(0, min(i, len(self.pages)-1))
            px1, py1, px2, py2 = self.page_printable_rect(i)
            for obj in self.pages[i].objects:
                x1, y1, x2, y2 = obj.bounding_box()
                if x1 < px1 or y1 < py1 or x2 > px2 or y2 > py2:
                    outside.append(obj)
        return outside

    def nonPrintingItems(self):
        items = []
        items.extend(self._page_backgrounds)
        items.extend(self._printable_backgrounds)
        items.extend(self._page_guides)
        items.extend(self._margin_guides)
        items.extend(self._canvas_grid_items)
        if self._active_page_guide:
            items.append(self._active_page_guide)
        if self._limit_warning_item:
            items.append(self._limit_warning_item)
        return items

    def page_limit_state_for_bbox(self, bbox):
        """Return page limit state for bbox: inside, outside_printable, or outside_page."""
        if not self.pages:
            return "inside", 0
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        index = self.pageIndexAt(cx, cy)
        if index is None:
            return "outside_page", None
        px1, py1, px2, py2 = self.page_rect(index)
        if x1 < px1 or y1 < py1 or x2 > px2 or y2 > py2:
            return "outside_page", index
        mx1, my1, mx2, my2 = self.page_printable_rect(index)
        if x1 < mx1 or y1 < my1 or x2 > mx2 or y2 > my2:
            return "outside_printable", index
        return "inside", index

    def clear_limit_feedback(self, clear_status=True):
        if self._limit_warning_item:
            try:
                self.removeItem(self._limit_warning_item)
            except Exception:
                pass
            self._limit_warning_item = None
        if clear_status and self._limit_feedback_status_active and App.window:
            App.window.clearStatus()
        self._limit_feedback_status_active = False

    def _update_limit_feedback_for_selection(self):
        if not self.pages or not self.selected_objs:
            self.clear_limit_feedback()
            return
        bbox = bbox_of_bboxes([o.bounding_box() for o in self.selected_objs])
        state, _page_index = self.page_limit_state_for_bbox(bbox)
        if state == "inside":
            self.clear_limit_feedback()
            return
        if self._limit_warning_item:
            try:
                self.removeItem(self._limit_warning_item)
            except Exception:
                pass
            self._limit_warning_item = None
        color = self.outside_page_warning_color if state == "outside_page" else self.margin_warning_color
        x1, y1, x2, y2 = bbox
        self._limit_warning_item = self.addRect([x1-5, y1-5, x2+5, y2+5],
                                                width=2, color=color, style=PenStyle.dashed)
        self._limit_warning_item.setZValue(8)
        self._limit_warning_item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self._limit_warning_item.setFlag(QGraphicsItem.ItemIsMovable, False)
        if App.window:
            if state == "outside_page":
                App.window.showStatus("Selection is outside the page and will snap back on release.")
            else:
                App.window.showStatus("Selection is inside the page margin and may be clipped when printing.")
            self._limit_feedback_status_active = True

    def pageIndexAt(self, x, y):
        if not self.pages:
            return 0
        for i in range(len(self.pages)):
            x1, y1, x2, y2 = self.page_rect(i)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return None

    def pageCount(self):
        return len(self.pages) if self.pages else 1

    def setActivePage(self, index):
        if not self.pages:
            self.active_page_index = 0
            return
        self._set_active_objects(index)
        # refresh active highlight only
        if self._active_page_guide:
            try:
                self.removeItem(self._active_page_guide)
            except Exception:
                pass
            self._active_page_guide = None
        self._rebuild_active_page_guide()

    def getDocument(self):
        doc = Document()
        if self.pages:
            doc.pages = []
            for i, p in enumerate(self.pages):
                page = Page(page_w=p.page_w, page_h=p.page_h, margins=p.margins, objects=p.objects[:])
                doc.pages.append(page)
            # preserve legacy single-page fields for compatibility (active page)
            ap = self.pages[self.active_page_index]
            doc.page_w, doc.page_h = ap.page_w, ap.page_h
            doc.objects = ap.objects[:]
        else:
            x, y, doc.page_w, doc.page_h = self.sceneRect().getRect()
            doc.objects = self.objects[:]
        return doc

    def clearDocument(self, reset_pages=False):
        self.deselectAll()
        if self.pages:
            for page in self.pages:
                self.objects = page.objects
                for obj in page.objects[:]:
                    obj.delete_from_paper()
                page.objects = []
            self.objects = self.pages[self.active_page_index].objects if self.pages else []
        else:
            for obj in self.objects[:]:
                obj.delete_from_paper()
            self.objects = []
        self.dirty_objects.clear()
        if reset_pages:
            self.pages = []
            self.page_origins = []
            self.active_page_index = 0
            self._rebuild_page_layout()

    def setDocument(self, doc):
        """ Return True if document is new, and False if objects are added to existing """
        doc.ensure_pages()
        if doc.pages and (not self.pages):
            # initialize multipage structure on empty canvas
            self.pages = [Page(page_w=p.page_w or 595/72*Settings.render_dpi,
                               page_h=p.page_h or 842/72*Settings.render_dpi,
                               margins=p.margins,
                               objects=[]) for p in doc.pages]
            self.active_page_index = 0
            self._rebuild_page_layout()

        if self.pages and doc.pages:
            # Load all pages into the stacked layout
            is_new = (len(self.objects) == 0 and all(len(p.objects) == 0 for p in self.pages))
            # clear existing objects
            for p in self.pages:
                for obj in p.objects:
                    try:
                        obj.delete_from_paper()
                    except Exception:
                        pass
            self.objects = []
            for p in self.pages:
                p.objects = []
            # Ensure pages count matches incoming doc
            if len(self.pages) != len(doc.pages):
                self.pages = [Page(page_w=p.page_w, page_h=p.page_h, margins=p.margins, objects=[]) for p in doc.pages]
            self._rebuild_page_layout()
            for page_index, page in enumerate(doc.pages):
                ox, oy = self.page_origins[page_index]
                # reposition objects into this page origin if necessary
                bboxes = [obj.bounding_box() for obj in page.objects]
                bbox = bbox_of_bboxes(bboxes)
                w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
                x, y = self.find_place_for_obj_size(w, h, page_index=page_index)
                move_objs(page.objects, (ox + x) - bbox[0], (oy + y) - bbox[1])
                for obj in page.objects:
                    self.addObject(obj)
                    self.pages[page_index].objects.append(obj)
                    draw_objs_recursively([obj])
            self._set_active_objects(self.active_page_index)
            return is_new

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
            x, y = self.find_place_for_obj_size(w, h, page_index=self.active_page_index if self.pages else None)
            if self.pages:
                ox, oy = self.page_origins[self.active_page_index]
                move_objs(doc.objects, (ox + x)-bbox[0], (oy + y)-bbox[1])
            else:
                move_objs(doc.objects, x-bbox[0], y-bbox[1])

        for obj in doc.objects:
            self.addObject(obj)
            if self.pages:
                self.pages[self.active_page_index].objects.append(obj)
            draw_objs_recursively([obj])
        if self.pages:
            self._set_active_objects(self.active_page_index)
        return is_new


    def _set_active_objects(self, page_index):
        if not self.pages:
            return
        self.active_page_index = max(0, min(page_index, len(self.pages)-1))
        self.objects = self.pages[self.active_page_index].objects

    def find_place_for_obj_size(self, w, h, page_index=None):
        """ find place for new object. return new object position."""
        if self.pages:
            if page_index is None:
                page_index = self.active_page_index
            page_index = max(0, min(page_index, len(self.pages)-1))
            # temporarily treat only active page objects as layout constraints
            page_objects = self.pages[page_index].objects
            ox, oy = self.page_origins[page_index]
            page = self.pages[page_index]
            rects = []
            for obj in page_objects:
                x1, y1, x2, y2 = obj.bounding_box()
                rects.append([x1-ox, y1-oy, x2-ox, y2-oy])
            old_objects = self.objects
            self.objects = page_objects
            try:
                x, y = self._find_place_for_obj_size_single(w, h, page_w=page.page_w,
                                                            page_h=page.page_h,
                                                            margins=page.margins,
                                                            existing_rects=rects)
            finally:
                self.objects = old_objects
            return (x, y)
        return self._find_place_for_obj_size_single(w, h, page_w=self.width(), page_h=self.height(), origin=(0, 0))

    def _find_place_for_obj_size_single(self, w, h, page_w, page_h, origin=(0,0),
                                        margins=(0,0,0,0), existing_rects=None):
        # It works by first placing rect beside the object in lowest position.
        # If does not fit there, then find the object just above rect
        # and place just beside it. Continue the loop until either
        # fit properly or reaches right edge of page.
        top, right, bottom, left = [max(0, float(v)) for v in margins]
        left = min(left, page_w)
        right = min(right, max(0, page_w-left))
        top = min(top, page_h)
        bottom = min(bottom, max(0, page_h-top))
        content_x1, content_y1 = left, top
        content_x2, content_y2 = page_w-right, page_h-bottom
        page_margin = 1/2.54*Settings.render_dpi # 1 cm
        spacing = 0.75/2.54*Settings.render_dpi # 0.75 cm
        rects = existing_rects
        if rects is None:
            rects = [o.bounding_box() for o in self.objects]
        if not rects:# page empty
            x = content_x1 + min(page_margin, max(0, (content_x2-content_x1-w)/2))
            y = content_y1 + min(page_margin, max(0, (content_y2-content_y1-h)/2))
            return (x,y)
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
        if x+w>content_x2:
            x = content_x1 + min(page_margin, max(0, (content_x2-content_x1-w)/2))
            y = lowest_rect[3] + spacing
        # adjust pos when object is outside of page
        x = max(min(x, content_x2-w), content_x1)
        y = max(min(y, content_y2-h), content_y1)
        return (x,y)

    # --------------------- OBJECT MANAGEMENT -----------------------

    def addObject(self, obj):
        self.objects.append(obj)
        obj.paper = self

    def removeObject(self, obj):
        obj.paper = None
        if obj in self.objects:
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
        if isinstance(fill, tuple):# a color
            fill = QColor(*fill)
        brush = QBrush(fill) if fill else QBrush()
        return QGraphicsScene.addRect(self, x1,y1, x2-x1, y2-y1, pen, brush)

    def addPolygon(self, points, width=1, color=Color.black, style=PenStyle.solid, fill=None):
        polygon = QPolygonF([QPointF(*p) for p in points])
        pen = QPen(QColor(*color), width, style)
        if isinstance(fill, tuple):# a color
            fill = QColor(*fill)
        brush = QBrush(fill) if fill else QBrush()
        return QGraphicsScene.addPolygon(self, polygon, pen, brush)

    def addPolyline(self, points, width=1, color=Color.black, style=PenStyle.solid):
        shape = QPainterPath(QPointF(*points[0]))
        [shape.lineTo(QPointF(*pt)) for pt in points[1:]]
        pen = QPen(QColor(*color), width, style)
        return QGraphicsScene.addPath(self, shape, pen)

    def addEllipse(self, rect, width=1, color=Color.black, fill=None):
        x1,y1, x2,y2 = rect
        pen = QPen(QColor(*color), width)
        if isinstance(fill, tuple):# a color
            fill = QColor(*fill)
        brush = QBrush(fill) if fill else QBrush()
        return QGraphicsScene.addEllipse(self, x1,y1, x2-x1, y2-y1, pen, brush)

    def addCubicBezier(self, points, width=1, color=Color.black, style=PenStyle.solid, fill=None):
        """ draw single bezier or multiple connected bezier curves.
        for n curves, it requires 1+3n points"""
        pts = [QPointF(*pt) for pt in points]
        shape = QPainterPath(pts[0])
        for i in range( (len(pts)-1)//3 ):
            shape.cubicTo(*pts[3*i+1:3*i+4])
        pen = QPen(QColor(*color), width, style)
        if isinstance(fill, tuple):# a color
            fill = QColor(*fill)
        brush = QBrush(fill) if fill else QBrush()
        return QGraphicsScene.addPath(self, shape, pen, brush)

    def addArc(self, rect, start_ang, span_ang, width=1, color=Color.black):
        """ draw arc """
        x1,y1,x2,y2 = rect
        path = QPainterPath()
        path.arcMoveTo(x1,y1,x2-x1,y2-y1, start_ang)
        path.arcTo(x1,y1,x2-x1,y2-y1, start_ang, span_ang)
        pen = QPen(QColor(*color), width)
        return QGraphicsScene.addPath(self, path, pen)

    def addPath(self, path, width=1, color=Color.black, style=PenStyle.solid, fill=None):
        """ draw path from QPainterPath """
        pen = QPen(QColor(*color), width, style)
        if isinstance(fill, tuple):# a color
            fill = QColor(*fill)
        brush = QBrush(fill) if fill else QBrush()
        return QGraphicsScene.addPath(self, path, pen, brush)


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

    def item_at(self, x,y):
        return self.itemAt(QPointF(x,y), QTransform())

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

    def toTopLayer(self, item):
        item.setZValue(4)

    def toBottomLayer(self, item):
        item.setZValue(-4)

    def toBondLayer(self, item):
        item.setZValue(-2)

    def toSelectionLayer(self, item):
        item.setZValue(-3)

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

    def selectAll(self):
        self.deselectAll()
        gfx_items = set(self.items())
        selected = [itm.object for itm in gfx_items & self.focusable_items]
        [self.selectObject(o) for o in selected]

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
                focusables = set(self.items(QPointF(x,y))) & self.focusable_items
                under_cursor = [itm.object for itm in self.items(QPointF(x,y)) if itm in focusables]
                objs = under_cursor + objs
                objs = [o for o in objs if o not in self.do_not_focus]
            focused_obj = objs[0] if objs else None
            self.changeFocusTo(focused_obj)

        App.tool.on_mouse_move(x, y)
        if self.pages and self.dragging and self.selected_objs:
            self._update_limit_feedback_for_selection()
        QGraphicsScene.mouseMoveEvent(self, ev)


    def mouseReleaseEvent(self, ev):
        if self.mouse_pressed:
            self.mouse_pressed = False
            pos = ev.scenePos()
            App.tool.on_mouse_release(pos.x(), pos.y())
            if self.pages and self.dragging and self.selected_objs:
                self._maybe_move_selection_to_page()
                self.clear_limit_feedback()
            self.dragging = False
        QGraphicsScene.mouseReleaseEvent(self, ev)

    def _maybe_move_selection_to_page(self):
        bboxes = [o.bounding_box() for o in self.selected_objs]
        bbox = bbox_of_bboxes(bboxes)
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        dst = self.pageIndexAt(cx, cy)
        if dst is None:
            # outside any page: snap selection into active page
            w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
            x, y = self.find_place_for_obj_size(w, h, page_index=self.active_page_index)
            ox, oy = self.page_origins[self.active_page_index]
            move_objs(self.selected_objs, (ox + x) - bbox[0], (oy + y) - bbox[1])
            draw_objs_recursively(self.selected_objs)
            self.save_state_to_undo_stack("Move Objects To Page")
            return
        moved = False
        for obj in list(self.selected_objs):
            src = None
            for i, p in enumerate(self.pages):
                if obj in p.objects:
                    src = i
                    break
            if src is None or src == dst:
                continue
            self.pages[src].objects.remove(obj)
            self.pages[dst].objects.append(obj)
            moved = True
        if moved:
            self.save_state_to_undo_stack("Move Objects To Page")


    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            pos = ev.scenePos()
            App.tool.on_mouse_double_click(pos.x(), pos.y())
        QGraphicsScene.mouseDoubleClickEvent(self, ev)


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

    def getImage(self, dpi=-1, margin=0):
        # source area
        x1, y1, x2, y2 = map(int, self.allObjectsBoundingBox())
        src_rect = QRectF(x1,y1, x2-x1+1, y2-y1+1)
        # dest area
        scale = dpi/Settings.render_dpi if dpi>0 else 1.0
        w, h = int(round((x2-x1+1)*scale)), int(round((y2-y1+1)*scale))
        dst_rect = QRectF(margin, margin, w, h)
        # render
        paper_visible = self.paper.isVisible() if self.paper else None
        if self.paper:
            self.paper.setVisible(False)
        hidden_items = self.nonPrintingItems()
        grid_visibility = [item.isVisible() for item in hidden_items]
        for item in hidden_items:
            item.setVisible(False)
        image = QImage(w+2*margin, h+2*margin, QImage.Format_ARGB32)
        if Settings.image_export_background=="transparent":
            image.fill(Qt.transparent)
        else:
            image.fill(QColor(Settings.image_export_background))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.render(painter, dst_rect, src_rect)
        painter.end()
        if self.paper and paper_visible is not None:
            self.paper.setVisible(paper_visible)
        for item, visible in zip(hidden_items, grid_visibility):
            item.setVisible(visible)
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


    def updatePageSize(self):
        """ Refresh canvas size from current global settings. """
        presets = {
            "A4": (595, 842),
            "A3": (842, 1191),
            "Letter": (612, 792),
            "Legal": (612, 1008),
        }
        w_pt, h_pt = Settings.custom_width, Settings.custom_height
        if Settings.page_size_preset in presets:
            w_pt, h_pt = presets[Settings.page_size_preset]
        if Settings.page_orientation == "Landscape":
            w_pt, h_pt = h_pt, w_pt

        w_px = w_pt * Settings.render_dpi / 72
        h_px = h_pt * Settings.render_dpi / 72
        if self.pages:
            for page in self.pages:
                page.page_w = w_px
                page.page_h = h_px
            self._rebuild_page_layout()
            self.setActivePage(self.active_page_index)
            return
        self.setSize(w_px, h_px)


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

        image = self.getImage()
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


def points_str(pts):
    return " ".join(",".join(tuple(map(float_to_str,pt))) for pt in pts)

# converts some basic html4 formattings to svg format
def html_to_svg(text):
    # < and > characters already replaced with &lt; and &gt; in Text obj.
    # replacing & character also replaces & character of &lt; and &gt;
    text = text.replace("&", "&amp;").replace("&amp;lt;", "&lt;").replace("&amp;gt;", "&gt;")
    text = text.replace('<b>', '<tspan font-weight="bold">')
    text = text.replace('<i>', '<tspan font-style="italic">')
    text = text.replace('<u>', '<tspan text-decoration="underline">')
    text = text.replace('<sub>', '<tspan baseline-shift="sub" font-size="75%">')
    text = text.replace('<sup>', '<tspan baseline-shift="super" font-size="75%">')
    for tag in ('</b>', '</i>', '</u>', '</sub>', '</sup>'):
        text = text.replace(tag, '</tspan>')
    return text


class SvgPaper:
    def __init__(self):
        self.items = []
        self.radial_grads = {}
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
        if self.radial_grads:
            svg += "<defs>"
            for grad,grad_id in self.radial_grads.items():
                svg += '\n  <radialGradient id="%s" %s  </radialGradient>' % (grad_id,grad)
            svg += "\n</defs>\n"
        # for text, fill=none must be mentioned
        svg += '<g fill="none" stroke-linecap="square" font-style="normal" >\n'
        for item in self.items:
            svg += item + '\n'
        svg += '</g>\n</svg>'
        return svg

    def drawLine(self, line, pen):
        line = line.x1(), line.y1(), line.x2(), line.y2()
        attrs = ['x1="%s" y1="%s" x2="%s" y2="%s"' % tuple(map(float_to_str, line))]
        attrs += [self.stroke_attrs(pen)]
        cmd = '<line %s />' % " ".join(attrs)
        self.items.append(cmd)

    def drawRect(self, rect, pen, brush):
        x1, y1, x2, y2 =  rect
        attrs = ['x="%s" y="%s" width="%s" height="%s"' % tuple(map(float_to_str,(x1,y1,x2-x1,y2-y1)))]
        attrs += [self.stroke_attrs(pen)]
        attrs += [self.fill_attr(brush)]
        cmd = '<rect %s />' % " ".join(attrs)
        self.items.append(cmd)

    def drawPolygon(self, points, pen, brush):
        attrs = ['points="%s"' % points_str(points)]
        attrs += [self.stroke_attrs(pen)]
        attrs += [self.fill_attr(brush)]
        cmd = '<polygon %s />' % " ".join(attrs)
        self.items.append(cmd)

    def drawEllipse(self, rect, pen, brush):
        x1, y1, x2, y2 = rect
        rx, ry = (x2-x1)/2, (y2-y1)/2
        ellipse = (x1+rx, y1+ry, rx, ry)
        attrs = ['cx="%s" cy="%s" rx="%s" ry="%s"' % tuple(map(float_to_str, ellipse))]
        attrs += [self.stroke_attrs(pen)]
        attrs += [self.fill_attr(brush)]
        cmd = '<ellipse %s />' % " ".join(attrs)
        self.items.append(cmd)

    def drawPath(self, path, pen, brush):
        datas = []
        for i in range(path.elementCount()):
            elm = path.elementAt(i)
            elm_type, x, y = elm.type, elm.x, elm.y
            if elm_type == QPainterPath.MoveToElement:
                datas.append("M %g,%g" % (x,y))
            if elm_type == QPainterPath.LineToElement:
                datas.append("L %g,%g" % (x,y))
            elif elm_type == QPainterPath.CurveToElement:
                datas.append("C %g,%g" % (x,y))
            elif elm_type == QPainterPath.CurveToDataElement:
                datas.append("%g,%g" % (x,y))
        attrs = ['d="%s"' % " ".join(datas)]
        # pen to stroke
        attrs += [ self.stroke_attrs(pen)]
        # brush to fill
        attrs += [ self.fill_attr(brush)]
        cmd = "<path %s />" % " ".join(attrs)
        self.items.append(cmd)

    def drawHtmlText(self, text, pos, font, color, transform=None):
        """ Draw Html Text """
        x, y = float_to_str(pos[0]), float_to_str(pos[1])
        attrs = ['x="%s" y="%s"' % (x, y)]
        attrs += ['fill="%s"' % qcolor_to_hex(color)]
        if transform:
            attrs += ['transform="%s"' % transform]
        text = html_to_svg(text)
        cmd = '<text %s>%s</text>' % (" ".join(attrs),text)
        # set font
        font_name, font_size = font.family(), float_to_str(font.pixelSize())
        cmd = '<g font-family="%s" font-size="%spx">%s</g>'%(font_name, font_size, cmd)
        self.items.append(cmd)


    def stroke_attrs(self, pen):
        width = pen.widthF()
        line_style, cap_style = pen.style(), pen.capStyle()
        attrs = []
        # set stroke width
        attrs += ['stroke-width="%s"' % float_to_str(width)]
        # set stroke color
        attrs += ['stroke="%s"' % qcolor_to_hex(pen.color())]
        # set stroke line style
        if line_style == PenStyle.dotted:
            attrs += ['stroke-dasharray="2"']
            cap_style = LineCap.butt
        elif line_style == PenStyle.dashed:
            attrs += ['stroke-dasharray="4"']
            cap_style = LineCap.butt
        # set line capstyle (butt | square | round)
        # in svg butt is default and in SvgPaper square is default capstyle
        if cap_style==LineCap.butt:
            attrs += ['stroke-linecap="butt"']
        elif cap_style==LineCap.round:
            attrs += ['stroke-linecap="round"']
        return " ".join(attrs)

    def fill_attr(self, brush):
        if brush.style()==Qt.SolidPattern:
            fill = qcolor_to_hex(brush.color())
        elif brush.style()==Qt.RadialGradientPattern:
            fill = self.get_radial_gradient(brush.gradient())
        else:# Qt.NoBrush
            fill = "none"
        return 'fill="%s"' % fill

    def get_radial_gradient(self, gradient):
        grad = 'cx="%g" cy="%g" ' % (gradient.center().x(), gradient.center().y())
        grad += 'r="%g" >\n' % gradient.radius()
        for offset,color in gradient.stops():
            grad += '    <stop offset="%g" stop-color="%s" />\n' % (offset, qcolor_to_hex(color))
        if gradient.coordinateMode()==gradient.LogicalMode:# use center and radius in pixel val
            grad = 'gradientUnits="userSpaceOnUse" ' + grad
        # if already added, use the previous gradient
        if grad in self.radial_grads:
            grad_id = self.radial_grads[grad]
        else:
            grad_id = "radGrad%i" % len(self.radial_grads)
            self.radial_grads[grad] = grad_id
        return "url(#%s)" % grad_id


def qcolor_to_hex(qcolor):
    # converts QColor to (r,g,b) or (r,g,b,a)
    color = qcolor.getRgb()
    color = color[:3] if color[3] == 255 else color
    # convert to hex format
    return hex_color(color)



# ----------------- GRAPHICS ITEM DRAWING INTERFACE --------------------


def draw_graphicsitem(item, paper):
    # If a QGraphicsLineItem is moved by calling moveBy() method,
    # the item.line() does not change, instead item.pos() changes.
    # So we need to translate the line coordinates by item pos to get
    # actual coordinates. Thus all other graphics items' coordinates are translated.
    # draw line
    if item.type()==6:# QGraphicsLineItem
        line = item.line().translated(item.scenePos())
        paper.drawLine(line, item.pen())
    # draw rectangle
    elif item.type()==3:# QGraphicsRectItem
        rect = item.rect().translated(item.scenePos()).getCoords()
        paper.drawRect(rect, item.pen(), item.brush())
    # draw polygon
    elif item.type()==5:# QGraphicsPolygonItem
        polygon = item.polygon().translated(item.scenePos())
        points = [polygon.at(i) for i in range(polygon.count())]
        points = [(pt.x(), pt.y()) for pt in points]
        paper.drawPolygon(points, item.pen(), item.brush())
    # draw ellipse
    elif item.type()==4:# QGraphicsEllipseItem
        rect = item.rect().translated(item.scenePos()).getCoords()
        paper.drawEllipse(rect, item.pen(), item.brush())
    # draw path
    elif item.type()==2:# QGraphicsPathItem
        path = item.path()
        path.translate(item.scenePos())
        paper.drawPath(path, item.pen(), item.brush())
    # draw text
    elif item.type()==8:# QGraphicsTextItem
        text = item.text# not a property of QGraphicsTextItem, but we added it in our paper
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
            paper.drawHtmlText(line, (x, y), item.font(), item.defaultTextColor(), transform)
            y += font_metrics.height()
