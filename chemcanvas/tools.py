# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, Settings
from drawing_parents import Color, Align, PenStyle
from paper import get_objs_with_all_children
from molecule import Molecule
from atom import Atom
from bond import Bond
from marks import Mark, Charge, Electron
from text import Text, Plus
from arrow import Arrow
from bracket import Bracket
import geometry as geo
import common

from math import sin, cos, pi, asin, atan2
from functools import reduce
import operator


class Tool:
    def __init__(self):
        pass

    @property
    def class_name(self):
        return self.__class__.__name__

    def onMousePress(self, x, y):
        pass

    def onMouseRelease(self, x, y):
        pass
    def onMouseMove(self, x, y):
        pass

    def onMouseDoubleClick(self, x, y):
        pass

    def onKeyPress(self, key, text):
        """ key is a string """
        pass

    def onRightClick(self, x,y):
        focused = App.paper.focused_obj
        if focused and isinstance(focused, (Atom,Bond)):
            menu = App.paper.createMenu()
            menu.object = focused
            create_menu_items_from_template(menu, focused.menu_template)
            menu.triggered.connect(on_object_property_action_click)
            # we could save state inside on_object_property_action_click(), but then
            # state will be saved twice if we use mark tool to set isotope number.
            menu.triggered.connect(save_state_to_undo_stack)
            App.paper.showMenu(menu, (x,y))

    def onPropertyChange(self, key, value):
        """ this is called when a tool settings is changed in settingsbar """
        pass

    def clear(self):
        """ clear graphics temporarily created by itself"""
        # clear temp graphics and the variables initially required in onMousePress(),
        # onMouseMove() (without dragging) and onKeyPress().
        # This is required in cases like, (1) not finished text editing and then doing undo.
        # (2) doing undo while scale tool bounding box is there.
        pass

    def showStatus(self, msg):
        App.window.showStatus(msg)

    def clearStatus(self):
        App.window.clearStatus()


# Menu Template Format -> ("Action1", SubMenu1, ...)
# Menu = a tuple of actions and submenus.
# Action = a string of "Action Name"
# SubMenu = another menu, i.e a tuple of actions and more submenus

def create_menu_items_from_template(menu, items_template):
    # for root menu, title is empty
    curr_val = menu.title() and menu.object.getProperty(menu.title()) or None

    for item in items_template:
        if isinstance(item, str):
            action = menu.addAction(item)
            action.key = menu.title()
            action.value = item
            action.object = menu.object
            if item==curr_val:
                action.setCheckable(True)
                action.setChecked(True)

        if isinstance(item, tuple):
            submenu = menu.addMenu(item[0])
            submenu.object = menu.object
            create_menu_items_from_template(submenu, item[1])


def on_object_property_action_click(action):
    action.object.setProperty(action.key, action.value)
    on_object_property_change(action.object)

def on_object_property_change(obj):
    obj.draw()
    if isinstance(obj, Atom):
        [bond.draw() for bond in obj.bonds]

def save_state_to_undo_stack():
    App.paper.save_state_to_undo_stack("Object Property Change")



class SelectTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        self._selection_rect_item = None

    def onMousePress(self, x, y):
        self.mouse_press_pos = (x, y)

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
        rect = geo.rect_normalize(self.mouse_press_pos + (x,y))
        if not self._selection_rect_item:
            self._selection_rect_item = App.paper.addRect(rect, style=PenStyle.dashed)
        else:
            App.paper.removeItem(self._selection_rect_item)
            self._selection_rect_item = App.paper.addRect(rect, style=PenStyle.dashed)
        objs = App.paper.objectsInRegion(rect)
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
        self.showStatus(self.tips["on_init"])

    def reset(self):
        self.drag_to_select = False
        self.objs_moved = False
        # self.have_objs_to_move = False
        # self.objs_to_move = set()
        # self.objs_to_redraw = set() # Bonds and Marks (eg lone-pair) need to redraw

    def onMousePress(self, x, y):
        self.reset()
        # if we have pressed on blank area, we are going to draw selection rect, and select objs
        if not App.paper.focused_obj:
            SelectTool.onMousePress(self, x,y)
            self.drag_to_select = True
            return
        self._prev_pos = [x,y]
        # if we drag a selected obj, all selected objs are moved
        if App.paper.focused_obj in App.paper.selected_objs:
            to_move = App.paper.selected_objs[:]
        else:
            # when we try to move atom or bond, whole molecule is moved
            if isinstance(App.paper.focused_obj.parent, Molecule):# atom or bond
                to_move = App.paper.focused_obj.parent.atoms[:]# moving atoms also moves bonds
            else:
                to_move = [App.paper.focused_obj]

        for obj in to_move:
            if isinstance(obj, Bond):
                to_move += obj.atoms

        self.objs_to_move = set(to_move)
        self.objs_to_redraw = set()# Bonds and Marks (eg lone-pair) need to redraw

        # Don't need this, unless objs other than Molecule have children
        #self.objs_to_move = set(get_objs_with_all_children(to_move))

        # get objects to redraw
        for obj in list(self.objs_to_move):
            if isinstance(obj, Atom):
                # when atom is moved, marks are automatically moved along (as they have
                # relative position). This prevents the marks from moving again.
                self.objs_to_move -= set(obj.marks)
                self.objs_to_redraw |= set(obj.marks)
                self.objs_to_redraw |= set(obj.bonds)
            # some marks need redraw, moving graphics items does not work.
            # eg - lone pair may rotate with position change
            elif isinstance(obj, Mark):
                self.objs_to_redraw.add(obj)

        anchored_arrows = set(o for o in App.paper.objects if isinstance(o,Arrow) and o.anchor)
        self.arrows_to_move_tail =  set(o for o in anchored_arrows if o.anchor in self.objs_to_redraw)
        self.arrows_to_move_body = set(o for o in anchored_arrows if o in self.objs_to_move)
        self.objs_to_move -= self.arrows_to_move_body
        self.objs_to_redraw |= self.arrows_to_move_tail
        self.objs_to_redraw |= self.arrows_to_move_body

        self.have_objs_to_move = bool(self.objs_to_move or self.arrows_to_move_tail
                                or self.arrows_to_move_body)

    def onMouseMove(self, x, y):
        if self.drag_to_select:
            SelectTool.onMouseMove(self, x, y)
            return
        if not (App.paper.dragging and self.have_objs_to_move):
            return
        dx, dy = x-self._prev_pos[0], y-self._prev_pos[1]
        for obj in self.objs_to_move:
            obj.moveBy(dx, dy)
            App.paper.moveItemsBy(obj.all_items, dx, dy)

        for arr in self.arrows_to_move_tail:
            arr.points[0] = (arr.points[0][0]+dx, arr.points[0][1]+dy)
        for arr in self.arrows_to_move_body:
            tail_pos = arr.points[0]
            arr.moveBy(dx, dy)
            arr.points[0] = tail_pos

        [obj.draw() for obj in self.objs_to_redraw]
        self.objs_moved = True
        self._prev_pos = [x,y]


    def onMouseRelease(self, x, y):
        # if not moving objects
        if self.drag_to_select or not App.paper.dragging:
            SelectTool.onMouseRelease(self, x, y)
            if App.paper.selected_objs:
                self.showStatus(self.tips["on_select"])
            else:
                self.clearStatus()
            return
        if self.objs_moved:
            App.paper.save_state_to_undo_stack("Move Object(s)")
            self.showStatus(self.tips["on_move"])

    def onKeyPress(self, key, text):
        if key=="Delete":
            self.deleteSelected()

    def deleteSelected(self):
        delete_objects(App.paper.selected_objs)# it has every object types, except Molecule
        App.paper.save_state_to_undo_stack("Delete Selected")
        # if there is no object left on paper, nothing to do with MoveTool
        if len(App.paper.objects)==0:
            App.window.selectToolByName("StructureTool")

    def clear(self):
        SelectTool.clear(self)


