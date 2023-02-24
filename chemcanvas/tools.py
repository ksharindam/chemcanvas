
from app_data import App
from atom import Atom
from bond import Bond
from molecule import Molecule
from geometry import *
#import common
from functools import reduce
import operator

class Tool:
    name = "Tool"
    settings_type = None

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


class SelectTool(Tool):
    name = "SelectTool"
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
        App.paper.deselectAll()
        if App.paper.focused_obj:
            App.paper.selectObject(App.paper.focused_obj)

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
        objs = set(objs) - not_selected_bonds
        App.paper.deselectAll()
        for obj in objs:
            App.paper.selectObject(obj)



class MoveTool(SelectTool):
    """ Selection or Move tool. Used to select or move molecules, atoms, bonds etc """
    name = "MoveTool"
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
                self.objs_to_move |= set(obj.atoms)
                self.objs_to_move.remove(obj)

    def onMouseMove(self, x, y):
        if App.paper.dragging and self.objs_to_move:
            objs_to_redraw = []
            for obj in self.objs_to_move:
                obj.translateDrawings(x-self._prev_pos[0], y-self._prev_pos[1])
                if type(obj)==Atom:
                    objs_to_redraw += obj.bonds
            [obj.draw() for obj in set(objs_to_redraw)]
            self.objs_moved = True
            self._prev_pos = [x,y]
            return
        SelectTool.onMouseMove(self, x, y)

    def onMouseRelease(self, x, y):
        if not self.objs_moved:
            SelectTool.onMouseRelease(self, x, y)
        self.clear()

    def deleteSelected(self):
        # TODO : delete orphan atoms
        atoms, bonds = set(), set()
        modified_molecules = set()
        # separate atoms, bonds etc
        for obj in App.paper.selected_objs:
            if type(obj) is Atom:
                atoms.add(obj)
                bonds |= set(obj.bonds)
            elif type(obj) is Bond:
                bonds.add(obj)
        # first delete bonds
        while len(bonds):
            bond = bonds.pop()
            modified_molecules.add(bond.molecule)
            bond.disconnectAtoms()
            bond.molecule.removeBond(bond)
            bond.deleteFromPaper()
        # then delete atoms
        while len(atoms):
            atom = atoms.pop()
            atom.molecule.removeAtom(atom)
            atom.deleteFromPaper()
        # split molecule
        while len(modified_molecules):
            mol = modified_molecules.pop()
            if len(mol.bonds)==0:
                mol.deleteFromPaper()
            else:
                mol.splitFragments()


class RotateTool(SelectTool):
    """ Rotate objects tools """
    name = "RotateTool"
    settings_type = "Rotation"

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
            elif type(selected_obj)==Bond and toolsettings['rotation_type']=='3d':
                self.rot_axis = selected_obj.atom1.pos3d + selected_obj.atom2.pos3d

        if not self.rot_center and not self.rot_axis:
            self.rot_center = Rect(focused.parent.boundingBox()).center() + [0]

    def onMouseMove(self, x, y):
        if not App.paper.dragging or len(self.atoms_to_rotate)==0:
            return
        dx = x - App.paper.mouse_press_pos[0]
        dy = y - App.paper.mouse_press_pos[1]

        if toolsettings['rotation_type'] == '2d':
            sig = on_which_side_is_point( self.rot_center[:2]+App.paper.mouse_press_pos, [x, y])
            angle = round( sig * (abs( dx) +abs( dy)) / 50.0, 2)
            tr = Transform()
            tr.translate( -self.rot_center[0], -self.rot_center[1])
            tr.rotate( angle)
            tr.translate( self.rot_center[0], self.rot_center[1])
            transformed_points = tr.transformPoints(self.initial_pos_of_atoms)
            bonds_to_redraw = []
            for i, atom in enumerate(self.atoms_to_rotate):
                atom.setPos(transformed_points[i])
                atom.draw()
                bonds_to_redraw += atom.bonds
            [bond.draw() for bond in set(bonds_to_redraw)]

        elif toolsettings['rotation_type'] == '3d':
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
            bonds_to_redraw = []
            for i, atom in enumerate(self.atoms_to_rotate):
                x, y, z = transformed_points[i]
                atom.setPos([x, y])
                atom.z = z
                atom.draw()
                bonds_to_redraw += atom.bonds
            [bond.draw() for bond in set(bonds_to_redraw)]

    def onMouseRelease(self, x, y):
        self.clear()
        SelectTool.onMouseRelease(self, x ,y)



