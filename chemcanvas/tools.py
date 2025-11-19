# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from functools import reduce
import operator
from math import sin, cos, asin, atan2
from math import pi as PI

from PyQt5.QtGui import QIcon

from app_data import App, Settings
from drawing_parents import Color, Align, PenStyle
from tool_helpers import *
from molecule import Molecule
from atom import Atom
from bond import Bond
from delocalization import Delocalization
from text import Text, Plus
from arrow import Arrow
from bracket import Bracket
import geometry as geo
from common import bbox_of_bboxes, flatten
from fileformat_smiles import Smiles
from coords_generator import CoordsGenerator


class Tool:
    def __init__(self):
        pass

    @property
    def class_name(self):
        return self.__class__.__name__

    def on_mouse_press(self, x, y):
        pass

    def on_mouse_release(self, x, y):
        pass
    def on_mouse_move(self, x, y):
        pass

    def on_mouse_double_click(self, x, y):
        pass

    def on_key_press(self, key, text):
        """ key is a string """
        pass

    def on_right_click(self, x,y):
        menu = self.get_default_context_menu()
        if menu:
            App.paper.showMenu(menu, (x,y))

    def get_default_context_menu(self):
        focused = App.paper.focused_obj
        menu = create_object_property_menu(focused)
        if isinstance(focused, (Atom,Bond)):
            if not menu:
                menu = App.paper.createMenu()
            if isinstance(focused, Atom) and focused.is_group:
                action = menu.addAction("Expand Group")
                action.data = {"object":focused, "callback":expand_functional_group}
            else:
                template_menu = menu.addMenu("Template")
                for title in (f"Set as Template-{focused.class_name}", "Save Molecule as Template"):
                    action = template_menu.addAction(title)
                    action.data = {"object":focused, "title": title,
                                    "callback":on_template_menu_click}
        if menu:
            menu.triggered.connect(on_object_context_menu_click)
        return menu

    def on_property_change(self, key, value):
        """ this is called when a tool settings is changed in settingsbar """
        pass

    def clear(self):
        """ clear graphics temporarily created by itself"""
        # clear temp graphics and the variables initially required in on_mouse_press(),
        # on_mouse_move() (without dragging) and on_key_press().
        # This is required in cases like, (1) not finished text editing and then doing undo.
        # (2) doing undo while scale tool bounding box is there.
        pass

    def show_status(self, msg):
        App.window.showStatus(msg)

    def clear_status(self):
        App.window.clearStatus()


def on_object_context_menu_click(action):
    action.data["callback"](action.data)

# Menu Template Format -> ("Action1", SubMenu1, ...)
# Menu = a tuple of actions and submenus.
# Action = a string of "Action Name"
# SubMenu = another menu, i.e a tuple of actions and more submenus

def create_object_property_menu(obj):
    if obj and isinstance(obj, (Atom,Bond)):
        menu_template = obj.menu_template
        if not menu_template:
            return
        menu = App.paper.createMenu()
        for submenu_template in menu_template:
            submenu = create_object_property_submenu(obj, menu, submenu_template)
        return menu

def create_object_property_submenu(obj, menu, submenu_template):
    """ Creates object property submenu from template """
    submenu_title, action_titles = submenu_template
    submenu = menu.addMenu(submenu_title)
    curr_val = obj.get_property(submenu_title)
    for title in action_titles:
        action = submenu.addAction(title)
        action.data = {"object":obj, "key":submenu_title, "value":title,
                        "callback": set_object_property}
        if title==curr_val:
            action.setCheckable(True)
            action.setChecked(True)
    return submenu


def set_object_property(data):
    obj = data["object"]
    obj.set_property(data["key"], data["value"])
    # redraw required objects
    obj.draw()
    if isinstance(obj, Atom):
        [bond.draw() for bond in obj.bonds]
    App.paper.save_state_to_undo_stack("Object Property Change")


def on_template_menu_click(data):
    obj = data["object"]
    title = data["title"]
    if title == "Save Molecule as Template":
        App.template_manager.save_template(obj.molecule)
    elif title == "Set as Template-Atom":
        obj.molecule.template_atom = obj
    elif title == "Set as Template-Bond":
        obj.molecule.template_bond = obj



def expand_functional_group(data):
    group_atom = data["object"]
    mol = group_atom.molecule
    if group_atom.symbol not in group_smiles_dict:
        return
    smiles = group_smiles_dict[group_atom.symbol]
    reader = Smiles()
    new_mol = reader.get_molecule(smiles)
    if not new_mol:
        return
    group_atom.copy_from(new_mol.atoms[0], keep=["molecule", "x","y"])
    group_atom.eat_atom(new_mol.atoms[0])
    g = CoordsGenerator()
    g.calculate_coords(mol, bond_length=Settings.bond_length)
    draw_recursively(mol)
    App.paper.save_state_to_undo_stack("Expand Group")




class SelectTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        self._selection_item = None

    def on_mouse_press(self, x, y):
        self.mouse_press_pos = (x, y)
        self._polygon = [(x,y)]

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.on_mouse_click(x, y)
            return
        if self._selection_item:
            App.paper.removeItem(self._selection_item)
            self._selection_item = None

    def on_mouse_click(self, x, y):
        App.paper.deselectAll()
        if App.paper.focused_obj:
            App.paper.selectObject(App.paper.focused_obj)

    def on_mouse_move(self, x, y):
        if not App.paper.dragging:
            return
        if self._selection_item:
            App.paper.removeItem(self._selection_item)
        if toolsettings["selection_mode"] == 'lasso':
            self._polygon.append((x,y))
            self._selection_item = App.paper.addPolygon(self._polygon, style=PenStyle.dashed)
            objs = App.paper.objectsInPolygon(self._polygon)
        else: # toolsettings["selection_mode"] == 'rectangular'
            rect = geo.rect_normalize(self.mouse_press_pos + (x,y))
            self._selection_item = App.paper.addRect(rect, style=PenStyle.dashed)
            objs = App.paper.objectsInRect(rect)
        # bond is dependent to two atoms, so select bond only if their atoms are selected
        not_selected_bonds = set()
        for obj in objs:
            if type(obj)==Bond and (obj.atom1 not in objs or obj.atom2 not in objs):
                not_selected_bonds.add(obj)
        objs = set(objs) - not_selected_bonds
        App.paper.deselectAll()
        for obj in objs:
            App.paper.selectObject(obj)

    def clear(self):
        App.paper.deselectAll()

# ------------------------- END SELECTION TOOL -------------------------



class MoveTool(SelectTool):
    """ Selection or Move tool. Used to select or move molecules, atoms, bonds etc """
    tips = {
        "on_init": "Drag an object to move it ; Click to select an object ; Press-and-drag to select multiple objects",
        "on_select": "Drag selected objects to move them",
        "on_move": "To move single atom or bond, click to select and then drag",
    }

    def __init__(self):
        SelectTool.__init__(self)
        self.reset()
        self.show_status(self.tips["on_init"])

    def reset(self):
        self.drag_to_select = False
        self.objs_moved = False
        # self.objs_to_move = set()
        # self.objs_to_redraw = set() # Bonds need to redraw

    def on_mouse_press(self, x, y):
        self.reset()
        # if we have pressed on blank area, we are going to draw selection rect, and select objs
        if not App.paper.focused_obj:
            SelectTool.on_mouse_press(self, x,y)
            self.drag_to_select = True
            return
        self._prev_pos = [x,y]

        to_move = []
        to_redraw = set()
        self.redraw_on_finish = set()
        # if we drag a selected obj, all selected objs are moved
        if App.paper.focused_obj in App.paper.selected_objs:
            to_move = App.paper.selected_objs[:]
            [to_move.extend(obj.atoms) for obj in to_move if isinstance(obj,Bond)]
            to_move = set(to_move)
            # redraw bonds which are not selected but attached to selected atoms
            bonds_to_redraw = flatten( [o.bonds for o in to_move if isinstance(o,Atom)])
            bonds_to_redraw = set(bonds_to_redraw)-to_move
            to_redraw |= bonds_to_redraw
            # to rearrange marks if not all neighbors are moved along
            self.redraw_on_finish = set(flatten([b.atoms for b in bonds_to_redraw]))
            # delocalizations need to redraw if related atoms are moved
            atoms = [o for o in to_move if isinstance(o,Atom)]
            to_redraw |= set(get_delocalizations_having_atoms(atoms))
        else:
            # when we try to move atom or bond, whole molecule is moved
            if isinstance(App.paper.focused_obj.parent, Molecule):# atom or bond
                to_move = set(App.paper.focused_obj.parent.atoms)
                to_move |= App.paper.focused_obj.parent.bonds
                to_move |= set(App.paper.focused_obj.parent.delocalizations)
            else:
                to_move = set([App.paper.focused_obj])

        self.objs_to_move = to_move
        self.objs_to_redraw = to_redraw

        # handle anchored arrows
        self.anchor_dict = {}
        for o in [o for o in App.paper.objects if isinstance(o,Arrow)]:
            tail_pos = o.points[0]  if o.e_src else None
            head_pos = o.points[-1] if o.e_dst else None
            if tail_pos or head_pos:
                self.anchor_dict[o] = [tail_pos, o.e_src in self.objs_to_move,
                                       head_pos, o.e_dst in self.objs_to_move]
                self.objs_to_redraw.add(o)


    def on_mouse_move(self, x, y):
        if self.drag_to_select:
            SelectTool.on_mouse_move(self, x, y)
            return
        if not (App.paper.dragging and self.objs_to_move):
            return
        dx, dy = x-self._prev_pos[0], y-self._prev_pos[1]
        for obj in self.objs_to_move:
            obj.move_by(dx, dy)
        for obj in self.objs_to_move - self.objs_to_redraw:
            App.paper.moveItemsBy(obj.all_items, dx, dy)

        for o,vals in self.anchor_dict.items():
            tail_pos, tail_moving, head_pos, head_moving = vals
            if tail_pos:# tail anchored
                if tail_moving:
                    tail_pos = (tail_pos[0]+dx, tail_pos[1]+dy)
                self.anchor_dict[o][0] = tail_pos
                o.points[0] = tail_pos
            if head_pos:# head anchored
                if head_moving:
                    head_pos = (head_pos[0]+dx, head_pos[1]+dy)
                self.anchor_dict[o][2] = head_pos
                o.points[-1] = head_pos

        [obj.draw() for obj in self.objs_to_redraw]
        self.objs_moved = True
        self._prev_pos = [x,y]


    def on_mouse_release(self, x, y):
        # if not moving objects
        if self.drag_to_select or not App.paper.dragging:
            SelectTool.on_mouse_release(self, x, y)
            if App.paper.selected_objs:
                self.show_status(self.tips["on_select"])
            else:
                self.clear_status()
            return
        if self.objs_moved:
            # marks position on atoms need to be updated
            [o.draw() for o in self.redraw_on_finish]
            for arrow in [o for o in self.anchor_dict if o.e_src in self.redraw_on_finish]:
                arrow.adjust_anchored_points()
                arrow.draw()
            App.paper.save_state_to_undo_stack("Move Object(s)")
            self.show_status(self.tips["on_move"])


    def on_key_press(self, key, text):
        if key=="Delete":
            self.delete_selected()
        if "Ctrl" in App.paper.modifier_keys:
            if key=="A":
                App.paper.selectAll()
            elif key=="D":
                self.duplicate_selected()


    def on_property_change(self, key, value):
        if key=="action":
            if value=="Duplicate":
                self.duplicate_selected()
            elif value=="Convert to Aromatic Form":
                self.convert_to_aromatic_form()

    def delete_selected(self):
        delete_objects(App.paper.selected_objs)# it has every object types, except Molecule
        App.paper.save_state_to_undo_stack("Delete Selected")
        # if there is no object left on paper, nothing to do with MoveTool
        if len(App.paper.objects)==0:
            App.window.selectToolByName("StructureTool")


    def duplicate_selected(self):
        if not App.paper.selected_objs:
            self.show_status("Error ! Select a molecule or part of molecule first")
            return
        objs = duplicate_objects(App.paper.selected_objs)# it has every object types, except Molecule
        if not objs:# if selection does not contain molecules
            return
        bboxes = [obj.bounding_box() for obj in objs]
        bbox = bbox_of_bboxes(bboxes)
        x, y = App.paper.find_place_for_obj_size(bbox[2]-bbox[0], bbox[3]-bbox[1])
        move_objs(objs, x-bbox[0], y-bbox[1])
        draw_objs_recursively(objs)
        App.paper.redraw_dirty_objects()
        App.paper.save_state_to_undo_stack("Duplicate Selected")


    def convert_to_aromatic_form(self):
        mols = set(o.molecule for o in App.paper.selected_objs if isinstance(o,Atom))
        if not mols:
            mols = set(o for o in App.paper.objects if isinstance(o,Molecule))
        aromaticity_found = False
        for mol in mols:
            aromatic_rings = find_aromatic_rings_in_molecule(mol)
            for ring in aromatic_rings:
                mol.add_delocalization(Delocalization(ring+[ring[0]]))
            if aromatic_rings:
                aromaticity_found = True
                mol.mark_dirty()

        if aromaticity_found:
            App.paper.redraw_dirty_objects()
            App.paper.save_state_to_undo_stack("Convert To Aromatic")
        else:
            self.show_status("Aromaticity detection done")

    def clear(self):
        SelectTool.clear(self)