def delete_objects(objects):
    objects = set(objects)
    # separate objects that need to be handled specially (eg- atoms, bonds)
    marks = set(o for o in objects if isinstance(o,Mark))
    objects -= marks
    bonds = set(o for o in objects if isinstance(o,Bond))
    objects -= bonds
    atoms = set(o for o in objects if isinstance(o,Atom))
    objects -= atoms
    for atom in atoms:
        bonds |= set(atom.bonds)
        marks |= set(atom.marks)

    # delete all other objects
    while marks:
        mark = marks.pop()
        mark.atom.marks.remove(mark)
        mark.deleteFromPaper()
    while objects:
        obj = objects.pop()
        obj.deleteFromPaper()

    # first delete bonds
    modified_molecules = set()
    while bonds:
        bond = bonds.pop()
        modified_molecules.add(bond.molecule)
        bond.disconnectAtoms()
        bond.molecule.removeBond(bond)
        bond.deleteFromPaper()
    # then delete atoms
    while atoms:
        atom = atoms.pop()
        atom.molecule.removeAtom(atom)
        atom.deleteFromPaper()
    # split molecule
    while modified_molecules:
        mol = modified_molecules.pop()
        if len(mol.bonds)==0:# delete lone atom
            for child in mol.children:
                child.deleteFromPaper()
            mol.paper.removeObject(mol)
        else:
            new_mols = mol.splitFragments()
            # delete lone atoms
            [modified_molecules.add(mol) for mol in new_mols if len(mol.bonds)==0]

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
        self.showStatus(self.tips[toolsettings["rotation_type"]])

    def reset(self):
        self.mol_to_rotate = None
        self.rot_center = None
        self.rot_axis = None

    def onMousePress(self, x, y):
        self.mouse_press_pos = (x, y)
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
            self.rot_center = geo.rect_get_center(focused.parent.boundingBox()) + (0,)

        # initial angle
        if self.rot_center:
            self.start_angle = geo.line_get_angle_from_east([self.rot_center[0], self.rot_center[1], x,y])

    def onMouseMove(self, x, y):
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
                tr.rotateX(round(dy/50, 2))
                tr.rotateY(round(dx/50, 2))
                tr.translate( self.rot_center[0], self.rot_center[1], self.rot_center[2])
            # Rotate atoms
            for i, atom in enumerate(self.mol_to_rotate.atoms):
                atom.x, atom.y, atom.z = tr.transform(*self.initial_positions[i])

        # redraw whole molecule recursively
        draw_recursively(self.mol_to_rotate)

    def onMouseRelease(self, x, y):
        SelectTool.onMouseRelease(self, x ,y)
        App.paper.save_state_to_undo_stack("Rotate Objects")

    def clear(self):
        SelectTool.clear(self)

    def onPropertyChange(self, key, val):
        if key=="rotation_type":
            self.showStatus(self.tips[val])

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
        self.showStatus(self.tips["on_init"])

    def onMousePress(self, x,y):
        self.mouse_press_pos = (x, y)
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

    def onMouseRelease(self, x,y):
        if self.mode=="selection":
            SelectTool.onMouseRelease(self, x,y)
            self.getObjsToScale(App.paper.selected_objs)
            App.paper.deselectAll()
            self.createBoundingBox()
            return
        # resizing done, recalc and redraw bbox
        self.clear()
        self.createBoundingBox()
        App.paper.save_state_to_undo_stack("Scale Objects")

    def onMouseMove(self, x,y):
        """ drag modes : resizing, drawing selection bbox"""
        if not App.paper.dragging:
            return
        if self.mode=="selection":
            # draws selection box
            SelectTool.onMouseMove(self, x,y)
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


    def getObjsToScale(self, selected):
        """ get toplevel objects from selected """
        objs = set(filter(lambda o: o.is_toplevel, selected))
        objs |= set([obj.parent for obj in selected if not obj.is_toplevel and obj.parent.is_toplevel])
        self.objs_to_scale = get_objs_with_all_children(objs)

    def createBoundingBox(self):
        bboxes = [obj.boundingBox() for obj in self.objs_to_scale]
        if not bboxes:
            self.bbox = None
            return
        self.bbox = common.bbox_of_bboxes( bboxes)
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
        self.showStatus(self.tips[toolsettings["mode"]])

    def onMousePress(self, x,y):
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
        draw_recursively(mol)
        App.paper.save_state_to_undo_stack("Transform : %s" % toolsettings['mode'])

    def _apply_horizontal_align(self, coords, mol):
        x1,y1, x2,y2 = coords
        centerx = ( x1 + x2) / 2
        centery = ( y1 + y2) / 2
        angle0 = geo.line_get_angle_from_east( [x1, y1, x2, y2])
        if angle0 >= pi :
            angle0 = angle0 - pi
        if (angle0 > -0.005) and (angle0 < 0.005):# angle0 = 0
            # bond is already horizontal => horizontal "flip"
            angle = pi
        elif angle0 <= pi/2:
            angle = -angle0
        else:# pi/2 < angle < pi
            angle = pi - angle0
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
        if angle0 >= pi :
            angle0 = angle0 - pi
        if (angle0 > pi/2 - 0.005) and (angle0 < pi/2 + 0.005):# angle0 = 90 degree
            # bond is already vertical => vertical "flip"
            angle = pi
        else:
            angle = pi/2 - angle0
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
        if angle0 >= pi :
            angle0 = angle0 - pi
        tr = geo.Transform()
        tr.translate( -centerx, -centery)
        tr.rotate( -angle0)
        tr.scaleXY( 1, -1)
        tr.rotate( angle0)
        tr.translate(centerx, centery)
        return tr

    def _apply_mirror( self, coords, mol):
        tr = self._get_mirror_transformation(coords)
        transform_recursively(mol, tr)

    def _apply_freerotation( self, coords, mol):
        b = self.focused
        a1, a2 = b.atoms
        b.disconnectAtoms()
        cc = list( mol.get_connected_components())
        b.connectAtoms(a1, a2)
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

    def onPropertyChange(self, key, value):
        if key=="mode":
            self.showStatus(self.tips[value])


