# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import Settings
from arrow import Arrow
from text import Plus
from fileformat import *
from tool_helpers import reposition_document

import io
import xml.dom.minidom as Dom

# TODO :
# implement coordinate bond, wedge and hatch

class MRV(FileFormat):
    """ Marvin MRV file """
    readable_formats = [("Marvin Document", "mrv")]

    bond_type_remap = { "1": 'normal', "2": 'double', "3": 'triple', "A": 'aromatic'}

    def reset(self):
        # Marvin uses angstrom unit. And C-C bond length is 1.54Å
        self.coord_multiplier =  Settings.bond_length/1.54
        # for read mode
        self.id_to_obj = {}


    def registerObjectID(self, obj, obj_id):
        self.id_to_obj[obj_id] = obj

    def getObject(self, obj_id):
        """ get object with ID obj_id while reading. returns None if ID not registered """
        return self.id_to_obj.get(obj_id, None)

    def getID(self, obj):
        """ get ID of an object while writing. creates a new one if not exists """
        if obj not in self.obj_to_id:
            self.obj_to_id[obj] = str(len(self.obj_to_id)+1)
        return self.obj_to_id[obj]

    def scaled_coord(self, coords):
        return tuple(x*self.coord_multiplier for x in coords)


    def readChildrenByTagNames(self, tag_names, parent):
        result = []
        for name in tag_names:
            elms = filter(lambda x: x.tagName==name, parent.childNodes)
            for elm in elms:
                obj = getattr(self, "read"+name[:1].upper()+name[1:])(elm)
                if obj:
                    result.append(obj)
        return result

    def read(self, filename):
        self.reset()
        dom_doc = Dom.parse(filename)
        cmls = dom_doc.getElementsByTagName("cml")
        if not cmls:
            return
        root = cmls[0]
        # root node contains MDocument child
        self.doc = Document()
        self.readChildrenByTagNames(["MDocument"], root)
        reposition_document(self.doc)
        return self.doc.objects and self.doc or None


    def readMDocument(self, element):
        self.readChildrenByTagNames(["MChemicalStruct"], element)

    def readMChemicalStruct(self, element):
        mols = self.readChildrenByTagNames(["molecule", "reaction"], element)
        self.doc.objects += mols

    def readReaction(self, element):
        arrows = self.readChildrenByTagNames(["arrow"], element)
        reactants, agents, products = [], [], []

        for elm in element.getElementsByTagName("reactantList"):
            reactants += self.readChildrenByTagNames(["molecule"], elm)

        for elm in element.getElementsByTagName("agentList"):
            agents += self.readChildrenByTagNames(["molecule"], elm)

        for elm in element.getElementsByTagName("productList"):
            products += self.readChildrenByTagNames(["molecule"], elm)

        self.doc.objects += arrows + reactants + agents + products


    def readMolecule(self, element):
        molecule = Molecule()
        # add atoms
        for elm in element.getElementsByTagName("atomArray"):
            atoms = self.readChildrenByTagNames(["atom"], elm)
            [molecule.addAtom(atom) for atom in atoms]
        # add bonds
        for elm in element.getElementsByTagName("bondArray"):
            bonds = self.readChildrenByTagNames(["bond"], elm)
            [molecule.addBond(bond) for bond in bonds]

        return molecule


    def readAtom(self, element):
        atom = Atom()
        uid, elm_type, x2,y2, x3,y3,z3 = map(element.getAttribute, (
                    "id", "elementType", "x2", "y2", "x3", "y3", "z3"))
        if uid:
            self.registerObjectID(atom, uid)
        if elm_type:
            atom.setSymbol(elm_type)

        if x3 and y3 and z3:
            atom.x, atom.y, atom.z = self.scaled_coord(map(float, [x3, y3, z3]))
        elif x2 and y2:
            atom.x, atom.y = self.scaled_coord(map(float, [x2,y2]))

        return atom


    def readBond(self, element):
        bond = Bond()
        atoms, order = map(element.getAttribute, ("atomRefs2", "order"))
        if atoms:
            atom1, atom2 = map(self.getObject, atoms.split())
            bond.connectAtoms(atom1, atom2)

        typ = self.bond_type_remap.get(order, 'normal')
        bond.setType(typ)
        # convention="cxn:coord"

        # Stereo W=wedge, H=hatch

        return bond


    def readArrow(self, element):
        arrow = Arrow()
        x1,y1, x2,y2 = map(element.getAttribute, ("x1", "y1", "x2", "y2"))
        if x1 and y1 and x2 and y2:
            x1,y1, x2,y2 = self.scaled_coord(map(float, [x1,y1,x2,y2]))
            arrow.points = [(x1,y1), (x2,y2)]

        return arrow