def delete_objects(objects):
    objects = set(objects)
    # separate objects that need to be handled specially (eg- atoms, bonds)
    bonds = set(o for o in objects if isinstance(o,Bond))
    objects -= bonds
    atoms = set(o for o in objects if isinstance(o,Atom))
    objects -= atoms
    for atom in atoms:
        bonds |= set(atom.bonds)

    # need to redraw atoms whose bonds are deleted, and occupied valency changed
    to_redraw = set()
    for bond in bonds:
        to_redraw |= set(bond.atoms)
    to_redraw -= atoms
    # in "Show Terminal Carbon" mode, atom symbol may become visible and bonds need to be redrawn
    bonds_to_redraw = set()
    for atom in to_redraw:
        bonds_to_redraw |= set(atom.bonds)
    to_redraw |= bonds_to_redraw - bonds

    while objects:
        obj = objects.pop()
        obj.delete_from_paper()

    modified_molecules = set(bond.molecule for bond in bonds)
    # break delocalizations
    for mol in modified_molecules:
        for deloc in mol.delocalizations[:]:
            if set(deloc.bonds) & bonds:
                mol.destroy_delocalization(deloc)
                to_redraw |= (set(deloc.bonds) - bonds)
    # first delete bonds
    while bonds:
        bond = bonds.pop()
        bond.disconnect_atoms()
        bond.molecule.remove_bond(bond)
        bond.delete_from_paper()
    # then delete atoms
    while atoms:
        atom = atoms.pop()
        if not atom.bonds:# helps to delete single atom molecule
            modified_molecules.add(atom.molecule)
        atom.molecule.remove_atom(atom)
        atom.delete_from_paper()
    # split molecule
    while modified_molecules:
        mol = modified_molecules.pop()
        if len(mol.bonds)==0:# delete lone atom
            to_redraw -= set(mol.atoms)
            for child in mol.children:
                child.delete_from_paper()
            mol.paper.removeObject(mol)
        else:
            new_mols = mol.split_fragments()
            # delete lone atoms
            [modified_molecules.add(mol) for mol in new_mols if len(mol.bonds)==0]

    draw_objs_recursively(to_redraw)


def duplicate_objects(objects):
    """ Currently it only duplicates molecules """
    objects = set(objects)
    bonds = [o for o in objects if isinstance(o,Bond)]
    atoms = set(o for o in objects if isinstance(o,Atom))
    for bond in bonds:
        atoms |= set(bond.atoms)
    mols = set(atom.molecule for atom in atoms)

    obj_map = {}

    # copy molecules
    new_mols = []
    for mol in mols:
        new_mol = Molecule()
        App.paper.addObject(new_mol)
        obj_map[mol.id] = new_mol
        new_mols.append(new_mol)

    # copy atoms
    for atom in atoms:
        new_atom = atom.copy()
        obj_map[atom.molecule.id].add_atom(new_atom)
        obj_map[atom.id] = new_atom
    # copy bonds
    for bond in bonds:
        new_bond = bond.copy()
        obj_map[bond.molecule.id].add_bond(new_bond)
        new_bond.connect_atoms(obj_map[bond.atom1.id], obj_map[bond.atom2.id])
        obj_map[bond.id] = new_bond

    # copy delocalizations
    delocalized_bonds = set()# that are being copied
    for deloc in get_delocalizations_having_atoms(atoms):
        # if all bonds of delocalization are copied, copy delocalization
        if set(deloc.bonds).issubset(bonds):
            new_deloc = deloc.copy()
            new_deloc.atoms = [obj_map[a.id] for a in deloc.atoms]
            obj_map[deloc.molecule.id].add_delocalization(new_deloc)
            obj_map[deloc.id] = new_deloc
            delocalized_bonds |= set(new_deloc.bonds)
        # if some of the atoms are copied, delocalization is removed
        # and each bond is displayed as aromatic (one and half) bond
        else:
            for bond in deloc.bonds:# when all bonds are not copied
                if bond.id in obj_map:
                    obj_map[bond.id].show_delocalization = True
                    # above line shows dashed line even if the bond is part of
                    # another delocalocaized ring, though it should not

    # this part is used to hide the dashed line again
    for bond in delocalized_bonds:
        bond.show_delocalization = False

    # split molecules
    new_mols2 = []
    for mol in new_mols:
        new_mols2 += mol.split_fragments()

    return new_mols + new_mols2



# ---------------------------- END MOVE TOOL ---------------------------



class RotateTool(SelectTool):
    """ Rotate objects tools """
    tips = {
        "on_init": "Drag molecule to rotate",
        "2d": "You can select an Atom to rotate around",
        "3d": "You can select an Atom or Bond to rotate around",
    }
    def __init__(self):
        SelectTool.__init__(self)
        self.show_status(self.tips[toolsettings["rotation_type"]])

    def reset(self):
        self.mol_to_rotate = None
        self.rot_center = None
        self.rot_axis = None

    def on_mouse_press(self, x, y):
        SelectTool.on_mouse_press(self, x, y)
        self.reset()
        focused = App.paper.focused_obj
        if not focused or not isinstance(focused.parent, Molecule):
            return
        self.mol_to_rotate = focused.parent
        # backup initial positions
        self.initial_positions = []
        for atom in self.mol_to_rotate.atoms:
            self.initial_positions.append(atom.pos3d)
        # find rotation center
        selected_obj = len(App.paper.selected_objs) and App.paper.selected_objs[0] or None

        if selected_obj and selected_obj.parent is focused.parent:
            if isinstance(selected_obj, Atom):
                self.rot_center = selected_obj.pos3d
            elif isinstance(selected_obj, Bond) and toolsettings['rotation_type']=='3d':
                self.rot_axis = selected_obj.atom1.pos3d + selected_obj.atom2.pos3d

        if not self.rot_center and not self.rot_axis:
            self.rot_center = geo.rect_get_center(focused.parent.bounding_box()) + (0,)

        # initial angle
        if self.rot_center:
            self.start_angle = geo.line_get_angle_from_east([self.rot_center[0], self.rot_center[1], x,y])

    def on_mouse_move(self, x, y):
        if not App.paper.dragging or not self.mol_to_rotate:
            return
        is_2D = toolsettings['rotation_type'] == '2d'

        # create 2D or 3D transformation
        if is_2D:
            angle = geo.line_get_angle_from_east([self.rot_center[0], self.rot_center[1], x,y])
            tr = geo.Transform()
            tr.translate( -self.rot_center[0], -self.rot_center[1])
            tr.rotate( angle-self.start_angle)
            tr.translate( self.rot_center[0], self.rot_center[1])
            # rotate atoms
            for i, atom in enumerate(self.mol_to_rotate.atoms):
                ax, ay, az = self.initial_positions[i]
                atom.x, atom.y = tr.transform(ax, ay)

        else: # 3D
            dx = x - self.mouse_press_pos[0]
            dy = y - self.mouse_press_pos[1]
            angle = round((abs( dx) +abs( dy)) / 50, 2)
            if self.rot_axis:
                tr = geo.create_transformation_to_rotate_around_line( self.rot_axis, angle)
            else: # rotate around center
                tr = geo.Transform3D()
                tr.translate( -self.rot_center[0], -self.rot_center[1], -self.rot_center[2])
                tr.rotate_x(round(dy/50, 2))
                tr.rotate_y(round(dx/50, 2))
                tr.translate( self.rot_center[0], self.rot_center[1], self.rot_center[2])
            # Rotate atoms
            for i, atom in enumerate(self.mol_to_rotate.atoms):
                atom.x, atom.y, atom.z = tr.transform(*self.initial_positions[i])

        # redraw whole molecule recursively
        draw_recursively(self.mol_to_rotate)

    def on_mouse_release(self, x, y):
        SelectTool.on_mouse_release(self, x ,y)
        App.paper.save_state_to_undo_stack("Rotate Objects")

    def clear(self):
        SelectTool.clear(self)

    def on_property_change(self, key, val):
        if key=="rotation_type":
            self.show_status(self.tips[val])