# --------------------------- END ALIGN TOOL ---------------------------



class StructureTool(Tool):

    tips = {
        "on_init": "Click → make new atom ; Press-and-drag → make new Bond",
        "on_empty_click": "Press-and-drag an atom to add bond ; Double click to edit atom text",
        "on_drag": "While pressing mouse, Press Shift → free bond length",
        "on_new_bond": "Click on atom → show/hide hydrogens ; Double click → edit atom text",
        "on_atom_click": "Click on different type of atom to change atom type",
        "on_text_edit": "Type symbol or formula, then Press Enter → accept, Esc → cancel changes"
    }

    def __init__(self):
        Tool.__init__(self)
        self.editing_atom = None
        self.reset()
        self.showStatus(self.tips["on_init"])

    def reset(self):
        self.atom1 = None
        self.atom2 = None
        self.bond = None

    def onMousePress(self, x, y):
        #print("press   : %i, %i" % (x,y))
        self.mouse_press_pos = (x,y)
        if self.editing_atom:
            self.exitFormulaEditMode()
            return
        self.prev_text = ""

        if not App.paper.focused_obj:
            mol = Molecule()
            App.paper.addObject(mol)
            self.atom1 = mol.newAtom(toolsettings["atom"])
            self.atom1.setPos(x,y)
            self.atom1.draw()
        elif type(App.paper.focused_obj) is Atom:
            # we have clicked on existing atom, use this atom to make new bond
            self.atom1 = App.paper.focused_obj


    def onMouseMove(self, x, y):
        if not App.paper.dragging:
            return
        if [x,y] == self.mouse_press_pos:# can not calculate atom pos in such situation
            return
        if not self.atom1: # in case we have clicked on object other than atom
            return
        if "Shift" in App.paper.modifier_keys:
            atom2_pos = (x,y)
        else:
            angle = int(toolsettings["bond_angle"])
            bond_length = Settings.bond_length * self.atom1.molecule.scale_val
            atom2_pos = geo.circle_get_point( self.atom1.pos, bond_length, [x,y], angle)
        # we are clicking and dragging mouse
        if not self.atom2:
            self.atom2 = self.atom1.molecule.newAtom(toolsettings["atom"])
            self.atom2.setPos(*atom2_pos)
            self.bond = self.atom1.molecule.newBond()
            self.bond.setType(toolsettings['bond_type'])
            self.bond.connectAtoms(self.atom1, self.atom2)
            if self.atom1.redrawNeeded():# because, hydrogens may be changed
                self.atom1.draw()
            self.atom2.draw()
            self.bond.draw()
            App.paper.dont_focus.add(self.atom2)
        else: # move atom2
            if type(App.paper.focused_obj) is Atom and App.paper.focused_obj is not self.atom1:
                self.atom2.setPos(*App.paper.focused_obj.pos)
            else:
                self.atom2.setPos(*atom2_pos)
            self.atom2.draw()
            [bond.draw() for bond in self.atom2.bonds]

        self.showStatus(self.tips["on_drag"])


    def onMouseRelease(self, x, y):
        #print("release : %i, %i" % (x,y))
        if not App.paper.dragging:
            self.onMouseClick(x,y)
            return
        #print("mouse dragged")
        if not self.atom2:
            return
        App.paper.dont_focus.remove(self.atom2)
        touched_atom = App.paper.touchedAtom(self.atom2)
        if touched_atom:
            if touched_atom is self.atom1 or touched_atom in self.atom1.neighbors:
                # we can not create another bond over an existing bond
                self.bond.disconnectAtoms()
                self.bond.molecule.removeBond(self.bond)
                self.bond.deleteFromPaper()
                self.atom2.molecule.removeAtom(self.atom2)
                self.atom2.deleteFromPaper()
                self.reset()
                return
            touched_atom.eatAtom(self.atom2)# this does atom1.resetText()
            self.atom2 = touched_atom

        # these two lines must be after handling touched atom, not before.
        self.atom1.resetTextLayout()
        self.atom1.draw()

        self.atom2.resetTextLayout()
        self.atom2.draw()
        self.bond.draw()
        reposition_bonds_around_atom(self.atom1)
        if touched_atom:
            reposition_bonds_around_atom(self.atom2)
        self.reset()
        App.paper.save_state_to_undo_stack()
        self.showStatus(self.tips["on_new_bond"])


    def onMouseClick(self, x, y):
        #print("click   : %i, %i" % (x,y))
        focused_obj = App.paper.focused_obj
        if not focused_obj:
            if self.atom1:# atom1 is None when previous mouse press finished editing atom text
                self.atom1.show_symbol = True
                self.atom1.resetText()
                self.atom1.draw()
                self.showStatus(self.tips["on_empty_click"])

        elif type(focused_obj) is Atom:
            atom = focused_obj
            # prev_text is used to undo single click effect if double click happens
            self.prev_text = atom.symbol
            if atom.hydrogens:
                self.prev_text += atom.hydrogens==1 and "H" or "H%i"%atom.hydrogens

            if atom.symbol != toolsettings["atom"]:
                atom.setSymbol(toolsettings["atom"])
            elif atom.symbol == "C":
                atom.show_symbol = not atom.show_symbol
                atom.resetText()
            else:
                atom.toggleHydrogens()
                atom.resetText()
            atom.draw()
            [bond.draw() for bond in atom.bonds]
            self.showStatus(self.tips["on_atom_click"])

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
            elif selected_bond_type in ("double", "aromatic"):
                bond.changeDoubleBondAlignment()
            elif selected_bond_type in ("coordinate", "wedge", "hatch"):
                # reverse bond direction
                atom1, atom2 = bond.atoms
                bond.disconnectAtoms()
                bond.connectAtoms(atom2, atom1)
            # if bond order changes, hydrogens of atoms will be changed, so redraw
            [atom.draw() for atom in bond.atoms if atom.redrawNeeded()]
            bond.draw()

        self.reset()
        App.paper.save_state_to_undo_stack()

    def onMouseDoubleClick(self, x,y):
        #print("double click   : %i, %i" % (x,y))
        focused = App.paper.focused_obj
        if not focused or not isinstance(focused, Atom):
            return
        # ------- Enter Formula Edit Mode -------
        # when there is slight movement of mouse between single and double click,
        # double click may occur on different object than single click.
        # in that case prev_text is empty string
        if self.prev_text:
            # double click is preceeded by a single click event, setting symbol
            # to prev_text reverses the effect of previous single click
            focused.setSymbol(self.prev_text)
        self.editing_atom = focused
        self.text = self.editing_atom.symbol
        # show text cursor
        self.redrawEditingAtom()
        self.showStatus(self.tips["on_text_edit"])

    def onKeyPress(self, key, text):
        if not self.editing_atom:
            return
        if text.isalnum() or text in ("(", ")"):
            self.text += text
        else:
            if key == "Backspace":
                if self.text:
                    self.text = self.text[:-1]
            elif key in ("Enter", "Return"):
                self.clear()
                return
            elif key == "Esc":# restore text and exit editing mode
                self.text = ""
                self.clear()
                return
        self.redrawEditingAtom()

    def redrawEditingAtom(self):
        # append a cursor symbol
        self.editing_atom.setSymbol(self.text+"|")
        self.editing_atom.draw()
        [bond.draw() for bond in self.editing_atom.bonds]

    def exitFormulaEditMode(self):
        if not self.editing_atom:
            return
        if not self.text:# cancel changes if we have erased whole formula using Backspace
            self.text = self.prev_text
        self.editing_atom.setSymbol(self.text)
        # prevent automatically adding hydrogen if symbol has one atom
        self.editing_atom.auto_hydrogens = False
        self.editing_atom.hydrogens = 0
        self.editing_atom.draw()
        [bond.draw() for bond in self.editing_atom.bonds]
        self.editing_atom = None
        self.text = ""
        App.paper.save_state_to_undo_stack("Edit Atom Text")
        self.clearStatus()

    def clear(self):
        self.exitFormulaEditMode()


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
        self.showStatus(self.tips["on_init"])

    def onMousePress(self, x,y):
        self.mouse_press_pos = (x, y)
        self.start_atom = None
        focused = App.paper.focused_obj
        if focused and isinstance(focused, Atom):
            self.start_atom = focused

    def onMouseMove(self, x,y):
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

    def onMouseRelease(self, x,y):
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
        last_atom = mol.newAtom()
        last_atom.setPos(*start_pos)

    for pt in coords:
        atom = mol.newAtom()
        atom.setPos(*pt)
        bond = mol.newBond()
        bond.connectAtoms(last_atom, atom)
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
        self.showStatus(self.tips["on_init"])

    def onMousePress(self, x,y):
        self.mouse_press_pos = (x, y)
        focused = App.paper.focused_obj
        self.attach_to = isinstance(focused, (Atom,Bond)) and focused or None
        # the focused atom must have one neighbor
        if isinstance(focused, Atom) and len(focused.neighbors)!=1:
            self.attach_to = None

    def onMouseMove(self, x,y):
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
            sides = int(pi/asin(f))
        else:
            sides = 3
        # previous radius can be different for same polygon depending on mouse pos.
        # recalculating radius, so that we have fixed size for same type polygon
        r = l/(2*sin(pi/sides))
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
            self.coords = tr.transformPoints(self.coords)
            center = tr.transform(*center)

        self.polygon_item = App.paper.addPolygon(self.coords)
        self.count_item = App.paper.addHtmlText(str(sides), center, align=Align.HCenter|Align.VCenter)

    def onMouseRelease(self, x,y):
        self.clear()
        if self.coords:
            mol = create_cyclic_molecule_from_coordinates(self.coords)
            App.paper.addObject(mol)
            draw_recursively(mol)
            if self.attach_to:
                self.attach_to.molecule.eatMolecule(mol)
                self.attach_to.molecule.handleOverlap()
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
        atom = mol.newAtom()
        atom.setPos(*pt)
        if atoms:
            bond = mol.newBond()
            bond.connectAtoms(atoms[-1], atom)
        atoms.append(atom)
    bond = mol.newBond()
    bond.connectAtoms(atoms[-1], atoms[0])# to form a ring
    return mol


