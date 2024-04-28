# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App, atomic_num_to_symbol
from molecule import Molecule
from atom import Atom
from bond import Bond
from marks import Charge, Electron
from arrow import Arrow
from bracket import Bracket
from text import Text, Plus
from fileformat import *
from tool_helpers import scale_objs

import io
import xml.dom.minidom as Dom



class CDXML(FileFormat):
    """ ChemDraw XML file """
    readable_formats = [("ChemDraw XML", "cdxml")]

    def reset(self):
        # private
        self.id_to_obj = {}# for read mode
        self.obj_to_id = {}# for write mode
        self.color_table = [(0,0,0), (255,255,255)]
        self._charged_atoms = []
        self._radicals = []


    def registerObjectID(self, obj, obj_id):
        self.id_to_obj[obj_id] = obj

    def getObject(self, obj_id):
        try:
            return self.id_to_obj[obj_id]
        except KeyError:# object not read yet
            return None

    def read(self, filename):
        self.reset()
        dom_doc = Dom.parse(filename)
        cdxmls = dom_doc.getElementsByTagName("CDXML")
        if not cdxmls:
            return
        root = cdxmls[0]
        # root node contains 'page', 'fonttable' and 'colortable' children
        self.doc = Document()
        # read color table
        elms = root.getElementsByTagName("colortable")
        for elm in elms:
            self.readColorTable(elm)
        # A Document must contain atleast one page object
        # Here, we can read the first page only
        elms = root.getElementsByTagName("page")
        if elms:
            self.readPage(elms[0])

        return self.doc.objects and self.doc or None


    def readPage(self, element):
        # read Fragments/Molecules
        elms = element.getElementsByTagName("fragment")
        for elm in elms:
            mol = self.readFragmemt(elm)
            if mol:
                self.doc.objects.append(mol)

        # read Arrows
        elms = element.getElementsByTagName("arrow")
        for elm in elms:
            arrow = self.readArrow(elm)
            if arrow:
                self.doc.objects.append(arrow)

        # read Graphic items
        elms = element.getElementsByTagName("graphic")
        for elm in elms:
            graphic = self.readGraphic(elm)
            if graphic:
                self.doc.objects.append(graphic)

        scale_objs(self.doc.objects, 100/72)# point to px @100dpi conversion factor

        for atom in self._charged_atoms:
            charge = atom.properties_["charge"]
            mark = create_new_mark_in_atom(atom, "charge_plus")
            mark.setValue(charge)
            atom.properties_.pop("charge")

        for atom in self._radicals:
            radical = atom.properties_["radical"]
            if radical=="Singlet":
                create_new_mark_in_atom(atom, "electron_pair")
            elif radical=="Doublet":
                create_new_mark_in_atom(atom, "electron_single")
            elif radical=="Triplet":
                create_new_mark_in_atom(atom, "electron_single")
                create_new_mark_in_atom(atom, "electron_single")
            atom.properties_.pop("radical")


    def readColorTable(self, element):
        # color index 0 and 1 is always black and white respectively
        # color index 2 and 3 denotes background and foreground color respectively
        color_table = [(0,0,0), (255,255,255)]
        elms = element.getElementsByTagName("color")
        for elm in elms:
            r, g, b = map(elm.getAttribute, ('r','g', 'b'))
            if r and g and b:
                color_conv = lambda x : int(round(float(x)*255))
                color_table.append(tuple(map(color_conv, (r,g,b))))
            else:
                return
        self.color_table = color_table

    def readFragmemt(self, element):
        molecule = Molecule()
        uid = element.getAttribute("id")
        if uid:
            self.registerObjectID(molecule, uid)
        # find atoms
        elms = element.getElementsByTagName("n")
        for elm in elms:
            atom = self.readAtom(elm)
            molecule.addAtom(atom)
        # find bonds
        elms = element.getElementsByTagName("b")
        for elm in elms:
            bond = self.readBond(elm)
            molecule.addBond(bond)

        return molecule


    def readAtom(self, element):
        atom = Atom()
        uid, atm_num, pos, hydrogens, color = map(element.getAttribute, (
                    "id", "Element", "p", "NumHydrogens", "color"))
        isotope, charge, radical = map(element.getAttribute, (
                    "Isotope", "Charge", "Radical"))
        if uid:
            self.registerObjectID(atom, uid)
        # read symbol
        if atm_num and atm_num.isdigit():
            atom.setSymbol(atomic_num_to_symbol(int(atm_num)))
        # read postion
        if pos:
            pos = list(map(float, pos.split()))
            atom.x, atom.y = pos[:2]
        # hydrogens
        if hydrogens:
            atom.hydrogens = int(hydrogens)
            atom.auto_hydrogens = False
        # isotope
        if isotope:
            atom.isotope = int(isotope)
        # charge
        if charge:
            atom.properties_["charge"] = int(charge)
            self._charged_atoms.append(atom)
        # radical (values are None, Singlet, Doublet, Triplet)
        if radical:
            atom.properties_["radical"] = radical
            self._radicals.append(atom)
        # read color
        if color:
            atom.color = self.color_table[int(color)]

        return atom


    def readBond(self, element):
        bond = Bond()
        uid, begin, end, order = map(element.getAttribute, ("id", "B", "E", "order"))
        if uid:
            self.registerObjectID(bond, uid)
        # read connected atoms
        atoms = []
        if begin and end:
            atoms = [self.getObject(begin), self.getObject(end)]
            bond.connectAtoms(*atoms)
        # set order. 1=single, 2=double, 3=triple, 1.5=aromatic, 2.5=bond in benzyne,
        # 0.5=half bond, dative=dative, ionic=ionic bond, hydrogen=H-bond, threecenter
        if order:
            type_remap = {"1": "normal", "2": "double", "3": "triple", "0.5": "partial",
                        "1.5": "aromatic", "hydrogen": "hbond", "dative": "coordinate"}
            if order in type_remap:
                bond.setType(type_remap[order])
        return bond

    def readArrow(self, element):
        arrow = Arrow()
        uid, head, tail = map(element.getAttribute, ("id", "Head3D", "Tail3D"))
        if uid:
            self.registerObjectID(arrow, uid)
        if head and tail:
            x1,y1,z1 = map(float, tail.split())
            x2,y2,z2 = map(float, head.split())
            arrow.points = [(x1,y1), (x2,y2)]

        return arrow

    def readGraphic(self, element):
        graphic_type, bbox = map(element.getAttribute, ("GraphicType", "BoundingBox"))
        # get bounding box
        if bbox:
            x1,y1, x2,y2 = map(float, bbox.split())
            bbox = [x1,y1,x2,y2]
        # create known symbols
        if graphic_type=="Symbol":
            symbol_type = element.getAttribute("SymbolType")
            if symbol_type and symbol_type=="Plus" and bbox:
                plus = Plus()
                plus.x, plus.y = (x1+x2)/2, (y1+y2)/2
                return plus