# -------------------------- END ROTATE TOOL ---------------------------



class ScaleTool(SelectTool):
    """ Scale Objects """
    tips = {
        "on_init": "Select objects and then drag corner to scale",
    }

    def __init__(self):
        SelectTool.__init__(self)
        self.bbox_items = []
        self.bbox = None
        self.objs_to_scale = []
        #self.mode = "selection"# vals : selection | resize-top-left | resize-bottom-right
        self._backup = {}
        self.show_status(self.tips["on_init"])

    def on_mouse_press(self, x,y):
        SelectTool.on_mouse_press(self, x, y)
        self.mode = "selection"
        if self.bbox:
            if geo.points_within_range(self.bbox[2:], (x,y), 10):
                self.mode = "resize-bottom-right"
            elif geo.points_within_range(self.bbox[:2], (x,y), 10):
                self.mode = "resize-top-left"
        # resize mode
        if self.mode.startswith("resize"):
            for obj in self.objs_to_scale:
                self.backup_position_and_size(obj)
            return
        # selection mode
        self._backup.clear()
        self.clear()

    def on_mouse_release(self, x,y):
        if self.mode=="selection":
            SelectTool.on_mouse_release(self, x,y)
            self.get_objs_to_scale(App.paper.selected_objs)
            App.paper.deselectAll()
            self.create_bbox()
            return
        # resizing done, recalc and redraw bbox
        self.clear()
        self.create_bbox()
        App.paper.save_state_to_undo_stack("Scale Objects")

    def on_mouse_move(self, x,y):
        """ drag modes : resizing, drawing selection bbox"""
        if not App.paper.dragging:
            return
        if self.mode=="selection":
            # draws selection box
            SelectTool.on_mouse_move(self, x,y)
            return
        # calculate scale
        dx, dy = x-self.mouse_press_pos[0], y-self.mouse_press_pos[1]
        bbox_w, bbox_h = self.bbox[2]-self.bbox[0], self.bbox[3]-self.bbox[1]

        if self.mode=="resize-top-left":
            rect_w, rect_h = bbox_w-dx, bbox_h-dy
        else:# "resize-bottom-right"
            rect_w, rect_h = bbox_w+dx, bbox_h+dy
        if rect_w < 0 or rect_h < 0:# width, heigt can not be negative
            return

        scaled_w, scaled_h = geo.get_size_to_fit(bbox_w, bbox_h, rect_w, rect_h)
        if self.mode=="resize-top-left":
            scaled_bbox = [self.bbox[2]-scaled_w, self.bbox[3]-scaled_h] + self.bbox[2:]
            fixed_pt = self.bbox[2:]
        else:
            scaled_bbox = self.bbox[:2] + [self.bbox[0]+scaled_w, self.bbox[1]+scaled_h]
            fixed_pt = self.bbox[:2]
        scale = scaled_w/bbox_w if rect_w==scaled_w else scaled_h/bbox_h

        # calculate transformation
        tr = geo.Transform()
        tr.translate(-fixed_pt[0], -fixed_pt[1])
        tr.scale(scale)
        tr.translate(fixed_pt[0], fixed_pt[1])

        # clear prev bbox item, resize objs, and draw new scaled bbox item
        for item in self.bbox_items:
            App.paper.removeItem(item)
        self.bbox_items = []
        for obj in self.objs_to_scale:
            self.restore_position_and_size(obj)
            obj.transform(tr)
            obj.scale(scale)
        objs = sorted(self.objs_to_scale, key=lambda obj : obj.redraw_priority)
        [obj.draw() for obj in objs]
        self.bbox_items = [App.paper.addRect(scaled_bbox, color=Color.blue)]


    def get_objs_to_scale(self, selected):
        """ get toplevel objects from selected """
        objs = set(filter(lambda o: o.is_toplevel, selected))
        objs |= set([obj.parent for obj in selected if not obj.is_toplevel and obj.parent.is_toplevel])
        self.objs_to_scale = get_objs_with_all_children(objs)

    def create_bbox(self):
        items = flatten([obj.all_items for obj in self.objs_to_scale])
        bboxes = [App.paper.itemBoundingBox(item) for item in items]
        if not bboxes:
            self.bbox = None
            return
        self.bbox = bbox_of_bboxes( bboxes)
        if self.bbox:
            topleft = App.paper.addRect(self.bbox[:2] + [self.bbox[0]+8, self.bbox[1]+8], fill=Color.blue)
            btmright = App.paper.addRect([self.bbox[2]-8, self.bbox[3]-8] + self.bbox[2:], fill=Color.blue)
            self.bbox_items = [App.paper.addRect(self.bbox, color=Color.blue), topleft, btmright]

    def clear(self):
        for item in self.bbox_items:
            App.paper.removeItem(item)
        self.bbox_items = []
        self.bbox = None

    def backup_position_and_size(self, obj):
        props = {}
        for attr in obj.meta__scalables:
            props[attr] = getattr(obj, attr)
        self._backup[obj] = props

    def restore_position_and_size(self, obj):
        props = self._backup[obj]
        for attr in obj.meta__scalables:
            setattr(obj, attr, props[attr])

# -------------------------- END SCALE TOOL ---------------------------




class AlignTool(Tool):
    """ Align or Transform molecules """
    tips = {
        "horizontal_align": "Click on bond to align horizontally",
        "vertical_align": "Click on bond to align vertically",
        "mirror": "Click on Bond to mirror around",
        "inversion": "Click on Atom or Bond for inversion",
        "freerotation": "Click on bond for Cis-Trans conversion or 180° freerotation",
    }

    def __init__(self):
        Tool.__init__(self)
        self.show_status(self.tips[toolsettings["mode"]])

    def on_mouse_press(self, x,y):
        # get focused atom or bond
        self.focused = App.paper.focused_obj
        if not self.focused:
            return
        if not isinstance(self.focused, (Atom, Bond)):
            return
        elif isinstance(self.focused, Atom):
            if toolsettings['mode']!="inversion":
                return
            coords = self.focused.pos
        else:# Bond
            coords = self.focused.atom1.pos + self.focused.atom2.pos
        mol = self.focused.parent
        self.__class__.__dict__['_apply_'+toolsettings['mode']](self, coords, mol)
        # after mirror or inversion, hydrogen pos, double bond side etc need to be updated
        for o in get_objs_with_all_children([mol]):
            if isinstance(o,Atom):
                o.hydrogen_pos = None
            elif isinstance(o,Bond):
                if o.auto_second_line_side:
                    o.second_line_side = None
        draw_recursively(mol)
        App.paper.save_state_to_undo_stack("Transform : %s" % toolsettings['mode'])


    def _apply_horizontal_align(self, coords, mol):
        x1,y1, x2,y2 = coords
        centerx = ( x1 + x2) / 2
        centery = ( y1 + y2) / 2
        angle0 = geo.line_get_angle_from_east( [x1, y1, x2, y2])
        if angle0 >= PI :
            angle0 = angle0 - PI
        if (angle0 > -0.005) and (angle0 < 0.005):# angle0 = 0
            # bond is already horizontal => horizontal "flip"
            angle = PI
        elif angle0 <= PI/2:
            angle = -angle0
        else:# PI/2 < angle < PI
            angle = PI - angle0
        tr = geo.Transform()
        tr.translate( -centerx, -centery)
        tr.rotate( angle)
        tr.translate(centerx, centery)
        transform_recursively(mol, tr)


    def _apply_vertical_align( self, coords, mol):
        x1,y1, x2,y2 = coords
        centerx = ( x1 + x2) / 2
        centery = ( y1 + y2) / 2
        angle0 = geo.line_get_angle_from_east([x1, y1, x2, y2])
        if angle0 >= PI :
            angle0 = angle0 - PI
        if (angle0 > PI/2 - 0.005) and (angle0 < PI/2 + 0.005):# angle0 = 90 degree
            # bond is already vertical => vertical "flip"
            angle = PI
        else:
            angle = PI/2 - angle0
        tr = geo.Transform()
        tr.translate( -centerx, -centery)
        tr.rotate( angle)
        tr.translate(centerx, centery)
        transform_recursively(mol, tr)

    def _get_mirror_transformation(self, coords):
        x1, y1, x2, y2 = coords
        centerx = ( x1 + x2) / 2
        centery = ( y1 + y2) / 2
        angle0 = geo.line_get_angle_from_east( [x1, y1, x2, y2])
        if angle0 >= PI :
            angle0 = angle0 - PI
        tr = geo.Transform()
        tr.translate( -centerx, -centery)
        tr.rotate( -angle0)
        tr.scale_xy( 1, -1)
        tr.rotate( angle0)
        tr.translate(centerx, centery)
        return tr

    def _apply_mirror( self, coords, mol):
        tr = self._get_mirror_transformation(coords)
        transform_recursively(mol, tr)

    def _apply_freerotation( self, coords, mol):
        b = self.focused
        a1, a2 = b.atoms
        b.disconnect_atoms()
        cc = list( mol.get_connected_components())
        b.connect_atoms(a1, a2)
        if len( cc) == 1:
            print("Bond is part of a ring, there is no possiblity for rotation!")
            return
        to_rotate = list( len( cc[0]) < len( cc[1]) and cc[0] or cc[1])
        to_rotate += [b for b in mol.bonds if b.atom1 in to_rotate and b.atom2 in to_rotate]
        tr = self._get_mirror_transformation(coords)
        [o.transform(tr) for o in to_rotate]

    def _apply_inversion( self, coords, mol):
        if len( coords) == 4:
            x1, y1, x2, y2 = coords
            x = ( x1 +x2) /2.0
            y = ( y1 +y2) /2.0
        else:
            x, y = coords
        tr = geo.Transform()
        tr.translate( -x, -y)
        tr.scale(-1)
        tr.translate( x, y)
        transform_recursively(mol, tr)

    def on_property_change(self, key, value):
        if key=="mode":
            self.show_status(self.tips[value])