# ------------------------ END RING TOOL -------------------------




class TemplateTool(Tool):
    """ Template Tool """
    tips = {
        "on_init": "Select a template, and then click empty area or Atom or Bond",
    }

    def __init__(self):
        Tool.__init__(self)
        self.showStatus(self.tips["on_init"])

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
            draw_recursively(t)
            t.template_atom = None
            t.template_bond = None
        elif isinstance(focused, Atom):
            # (x1,y1) is the point where template atom is placed, (x2,y2) is the point
            # for aligning and scaling the template molecule
            if focused.free_valency >= App.template_manager.getTemplateValency():# merge atom
                x1, y1 = focused.x, focused.y
                if len(focused.neighbors)==1:# terminal atom
                    x2, y2 = focused.neighbors[0].pos
                else:
                    x2, y2 = focused.molecule.findPlace(focused, Settings.bond_length)
                    x2, y2 = (2*x1 - x2), (2*y1 - y2)# to opposite side of x1, y1
                t = App.template_manager.getTransformedTemplate([x1,y1,x2,y2], "Atom")
                focused.eatAtom(t.template_atom)
            else: # connect template atom and focused atom with bond
                x1, y1 = focused.molecule.findPlace(focused, Settings.bond_length)
                x2, y2 = focused.pos
                t = App.template_manager.getTransformedTemplate([x1,y1,x2,y2], "Atom")
                t_atom = t.template_atom
                focused.molecule.eatMolecule(t)
                bond = focused.molecule.newBond()
                bond.connectAtoms(focused, t_atom)
            focused.molecule.handleOverlap()
            draw_recursively(focused.molecule)
        elif isinstance(focused, Bond):
            x1, y1 = focused.atom1.pos
            x2, y2 = focused.atom2.pos
            # template is attached to the left side of the passed coordinates,
            atms = focused.atom1.neighbors + focused.atom2.neighbors
            atms = set(atms) - set(focused.atoms)
            coords = [a.pos for a in atms]
            # so if most atoms are at the left side, switch start and end point
            if reduce( operator.add, [geo.line_get_side_of_point( (x1,y1,x2,y2), xy) for xy in coords], 0) > 0:
                x1, y1, x2, y2 = x2, y2, x1, y1
            t = App.template_manager.getTransformedTemplate((x1,y1,x2,y2), "Bond")
            focused.molecule.eatMolecule(t)
            focused.molecule.handleOverlap()
            draw_recursively(focused.molecule)
        else:
            return
        App.paper.save_state_to_undo_stack("add template : %s"% App.template_manager.current.name)


    def onRightClick(self, x,y):
        focused = App.paper.focused_obj
        if focused and isinstance(focused, (Atom,Bond)):
            menu = App.paper.createMenu()
            menu.object = focused
            menu_template = ("Set As Template " + focused.class_name,)
            create_menu_items_from_template(menu, menu_template)
            menu.triggered.connect(mark_as_template)
            menu.triggered.connect(save_state_to_undo_stack)
            App.paper.showMenu(menu, (x,y))

