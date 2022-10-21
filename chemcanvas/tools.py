
from app_data import App
from atom import Atom
from bond import Bond
from geometry import *
#import common

class Tool:
    modes = []
    selected_modes = []

    def __init__(self):
        pass

    def onMousePress(self, x, y):
        pass
    def onMouseRelease(self, x, y):
        pass
    def onMouseMove(self, x, y):
        pass

    def clear(self):
        pass

    def selected_mode(self, index):
        return self.modes[index][self.selected_modes[index]]


class SelectTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        self._selection_rect_item = None

    def onMouseRelease(self, x, y):
        if not App.paper.dragging:
            self.onMouseClick(x, y)
            return
        # we are dragging, that means _selection_rect_item is already created
        App.paper.removeItem(self._selection_rect_item)
        self._selection_rect_item = None

    def onMouseClick(self, x, y):
        focused_obj = App.paper.focused_obj and [App.paper.focused_obj] or []
        if App.paper.selected_objs != focused_obj:
            App.paper.selectObjects(focused_obj)

    def onMouseMove(self, x, y):
        if not App.paper.dragging:
            return
        #start_x, start_y = App.paper.mouse_press_pos
        rect = Rect(App.paper.mouse_press_pos + [x,y]).normalized()
        rect = [rect.x1, rect.y1, rect.x2-rect.x1, rect.y2-rect.y1]
        if not self._selection_rect_item:
            self._selection_rect_item = App.paper.addRect(*rect)
        else:
            self._selection_rect_item.setRect(*rect)
        objs = App.paper.objectsInRegion(*rect)
        # bond is dependent to two atoms, so select bond only if their atoms are selected
        not_selected_bonds = set()
        for obj in objs:
            if type(obj)==Bond and (obj.atom1 not in objs or obj.atom2 not in objs):
                not_selected_bonds.add(obj)
        objs = list(set(objs) - not_selected_bonds)
        App.paper.selectObjects(objs)



class MoveTool(SelectTool):
    """ Selection or Move tool. Used to select or move molecules, atoms, bonds etc """
    def __init__(self):
        SelectTool.__init__(self)
        self.clear()

    def clear(self):
        self.objs_to_move = set()
        self.objs_moved = False

    def onMousePress(self, x, y):
        if not App.paper.focused_obj:
            return
        self.objs_moved = False
        self._prev_pos = [x,y]
        # if we have pressed on blank area, we are going to draw selection rect, and select objs
        if not App.paper.focused_obj:
            return
        # if we drag a selected obj, all selected objs are moved
        if App.paper.focused_obj in App.paper.selected_objs:
            self.objs_to_move = set(App.paper.selected_objs)
        else:
            self.objs_to_move = set(App.paper.focused_obj.parent.children)
        objs_to_move = self.objs_to_move.copy()# we can not modify same set while iterating
        for obj in objs_to_move:
            if type(obj)==Bond:
                self.objs_to_move |= obj.atoms
                self.objs_to_move.remove(obj)

    def onMouseMove(self, x, y):
        if App.paper.dragging and self.objs_to_move:
            for obj in self.objs_to_move:
                obj.moveBy(x-self._prev_pos[0], y-self._prev_pos[1])
            self.objs_moved = True
            self._prev_pos = [x,y]
            return
        SelectTool.onMouseMove(self, x, y)

    def onMouseRelease(self, x, y):
        if not self.objs_moved:
            SelectTool.onMouseRelease(self, x, y)
        self.clear()



class RotateTool(SelectTool):
    """ Rotate objects tools """
    def __init__(self):
        pass