# --------------------------- END ALIGN TOOL ---------------------------



class StructureTool(Tool):

    def __init__(self):
        Tool.__init__(self)
        self.mode = None
        self.subtool = None
        self.init_subtool(toolsettings['mode'])

    def init_subtool(self, mode):
        if mode=="group":
            mode="atom"
        if self.mode==mode:
            return
        if self.subtool:
            self.subtool.clear()
        if mode=="chain":
            self.subtool = ChainTool()
        elif mode=="ring":
            self.subtool = RingTool()
        elif mode == "template":
            self.subtool = TemplateTool()
        else:
            self.subtool = AtomTool()
        self.subtool.parent = self
        self.mode = mode

    def on_mouse_press(self, x,y):
        self.subtool.on_mouse_press(x,y)

    def on_mouse_move(self, x,y):
        self.subtool.on_mouse_move(x,y)

    def on_mouse_release(self, x,y):
        self.subtool.on_mouse_release(x,y)

    def on_mouse_double_click(self, x, y):
        self.subtool.on_mouse_double_click(x,y)

    def on_key_press(self, key, text):
        # if select all, then switch to movetool
        if "Ctrl" in App.paper.modifier_keys and key=="A":
            App.window.selectToolByName("MoveTool")
            App.paper.selectAll()
            return
        self.subtool.on_key_press(key, text)

    def clear(self):
        self.subtool.clear()

    def on_property_change(self, key, value):
        if key=='mode':# atom, group and template
            App.window.changeStructureToolMode(value)
            self.init_subtool(value)
        if key=='bond_type':
            if toolsettings['mode']!='atom':
                App.window.selectStructure("C")


class AtomTool(Tool):

    tips = {
        "over_empty_place": "Click → Place new atom ; Press-and-Drag → Draw new Bond",
        "over_atom": "Click/Drag → New bond ; Shit+Click → Show/Hide Carbon ; Ctrl+Click → edit atom text",
        "over_different_atom": "Click → change Symbol/Formula ; Drag → Add new Bond",
        "clicked_atom": "Click on different type of atom to change atom type",
        "over_bond": "Click on Bond to change bond type",
        "moving_bond": "Press Shift → free bond length",
        "editing_text": "Type symbol or formula, then Press Enter → accept",
    }

    def __init__(self):
        Tool.__init__(self)
        self.editing_atom = None
        self.preview_item = None
        self.atom_with_preview_bond = None
        self.reset()
        self.show_tip("over_empty_place")

    def show_tip(self, tip_name):
        self.show_status(self.tips[tip_name])

    def reset(self):
        self.atom1 = None
        self.atom2 = None
        self.bond = None

    def on_mouse_press(self, x, y):
        #print("press   : %i, %i" % (x,y))
        self.mouse_press_pos = (x,y)
        if self.editing_atom:
            return

        if not App.paper.focused_obj:
            mol = Molecule()
            App.paper.addObject(mol)
            self.atom1 = mol.new_atom(toolsettings['structure'])
            self.atom1.set_pos(x,y)
            self.atom1.draw()
        elif type(App.paper.focused_obj) is Atom:
            # we have clicked on existing atom, use this atom to make new bond
            self.atom1 = App.paper.focused_obj


    def on_mouse_move(self, x, y):
        if self.editing_atom:
            return
        focused = App.paper.focused_obj
        if not focused:
            self.show_tip("over_empty_place")
        if isinstance(focused, Bond):
            self.show_tip("over_bond")
        # on hover atom preview a new bond
        if not App.paper.mouse_pressed and focused!=self.atom_with_preview_bond:
            if self.atom_with_preview_bond:
                self.clear_preview()
            if isinstance(focused, Atom):
                if focused.symbol == toolsettings['structure']:
                    if not App.paper.modifier_keys:
                        self.show_preview(focused)
                    self.show_tip("over_atom")
                else:
                    self.show_tip("over_different_atom")
        if not App.paper.dragging:
            return
        self.clear_preview()
        if [x,y] == self.mouse_press_pos:# can not calculate atom pos in such situation
            return
        if not self.atom1: # in case we have clicked on object other than atom
            return
        # we are dragging an atom
        if "Shift" in App.paper.modifier_keys:
            atom2_pos = (x,y)
        else:
            angle = int(toolsettings["bond_angle"])
            bond_length = Settings.bond_length * self.atom1.molecule.scale_val
            atom2_pos = geo.circle_get_point( self.atom1.pos, bond_length, [x,y], angle)
        # we are clicking and dragging mouse
        if not self.atom2:
            self.atom2 = self.atom1.molecule.new_atom(toolsettings['structure'])
            self.atom2.set_pos(*atom2_pos)
            self.bond = self.atom1.molecule.new_bond()
            if toolsettings['mode']=='atom':# for functional group use default single bond
                self.bond.set_type(toolsettings['bond_type'])
            self.bond.connect_atoms(self.atom1, self.atom2)
            if self.atom1.redraw_needed():# because, hydrogens may be changed
                self.atom1.draw()
                [bond.draw() for bond in self.atom1.bonds]# atoms visibility change

            self.atom2.draw()
            self.bond.draw()
            App.paper.do_not_focus.add(self.atom2)
        else: # move atom2
            if type(App.paper.focused_obj) is Atom and App.paper.focused_obj is not self.atom1:
                self.atom2.set_pos(*App.paper.focused_obj.pos)
            else:
                self.atom2.set_pos(*atom2_pos)
            self.atom2.draw()
            [bond.draw() for bond in self.atom2.bonds]

        self.show_tip("moving_bond")


    def on_mouse_release(self, x, y):
        if self.editing_atom:
            self.exit_formula_edit_mode()
            return
        #print("release : %i, %i" % (x,y))
        if not App.paper.dragging:
            self.on_mouse_click(x,y)
            return
        #print("mouse dragged")
        if not self.atom2:
            return
        App.paper.do_not_focus.remove(self.atom2)
        touched_atom = App.paper.touchedAtom(self.atom2)
        if touched_atom:
            if touched_atom is self.atom1 or touched_atom in self.atom1.neighbors:
                # we can not create another bond over an existing bond
                self.bond.disconnect_atoms()
                self.bond.molecule.remove_bond(self.bond)
                self.bond.delete_from_paper()
                self.atom2.molecule.remove_atom(self.atom2)
                self.atom2.delete_from_paper()
                self.reset()
                return
            touched_atom.eat_atom(self.atom2)
            self.atom2 = touched_atom

        # these two lines must be after handling touched atom, not before.
        self.atom1.on_bonds_reposition()
        self.atom1.draw()

        self.atom2.on_bonds_reposition()
        self.atom2.draw()
        self.bond.draw()
        refresh_attached_double_bonds(self.atom1)
        if touched_atom:
            refresh_attached_double_bonds(self.atom2)
            [bond.draw() for bond in self.atom2.bonds]
        self.reset()
        App.paper.save_state_to_undo_stack()


    def on_mouse_click(self, x, y):
        #print("click   : %i, %i" % (x,y))
        focused_obj = App.paper.focused_obj
        if not focused_obj:
            if self.atom1:# atom1 is None when previous mouse press finished editing atom text
                # when we try to click over atom or bond but mouse got accidentally
                # unfocued. we should prevent placing atom too close.
                d = Settings.bond_length/3
                objs = App.paper.objectsInRect([x-d, y-d, x+d, y+d])
                objs = list(filter(lambda o : isinstance(o, (Atom,Bond)), objs))
                if len(objs)>1:# objs always contains self.atom1
                    mol = self.atom1.molecule
                    self.atom1.delete_from_paper()
                    mol.paper.removeObject(mol)
                    self.atom1 = None
                    return
                self.atom1.draw()

        elif isinstance(focused_obj, Atom):
            atom1 = focused_obj
             # Shift+Click shows/hides carbon symbol
            if App.paper.modifier_keys == {"Shift"}:
                if atom1.symbol == "C":
                    atom1.show_symbol = not atom1.show_symbol
                    atom1.draw()
                    [bond.draw() for bond in atom1.bonds]
            # Ctrl+Click enters text edit mode
            elif App.paper.modifier_keys == {"Ctrl"}:
                self.clear_preview()
                self.editing_atom = atom1
                self.text = self.editing_atom.symbol
                # show text cursor
                self.redraw_editing_atom()
                return# prevents from adding to undo stack
            else:
                if atom1.symbol != toolsettings['structure']:
                    atom1.set_symbol(toolsettings['structure'])
                    atom1.draw()
                    [bond.draw() for bond in atom1.bonds]
                else:
                    atom2 = atom1.molecule.new_atom(toolsettings['structure'])
                    atom2.set_pos(*self.next_atom_pos)
                    bond = atom1.molecule.new_bond()
                    if toolsettings['mode']=='atom':# for functional group use default single bond
                        bond.set_type(toolsettings['bond_type'])
                    bond.connect_atoms(atom1, atom2)
                    touched_atom = App.paper.touchedAtom(atom2)
                    if touched_atom:
                        touched_atom.eat_atom(atom2)
                        atom2 = touched_atom
                    self.clear_preview()
                    atom1.draw()# because, hydrogens may be changed
                    atom2.draw()
                    #bond.draw()
                    [bond.draw() for bond in atom1.bonds]# carbon visibility may change
                    refresh_attached_double_bonds(atom1)
                    if touched_atom:
                        refresh_attached_double_bonds(atom2)
                        [bond.draw() for bond in atom2.bonds]

                # for next bond to be added on same atom, without mouse movement
                self.show_preview(atom1)
                self.show_tip("clicked_atom")

        elif isinstance(focused_obj, Bond):
            bond = focused_obj
            selected_bond_type = toolsettings['bond_type']
            # switch between normal-double-triple
            bond_modes = ("single", "double", "triple")
            if selected_bond_type=="single" and bond.type in bond_modes:
                next_mode_index = (bond_modes.index(bond.type)+1) % 3
                bond.set_type(bond_modes[next_mode_index])
            elif selected_bond_type not in (bond.type, None):
                bond.set_type(selected_bond_type)
            # when selected type is either same as bond.type or None
            elif bond.type in ("double", "delocalized", "bold2"):
                bond.change_double_bond_alignment()
            elif bond.type in ("coordinate", "wedge", "hashed_wedge"):
                # reverse bond direction
                bond.reverse_direction()
            # if bond order changes, hydrogens of atoms will be changed, so redraw
            [atom.draw() for atom in bond.atoms if atom.redraw_needed()]
            bond.draw()

        App.paper.redraw_dirty_objects()
        self.reset()
        App.paper.save_state_to_undo_stack()


    def on_mouse_double_click(self, x, y):
        """ treat double click event as single click """
        self.on_mouse_click(x,y)


    def on_key_press(self, key, text):
        if not self.editing_atom:
            return
        if text.isalnum() or text in ("(", ")"):
            self.text += text
        else:
            if key == "Backspace":
                if self.text:
                    self.text = self.text[:-1]
            elif key in ("Enter", "Return", "Esc"):
                self.clear()
                return
        self.redraw_editing_atom()


    def redraw_editing_atom(self):
        # append a cursor symbol
        self.editing_atom.set_symbol(self.text+"|")
        self.editing_atom.draw()
        [bond.draw() for bond in self.editing_atom.bonds]
        self.show_tip("editing_text")
        self.update_tip = False # prevent changing tip while mouse move

    def exit_formula_edit_mode(self):
        if not self.editing_atom:
            return
        self.editing_atom.set_symbol(self.text or "C")
        # prevent automatically adding hydrogen if symbol has one atom
        self.editing_atom.auto_hydrogens = False
        self.editing_atom.hydrogens = 0
        self.editing_atom.draw()
        [bond.draw() for bond in self.editing_atom.bonds]
        self.editing_atom = None
        self.text = ""
        App.paper.save_state_to_undo_stack("Edit Atom Text")
        self.update_tip = True

    def clear(self):
        self.exit_formula_edit_mode()
        self.clear_preview()

    def show_preview(self, atom):
        """ Show preview bond while mouse hovered on atom """
        bond_length = Settings.bond_length * atom.molecule.scale_val
        self.next_atom_pos = atom.molecule.find_place(atom, bond_length)
        self.preview_item = App.paper.addLine(atom.pos+self.next_atom_pos, style=PenStyle.dashed)
        self.atom_with_preview_bond = atom

    def clear_preview(self):
        if self.preview_item:
            App.paper.removeItem(self.preview_item)
            self.preview_item = None
            self.atom_with_preview_bond = None



