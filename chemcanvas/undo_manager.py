# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
import copy

# ******* How It Works ************
# For each changes on paper, current paper state is saved.
# To save state, first all top level object list is copied.
# List of all objects on paper (top levels and their children) are generated
# Attribute values of each those objects are stored in separate dictionaries
# in {"attribute_name":value} format.
# While restoring, attribute values of those objects are restored.
# Finally, top level object list on paper is updated.
# redrawing of objects is done whenever necessary.

# each drawable must contain these three attributes
# meta__undo_properties -> attribute that dont need coping, eg - int, string, bool, tuple etc
# meta__undo_copy -> attributes that need copying (e.g - list, set, dict)
# meta__undo_children_to_record -> objects that are not top levels, must be list or set of objects


class UndoManager:
    MAX_UNDO_LEVELS = 50

    def __init__(self, paper):
        self.paper = paper
        self._stack = []
        self.clean()
        self.save_current_state("empty paper")

    def clean(self):
        self._pos = -1
        self._saved_to_disk_pos = 0# index of saved to disk
        for record in self._stack:
            record.clean()
        self._stack.clear()

    def save_current_state(self, name=''):
        """ push current paper state to the stack """
        if len( self._stack)-1 > self._pos:
            del self._stack[(self._pos+1):]
            if self._saved_to_disk_pos > self._pos:
                self._saved_to_disk_pos = -1# means not in the stack
        if len( self._stack) >= self.MAX_UNDO_LEVELS:
            del self._stack[0]
            self._pos -= 1
            self._saved_to_disk_pos -= 1
        self._stack.append(PaperState(self.paper, name))
        self._pos += 1

    def undo(self):
        """undoes the last step and returns the number of undo records available"""
        self._pos -= 1
        if self._pos >= 0:
            self._stack[self._pos].restore_state()
        else:
            self._pos = 0
        return self._pos

    def redo(self):
        """redoes the last undone step, returns number of redos available"""
        self._pos += 1
        if self._pos < len( self._stack):
            self._stack[ self._pos].restore_state()
        else:
            self._pos = len( self._stack)-1
        return len(self._stack) - self._pos -1


    def get_last_record_name(self):
        """returns the last closed record name"""
        if self._pos >= 1:
            return self._stack[self._pos-1].name
        else:
            return None

    def delete_last_record(self):
        """deletes the last record, useful for concatenation of several records to one;
        especially powerful in combination with named records"""
        if self._pos > 0:
            del self._stack[ self._pos-1]
            if self._saved_to_disk_pos == self._pos-1:# not in the stack
                self._saved_to_disk_pos = -1
            elif self._saved_to_disk_pos >= self._pos:
                self._saved_to_disk_pos -= 1
            self._pos -= 1

    def can_undo( self):
        return bool(self._pos)

    def can_redo( self):
        return bool( len(self._stack) - self._pos - 1)

    def has_unsaved_changes(self):
        return self._saved_to_disk_pos != self._pos

    def mark_saved_to_disk(self):
        self._saved_to_disk_pos = self._pos


##-------------------- STATE RECORD --------------------

class PaperState:
    """ It saves current paper state, and can restore whenever necessary """

    def __init__(self, paper, name):
        self.paper = paper
        self.name = name
        self.top_levels = self.paper.objects[:]# list of top level objects on paper
        self.objects = self.get_objects_on_paper()# list of objects whose attributes are stored
        self.records = []# attribute values of above objects
        for o in self.objects:
            rec = {}
            for a in o.meta__undo_properties:
                rec[a] = getattr(o, a)
            for a in o.meta__undo_copy:
                rec[a] = copy.copy(o.__dict__[a])
            self.records.append(rec)

    def clean(self):
        del self.name
        del self.paper
        del self.top_levels
        del self.objects
        del self.records

    def get_objects_on_paper(self):
        """ recursively list of all objects on paper (toplevel and non-toplevel) """
        stack = list(self.paper.objects)
        result = []
        while len(stack):
            obj = stack.pop()
            result.append(obj)
            for attr in obj.meta__undo_children_to_record:
                children = getattr(obj, attr)
                [stack.append(child) for child in children]
        return result

    def restore_state(self):
        """sets the system to the recorded state (update is done only where necessary,
        not changed values are not touched)."""
        current_objects = set(self.get_objects_on_paper())
        to_be_added = set(self.objects) - current_objects # previously deleted objects
        to_be_removed = current_objects - set(self.objects) # previously added objects

        changed_objs = set()
        changed_objs |= to_be_added
        # First restore attribute values, and check which objects changed
        for i, o in enumerate(self.objects):
            changed = 0
            for a in o.meta__undo_properties:
                if self.records[i][a] != getattr( o, a):
                    setattr( o, a, self.records[i][a])
                    changed = 1
            for a in o.meta__undo_copy:
                if self.records[i][a] != o.__dict__[a]:
                    o.__dict__[a] = copy.copy( self.records[i][a])
                    changed = 1

            if changed:
                # e.g - vertices and atoms in Molecule points to same list object
                for a1, a2 in o.meta__same_objects.items():
                    o.__dict__[a1] = o.__dict__[a2]
                changed_objs.add(o)

        # check which objects need to redraw
        to_redraw = changed_objs.copy()
        for o in changed_objs:
            # atom is changed, bonds also need to redraw
            if o.class_name == 'Atom':
                to_redraw |= set(o.bonds)
                to_redraw |= set(o.molecule.delocalizations)
            # if bond changed, attached atoms must be redrawn first
            elif o.class_name == 'Bond':
                to_redraw |= set(o.atoms)

        to_redraw -= to_be_removed
        for o in to_be_removed:
            o.delete_from_paper()# this also unfocus the object

        # now redrawing
        to_redraw = sorted(to_redraw, key=lambda obj : obj.redraw_priority)
        for o in to_redraw:
            o.paper = self.paper
            o.draw()

        self.paper.objects = self.top_levels[:]


