
from app_data import App
from atom import Atom
from bond import Bond
from molecule import Molecule
from geometry import *
#import common

class Tool:
    modes = {}
    selected_mode = {}

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

    def selectMode(self, index):
        if len(self.modes)==0:
            return
        for category, vals in self.modes.items():
            if index<len(vals):
                break
            index -= len(vals)
        self.selected_mode[category] = vals[index]


class SelectTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        self._selection_rect_item = None

    def onMouseRelease(self, x, y):
        if not App.paper.dragging:
            self.onMouseClick(x, y)
            return
        if self._selection_rect_item:
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
    modes = {'type': ['2d', '3d']}
    selected_mode = {'type': '2d'}

    def __init__(self):
        SelectTool.__init__(self)
        self.clear()

    def clear(self):
        self.atoms_to_rotate = []
        self.initial_pos_of_atoms = []
        self.rot_center = None
        self.rot_axis = None

    def onMousePress(self, x, y):
        focused = App.paper.focused_obj
        if not focused or type(focused.parent)!=Molecule:
            return
        self.atoms_to_rotate = focused.parent.atoms
        self.initial_pos_of_atoms = [atom.pos3d for atom in self.atoms_to_rotate]
        # find rotation center
        selected_obj = len(App.paper.selected_objs) and App.paper.selected_objs[0] or None

        if selected_obj and selected_obj.parent is focused.parent:
            if type(selected_obj)==Atom:
                self.rot_center = selected_obj.pos3d
            elif type(selected_obj)==Bond and self.selected_mode['type']=='3d':
                self.rot_axis = selected_obj.atom1.pos3d + selected_obj.atom2.pos3d

        if not self.rot_center and not self.rot_axis:
            self.rot_center = Rect(focused.parent.boundingBox()).center() + [0]

    def onMouseMove(self, x, y):
        if not App.paper.dragging or len(self.atoms_to_rotate)==0:
            return
        dx = x - App.paper.mouse_press_pos[0]
        dy = y - App.paper.mouse_press_pos[1]

        if self.selected_mode['type'] == '2d':
            sig = on_which_side_is_point( self.rot_center[:2]+App.paper.mouse_press_pos, [x, y])
            angle = round( sig * (abs( dx) +abs( dy)) / 50.0, 2)
            tr = Transform()
            tr.translate( -self.rot_center[0], -self.rot_center[1])
            tr.rotate( angle)
            tr.translate( self.rot_center[0], self.rot_center[1])
            transformed_points = tr.transformPoints(self.initial_pos_of_atoms)
            for i, atom in enumerate(self.atoms_to_rotate):
                atom.moveTo(transformed_points[i])

        elif self.selected_mode['type'] == '3d':
            angle = round((abs( dx) +abs( dy)) / 50, 2)
            tr = Transform3D()
            if self.rot_axis:
                tr = create_transformation_to_rotate_around_line( self.rot_axis, angle)
            else: # rotate around center
                tr.translate( -self.rot_center[0], -self.rot_center[1], -self.rot_center[2])
                tr.rotateX(round(dy/50, 2))
                tr.rotateY(round(dx/50, 2))
                tr.translate( self.rot_center[0], self.rot_center[1], self.rot_center[2])

            transformed_points = tr.transformPoints(self.initial_pos_of_atoms)
            for i, atom in enumerate(self.atoms_to_rotate):
                x, y, z = transformed_points[i]
                atom.z = z
                atom.moveTo([x, y])

    def onMouseRelease(self, x, y):
        self.clear()
        SelectTool.onMouseRelease(self, x ,y)



