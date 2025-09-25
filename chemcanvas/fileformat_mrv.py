# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import Settings
from arrow import Arrow
from text import Plus
from fileformat import *
from tool_helpers import identify_reaction_components

import io
from xml.dom import minidom

# TODO :
# Resonance and retrosynthetic type arrows currently not saved, as they are
# not detected by identify_reaction_components()
# fix : plus position is slight upward after reading


class MRV(FileFormat):
    """ Marvin MRV file """
    readable_formats = [("Marvin Document", "mrv")]
    writable_formats = [("Marvin Document", "mrv")]

    bond_type_remap = {"1": "single", "2": "double", "3": "triple", "A": "delocalized"}
    arrow_type_remap = {"normal": "DEFAULT", "equilibrium": "EQUILIBRIUM",
                    "resonance": "RESONANCE", "retrosynthetic": "RETROSYNTHETIC"}

    def reset(self):
        self.reset_status()
        self.read_mode = True
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
        """ converts between Å and pt. As y-axis direction in MRV is opposite
        of chemcanvas, sign of y is reversed. This handles the coordinates
        like (x,y), (x,y,x,y,..), (x,y,z) but not (x,y,z,x,y,z) """
        if self.read_mode:# 1-i%2*2 alternatively reverses the sign
            return tuple((1-i%2*2)*x*self.coord_multiplier for i,x in enumerate(coords))
        # write mode
        return tuple((1-i%2*2)*x/self.coord_multiplier for i,x in enumerate(coords))


    def readChildrenByTagName(self, tag_name, parent):
        result = []
        # whitespaces in xml are considered as TEXT_NODE
        elms = filter(lambda x: x.nodeType==x.ELEMENT_NODE and x.tagName==tag_name, parent.childNodes)
        for elm in elms:
            obj = getattr(self, "read"+tag_name[:1].upper()+tag_name[1:])(elm)
            if obj:
                result.append(obj)
        return result

    def read(self, filename):
        self.reset()
        self.read_mode = True
        dom_doc = minidom.parse(filename)
        cmls = dom_doc.getElementsByTagName("cml")
        if not cmls:
            self.message = "File has no cml element !"
            return
        root = cmls[0]
        # root node contains MDocument child
        self.doc = Document()
        try:
            self.readChildrenByTagName("MDocument", root)
            self.status = "ok"
            return self.doc.objects and self.doc or None
        except FileError as e:
            self.message = str(e)
            return


    def readMDocument(self, element):
        self.readChildrenByTagName("MChemicalStruct", element)
        plusses = self.readChildrenByTagName("MReactionSign", element)
        self.doc.objects += plusses

    def readMChemicalStruct(self, element):
        mols = self.readChildrenByTagName("molecule", element)
        self.readChildrenByTagName("reaction", element)
        self.doc.objects += mols

    def readReaction(self, element):
        arrows = self.readChildrenByTagName("arrow", element)
        reactants, agents, products = [], [], []

        for elm in element.getElementsByTagName("reactantList"):
            reactants += self.readChildrenByTagName("molecule", elm)

        for elm in element.getElementsByTagName("agentList"):
            agents += self.readChildrenByTagName("molecule", elm)

        for elm in element.getElementsByTagName("productList"):
            products += self.readChildrenByTagName("molecule", elm)

        self.doc.objects += arrows + reactants + agents + products


    def readMolecule(self, element):
        molecule = Molecule()
        # add atoms
        for elm in element.getElementsByTagName("atomArray"):
            atoms = self.readChildrenByTagName("atom", elm)
            [molecule.add_atom(atom) for atom in atoms]
        # add bonds
        for elm in element.getElementsByTagName("bondArray"):
            bonds = self.readChildrenByTagName("bond", elm)
            [molecule.add_bond(bond) for bond in bonds]

        return molecule


    def readAtom(self, element):
        atom = Atom()
        uid, elm_type, x2,y2, x3,y3,z3 = map(element.getAttribute, (
                    "id", "elementType", "x2", "y2", "x3", "y3", "z3"))
        if uid:
            self.registerObjectID(atom, uid)
        if elm_type:
            atom.set_symbol(elm_type)

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
            bond.connect_atoms(atom1, atom2)

        typ = self.bond_type_remap.get(order, "single")
        # read coordinate bond
        convention = element.getAttribute("convention")
        typ = convention=="cxn:coord" and "coordinate" or typ
        # read wedge or hashed wedge bond
        elms = element.getElementsByTagName("bondStereo")
        if elms:
            convention, val = map(elms[0].getAttribute, ("convention", "conventionValue"))
            if convention=="MDL" and val:
                typ = {"1":"wedge", "6":"hashed_wedge"}.get(val, typ)
            elif elms[0].firstChild:
                val = elms[0].firstChild.nodeValue
                typ = {"W":"wedge", "H":"hashed_wedge"}.get(val, typ)
        bond.set_type(typ)
        return bond


    def readArrow(self, element):
        arrow = Arrow()
        x1,y1, x2,y2 = map(element.getAttribute, ("x1", "y1", "x2", "y2"))
        if x1 and y1 and x2 and y2:
            x1,y1, x2,y2 = self.scaled_coord(map(float, [x1,y1,x2,y2]))
            arrow.points = [(x1,y1), (x2,y2)]
        return arrow


    def readMReactionSign(self, element):
        """ read reaction plus """
        plus = Plus()
        # bounding box is set by four corner points
        # [top-left, top-right, bottom-right, bottom-left]
        pts = self.readChildrenByTagName("MPoint", element)
        bbox = pts[0] + pts[2]
        pos = (bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2 # center of bbox
        plus.set_pos(*pos)
        return plus


    def readMPoint(self, element):
        x,y = map(element.getAttribute, ("x", "y"))
        return self.scaled_coord(map(float, (x, y)))


    # --------------------------- WRITE -------------------------------

    def write(self, doc, filename):
        string = self.generate_string(doc)
        if not string:
            return False
        try:
            with io.open(filename, "w", encoding="utf-8") as out_file:
                out_file.write(string)
            return True
        except:
            self.message = "Filepath is not writable !"
            return False


    def generate_string(self, doc):
        self.reset()
        self.read_mode = False
        dom_doc = minidom.Document()
        root = dom_doc.createElement("cml")
        dom_doc.appendChild(root)

        # write document
        m_doc = dom_doc.createElement("MDocument")
        root.appendChild(m_doc)

        try:
            mols = filter(lambda x: x.class_name=="Molecule", doc.objects)
            if mols:
                chem_struct = dom_doc.createElement("MChemicalStruct")
                m_doc.appendChild(chem_struct)
                reaction = identify_reaction_components(doc.objects)
                if reaction:
                    self.createReactionNode(reaction, chem_struct)
                    # write pluses
                    plusses = [o for o in doc.objects if o.class_name=="Plus"]
                    for plus in plusses:
                        self.createObjectNode(plus, m_doc)
                else:
                    for mol in mols:
                        self.createObjectNode(mol, chem_struct)
            # set generated ids
            for obj,id in self.obj_to_id.items():
                self.obj_element_map[obj].setAttribute("id", id)
            output = dom_doc.toprettyxml(indent="  ")
            self.status = "ok"
            return output
        except FileError as e:
            self.message = str(e)
            return ""


    def createObjectNode(self, obj, parent):
        if obj.class_name in ("Molecule", "Atom", "Bond", "Arrow", "Plus"):
            method = "create%sNode" % obj.class_name
            elm = getattr(self, method)(obj, parent)
            self.obj_element_map[obj] = elm


    def createReactionNode(self, reaction, parent):
        rxn_elm = parent.ownerDocument.createElement("reaction")
        parent.appendChild(rxn_elm)
        reactants, products, arrows, plusses = reaction
        # write reactants
        reactants_elm = parent.ownerDocument.createElement("reactantList")
        rxn_elm.appendChild(reactants_elm)
        for mol in reactants:
            self.createObjectNode(mol, reactants_elm)
        # write products
        products_elm = parent.ownerDocument.createElement("productList")
        rxn_elm.appendChild(products_elm)
        for mol in products:
            self.createObjectNode(mol, products_elm)
        # write arrows
        for arrow in arrows:
            self.createObjectNode(arrow, rxn_elm)
        return rxn_elm

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
            raise FileError("Functional groups not supported")
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
        if bond.type=="coordinate":
            elm.setAttribute("convention", "cxn:coord")
        elif bond.type in ("wedge", "hashed_wedge"):
            stereo_elm = parent.ownerDocument.createElement("bondStereo")
            elm.appendChild(stereo_elm)
            text_elm = parent.ownerDocument.createTextNode(bond.type=="wedge" and "W" or "H")
            stereo_elm.appendChild(text_elm)
        else:
            type_remap = {it[1]:it[0] for it in self.bond_type_remap.items()}
            order = type_remap.get(bond.type, "1")
            if order!="1":
                elm.setAttribute("order", order)
        return elm


    def createArrowNode(self, arrow, parent):
        elm = parent.ownerDocument.createElement("arrow")
        parent.appendChild(elm)
        # if type not set, arrow not visible in MarvinJS
        # MarvinJS does not support RETROSYNTHETIC arrows. (maybe MarvinSketch does)
        arr_type = self.arrow_type_remap.get(arrow.type, "DEFAULT")
        elm.setAttribute("type", arr_type)# (DEFAULT|RESONANCE|EQUILIBRIUM|RETROSYNTHETIC)
        pts = self.scaled_coord(arrow.points[0]+arrow.points[1])
        for name,val in zip(("x1","y1","x2","y2"), pts):
            elm.setAttribute(name, "%f"%val)
        return elm


    def createPlusNode(self, plus, parent):
        elm = parent.ownerDocument.createElement("MReactionSign")
        parent.appendChild(elm)
        bbox = self.scaled_coord(plus.bounding_box())
        self.createBoundingBox(bbox, elm)
        return elm


    def createBoundingBox(self, bbox, parent):
        """ adds bbox as four MPoint children to parent object """
        left, top, right, bottom = bbox
        for point in [(left,top), (right,top), (right,bottom), (left,bottom)]:
            elm = parent.ownerDocument.createElement("MPoint")
            parent.appendChild(elm)
            elm.setAttribute("x", "%f"%point[0])
            elm.setAttribute("y", "%f"%point[1])