def refresh_attached_double_bonds(obj):
    """ refresh double bonds side attached to obj """
    if isinstance(obj, Atom):
        bonds = obj.neighbor_edges
    elif isinstance(obj, Bond):
        bonds = set(obj.atom1.neighbor_edges + obj.atom2.neighbor_edges)
    [b.redraw() for b in bonds if b.type in ("double","delocalized","bold2")]



class TemplateTool(Tool):
    tips = {
        "on_init": "Click over Empty-Area/Atom/Bond to place template",
    }
    def __init__(self):
        Tool.__init__(self)
        self.show_status(self.tips["on_init"])

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.on_mouse_click(x,y)

    def on_mouse_click(self, x,y):
        focused = App.paper.focused_obj
        template = App.template_manager.templates[toolsettings['structure']]
        if isinstance(focused, Atom) and template.template_atom:
            # (x1,y1) is the point where template-atom is placed, (x2,y2) is the point
            # for aligning and scaling the template molecule
            if focused.free_valency >= template.template_atom.occupied_valency:# merge atom
                x1, y1 = focused.x, focused.y
                if len(focused.neighbors)==1:# terminal atom
                    x2, y2 = focused.neighbors[0].pos
                else:
                    x2, y2 = focused.molecule.find_place(focused, Settings.bond_length)
                    x2, y2 = (2*x1 - x2), (2*y1 - y2)# to opposite side of x1, y1
                t = App.template_manager.get_transformed_template(template, [x1,y1,x2,y2], "Atom")
                focused.eat_atom(t.template_atom)
            else: # connect template-atom and focused atom with bond
                x1, y1 = focused.molecule.find_place(focused, Settings.bond_length)
                x2, y2 = focused.pos
                t = App.template_manager.get_transformed_template(template, [x1,y1,x2,y2], "Atom")
                t_atom = t.template_atom
                focused.molecule.eat_molecule(t)
                bond = focused.molecule.new_bond()
                bond.connect_atoms(focused, t_atom)
            focused.molecule.handle_overlap()
            draw_recursively(focused.molecule)
        elif isinstance(focused, Bond) and template.template_bond:
            x1, y1 = focused.atom1.pos
            x2, y2 = focused.atom2.pos
            # template is attached to the left side of the passed coordinates,
            atms = focused.atom1.neighbors + focused.atom2.neighbors
            atms = set(atms) - set(focused.atoms)
            coords = [a.pos for a in atms]
            # so if most atoms are at the left side, switch start and end point
            if reduce( operator.add, [geo.line_get_side_of_point( (x1,y1,x2,y2), xy) for xy in coords], 0) > 0:
                x1, y1, x2, y2 = x2, y2, x1, y1
            t = App.template_manager.get_transformed_template(template, (x1,y1,x2,y2), "Bond")
            focused.molecule.eat_molecule(t)
            focused.molecule.handle_overlap()
            draw_recursively(focused.molecule)
        else:
            # when we try to click over atom or bond but mouse got accidentally
            # unfocued. we should prevent placing template too close.
            d = Settings.bond_length/2
            objs = App.paper.objectsInRect([x-d, y-d, x+d, y+d])
            objs = list(filter(lambda o : isinstance(o, (Atom,Bond)), objs))
            if objs:
                return
            t = App.template_manager.get_transformed_template(template, [x,y], "center")
            App.paper.addObject(t)
            draw_recursively(t)
            t.template_atom = None
            t.template_bond = None
        App.paper.save_state_to_undo_stack("add template : %s"% template.name)

# ------------------------ END STRUCTURE TOOL -------------------------