class StructureTool(Tool):
    name = "StructureTool"
    settings_type = "Drawing"

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
            self.atom1 = mol.newAtom(toolsettings["atom"])
            self.atom1.setPos([x,y])
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
        angle = int(toolsettings["bond_angle"])
        atom2_pos = point_on_circle( self.atom1.pos, App.bond_length, [x,y], angle)
        # we are clicking and dragging mouse
        if not self.atom2:
            self.atom2 = self.atom1.molecule.newAtom(toolsettings["atom"])
            self.atom2.setPos(atom2_pos)
            self.bond = self.atom1.molecule.newBond()
            self.bond.connectAtoms(self.atom1, self.atom2)
            self.bond.setType(toolsettings['bond_type'])
            if self.atom1.redrawNeeded():# because, hydrogens may be changed
                self.atom1.draw()
            self.atom2.draw()
            self.bond.draw()
        else: # move atom2
            if type(App.paper.focused_obj) is Atom and App.paper.focused_obj is not self.atom1:
                self.atom2.setPos(App.paper.focused_obj.pos)
            else:
                self.atom2.setPos(atom2_pos)
            self.atom2.draw()
            [bond.draw() for bond in self.atom2.bonds]


    def onMouseRelease(self, x, y):
        print("release : %i, %i" % (x,y))
        if not App.paper.dragging:
            self.onMouseClick(x,y)
            return
        #print("mouse dragged")
        if not self.atom2:
            return
        self.atom1.resetTextLayout()
        self.atom1.draw()
        touched_atom = App.paper.touchedAtom(self.atom2)
        if touched_atom:
            if touched_atom in self.atom1.neighbors:
                # we can not create another bond over an existing bond
                self.bond.disconnectAtoms()
                self.bond.molecule.removeBond(self.bond)
                self.bond.deleteFromPaper()
                self.atom2.molecule.removeAtom(self.atom2)
                self.atom2.deleteFromPaper()
                self.clear()
                return
            touched_atom.eatAtom(self.atom2)
            self.atom2 = touched_atom

        self.atom2.resetTextLayout()
        self.atom2.draw()
        self.bond.draw()
        reposition_bonds_around_atom(self.atom1)
        if touched_atom:
            reposition_bonds_around_atom(self.atom2)
        self.clear()
        App.paper.save_state_to_undo_stack()


    def onMouseClick(self, x, y):
        print("click   : %i, %i" % (x,y))
        focused_obj = App.paper.focused_obj
        if not focused_obj:
            self.atom1.show_symbol = True
            self.atom1.draw()

        elif type(focused_obj) is Atom:
            atom = focused_obj
            if atom.formula != toolsettings["atom"]:
                atom.setFormula(toolsettings["atom"])
            elif atom.formula == "C":
                atom.show_symbol = not atom.show_symbol
                atom.resetText()
            else:
                atom.show_hydrogens = not atom.show_hydrogens
                atom.resetText()
            atom.draw()
            [bond.draw() for bond in atom.bonds]

        elif type(focused_obj) is Bond:
            bond = focused_obj
            #prev_bond_order = bond.order
            selected_bond_type = toolsettings["bond_type"]
            # switch between normal-double-triple
            if selected_bond_type == "normal":
                modes = ["normal", "double", "triple"]
                if bond.type in modes:
                    curr_mode_index = modes.index(bond.type)-len(modes)# using -ve index to avoid out of index error
                    bond.setType(modes[curr_mode_index+1])
                else:
                    bond.setType("normal")
            elif selected_bond_type != bond.type:
                bond.setType(selected_bond_type)
            # all these have bond type and selected type same
            elif selected_bond_type == "double":
                bond.changeDoubleBondAlignment()
            # if bond order changes, hydrogens of atoms will be changed, so redraw
            [atom.draw() for atom in bond.atoms if atom.redrawNeeded()]
            bond.draw()

        self.clear()
        App.paper.save_state_to_undo_stack()


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


