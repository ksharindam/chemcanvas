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

# A Document must contain atleast one page object






class CDXML:
    """ ChemDraw XML file """
    can_read = True
    can_write = False

    def __init__(self):
        self.id_to_obj = {}# for read mode
        self.obj_to_id = {}# for write mode
        self.objects = []

    def registerObjectID(self, obj, obj_id):
        self.id_to_obj[obj_id] = obj

    def getObject(self, obj_id):
        try:
            return self.id_to_obj[obj_id]
        except KeyError:# object not read yet
            return None

    def read(self, filename):
        doc = Dom.parse(filename)
        cdxmls = doc.getElementsByTagName("CDXML")
        if not cdxmls:
            return []
        root = cdxmls[0]
        # root node contains 'page', 'fonttable' and 'colortable' children
        document = Document()
        # read page
        page_elms = root.getElementsByTagName("page")
        for page_elm in page_elms:
            page = self.readPage(page_elms[0])
            if page:
                document.pages.append(page)

        return document.pages and document or None


    def readPage(self, elm):
        page = Page()
        frag_elms = elm.getElementsByTagName("fragment")
        for frag_elm in frag_elms:
            mol = self.readFragmemt(frag_elm)
            if mol:
                page.objects.append(mol)
        scale_objs(page.objects, 100/72)# point to px @100dpi conversion factor
        return page.objects and page or None

    def readFragmemt(self, elm):
        molecule = Molecule()
        uid = elm.getAttribute("id")
        if uid:
            self.registerObjectID(molecule, uid)
        # find atoms
        atom_elms = elm.getElementsByTagName("n")
        for atom_elm in atom_elms:
            atom = self.readAtom(atom_elm)
            molecule.addAtom(atom)
        # find bonds
        bond_elms = elm.getElementsByTagName("b")
        for bond_elm in bond_elms:
            bond = self.readBond(bond_elm)
            molecule.addBond(bond)

        return molecule


    def readAtom(self, elm):
        atom = Atom()
        uid = elm.getAttribute("id")
        if uid:
            self.registerObjectID(atom, uid)
        # read symbol
        atm_num = elm.getAttribute("Element")
        if atm_num and atm_num.isdigit():
            atom.setSymbol(atomic_num_to_symbol(int(atm_num)))
        # read postion
        pos = elm.getAttribute("p")
        if pos:
            pos = list(map(float, pos.split()))
            atom.x, atom.y = pos[:2]
        # hydrogens
        hydrogens = elm.getAttribute("NumHydrogens")
        if hydrogens:
            atom.hydrogens = int(hydrogens)
            atom.auto_hydrogens = False
        # read show carbon
        show_symbol = elm.getAttribute("show_C")
        if show_symbol and atom.symbol=="C":
            atom.show_symbol = bool(int(show_symbol))

        return atom


    def readBond(self, elm):
        bond = Bond()
        uid = elm.getAttribute("id")
        if uid:
            self.registerObjectID(bond, uid)
        # read connected atoms
        begin = elm.getAttribute("B")
        end = elm.getAttribute("E")
        atoms = []
        if begin and end:
            atoms = [self.getObject(begin), self.getObject(end)]
            bond.connectAtoms(*atoms)
        return bond