class ChainTool(Tool):
    """ Create chain of varying size """
    tips = {
        "on_init": "Click and drag to draw carbon chain of varying size",
    }

    def __init__(self):
        Tool.__init__(self)
        self.coords = []
        self.polyline_item = None
        self.count_item = None
        self.show_status(self.tips["on_init"])

    def on_mouse_press(self, x,y):
        self.mouse_press_pos = (x, y)
        self.start_atom = None
        focused = App.paper.focused_obj
        if focused and isinstance(focused, Atom):
            self.start_atom = focused

    def on_mouse_move(self, x,y):
        if not App.paper.dragging:
            return
        if (x,y)==self.mouse_press_pos:
            return
        self.clear()
        bond_len = Settings.bond_length
        d = bond_len*0.866025404 # cos(pi/6) = sqrt(3)/2
        h = bond_len*0.5 # sin(pi/6) = 0.5
        bond_count = int(geo.point_distance(self.mouse_press_pos, (x,y))//d) or 1
        center = self.start_atom and self.start_atom.pos or self.mouse_press_pos
        # find on which side zigzag chain will be placed
        last_pt = geo.circle_get_point( center, d*bond_count, (x,y), 15)
        side = geo.line_get_side_of_point(center+last_pt, (x,y)) or 1

        self.coords = [center]
        for n in range(1, bond_count+1):
            pos = geo.circle_get_point( center, d*n, (x,y), 15)
            if n%2==1:# odd
                pos = geo.line_get_point_at_distance(center+pos, side*h)
            self.coords.append(pos)

        self.polyline_item = App.paper.addPolyline(self.coords)
        chain_size = self.start_atom and bond_count or bond_count+1
        self.count_item = App.paper.addHtmlText(str(chain_size), (self.mouse_press_pos[0],self.mouse_press_pos[1]-10))

    def on_mouse_release(self, x,y):
        self.clear()
        if self.coords:
            mol = create_carbon_chain_from_coordinates(self.coords, self.start_atom)
            if not self.start_atom:# if start_atom, molecule already exists on paper
                App.paper.addObject(mol)
            draw_recursively(mol)
            self.coords = []
            App.paper.save_state_to_undo_stack("Chain Added")

    def clear(self):
        if self.polyline_item:
            App.paper.removeItem(self.polyline_item)
            App.paper.removeItem(self.count_item)
            self.polyline_item = None
            self.count_item = None


def create_carbon_chain_from_coordinates(coords, start_atom=None):
    """ if start_atom is provided, first coordinate is ignored """
    start_pos = coords.pop(0)
    if start_atom:
        mol = start_atom.molecule
        last_atom = start_atom
    else:
        mol = Molecule()
        last_atom = mol.new_atom()
        last_atom.set_pos(*start_pos)

    for pt in coords:
        atom = mol.new_atom()
        atom.set_pos(*pt)
        bond = mol.new_bond()
        bond.connect_atoms(last_atom, atom)
        last_atom = atom
    return mol


# ------------------------ END CHAIN TOOL -------------------------




class RingTool(Tool):
    """ Create ring of varying size """
    tips = {
        "on_init": "Click and drag to draw ring of varying size",
    }

    def __init__(self):
        Tool.__init__(self)
        self.coords = []
        self.polygon_item = None
        self.count_item = None
        self.attach_to = None
        self.show_status(self.tips["on_init"])

    def on_mouse_press(self, x,y):
        self.mouse_press_pos = (x, y)
        focused = App.paper.focused_obj
        self.attach_to = isinstance(focused, (Atom,Bond)) and focused or None
        # the focused atom must have one neighbor
        if isinstance(focused, Atom) and len(focused.neighbors)!=1:
            self.attach_to = None

    def on_mouse_move(self, x,y):
        if not App.paper.dragging:
            return
        self.clear()
        center = self.mouse_press_pos
        l = Settings.bond_length
        r = geo.point_distance(center, (x,y))
        if r==0:
            return
        # formula of circum radius, r = l/(2*sin(pi/n))
        # so, n = pi/asin(l/(2*r))
        f = l/(2*r)
        if f<0.866:
            sides = int(PI/asin(f))
        else:
            sides = 3
        # previous radius can be different for same polygon depending on mouse pos.
        # recalculating radius, so that we have fixed size for same type polygon
        r = l/(2*sin(PI/sides))
        self.coords = geo.calc_polygon_coords(sides, center, r)

        if self.attach_to:
            if isinstance(self.attach_to, Atom):
                x1,y1, x2,y2 = self.attach_to.neighbors[0].pos + self.attach_to.pos
                xt1,yt1, xt2,yt2 = self.coords[0] + self.mouse_press_pos #self.coords[1]
                tr = geo.Transform()
                tr.translate(-xt1,-yt1)
                tr.rotate(atan2( xt1-xt2, yt1-yt2) - atan2( x1-x2, y1-y2))
                tr.translate(x2,y2)

            elif isinstance(self.attach_to, Bond):
                line1 = self.coords[0]+self.coords[1]
                line2 = self.attach_to.atom1.pos + self.attach_to.atom2.pos
                if geo.line_get_side_of_point(line2, (x,y))==1:
                    line2 = line2[2:] + line2[:2]
                tr = geo.create_transformation_to_coincide_two_lines(line1, line2)
            self.coords = tr.transform_points(self.coords)
            center = tr.transform(*center)

        self.polygon_item = App.paper.addPolygon(self.coords)
        self.count_item = App.paper.addHtmlText(str(sides), center, align=Align.HCenter|Align.VCenter)

    def on_mouse_release(self, x,y):
        self.clear()
        if self.coords:
            mol = create_cyclic_molecule_from_coordinates(self.coords)
            App.paper.addObject(mol)
            draw_recursively(mol)
            if self.attach_to:
                self.attach_to.molecule.eat_molecule(mol)
                self.attach_to.molecule.handle_overlap()
                draw_recursively(self.attach_to.molecule)
                self.attach_to = None
            self.coords = []
            App.paper.save_state_to_undo_stack("Ring Added")

    def clear(self):
        if self.polygon_item:
            App.paper.removeItem(self.polygon_item)
            App.paper.removeItem(self.count_item)
            self.polygon_item = None
            self.count_item = None

def create_cyclic_molecule_from_coordinates(coords):
    mol = Molecule()
    atoms = []
    for pt in coords:
        atom = mol.new_atom()
        atom.set_pos(*pt)
        if atoms:
            bond = mol.new_bond()
            bond.connect_atoms(atoms[-1], atom)
        atoms.append(atom)
    bond = mol.new_bond()
    bond.connect_atoms(atoms[-1], atoms[0])# to form a ring
    return mol


# ------------------------ END RING TOOL -------------------------




class ArrowPlusTool(Tool):
    tips = {
        "on_init": "Click to draw Plus (+); Press and drag to draw an Arrow",
    }

    def __init__(self):
        Tool.__init__(self)
        self.show_status(self.tips["on_init"])
        self.init_subtool(toolsettings["arrow_type"])

    def init_subtool(self, type_):
        if type_ in ("electron_flow", "fishhook"):
            self.subtool = SplineArrowTool()
        elif type_ == "circular":
            self.subtool = CircularArrowTool()
        else:
            self.subtool = NormalArrowTool()
        self.subtool.parent = self

    def on_mouse_press(self, x,y):
        self.mouse_press_pos = (x,y)
        self.subtool.on_mouse_press(x,y)

    def on_mouse_move(self, x,y):
        self.subtool.on_mouse_move(x,y)

    def on_mouse_release(self, x,y):
        self.subtool.on_mouse_release(x,y)

    def on_mouse_click(self, x, y):
        """ draw plus """
        plus = Plus()
        plus.set_pos(*self.mouse_press_pos)
        App.paper.addObject(plus)
        plus.draw()
        App.paper.save_state_to_undo_stack("Add Plus")

    def clear(self):
        self.subtool.clear()

    def on_property_change(self, key, value):
        if key=="arrow_type":
            self.subtool.clear()
            self.init_subtool(value)


class NormalArrowTool:
    def __init__(self):
        self.focus_item = None
        self.head_focused_arrow = None
        self.reset()

    def reset(self):
        self.arrow = None # working arrow
        self.mouse_press_pos = None

    def on_mouse_press(self, x,y):
        self.mouse_press_pos = (x,y)

    def on_mouse_move(self, x,y):
        # on mouse hover focus the arrow head
        if not App.paper.dragging:
            # check here if we have entered/left the head
            head_focused_arrow = None
            focused = App.paper.focused_obj
            if focused and isinstance(focused, Arrow):
                if geo.rect_contains_point(focused.head_bounding_box(), (x,y)):
                    head_focused_arrow = focused
            # draw head bounding box
            if head_focused_arrow!=self.head_focused_arrow:
                if self.head_focused_arrow:
                    App.paper.removeItem(self.focus_item)
                    self.focus_item = None
                    self.head_focused_arrow = None
                if head_focused_arrow:
                    self.head_focused_arrow = head_focused_arrow
                    rect = focused.head_bounding_box()
                    self.focus_item = App.paper.addRect(rect)
            return
        # on mouse drag
        if not self.arrow:
            if self.head_focused_arrow:
                self.arrow = self.head_focused_arrow
                # other arrows (e.g equilibrium) can not have more than two points
                if "normal" in self.arrow.type:
                    self.arrow.points.append(self.mouse_press_pos)
                self.head_focused_arrow = None
                if self.focus_item:
                    # remove focus item while dragging head, otherwise it stucks in prev position
                    App.paper.removeItem(self.focus_item)
                    self.focus_item = None
            else:
                # dragging on empty area, create new arrow
                self.arrow = Arrow(toolsettings["arrow_type"])
                self.arrow.set_points([self.mouse_press_pos]*2)
                App.paper.addObject(self.arrow)

        angle = int(toolsettings["angle"])
        d = max(Settings.min_arrow_length, geo.point_distance(self.arrow.points[-2], (x,y)))
        pos = geo.circle_get_point(self.arrow.points[-2], d, (x,y), angle)
        self.arrow.points[-1] = pos
        self.arrow.draw()

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.parent.on_mouse_click(x,y)
            return
        # if two lines are linear, merge them to single line
        if len(self.arrow.points)>2:
            a,b,c = self.arrow.points[-3:]
            if "normal" in self.arrow.type:# normal and normal_simple
                if abs(geo.line_get_angle_from_east([a[0], a[1], b[0], b[1]]) - geo.line_get_angle_from_east([a[0], a[1], c[0], c[1]])) < 0.02:
                    self.arrow.points.pop(-2)
                    self.arrow.draw()
        self.reset()
        App.paper.save_state_to_undo_stack("Add Arrow")

    def clear(self):
        if self.focus_item:
            App.paper.removeItem(self.focus_item)


class CircularArrowTool:
    def __init__(self):
        self.reset()

    def reset(self):
        self.arrow = None # working arrow
        self.mouse_press_pos = None
        # for curved arrow
        self.start_point = None
        self.end_point = None

    def on_mouse_press(self, x,y):
        self.mouse_press_pos = (x,y)

    def on_mouse_move(self, x,y):
        # dragging or not dragging, both cases
        if self.start_point and self.end_point:
            # draw curved arrow
            self.arrow.set_points([self.start_point, (x,y), self.end_point])
            self.arrow.draw()
            return

        if App.paper.dragging:
            if not self.start_point:# drag just started after mouse press
                self.start_point = self.mouse_press_pos
                self.arrow = Arrow(toolsettings["arrow_type"])
                App.paper.addObject(self.arrow)
            # draw straight arrow
            self.arrow.set_points([self.start_point, (x,y)])
            self.arrow.draw()

    def on_mouse_release(self, x,y):
        if self.start_point and self.end_point:
            App.paper.save_state_to_undo_stack("Add Arrow")
            self.reset()
        elif self.start_point:# first time release after dragging
            self.end_point = (x,y)
        elif not App.paper.dragging:
            self.parent.on_mouse_click(x,y)

    def clear(self):
        pass



class SplineArrowTool:
    def __init__(self):
        self.reset()

    def reset(self):
        self.arrow = None # working arrow
        self.mouse_press_pos = None
        # for curved arrow
        self.start_point = None
        self.end_point = None

    def on_mouse_press(self, x,y):
        self.mouse_press_pos = (x,y)
        self.focused_on_press = App.paper.focused_obj

    def on_mouse_move(self, x,y):
        # dragging or not dragging, both cases
        if self.start_point and self.end_point:
            # draw curved arrow
            knots = [self.start_point, (x,y), self.end_point]
            quad = geo.quad_bezier_through_points(knots)
            self.arrow.set_points(geo.quad_to_cubic_bezier(quad))
            self.arrow.adjust_anchored_points()
            self.arrow.draw()
            return

        if App.paper.dragging:
            if not self.start_point:# drag just started after mouse press
                self.start_point = self.mouse_press_pos
                self.arrow = Arrow(toolsettings["arrow_type"])
                App.paper.addObject(self.arrow)
                if focused := self.focused_on_press:
                    if (focused.class_name=="Atom" and focused.electron_src_marks_pos) \
                        or focused.class_name == "Bond":
                        self.arrow.e_src = focused
            # draw straight arrow
            # here we represent a straight line with cubic bezier, by dividing
            # straight line into three parts and use the points as control points
            p1 = (x+2*self.start_point[0])/3, (y+2*self.start_point[1])/3
            p2 = (2*x+self.start_point[0])/3, (2*y+self.start_point[1])/3
            self.arrow.set_points([self.start_point, p1, p2, (x,y)])
            self.arrow.draw()

    def on_mouse_release(self, x,y):
        if self.start_point and self.end_point:
            App.paper.save_state_to_undo_stack("Add Arrow")
            self.reset()
        elif self.start_point:# first time release after dragging
            self.end_point = (x,y)
            # set electron destination
            if (focused:=App.paper.focused_obj) and focused.class_name in ("Atom","Bond"):
                self.arrow.e_dst = focused
        elif not App.paper.dragging:
            self.parent.on_mouse_click(x,y)

    def clear(self):
        pass


# --------------------------- END ARROW-PLUS TOOL ---------------------------


class PlusChargeTool(Tool):
    tips = {
        "on_init": "Left click to increase +ve charge; Right click to remove charge",
    }

    def __init__(self):
        Tool.__init__(self)
        self.show_status(self.tips["on_init"])

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.on_mouse_click(x,y)

    def increase_charge(self, increase):
        focused = App.paper.focused_obj
        if not isinstance(focused, Atom):
            return
        charge = focused.charge+1 if increase else 0
        circle = toolsettings["type"] == "circled"
        # if type changed between normal and circled, do not change charge value
        if not (increase and focused.charge and circle!=focused.circle_charge):
            focused.set_charge(charge)
        elif circle==focused.circle_charge:# nothing is changed
            return
        focused.circle_charge = circle
        focused.draw()
        App.paper.save_state_to_undo_stack("Set Charge")

    def on_mouse_click(self, x, y):
        self.increase_charge(True)

    def on_right_click(self, x, y):
        self.increase_charge(False)

    def on_mouse_double_click(self, x,y):
        self.on_mouse_click(x,y)


class MinusChargeTool(Tool):
    tips = {
        "on_init": "Left click to increase -ve charge; Right click to remove charge",
    }

    def __init__(self):
        Tool.__init__(self)
        self.show_status(self.tips["on_init"])

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.on_mouse_click(x,y)

    def decrease_charge(self, decrease):
        focused = App.paper.focused_obj
        if not isinstance(focused, Atom):
            return
        charge = focused.charge-1 if decrease else 0
        circle = toolsettings["type"] == "circled"
        # if type changed between normal and circled, do not change charge value
        if not (decrease and focused.charge and circle!=focused.circle_charge):
            focused.set_charge(charge)
        elif circle==focused.circle_charge:# nothing is changed
            return
        focused.circle_charge = circle
        focused.draw()
        App.paper.save_state_to_undo_stack("Set Charge")

    def on_mouse_click(self, x, y):
        self.decrease_charge(True)

    def on_right_click(self, x, y):
        self.decrease_charge(False)

    def on_mouse_double_click(self, x,y):
        self.on_mouse_click(x,y)


class LonepairTool(Tool):
    tips = {
        "on_init": "Left Click to add Lone-pair; Right click to remove Lone-pair",
    }

    def __init__(self):
        Tool.__init__(self)
        self.show_status(self.tips["on_init"])

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.on_mouse_click(x,y)

    def increase_lonepair_count(self, change):
        focused = App.paper.focused_obj
        if not isinstance(focused, Atom):
            return
        # if type changed between dotted and dashed, do not change lonepair number
        if focused.lonepairs and focused.lonepair_type!=toolsettings["type"]:
            focused.lonepair_type = toolsettings["type"]
            focused.draw()
            return
        count = max(focused.lonepairs+change, 0)
        if count != focused.lonepairs:
            focused.set_lonepairs(count)
            focused.lonepair_type = toolsettings["type"]
            focused.draw()
            App.paper.save_state_to_undo_stack("Set Lonepairs")

    def on_mouse_click(self, x, y):
        self.increase_lonepair_count(1)

    def on_right_click(self, x, y):
        self.increase_lonepair_count(-1)

    def on_mouse_double_click(self, x,y):
        self.on_mouse_click(x,y)



class RadicalTool(Tool):
    tips = {
        "on_init": "Left click to add or change radical; Right click to remove radical",
    }

    def __init__(self):
        Tool.__init__(self)
        self.show_status(self.tips["on_init"])

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.on_mouse_click(x,y)

    def add_radical(self, add):
        focused = App.paper.focused_obj
        if not isinstance(focused, Atom):
            return
        if add:
            next_vals = {0:2, 2:3, 3:1, 1:2}
            radical = next_vals[focused.radical]
        else:
            radical = 0
        if radical != focused.radical:
            focused.set_radical(radical)
            focused.draw()
            App.paper.save_state_to_undo_stack("Set Radical")

    def on_mouse_click(self, x, y):
        self.add_radical(True)

    def on_right_click(self, x, y):
        self.add_radical(False)

    def on_mouse_double_click(self, x,y):
        self.on_mouse_click(x,y)


# ---------------------------- END MARK TOOLS ---------------------------


class TextTool(Tool):
    tips = {
        "on_init": "Click on empty place to enter text edit mode",
        "on_edit": "Press Esc to finish editing",
    }

    def __init__(self):
        Tool.__init__(self)
        self.text_obj = None
        self.prev_font_info = None
        self.clear()
        self.show_status(self.tips["on_init"])

    def on_mouse_release(self, x,y):
        if not App.paper.dragging:
            self.on_mouse_click(x,y)

    def on_mouse_click(self, x,y):
        prev_text_closed = bool(self.text_obj)
        self.clear()
        focused = App.paper.focused_obj
        if focused:
            if isinstance(focused, Text):
                self.text_obj = focused
                self.text = self.text_obj.text
                # backup original font info
                self.prev_font_info = (toolsettings['font_name'], toolsettings['font_size'])
                # get font settings from selected text object, and set in settingsbar
                App.window.setCurrentToolProperty("font_name", self.text_obj.font_name)
                App.window.setCurrentToolProperty("font_size", self.text_obj.font_size)
            else:
                return
        else:
            if prev_text_closed:
                return
            self.text_obj = Text()
            App.paper.addObject(self.text_obj)
            self.text_obj.set_pos(x,y)
            self.text_obj.font_name = toolsettings['font_name']
            self.text_obj.font_size = toolsettings['font_size']
        self.started_typing = True
        self.text_obj.set_text(self.text+"|")
        self.text_obj.draw()
        self.show_status(self.tips["on_edit"])

    def clear(self):
        # finish typing, by removing cursor symbol
        if self.text_obj:
            if self.text:
                self.text_obj.set_text(self.text)# removes cursor symbol
                self.text_obj.draw()
                App.paper.save_state_to_undo_stack("Add Text")
            else:
                self.text_obj.delete_from_paper()
            self.text_obj = None
        self.text = ""
        self.started_typing = False
        if self.prev_font_info:
            App.window.setCurrentToolProperty("font_name", self.prev_font_info[0])
            App.window.setCurrentToolProperty("font_size", self.prev_font_info[1])
            self.prev_font_info = None
        self.show_status(self.tips["on_init"])

    def on_key_press(self, key, text):
        if not self.started_typing:
            return
        if text:
            self.text += text
        else:
            if key=="Backspace":
                if self.text:
                    self.text = self.text[:-1]
            elif key in ("Return", "Enter"):
                self.text += "\n"
            elif key=="Esc":
                self.clear()
                return
        self.text_obj.set_text(self.text+"|")
        self.text_obj.draw()

    def on_property_change(self, key, value):
        if key=="text" and self.started_typing:
            self.text += value
            self.text_obj.set_text(self.text+"|")
            self.text_obj.draw()

# ---------------------------- END TEXT TOOL ---------------------------


class ColorTool(SelectTool):

    def __init__(self):
        SelectTool.__init__(self)

    def on_mouse_press(self, x,y):
        SelectTool.on_mouse_press(self, x, y)

    def on_mouse_release(self, x,y):
        SelectTool.on_mouse_release(self, x,y)
        selected = App.paper.selected_objs.copy()
        App.paper.deselectAll()
        if selected:
            set_objects_color(selected, toolsettings["color"])
            App.paper.save_state_to_undo_stack("Color Changed")

    def on_mouse_move(self, x,y):
        if not App.paper.dragging:
            return
        # draws selection area
        SelectTool.on_mouse_move(self, x,y)

def set_objects_color(objs, color):
    for obj in objs:
        obj.color = color
    draw_objs_recursively(objs)


# ---------------------------- END COLOR TOOL ---------------------------


class BracketTool(Tool):

    def __init__(self):
        Tool.__init__(self)
        self.reset()

    def on_mouse_press(self, x,y):
        SelectTool.on_mouse_press(self, x, y)

    def on_mouse_release(self, x,y):
        App.paper.save_state_to_undo_stack("Bracket Added")
        self.reset()

    def on_mouse_move(self, x,y):
        if not App.paper.dragging:
            return
        if not self.bracket:
            self.bracket = Bracket(toolsettings['bracket_type'])
            App.paper.addObject(self.bracket)
        rect = geo.rect_normalize(self.mouse_press_pos + (x,y))
        self.bracket.set_points([(rect[0], rect[1]), (rect[2], rect[3])])
        self.bracket.draw()

    def reset(self):
        self.bracket = None

# ---------------------------- END BRACKET TOOL ---------------------------





# --------------------------- For Creating GUI ------------------------

# get tool class from name
def tool_class(name):
    return globals()[name]


atomtools_template = [
    "C",  "N",  "O",  "F",
    "Si", "P",  "S",  "Cl",
    "H",  "B",  "Mg", "Br",
    "Li", "Na", "K",  "I"
]
grouptools_template = [
    "R", "Ph",
    "NO2", "CN",
    "CHO", "COOH",
    "CONH2", "COCH3",
    "COCl", "COBr",
    "OCH3", "OEt",
    "OAc", "SO3H",
    "OTs", "OBs",
]
# alphabetically sorted
group_smiles_dict = {
    "CHO": "C=O",
    "CN": "C#N",
    "COBr": "C(=O)Br",
    "COCH3": "C(=O)C",
    "COCl": "C(=O)Cl",
    "CONH2": "C(=O)N",
    "COOH": "C(O=)O",
    "NO2": "N(=O)O",
    "OAc": "OC(=O)C",
    "OBs": "OS(=O)(=O)C1=CC=C(Br)C=C1",
    "OCH3": "OC",
    "OEt": "OCC",
    "OTs": "OS(=O)(=O)C1=CC=C(C)C=C1",
    "Ph" : "C1=CC=CC=C1",
    "SO3H": "S(=O)(=O)O",
}


# required only once when main tool bar is created
tools_template = {
    # name         title          icon_name
    "MoveTool" :  ("Select/Move",     "move"),
    "RotateTool" : ("Rotate Molecule",  "rotate"),
    "ScaleTool" : ("Resize Objects",  "scale"),
    "AlignTool" : ("Align or Transform Molecule",  "align"),
    "StructureTool" : ("Draw Molecular Structure", "bond"),
    "ArrowPlusTool" : ("Plus and Arrow Tool", "plus-arrow"),
    "PlusChargeTool" : ("Increase +ve Charge", "charge-circledplus"),
    "MinusChargeTool" : ("Increase -ve Charge", "charge-circledminus"),
    "LonepairTool" : ("Add Lonepair", "lonepair"),
    "RadicalTool" : ("Add Radical", "radical"),
    "BracketTool" : ("Bracket Tool", "bracket-square"),
    "TextTool" : ("Write Text", "text"),
    "ColorTool" : ("Color Tool", "color"),
}

# ordered tools that appears on toolbar
toolbar_tools = ["MoveTool", "ScaleTool", "RotateTool", "AlignTool", "StructureTool",
    "PlusChargeTool", "MinusChargeTool", "LonepairTool",
    "RadicalTool", "ArrowPlusTool", "BracketTool", "TextTool", "ColorTool"
]

# in each settings mode, items will be shown in settings bar as same order as here
settings_template = {
    "StructureTool" : [# mode
        ["ButtonGroup", "bond_angle",# key/category
            # value   title         icon_name
            [('30', "30 degree", "angle-30"),
            ('15', "15 degree", "angle-15"),
            ('1', "1 degree", "angle-1"),
        ]],
        ["ButtonGroup", 'bond_type', [
            ('single', "Single Bond", "bond"),
            ('double', "Double Bond", "bond-double"),
            ('triple', "Triple Bond", "bond-triple"),
            ('delocalized', "Delocalized Bond", "bond-delocalized"),
            ('partial', "Partial Bond", "bond-partial"),
            ('hbond', "H-Bond", "bond-hydrogen"),
            ('coordinate', "Coordinate Bond", "bond-coordinate"),
            ('E_or_Z', "Cis or Trans Bond", "bond-EZ"),
            ('wavy', "Wavy (Up or Down) Bond", "bond-wavy"),
            ('wedge', "Solid Wedge Bond", "bond-wedge"),
            ('hashed_wedge', "Hashed Wedge Bond", "bond-hashed-wedge"),
            ('bold', "Bold (Above) Bond", "bond-bold"),
            ('hashed', "Hashed (Below) Bond", "bond-hashed"),
            ('bold2', "Bold Double Bond", "bond-bold2"),
            ('1_or_2', "Single or Double", "bond-SD"),
            ('1_or_a', "Single or Aromatic", "bond-SA"),
            ('2_or_a', "Double or Aromatic", "bond-DA"),
            ('any', "Any Bond", "bond-any"),
        ]],
        ["ButtonGroup", 'mode', [
            ('chain', "Draw Chain of varying size", "variable-chain"),
            ('ring', "Draw Ring of varying size", "variable-ring"),
        ]],
    ],
    "MoveTool" : [
        ["ButtonGroup", 'selection_mode',
            [('rectangular', "Rectangular Selection", "select-rectangular"),
            ('lasso', "Lasso Selection", "select-lasso"),
        ]],
        ["Button", "action", ("Duplicate", "duplicate")],
        ["Button", "action", ("Convert to Aromatic Form", "benzene-aromatic")],
    ],
    "ScaleTool" : [
        ["ButtonGroup", 'selection_mode',
            [('rectangular', "Rectangular Selection", "select-rectangular"),
            ('lasso', "Lasso Selection", "select-lasso"),
        ]],
    ],
    "RotateTool" : [
        ["ButtonGroup", 'rotation_type',
            [('2d', "2D Rotation", "rotate"),
            ('3d', "3D Rotation", "rotate3d"),
        ]]
    ],
    "AlignTool" : [
        ["ButtonGroup", 'mode', [
            ('horizontal_align', "Horizontal Align", "align-horizontal"),
            ('vertical_align', "Vertical Align", "align-vertical"),
            ('mirror', "Mirror", "transform-mirror"),
            ('inversion', "Inversion", "transform-inversion"),
            ('freerotation', "180° freerotation", "transform-freerotation"),
        ]]
    ],
    "PlusChargeTool" : [
        ["ButtonGroup", 'type',
            [('normal', "Normal", "charge-plus"),
            ('circled', "Circled", "charge-circledplus"),
        ]]
    ],
    "MinusChargeTool" : [
        ["ButtonGroup", 'type',
            [('normal', "Normal", "charge-minus"),
            ('circled', "Circled", "charge-circledminus"),
        ]]
    ],
    "LonepairTool" : [
        ["ButtonGroup", 'type',
            [('dots', "Dotted Lonepair", "lonepair"),
            ('dash', "Dashed Lonepair", "charge-minus"),
        ]]
    ],
    "RadicalTool" : [
    ],
    "ArrowPlusTool" : [
        ["ButtonGroup", 'angle',
            [('15', "15 degree", "angle-15"),
            ('1', "1 degree", "angle-1")],
        ],
        ["ButtonGroup", 'arrow_type',
            [('normal', "Normal", "arrow"),
            ('resonance', "Resonance", "arrow-resonance"),
            ('reversible', "Reversible", "arrow-reversible"),
            ('equilibrium', "Equilibrium", "arrow-equilibrium"),
            ('unbal_eqm', "Unbalanced Equilibrium", "arrow-unbalanced-eqm"),
            ('hollow', "Hollow", "arrow-hollow"),
            ('retrosynthetic', "Retrosynthetic", "arrow-retrosynthetic"),
            ('dashed', "Dashed (Theoretical Step)", "arrow-dashed"),
            ('crossed', "No Reaction (Crossed)", "arrow-crossed"),
            ('hashed', "No Reaction (Hashed)", "arrow-hashed"),
            ('harpoon_l', "Harpoon (Left)", "arrow-harpoon-left"),
            ('harpoon_r', "Harpoon (Right)", "arrow-harpoon-right"),
            ('circular', "Circular", "arrow-circular"),
            ('electron_flow', "Electron Pair Shift", "arrow-electron-shift"),
            ('fishhook', "Fishhook - Single electron shift", "arrow-fishhook"),
        ]],
    ],
    "BracketTool" : [
        ["ButtonGroup", 'bracket_type',
            [('square', "Square Bracket", "bracket-square"),
            ('curly', "Curly Bracket", "bracket-curly"),
            ('round', "Round Bracket", "bracket-round"),
        ]]
    ],
    "TextTool" : [
        ["Label", "Font : ", None],
        ["FontComboBox", "font_name", []],
        ["Label", "Size : ", None],
        ["SpinBox", "font_size", (6, 72)],
        ["Button", "text", ("°", None)],
        ["Button", "text", ("Δ", None)],
        ["Button", "text", ("α", None)],
        ["Button", "text", ("β", None)],
        ["Button", "text", ("γ", None)],
        ["Button", "text", ("δ", None)],
        ["Button", "text", ("λ", None)],
        ["Button", "text", ("μ", None)],
        ["Button", "text", ("ν", None)],
        ["Button", "text", ("π", None)],
        ["Button", "text", ("σ", None)],
        ["Button", "text", ("‡", None)],
    ],
    "ColorTool" : [
        ["ButtonGroup", 'selection_mode',
            [('rectangular', "Rectangular Selection", "select-rectangular"),
            ('lasso', "Lasso Selection", "select-lasso"),
        ]],
        ["PaletteWidget", 'color', []],
    ],
}

# tool settings manager
class ToolSettings:
    def __init__(self):
        self._dict = { # initialize with default values
            "MoveTool" : {'selection_mode': 'rectangular'},
            "ScaleTool" : {'selection_mode': 'rectangular'},
            "RotateTool" : {'rotation_type': '2d'},
            "AlignTool" : {'mode': 'horizontal_align'},# mode is atom, group or template
            "StructureTool" :  {'mode': 'atom', 'bond_angle': '30', 'bond_type': 'single', 'structure': 'C'},
            "ArrowPlusTool" : {'angle': '15', 'arrow_type':'normal'},
            "PlusChargeTool" : {'type': 'normal'},
            "MinusChargeTool" : {'type': 'normal'},
            "LonepairTool" : {'type': 'dots'},
            "TextTool" : {'font_name': 'Sans Serif', 'font_size': Settings.text_size},
            "ColorTool" : {'color': (240,2,17), 'color_index': 13, 'selection_mode': 'rectangular'},
            "BracketTool" : {'bracket_type': 'square'},
        }
        self._scope = "StructureTool"

    def setScope(self, scope):
        self._scope = scope

    def getValue(self, scope, key):
        return self._dict[scope][key]

    def setValue(self, scope, key, value):
        self._dict[scope][key] = value

    def __getitem__(self, key):
        return self._dict[self._scope][key]

    def __setitem__(self, key, value):
        self._dict[self._scope][key] = value

    def __delitem__(self, key):
        del self._dict[key]

# global tool settings container
toolsettings = ToolSettings()