class TemplateTool(Tool):
    name = "TemplateTool"
    settings_type = "Template"

    def __init__(self):
        Tool.__init__(self)

    def onMousePress(self, x,y):
        pass

    def onMouseMove(self, x,y):
        pass

    def onMouseRelease(self, x,y):
        if not App.paper.dragging:
            self.onMouseClick(x,y)
            return

    def onMouseClick(self, x,y):
        focused = App.paper.focused_obj
        if not focused:
            t = App.template_manager.getTransformedTemplate([x,y])
            App.paper.addObject(t)
            t.drawSelfAndChildren()
            t.template_atom = None
            t.template_bond = None
        elif focused.object_type == "Atom":
            # (x1,y1) is the point where template atom is placed, (x2,y2) is the point
            # for aligning and scaling the template molecule
            if focused.free_valency >= App.template_manager.getTemplateValency():# merge atom
                x1, y1 = focused.x, focused.y
                if len(focused.neighbors)==1:# terminal atom
                    x2, y2 = focused.neighbors[0].pos
                else:
                    x2, y2 = focused.molecule.findPlace(focused, App.bond_length)
                    x2, y2 = (2*x1 - x2), (2*y1 - y2)# to opposite side of x1, y1
                t = App.template_manager.getTransformedTemplate([x1,y1,x2,y2], "Atom")
                focused.eatAtom(t.template_atom)
            else: # connect template atom and focused atom with bond
                x1, y1 = focused.molecule.findPlace(focused, App.bond_length)
                x2, y2 = focused.pos
                t = App.template_manager.getTransformedTemplate([x1,y1,x2,y2], "Atom")
                t_atom = t.template_atom
                focused.molecule.eatMolecule(t)
                bond = focused.molecule.newBond()
                bond.connectAtoms(focused, t_atom)
            focused.molecule.handleOverlap()
            focused.molecule.drawSelfAndChildren()
        elif focused.object_type == "Bond":
            x1, y1 = focused.atom1.pos
            x2, y2 = focused.atom2.pos
            #find appropriate side of bond to append template to
            atms = focused.atom1.neighbors + focused.atom2.neighbors
            atms = set(atms) - set(focused.atoms)
            coords = [a.pos for a in atms]
            if reduce( operator.add, [on_which_side_is_point( (x1,y1,x2,y2), xy) for xy in coords], 0) > 0:
                x1, y1, x2, y2 = x2, y2, x1, y1
            t = App.template_manager.getTransformedTemplate((x1,y1,x2,y2), "Bond")
            focused.molecule.eatMolecule(t)
            focused.molecule.handleOverlap()
            focused.molecule.drawSelfAndChildren()
        else:
            return
        App.paper.save_state_to_undo_stack("add template : %s"% App.template_manager.current.name)



class ArrowTool(Tool):
    def __init__(self):
        Tool.__init__(self)


atomtools_template = ["C", "H", "O", "N", "S", "P", "Cl", "Br", "I"]
grouptools_template = ["OH", "CHO", "COOH", "NH2", "CONH2", "SO3H", "OTs", "OBs"]


# required only once when main tool bar is created
tools_template = {
    # name         title          icon_name
    "MoveTool" :  ("Move",     "move"),
    "RotateTool" : ("Rotate",  "rotate"),
    "StructureTool" : ("Draw Molecular Structure", "bond"),
    "TemplateTool" : ("Template Tool", "benzene"),
}

# ordered tools that appears on toolbar
toolbar_tools = ["MoveTool", "RotateTool", "StructureTool", "TemplateTool"]

# required when tool is changed. includes tools which is not in toolbar.
tool_class_dict = {
    "MoveTool" : MoveTool,
    "RotateTool" : RotateTool,
    "StructureTool":StructureTool,
    "TemplateTool": TemplateTool,
}

# in each settings mode, items will be shown in settings bar as same order as here
settings_template = {
    "Drawing" : [# mode
        ["bond_angle",# key/category
            # value   title         icon_name
            [("30", "30 degree", "30"),
            ("15", "15 degree", "15"),
            ("1", "1 degree", "1")],
        ],
        ["bond_type", [
            ("normal", "Single Bond", "bond"),
            ("double", "Double Bond", "double"),
            ("triple", "Triple Bond", "triple")],
        ]
    ],
    "Template" : [
    ],
    "Rotation" : [
        ["rotation_type",
            [("2d", "2D Rotation", "rotate"),
            ("3d", "3D Rotation", "rotate3d")]
        ]
    ],
}

# tool settings manager
class ToolSettings:
    def __init__(self):
        self._dict = { # initialize with default values
            "Rotation" : {'rotation_type': '2d'},
            "Drawing" :  {"bond_angle": "30", "bond_type": "normal", "atom": "C"},
            "Template" : {'template': 'benzene'},
        }
        self._scope = "Drawing"

    def setScope(self, scope):
        self._scope = scope

    def __getitem__(self, key):
        return self._dict[self._scope][key]

    def __setitem__(self, key, value):
        self._dict[self._scope][key] = value

    def __delitem__(self, key):
        del self._dict[key]

# global tool settings container
toolsettings = ToolSettings()