class StructureTool(Tool):
    modes = {"bond_angle" : ["30", "18", "1"],
            "bond_type" : ["normal", "double", "triple",
                        "wedge_near", "wedge_far", "dashed", "dotted"]
            }
    atom_types = ["C", "H", "O", "N", "S", "P", "Cl", "Br", "I"]
    group_types = ["OH", "CHO", "COOH", "NH2", "CONH2", "SO3H", "OTs", "OBs"]

    selected_mode = {"bond_angle": "30", "bond_type": "normal", "atom": "C"}

    def __init__(self):
        Tool.__init__(self)
        self.clear()

    def clear(self):
        self.atom1 = None
        self.atom2 = None
        self.bond = None

    def onMousePress(self, x, y):
        print("press   : %i, %i" % (x,y))
        if not App.paper.focused_obj:
            mol = App.paper.newMolecule()
            self.atom1 = mol.newAtom(self.selected_mode["atom"])
            self.atom1.pos = [x,y]
            self.atom1.draw()
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
        angle = int(self.selected_mode["bond_angle"])
        atom2_pos = point_on_circle( self.atom1.pos, App.bond_length, [x,y], angle)
        # we are clicking and dragging mouse
        if not self.atom2:
            self.atom2 = self.atom1.molecule.newAtom(self.selected_mode["atom"])
            self.atom2.pos = atom2_pos
            self.bond = self.atom1.molecule.newBond(self.atom1, self.atom2, self.selected_mode['bond_type'])
            self.atom2.draw()
            self.bond.draw()
        else: # move atom2
            if type(App.paper.focused_obj) is Atom and App.paper.focused_obj is not self.atom1:
                self.atom2.moveTo(App.paper.focused_obj.pos)
            else:
                self.atom2.moveTo(atom2_pos)


    def onMouseRelease(self, x, y):
        print("release : %i, %i" % (x,y))
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
            self.bond.draw()
            reposition_bonds_around_atom(touched_atom)

        reposition_bonds_around_atom(self.atom1)
        self.clear()


    def onMouseClick(self, x, y):
        print("click   : %i, %i" % (x,y))
        obj = App.paper.focused_obj
        if not obj:
            self.atom1.show_symbol = True
            self.atom1.draw()

        elif type(obj) is Atom:
            if obj.formula != self.selected_mode["atom"]:
                obj.setFormula(self.selected_mode["atom"])
            elif obj.formula == "C":
                obj.show_symbol = not obj.show_symbol
            else:
                obj.show_hydrogens = not obj.show_hydrogens
            obj.draw()
            obj.redrawBonds()

        elif type(obj) is Bond:
            selected_bond_type = self.selected_mode["bond_type"]
            # switch between normal-double-triple
            if selected_bond_type == "normal":
                modes = ["normal", "double", "triple"]
                if obj.type in modes:
                    curr_mode_index = modes.index(obj.type)-len(modes)# using -ve index to avoid out of index error
                    obj.type = modes[curr_mode_index+1]
                else:
                    obj.type = "normal"
            elif selected_bond_type != obj.type:
                obj.type = selected_bond_type
            # all these have bond type and selected type same
            elif selected_bond_type == "double":
                obj.changeDoubleBondAlignment()
            obj.draw()

        self.clear()

    def selectAtomType(self, index):
        types = self.atom_types + self.group_types
        self.selected_mode["atom"] = types[index]


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



class ArrowTool(Tool):
    def __init__(self):
        Tool.__init__(self)


atomtools_template = ["C", "H", "O", "N", "S", "P", "Cl", "Br", "I"]
grouptools_template = ["OH", "CHO", "COOH", "NH2", "CONH2", "SO3H", "OTs", "OBs"]

tools_template = [
# name   title          icon    subtools
    (MoveTool, "Move",      ":/icons/move.png", []),
    (RotateTool, "Rotate",  ":/icons/rotate.png", [
            [("2d", "2D Rotation", ":/icons/rotate.png"),
            ("3d", "3D Rotation", ":/icons/rotate3d.png")]
    ]),
    (StructureTool, "Draw Molecular Structure", ":/icons/bond.png", [
            [("30", "30 degree", ":/icons/30.png"),
            ("18", "18 degree", ":/icons/18.png"),
            ("1", "1 degree", ":/icons/1.png")],
            [("normal", "Single Bond", ":/icons/single.png"),
            ("double", "Double Bond", ":/icons/double.png"),
            ("triple", "Triple Bond", ":/icons/triple.png")]
    ]),
]

# list of tool names, (used to obtain index of a particular tool)
tools_list = [x[0] for x in tools_template]


