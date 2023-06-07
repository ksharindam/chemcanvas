# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>
from app_data import Settings


# Subclass of this class are ...
# Molecule, Atom, Bond, Mark, Plus, Arrow, Text

class DrawableObject:
    focus_priority = 10 # smaller number have higher priority
    redraw_priority = 10
    is_toplevel = True
    # undo helpers metadata
    meta__undo_properties = () # attribute that dont need coping, eg - int, string, bool etc
    meta__undo_copy = () # attributes that requires copying (e.g - list, set, dict)
    meta__undo_children_to_record = () # must be a list or set
    meta__same_objects = {}

    def __init__(self):
        self.paper = None

    @property
    def class_name(self):
        """ returns the class name """
        return self.__class__.__name__

    @property
    def parent(self):
        return None

    @property
    def children(self):
        return []

    @property
    def items(self):
        """ returns all graphics items """
        return []

    def draw(self):
        """ clears prev drawing, focus, selection. Then draws object, and restore focus and selection """
        pass

    def clearDrawings(self):
        """ clears drawing and unfocus and deselect itself"""
        pass

    def boundingBox(self):
        """ bounding box of all graphics items return as [x1,x2,y1,y2]
        reimplementation mandatory. required by ScaleTool """
        return None

#    def transform(self, tr):
#        pass

#   def scale(self, scale):
#       pass

    def moveBy(self, dx, dy):
        """ translate object coordinates by (dx,dy). (does not redraw)"""
        pass

    def deleteFromPaper(self):
        """ unfocus, deselect, unmap focusable, clear graphics"""
        if not self.paper:
            return
        self.paper.unfocusObject(self)
        self.paper.deselectObject(self)
        self.clearDrawings()
        if self.is_toplevel:
            self.paper.removeObject(self)

#---------------------------- END DRAWABLE ----------------------------------




#------------------------------- PLUS --------------------------------

class Plus(DrawableObject):
    meta__undo_properties = ("x", "y", "font_size")
    meta__scalables = ("x", "y", "font_size")

    def __init__(self):
        DrawableObject.__init__(self)
        #self.paper = None # inherited
        self.x = 0
        self.y = 0
        self.font_size = Settings.plus_size
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    def setPos(self, x, y):
        self.x = x
        self.y = y

    @property
    def items(self):
        return filter(None, [self._main_item, self._focus_item, self._selection_item])

    def clearDrawings(self):
        if self._main_item:
            self.paper.removeFocusable(self._main_item)
            self.paper.removeItem(self._main_item)
            self._main_item = None
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()
        font = self.paper.font()
        font.setPointSize(self.font_size)
        self._main_item = self.paper.addText("+", font)
        rect = self._main_item.boundingRect()
        self._main_item.setPos(self.x-rect.width()/2, self.y-rect.height()/2)
        self.paper.addFocusable(self._main_item, self)
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            rect = self._main_item.sceneBoundingRect().getCoords()
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            rect = self._main_item.sceneBoundingRect().getCoords()
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def boundingBox(self):
        if self._main_item:
            return self.paper.itemBoundingBox(self._main_item)
        d = self.font_size/2
        return self.x-d, self.y-d, self.x+d, self.y+d

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.font_size *= scale

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)

#---------------------------- END PLUS ----------------------------------



# ---------------------------- TEXT --------------------------------

class Text(DrawableObject):
    meta__undo_properties = ("x", "y", "text", "font_name", "font_size")
    meta__undo_copy = ("_formatted_text_parts",)
    meta__scalables = ("x", "y", "font_size")

    def __init__(self):
        DrawableObject.__init__(self)
        #self.paper = None # inherited
        self.x = 0
        self.y = 0
        self.text = ""
        self.font_name = "Sans Serif"
        self.font_size = Settings.text_size
        self._formatted_text_parts = []
        self._main_items = []
        self._focus_item = None
        self._selection_item = None

    def setText(self, text):
        self.text = text
        self._formatted_text_parts = []

    def append(self, char):
        self.text += char
        self._formatted_text_parts = []

    def deleteLastChar(self):
        if self.text:
            self.text = self.text[:-1]
        self._formatted_text_parts = []

    def setPos(self, x, y):
        self.x = x
        self.y = y

    @property
    def items(self):
        return filter(None, self._main_items + [self._focus_item, self._selection_item])

    def clearDrawings(self):
        for item in self._main_items:
            self.paper.removeFocusable(item)
            self.paper.removeItem(item)
        self._main_items.clear()
        if self._focus_item:
            self.setFocus(False)
        if self._selection_item:
            self.setSelected(False)

    def draw(self):
        focused = bool(self._focus_item)
        selected = bool(self._selection_item)
        self.clearDrawings()

        if not self._formatted_text_parts:
            # TODO : convert < and > to ;lt and ;gt
            self._formatted_text_parts = ["<br>".join(self.text.split('\n'))]

        line_spacing = self.font_size
        x, y = self.x, self.y
        for text_part in self._formatted_text_parts:
            if text_part:
                _font = Font(self.font_name, self.font_size)
                item = self.paper.addHtmlText(text_part, (x,y), font=_font)
                self._main_items.append(item)
                self.paper.addFocusable(item, self)
            y += line_spacing
        if focused:
            self.setFocus(True)
        if selected:
            self.setSelected(True)

    def setFocus(self, focus):
        if focus:
            rect = self.paper.itemBoundingBox(self._main_items[0])
            self._focus_item = self.paper.addRect(rect, fill=Settings.focus_color)
            self.paper.toBackground(self._focus_item)
        else:
            self.paper.removeItem(self._focus_item)
            self._focus_item = None

    def setSelected(self, select):
        if select:
            rect = self.paper.itemBoundingBox(self._main_items[0])
            self._selection_item = self.paper.addRect(rect, fill=Settings.selection_color)
            self.paper.toBackground(self._selection_item)
        elif self._selection_item:
            self.paper.removeItem(self._selection_item)
            self._selection_item = None

    def boundingBox(self):
        if self._main_items:
            return self.paper.itemBoundingBox(self._main_items[0])
        return self.x, self.y-self.font_size, self.x+font_size, self.y # TODO : need replacement

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy

    def scale(self, scale):
        self.font_size *= scale

    def transform(self, tr):
        self.x, self.y = tr.transform(self.x, self.y)



class Font:
    def __init__(self, name="Sans Serif", size=10):
        self.name = name# Family
        self.size = size# point size
        self.bold = False
        self.italic = False