class BondTool(Tool):
    modes = [['30', '18', '1'],
            ['normal', 'double', 'triple', 'wedge_near', 'wedge_far', 'dashed', 'dotted']]
    selected_modes = [0, 0]

    def __init__(self):
        Tool.__init__(self)
        self.clear()
        #print("created BondTool")

    def clear(self):
        self.atom1 = None
        self.atom2 = None
        self.bond = None

    def selectMode(self, index):
        for mode_index, mode in enumerate(self.modes):
            if index<len(mode):
                break
            index -= len(mode)
        self.selected_modes[mode_index] = index


    def onMousePress(self, x, y):
        #print("click : x=%i, y=%i"%(x, y))
        if not App.paper.focused_obj:
            mol = App.paper.newMolecule()
            self.atom1 = mol.newAtom([x,y])
            self.atom1.draw()
            App.paper.addObject(self.atom1)
        elif type(App.paper.focused_obj) is Atom:
            # we have clicked on existing atom, use this atom to make new bond
            self.atom1 = App.paper.focused_obj


    def onMouseMove(self, x, y):
        if not App.paper.dragging:
            return
        if [x,y] == App.paper.mouse_press_pos:
            return
        if not self.atom1: # in case we have clicked on object other than atom
            return
        angle = int(self.selected_mode(0))
        atom2_pos = point_on_circle( self.atom1.pos, App.bond_length, [x,y], angle)
        # we are clicking and dragging mouse
        if not self.atom2:
            self.atom2 = self.atom1.molecule.newAtom(atom2_pos)
            self.bond = self.atom1.molecule.newBond(self.atom1, self.atom2, self.selected_mode(1))
            self.atom2.draw()
            self.bond.draw()
        else: # move atom2
            if type(App.paper.focused_obj) is Atom and App.paper.focused_obj is not self.atom1:
                self.atom2.moveTo(App.paper.focused_obj.pos)
            else:
                self.atom2.moveTo(atom2_pos)


    def onMouseRelease(self, x, y):
        #print("reliz : x=%i, y=%i"%(pos.x(), pos.y()))
        if not App.paper.dragging:
            self.onMouseClick(x,y)
            return
        #print("mouse dragged")
        if not self.atom2:
            return
        touched_atom = App.paper.touchedAtom(self.atom2)
        if touched_atom:
            App.paper.changeFocusTo(None) # removing focus, so that it will not try to unfocus later
            App.paper.selectObjects([])
            touched_atom.merge(self.atom2)
            self.atom2 = touched_atom
            self.bond.redraw()
            reposition_bonds_around_atom(touched_atom)
        else:
            # we are using newly created atom2
            App.paper.addObject(self.atom2)

        App.paper.addObject(self.bond)
        reposition_bonds_around_atom(self.atom1)
        self.clear()

    def onMouseClick(self, x, y):
        #print("onMouseClick()")
        if type(App.paper.focused_obj) is Bond:
            # change bond type or bond order
            return
        elif self.atom1:
            self.atom2, self.bond = self.atom1.molecule.addAtomTo(self.atom1)
            self.bond.type = self.selected_mode(1)
            self.atom2.draw()
            App.paper.addObject(self.atom2)
            self.bond.draw()
            App.paper.addObject(self.bond)
        self.clear()

def reposition_bonds_around_atom(atom):
    bonds = atom.neighbor_edges
    [bond.redraw() for bond in bonds]
    #if isinstance( atom, textatom) or isinstance( atom, Atom):
    #    atom.reposition_marks()

def reposition_bonds_around_bond(bond):
    bonds = common.filter_unique( bond.atom1.neighbor_edges + bond.atom2.neighbor_edges)
    [b.redraw() for b in bonds if b.order == 2]
    # all atoms to update
    #atms = common.filter_unique( reduce( operator.add, [[b.atom1,b.atom2] for b in bs], []))
    #[a.reposition_marks() for a in atms if isinstance( a, Atom)]



class AtomTool(Tool):
    def __init__(self):
        Tool.__init__(self)



tools_class_dict = {
    "move" : MoveTool,
    "bond" : BondTool,
    "atom" : AtomTool
}

def newToolFromName(name):
    return tools_class_dict[name]()


tools_template = [
# name   title          icon    subtools
    ("move", "Move",      ":/icons/move.png", ()),
    ("bond", "Draw Bond", ":/icons/bond.png", (
            [("30", "30 degree", ":/icons/30.png"),
            ("18", "18 degree", ":/icons/18.png"),
            ("1", "1 degree", ":/icons/1.png")],
            [("normal", "Single Bond", ":/icons/single.png"),
            ("double", "Double Bond", ":/icons/double.png"),
            ("triple", "Triple Bond", ":/icons/triple.png")]
    )),
    ("atom", "Draw Atom", ":/icons/atom.png", ())
]



# list of tool names
tools_list = [x[0] for x in tools_template]