def mark_as_template(action):
    obj = action.object
    if obj.class_name=="Atom":
        obj.molecule.template_atom = obj
    elif obj.class_name=="Bond":
        obj.molecule.template_bond = obj

# ------------------------ END TEMPLATE TOOL ---------------------------




class PlusTool(Tool):
    def __init__(self):
        Tool.__init__(self)

    def onMouseRelease(self, x, y):
        if not App.paper.dragging:
            self.onMouseClick(x,y)

    def onMouseClick(self, x, y):
        plus = Plus()
        plus.font_size = toolsettings['size']
        plus.setPos(x,y)
        App.paper.addObject(plus)
        plus.draw()
        App.paper.save_state_to_undo_stack("Add Plus")

# ---------------------------- END PLUS TOOL ---------------------------


class ArrowTool(Tool):
    tips = {
        "on_init": "Press and drag to draw an Arrow",
    }

    def __init__(self):
        Tool.__init__(self)
        self.head_focused_arrow = None
        self.focus_item = None
        self.reset()
        self.showStatus(self.tips["on_init"])

    def reset(self):
        self.arrow = None # working arrow
        # for curved arrow
        self.start_point = None
        self.end_point = None

    def clear(self):
        if self.focus_item:
            App.paper.removeItem(self.focus_item)
        self.head_focused_arrow = None
        self.start_point = None

    def isSplineMode(self):
        return toolsettings["arrow_type"] in ("electron_shift", "fishhook")

    def onMousePress(self, x,y):
        if self.isSplineMode():
            self.onMousePressSpline(x,y)
            return
        if self.head_focused_arrow:
            self.arrow = self.head_focused_arrow
            # other arrows (e.g equilibrium) can not have more than two points
            if "normal" in self.arrow.type:
                self.arrow.points.append((x,y))
        else:
            # dragging on empty area, create new arrow
            self.arrow = Arrow(toolsettings["arrow_type"])
            self.arrow.setPoints([(x,y), (x,y)])
            App.paper.addObject(self.arrow)

    def onMouseMove(self, x, y):
        if self.isSplineMode():
            self.onMouseMoveSpline(x,y)
            return
        # on mouse hover
        if not App.paper.dragging:
            # check here if we have entered/left the head
            head_focused_arrow = None
            focused = App.paper.focused_obj
            if focused and isinstance(focused, Arrow):
                if geo.rect_contains_point(focused.headBoundingBox(), (x,y)):
                    head_focused_arrow = focused
            if head_focused_arrow!=self.head_focused_arrow:
                if self.head_focused_arrow:
                    App.paper.removeItem(self.focus_item)
                    self.focus_item = None
                    self.head_focused_arrow = None
                if head_focused_arrow:
                    rect = focused.headBoundingBox()
                    self.focus_item = App.paper.addRect(rect)
                    self.head_focused_arrow = head_focused_arrow
            return
        if self.focus_item:
            # remove focus item while dragging head, otherwise it stucks in prev position
            App.paper.removeItem(self.focus_item)
            self.focus_item = None
            self.head_focused_arrow = None

        angle = int(toolsettings["angle"])
        d = max(Settings.min_arrow_length, geo.point_distance(self.arrow.points[-2], (x,y)))
        pos = geo.circle_get_point(self.arrow.points[-2], d, (x,y), angle)
        self.arrow.points[-1] = pos
        self.arrow.draw()

    def onMouseRelease(self, x, y):
        if self.isSplineMode():
            self.onMouseReleaseSpline(x,y)
            return
        if not App.paper.dragging:
            self.onMouseClick(x,y)
        # if two lines are linear, merge them to single line
        if len(self.arrow.points)>2:
            a,b,c = self.arrow.points[-3:]
            if "normal" in self.arrow.type:# normal and normal_simple
                if abs(geo.line_get_angle_from_east([a[0], a[1], b[0], b[1]]) - geo.line_get_angle_from_east([a[0], a[1], c[0], c[1]])) < 0.02:
                    self.arrow.points.pop(-2)
                    self.arrow.draw()
                    #print("merged two lines")
        self.reset()
        App.paper.save_state_to_undo_stack("Add Arrow")

    def onMouseClick(self, x, y):
        self.arrow = Arrow(toolsettings["arrow_type"])
        self.arrow.setPoints([(x,y), (x+Settings.min_arrow_length,y)])
        App.paper.addObject(self.arrow)
        self.arrow.draw()

    # press and release cycle for curved arrow
    # press -> create start_point -> drag -> release -> create end_point
    #   ^                                                 |
    #   |                                                 v
    # reset <- release       <-     clear points <- press
    def onMousePressSpline(self, x,y):
        if not self.start_point:# first time press
            self.start_point = (x,y)
            self._anchor = None
            focused = App.paper.focused_obj
            if focused and focused.class_name in ("Electron", "Charge", "Bond"):
                self._anchor = focused
        else:
            # have both start and end point created by previous press and release
            self.start_point = None

    def onMouseReleaseSpline(self, x,y):
        if self.start_point and self.arrow:# first time release after dragging
            self.end_point = (x,y)
            return
        # a mouse click or second time release
        if self.arrow:
            App.paper.save_state_to_undo_stack("Add Arrow")
        self.reset()

    def onMouseMoveSpline(self, x,y):
        if self.start_point and self.end_point:
            # draw curved arrow
            self.arrow.setPoints([self.start_point, (x,y), self.end_point])
            anchor = self.arrow.anchor
            if anchor and isinstance(anchor, Mark):
                x1, y1 = geo.rect_get_intersection_of_line(anchor.boundingBox(), (x,y) + (anchor.x, anchor.y))
                self.arrow.setPoints([(x1,y1), (x,y), self.end_point])
            self.arrow.draw()
        elif self.start_point and App.paper.dragging:
            # draw straight arrow
            if not self.arrow:
                self.arrow = Arrow(toolsettings["arrow_type"])
                App.paper.addObject(self.arrow)
                if self._anchor:
                    self.arrow.setAnchor(self._anchor)
            self.arrow.setPoints([self.start_point, (x,y)])
            self.arrow.draw()


    def updateArrowPosition(self):
        if self.arrow.anchor:
            if self.arrow.anchor.class_name in ("Charge", "Electron"):
                self.points[0] = self.arrow.anchor.pos
            elif self.anchor.class_name == "Bond":
                self.anchor.getClosestPointFrom(self.points[1])

