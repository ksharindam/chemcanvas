from app_data import Settings


class DrawableObject:
    object_type = 'Drawable' # the object type name (e.g - Atom, Bond, Arrow etc)
    focus_priority = 10 # smaller number have higer priority
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
    def parent(self):
        return None

    @property
    def children(self):
        return []

    def setItemColor(self, item, color):
        pen = item.pen()
        pen.setColor(color)
        item.setPen(pen)

    def draw(self):
        """ clears prev drawing, focus, selection. Then draws object, and restore focus and selection """
        pass

    def drawSelfAndChildren(self):
        self.draw()

    def clearDrawings(self):
        """ clears drawing and unfocus and deselect itself"""
        pass

    def boundingBox(self):
        """ bounding box of all graphics items return as [x1,x2,y1,y2]"""
        return None

    def deleteFromPaper(self):
        """ unfocus, deselect, unmap focusable, clear graphics"""
        if not self.paper:
            return
        self.paper.unfocusObject(self)
        self.paper.deselectObject(self)
        self.clearDrawings()
        if self.is_toplevel:
            self.paper.removeObject(self)


class Plus(DrawableObject):
    def __init__(self):
        DrawableObject.__init__(self)
        self.paper = None
        self.x = 0
        self.y = 0
        self.font_size = Settings.plus_size
        self._main_item = None
        self._focus_item = None
        self._selection_item = None

    def setPos(self, x, y):
        self.x = x
        self.y = y

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

    def moveBy(self, dx, dy):
        self.x, self.y = self.x+dx, self.y+dy
        items = filter(None, [self._main_item, self._focus_item, self._selection_item])
        [item.moveBy(dx,dy) for item in items]


