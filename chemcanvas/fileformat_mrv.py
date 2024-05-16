# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import Settings
from arrow import Arrow
from text import Plus
from fileformat import *
from tool_helpers import reposition_document

import io
from xml.dom import minidom

# TODO :
# implement coordinate bond, wedge and hatch

class MRV(FileFormat):
    """ Marvin MRV file """
    readable_formats = [("Marvin Document", "mrv")]
    writable_formats = [("Marvin Document", "mrv")]

    bond_type_remap = { "1": "single", "2": "double", "3": "triple", "A": "aromatic"}

    def reset(self):
        self.reading_mode = True
        # Marvin uses angstrom unit. And C-C bond length is 1.54Å
        self.coord_multiplier =  Settings.bond_length/1.54
        # for read mode
        self.id_to_obj = {}
        # for write mode
        self.obj_to_id = {}
        self.obj_element_map = {}


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
        if self.reading_mode:
            return tuple(x*self.coord_multiplier for x in coords)
        # write mode
        return tuple(x/self.coord_multiplier for x in coords)


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
        self.reading_mode = True
        dom_doc = minidom.parse(filename)
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

        typ = self.bond_type_remap.get(order, "single")
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


    # --------------------------- WRITE -------------------------------

    def write(self, doc, filename):
        self.reset()
        self.reading_mode = False
        string = self.generateString(doc)
        try:
            with io.open(filename, "w", encoding="utf-8") as out_file:
                out_file.write(string)
            return True
        except:
            return False


    def generateString(self, doc):
        dom_doc = minidom.Document()
        root = dom_doc.createElement("cml")
        dom_doc.appendChild(root)

        # write document
        m_doc = dom_doc.createElement("MDocument")
        root.appendChild(m_doc)

        mols = filter(lambda x: x.class_name=="Molecule", doc.objects)
        if mols:
            chem_struct = dom_doc.createElement("MChemicalStruct")
            m_doc.appendChild(chem_struct)
            for mol in mols:
                self.createObjectNode(mol, chem_struct)

        # set generated ids
        for obj,id in self.obj_to_id.items():
            self.obj_element_map[obj].setAttribute("id", id)
        return dom_doc.toprettyxml(indent="  ")


    def createObjectNode(self, obj, parent):
        if obj.class_name in ("Molecule", "Atom", "Bond"):
            method = "create%sNode" % obj.class_name
            elm = getattr(self, method)(obj, parent)
            self.obj_element_map[obj] = elm


    def createMoleculeNode(self, molecule, parent):
        mol_elm = parent.ownerDocument.createElement("molecule")
        parent.appendChild(mol_elm)
        # create atom array and write atoms
        atom_arr = parent.ownerDocument.createElement("atomArray")
        mol_elm.appendChild(atom_arr)
        for atom in molecule.atoms:
            self.createObjectNode(atom, atom_arr)
        # write bonds
        if molecule.bonds:
            bond_arr = parent.ownerDocument.createElement("bondArray")
            mol_elm.appendChild(bond_arr)
            for bond in molecule.bonds:
                self.createObjectNode(bond, bond_arr)

        return mol_elm


    def createAtomNode(self, atom, parent):
        elm = parent.ownerDocument.createElement("atom")
        parent.appendChild(elm)
        # set symbol or formula
        if not atom.is_group:
            elm.setAttribute("elementType", atom.symbol)
        else:
            raise ValueError("Functional groups not supported")
        # set pos
        x, y, z = self.scaled_coord((atom.x, atom.y, atom.z))
        if atom.z==0:
            elm.setAttribute("x2", "%f"%x)
            elm.setAttribute("y2", "%f"%y)
        else:
            elm.setAttribute("x3", "%f"%x)
            elm.setAttribute("y3", "%f"%y)
            elm.setAttribute("z3", "%f"%z)
        return elm


    def createBondNode(self, bond, parent):
        elm = parent.ownerDocument.createElement("bond")
        parent.appendChild(elm)
        # set atoms
        elm.setAttribute("atomRefs2", "%s %s"%(self.getID(bond.atom1), self.getID(bond.atom2)))
        # set order
        type_remap = {it[1]:it[0] for it in self.bond_type_remap.items()}
        order = type_remap.get(bond.type, "1")
        if order!="1":
            elm.setAttribute("order", order)

        return elm