# --------------------------- END ARROW TOOL ---------------------------




class MarkTool(Tool):
    tips = {
        "on_init": "Click an Atom to place the mark",
        "on_new_charge": "Click again to increase charge; Select opposite charge and click atom to decrease charge",
        "delete_mode": "Click the Mark to delete, or Click Atom to delete last added Mark",
    }

    def __init__(self):
        Tool.__init__(self)
        self.reset()
        self.showStatus(self.tips["on_init"])

    def reset(self):
        self.prev_pos = None
        self.mark = None

    def onMousePress(self, x,y):
        if isinstance(App.paper.focused_obj, Mark):
            self.mark = App.paper.focused_obj
            self.prev_pos = (x,y)

    def onMouseMove(self, x,y):
        if not App.paper.dragging or not self.mark:
            return
        dx, dy = x-self.prev_pos[0], y-self.prev_pos[1]
        self.mark.moveBy(dx, dy)
        self.mark.draw()
        self.prev_pos = (x,y)

    def onMouseRelease(self, x, y):
        if not App.paper.dragging:
            self.onMouseClick(x,y)
        self.reset()
        App.paper.save_state_to_undo_stack("Add Mark : %s" % toolsettings["mark_type"])


    def onMouseClick(self, x, y):
        focused = App.paper.focused_obj
        if not focused:
            return
        mark_type = toolsettings["mark_type"]

        if mark_type=="DeleteMark":
            if isinstance(focused, Mark):
                delete_mark(focused)
            elif isinstance(focused, Atom) and len(focused.marks):
                # remove last mark from atom
                delete_mark(focused.marks[-1])

        # clicked on atom, create new mark
        elif isinstance(focused, Atom):
            if mark_type=="isotope":
                template = focused.isotope_template
                menu = App.paper.createMenu(template[0])
                menu.object = focused
                create_menu_items_from_template(menu, template[1])
                menu.triggered.connect(on_object_property_action_click)
                App.paper.showMenu(menu, (x,y))

            elif mark_type.startswith("charge"):
                charge = atom_get_charge_obj(focused)
                if charge:
                    self.on_charge_click(charge)# changes charge val
                else:
                    mark = create_new_mark_in_atom(focused, mark_type)
                    mark.draw()
                self.showStatus(self.tips["on_new_charge"])
            else:
                mark = create_new_mark_in_atom(focused, mark_type)
                mark.draw()

        elif focused.class_name=="Charge":
            if mark_type.startswith("charge"):
                self.on_charge_click(focused)


    def on_charge_click(self, charge):
        charge_type, val = charge_info[ toolsettings["mark_type"] ]
        if charge_type!=charge.type:
            charge.setType(charge_type)
        else:
            # same type charge, increment val
            val = charge.value + val or -charge.value
        charge.setValue(val)
        charge.draw()

    def onPropertyChange(self, key, val):
        if key=="mark_type":
            if val=="DeleteMark":
                self.showStatus(self.tips["delete_mode"])
            else:
                self.showStatus(self.tips["on_init"])

    def clear(self):
        # we dont want to remain in delete mode, when we come back from another tool
        if toolsettings["mark_type"]=="DeleteMark":
            toolsettings["mark_type"] = "charge_plus"



charge_info = {
    "charge_plus": ("normal", 1),
    "charge_minus": ("normal", -1),
    "charge_circledplus": ("circled", 1),
    "charge_circledminus": ("circled", -1),
    "charge_deltaplus": ("partial", 1),
    "charge_deltaminus": ("partial", -1),
}

def create_mark_from_type(mark_type):
    """ @mark_type types are specified in settings template """
    if mark_type.startswith("charge"):
        typ, val = charge_info[mark_type]
        mark = Charge(typ)
        mark.setValue(val)

    elif mark_type=="electron_single":
        mark = Electron("1")
    elif mark_type=="electron_pair":
        mark = Electron("2")
    else:
        raise ValueError("Can not create mark from invalid mark type")
    return mark

def create_new_mark_in_atom(atom, mark_type):
    mark = create_mark_from_type(mark_type)
    mark.atom = atom
    x, y = find_place_for_mark(mark)
    mark.setPos(x,y)
    # this must be done after setting the pos, otherwise it will not
    # try to find new place for mark
    atom.marks.append(mark)
    return mark

def find_place_for_mark(mark):
    """ find place for new mark. mark must have a parent atom """
    atom = mark.atom
    # deal with statically positioned marks # TODO
    #if mark.meta__mark_positioning == 'righttop':# oxidation_number
    #    bbox = atom.boundingBox()
    #    return bbox[2]+2, bbox[1]

    # deal with marks in linear_form
    #if atom.is_part_of_linear_fragment():
    #    if isinstance(mark, AtomNumber):
    #        bbox = atom.bbox()
    #        return int( atom.x-0.5*atom.font_size), bbox[1]-2

    # calculate distance from atom pos
    if not atom.show_symbol:
        dist = round(1.5*mark.size)
    else:
        dist = 0.75*atom.font_size + round( Settings.mark_size / 2)

    x, y = atom.x, atom.y

    neighbors = atom.neighbors
    # special cases
    if not neighbors:
        # single atom molecule
        if atom.hydrogens and atom.text_layout == "LTR":
            return x -dist, y-3
        else:
            return x +dist, y-3

    # normal case
    coords = [(a.x,a.y) for a in neighbors]
    # we have to take marks into account
    [coords.append( (m.x, m.y)) for m in atom.marks]
    # hydrogen positioning is also important
    if atom.show_symbol and atom.hydrogens:
        if atom.text_layout == 'RTL':
            coords.append( (x-10,y))
        else:
            coords.append( (x+10,y))

    # now we can compare the angles
    angles = [geo.line_get_angle_from_east([x,y, x1,y1]) for x1,y1 in coords]
    angles.append( 2*pi + min( angles))
    angles.sort(reverse=True)
    diffs = common.list_difference( angles)
    i = diffs.index( max( diffs))
    angle = (angles[i] + angles[i+1]) / 2
    direction = (x+cos(angle), y+sin(angle))

    # we calculate the distance here again as it is anisotropic (depends on direction)
    if atom.show_symbol:
        x0, y0 = geo.circle_get_point((x,y), 500, direction)
        x1, y1 = geo.rect_get_intersection_of_line(atom.boundingBox(), [x,y,x0,y0])
        dist = geo.point_distance((x,y), (x1,y1)) + round( Settings.mark_size / 2)

    return geo.circle_get_point((x,y), dist, direction)

def delete_mark(mark):
    mark.atom.marks.remove(mark)
    mark.deleteFromPaper()

def atom_get_charge_obj(atom):
    for mark in atom.marks:
        if mark.class_name=="Charge":
            return mark


# ---------------------------- END MARK TOOL ---------------------------


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
        self.showStatus(self.tips["on_init"])

    def onMouseRelease(self, x,y):
        if not App.paper.dragging:
            self.onMouseClick(x,y)

    def onMouseClick(self, x,y):
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
            self.text_obj.setPos(x,y)
            self.text_obj.font_name = toolsettings['font_name']
            self.text_obj.font_size = toolsettings['font_size']
        self.started_typing = True
        self.text_obj.setText(self.text+"|")
        self.text_obj.draw()
        self.showStatus(self.tips["on_edit"])

    def clear(self):
        # finish typing, by removing cursor symbol
        if self.text_obj:
            if self.text:
                self.text_obj.setText(self.text)# removes cursor symbol
                self.text_obj.draw()
                App.paper.save_state_to_undo_stack("Add Text")
            else:
                self.text_obj.deleteFromPaper()
            self.text_obj = None
        self.text = ""
        self.started_typing = False
        if self.prev_font_info:
            App.window.setCurrentToolProperty("font_name", self.prev_font_info[0])
            App.window.setCurrentToolProperty("font_size", self.prev_font_info[1])
            self.prev_font_info = None
        self.showStatus(self.tips["on_init"])

    def onKeyPress(self, key, text):
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
        self.text_obj.setText(self.text+"|")
        self.text_obj.draw()

    def onPropertyChange(self, key, value):
        if key=="text" and self.started_typing:
            self.text += value
            self.text_obj.setText(self.text+"|")
            self.text_obj.draw()

# ---------------------------- END TEXT TOOL ---------------------------


class ColorTool(SelectTool):

    def __init__(self):
        SelectTool.__init__(self)

    def onMousePress(self, x,y):
        self.mouse_press_pos = (x, y)

    def onMouseRelease(self, x,y):
        SelectTool.onMouseRelease(self, x,y)
        selected = App.paper.selected_objs.copy()
        App.paper.deselectAll()
        if selected:
            set_objects_color(selected, toolsettings["color"])
            App.paper.save_state_to_undo_stack("Color Changed")

    def onMouseMove(self, x,y):
        if not App.paper.dragging:
            return
        # draws selection box
        SelectTool.onMouseMove(self, x,y)

def set_objects_color(objs, color):
    objs = [obj for obj in objs if not isinstance(obj, Mark)]
    for obj in objs:
        obj.color = color
    draw_objs_recursively(objs)


# ---------------------------- END COLOR TOOL ---------------------------


class BracketTool(SelectTool):

    def __init__(self):
        Tool.__init__(self)
        self.reset()

    def onMousePress(self, x,y):
        self.mouse_press_pos = (x, y)

    def onMouseRelease(self, x,y):
        App.paper.save_state_to_undo_stack("Bracket Added")
        self.reset()

    def onMouseMove(self, x,y):
        if not App.paper.dragging:
            return
        if not self.bracket:
            self.bracket = Bracket(toolsettings['bracket_type'])
            App.paper.addObject(self.bracket)
        rect = geo.rect_normalize(self.mouse_press_pos + (x,y))
        self.bracket.setPoints([(rect[0], rect[1]), (rect[2], rect[3])])
        self.bracket.draw()

    def reset(self):
        self.bracket = None

# ---------------------------- END BRACKET TOOL ---------------------------




# ---------------------- Some Helper Functions -------------------------

def draw_recursively(obj):
    draw_objs_recursively([obj])

def draw_objs_recursively(objs):
    objs = get_objs_with_all_children(objs)
    objs = sorted(objs, key=lambda x : x.redraw_priority)
    [o.draw() for o in objs]

def transform_recursively(obj, tr):
    objs = get_objs_with_all_children([obj])
    [o.transform(tr) for o in objs]


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


# required only once when main tool bar is created
tools_template = {
    # name         title          icon_name
    "MoveTool" :  ("Select/Move",     "move"),
    "RotateTool" : ("Rotate Molecule",  "rotate"),
    "ScaleTool" : ("Resize Objects",  "scale"),
    "AlignTool" : ("Align or Transform Molecule",  "align"),
    "StructureTool" : ("Draw Molecular Structure", "bond"),
    "ChainTool" : ("Draw Chain of varying size", "variable-chain"),
    "RingTool" : ("Draw Ring of varying size", "variable-ring"),
    "TemplateTool" : ("Template Tool", "benzene"),
    "PlusTool" : ("Reaction Plus", "plus"),
    "ArrowTool" : ("Reaction Arrow", "arrow"),
    "MarkTool" : ("Add/Remove Atom Marks", "charge-circledplus"),
    "BracketTool" : ("Bracket Tool", "bracket-square"),
    "TextTool" : ("Write Text", "text"),
    "ColorTool" : ("Color Tool", "color"),
}

# ordered tools that appears on toolbar
toolbar_tools = ["MoveTool", "ScaleTool", "RotateTool", "AlignTool", "StructureTool",
    "ChainTool", "RingTool", "TemplateTool", "MarkTool", "ArrowTool", "PlusTool", "BracketTool", "TextTool",
     "ColorTool"
]

# in each settings mode, items will be shown in settings bar as same order as here
settings_template = {
    "StructureTool" : [# mode
        ["ButtonGroup", "bond_angle",# key/category
            # value   title         icon_name
            [("30", "30 degree", "angle-30"),
            ("15", "15 degree", "angle-15"),
            ("1", "1 degree", "angle-1"),
        ]],
        ["ButtonGroup", "bond_type", [
            ("normal", "Single Bond", "bond"),
            ("double", "Double Bond", "bond-double"),
            ("triple", "Triple Bond", "bond-triple"),
            ("aromatic", "Aromatic Bond", "bond-aromatic"),
            ("partial", "Partial Bond", "bond-partial"),
            ("hbond", "H-Bond", "bond-hydrogen"),
            ("coordinate", "Coordinate Bond", "bond-coordinate"),
            ("wedge", "Wedge (Up) Bond", "bond-wedge"),
            ("hatch", "Hatch (Down) Bond", "bond-hatch"),
            ("bold", "Bold (Above) Bond", "bond-bold"),
        ]],
    ],
    "ChainTool" : [
    ],
    "RingTool" : [
    ],
    "TemplateTool" : [
    ],
    "RotateTool" : [
        ["ButtonGroup", "rotation_type",
            [("2d", "2D Rotation", "rotate"),
            ("3d", "3D Rotation", "rotate3d"),
        ]]
    ],
    "AlignTool" : [
        ["ButtonGroup", "mode", [
            ("horizontal_align", "Horizontal Align", "align-horizontal"),
            ("vertical_align", "Vertical Align", "align-vertical"),
            ("mirror", "Mirror", "transform-mirror"),
            ("inversion", "Inversion", "transform-inversion"),
            ("freerotation", "180° freerotation", "transform-freerotation"),
        ]]
    ],
    "ArrowTool" : [
        ["ButtonGroup", "angle",
            [("15", "15 degree", "angle-15"),
            ("1", "1 degree", "angle-1")],
        ],
        ["ButtonGroup", "arrow_type",
            [("normal", "Normal", "arrow"),
            ("equilibrium", "Equilibrium", "arrow-equilibrium"),
            ("retrosynthetic", "Retrosynthetic", "arrow-retrosynthetic"),
            ("resonance", "Resonance", "arrow-resonance"),
            ("electron_shift", "Electron Pair Shift", "arrow-electron-shift"),
            ("fishhook", "Fishhook - Single electron shift", "arrow-fishhook"),
        ]],
    ],
    "MarkTool" : [
        ["ButtonGroup", "mark_type", [
            ("charge_plus", "Positive Charge", "charge-plus"),
            ("charge_minus", "Negative Charge", "charge-minus"),
            ("charge_circledplus", "Positive Charge", "charge-circledplus"),
            ("charge_circledminus", "Negative Charge", "charge-circledminus"),
            ("charge_deltaplus", "Positive Charge", "charge-deltaplus"),
            ("charge_deltaminus", "Negative Charge", "charge-deltaminus"),
            ("electron_pair", "Lone Pair", "electron-pair"),
            ("electron_single", "Single Electron/Radical", "electron-single"),
            ("isotope", "Isotope Number", "isotope"),
            ("DeleteMark", "Delete Mark", "delete"),
        ]]
    ],
    "PlusTool" : [
        ["Label", "Size : ", None],
        ["SpinBox", "size", (6, 72)],
    ],
    "BracketTool" : [
        ["ButtonGroup", "bracket_type",
            [("square", "Square Bracket", "bracket-square"),
            ("curly", "Curly Bracket", "bracket-curly"),
            ("round", "Round Bracket", "bracket-round"),
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
        ["PaletteWidget", "color", []],
    ],
}

# tool settings manager
class ToolSettings:
    def __init__(self):
        self._dict = { # initialize with default values
            "RotateTool" : {'rotation_type': '2d'},
            "AlignTool" : {'mode': 'horizontal_align'},
            "StructureTool" :  {"bond_angle": "30", "bond_type": "normal", "atom": "C"},
            "TemplateTool" : {'template': 'benzene'},
            "ArrowTool" : {'angle': '15', 'arrow_type':'normal'},
            "MarkTool" : {'mark_type': 'charge_plus'},
            "PlusTool" : {'size': Settings.plus_size},
            "TextTool" : {'font_name': 'Sans Serif', 'font_size': Settings.text_size},
            "ColorTool" : {'color': (0,0,0), 'color_index': 0},
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
