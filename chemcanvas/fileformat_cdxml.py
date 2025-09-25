# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import Settings, periodic_table, atomic_num_to_symbol
from arrow import Arrow
from text import Plus
from fileformat import *
from tool_helpers import calc_average_bond_length, identify_reaction_components

import io
import xml.dom.minidom as Dom
from functools import reduce
import operator

# NOTE :
# MarvinJS requires a reaction scheme to show plus and arrow



class CDXML(FileFormat):
    """ ChemDraw XML file """
    readable_formats = [("ChemDraw XML", "cdxml")]
    writable_formats = [("ChemDraw XML", "cdxml")]

    bond_type_remap = {"1": "single", "2": "double", "3": "triple", "0.5": "partial",
                    "1.5": "delocalized", "hydrogen": "hbond", "dative": "coordinate"}
    bond_stereo_remap = {"WedgeBegin":"wedge", "WedgedHashBegin":"hashed_wedge", "Bold":"bold"}

    def reset(self):
        self.reset_status()
        # for read mode
        self.id_to_obj = {}
        self.color_table = [(0,0,0), (255,255,255), (255,255,255), (0,0,0)]
        self.charged_atoms = []
        self.radicals = []
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
        return tuple(x*self.coord_multiplier for x in coords)


    def read(self, filename):
        self.reset()
        self.coord_multiplier =  Settings.render_dpi/72# point to px conversion factor
        dom_doc = Dom.parse(filename)
        cdxmls = dom_doc.getElementsByTagName("CDXML")
        if not cdxmls:
            self.message = "File has no CDXML element !"
            return
        root = cdxmls[0]
        # root node contains 'page', 'fonttable' and 'colortable' children
        self.doc = Document()
        try:
            # read color table
            elms = root.getElementsByTagName("colortable")
            for elm in elms:
                self.readColorTable(elm)
            # A Document must contain atleast one page object
            # Here, we can read the first page only
            elms = root.getElementsByTagName("page")
            if not elms:
                self.message = "File has no page element !"
                return
            self.readPage(elms[0])

            self.status = "ok"
            return self.doc.objects and self.doc or None

        except FileError as e:
            self.message = str(e)
            return


    def readPage(self, element):
        # get page size
        w, h = map(element.getAttribute, ('Width','Height'))
        if w and h:
            self.doc.set_page_size(float(w), float(h))
        else:
            self.doc.set_page_size(612,792) # letter size is default
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


        for atom in self.charged_atoms:
            charge = atom.properties_["charge"]
            mark = Charge()
            mark.setValue(charge)
            atom.add_mark(mark)
            atom.properties_.pop("charge")

        for atom in self.radicals:
            radical = atom.properties_["radical"]
            marks = []
            if radical=="Singlet":
                marks = [Electron("2")]
            elif radical=="Doublet":
                marks = [Electron("1")]
            elif radical=="Triplet":
                marks = [Electron("1"), Electron("1")]
            [atom.add_mark(mark) for mark in marks]
            atom.properties_.pop("radical")


    def readColorTable(self, element):
        # color index 0 and 1 denotes black and white respectively (not stored in colortable)
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
        if len(color_table)<4:
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
            molecule.add_atom(atom)
        # find bonds
        elms = element.getElementsByTagName("b")
        for elm in elms:
            bond = self.readBond(elm)
            molecule.add_bond(bond)

        return molecule


    def readAtom(self, element):
        atom = Atom()
        uid, atm_num, pos, pos3d, hydrogens, color = map(element.getAttribute, (
                    "id", "Element", "p", "xyz", "NumHydrogens", "color"))
        isotope, charge, radical = map(element.getAttribute, (
                    "Isotope", "Charge", "Radical"))
        if uid:
            self.registerObjectID(atom, uid)
        # read symbol
        if atm_num and atm_num.isdigit():
            atom.set_symbol(atomic_num_to_symbol(int(atm_num)))
        # read postion
        if pos3d:
            pos = list(map(float, pos3d.split()))
            atom.x, atom.y, atom.z = self.scaled_coord(pos)
        elif pos:
            pos = list(map(float, pos.split()))
            atom.x, atom.y = self.scaled_coord(pos)
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
            self.charged_atoms.append(atom)
        # radical (values are None, Singlet, Doublet, Triplet)
        if radical:
            atom.properties_["radical"] = radical
            self.radicals.append(atom)
        # read color
        if color:
            atom.color = self.color_table[int(color)]

        return atom


    def readBond(self, element):
        bond = Bond()
        begin, end, order, display = map(element.getAttribute, ("B", "E", "Order", "Display"))
        # read connected atoms
        atoms = []
        if begin and end:
            atoms = [self.getObject(begin), self.getObject(end)]
            bond.connect_atoms(*atoms)
        # set order. 1=single, 2=double, 3=triple, 1.5=aromatic, 2.5=bond in benzyne,
        # 0.5=half bond, dative=dative, ionic=ionic bond, hydrogen=H-bond, threecenter
        typ = self.bond_type_remap.get(order, "single")
        typ = self.bond_stereo_remap.get(display, typ)
        bond.set_type(typ)
        return bond

    def readArrow(self, element):
        arrow = Arrow()
        head, tail = map(element.getAttribute, ("Head3D", "Tail3D"))
        if head and tail:
            x1,y1,z1 = self.scaled_coord(map(float, tail.split()))
            x2,y2,z2 = self.scaled_coord(map(float, head.split()))
            arrow.points = [(x1,y1), (x2,y2)]

        return arrow

    def readGraphic(self, element):
        graphic_type, bbox = map(element.getAttribute, ("GraphicType", "BoundingBox"))
        # get bounding box
        if bbox:
            x1,y1, x2,y2 = self.scaled_coord( map(float, bbox.split()))
        # create known symbols
        if graphic_type=="Symbol":
            symbol_type = element.getAttribute("SymbolType")
            if symbol_type and symbol_type=="Plus" and bbox:
                plus = Plus()
                plus.x, plus.y = (x1+x2)/2, (y1+y2)/2
                return plus

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
        imp = Dom.getDOMImplementation()
        # this way we can add doctype. but we dont, because toprettyxml() causes
        # a line break inside doctype line and MarvinJS fails to read
        #doctype = imp.createDocumentType(qualifiedName='CDXML',
        #        publicId=None, systemId="http://www.cambridgesoft.com/xml/cdxml.dtd")
        #dom_doc = imp.createDocument(None, 'CDXML', doctype)
        dom_doc = imp.createDocument(None, 'CDXML', None)
        root = dom_doc.documentElement
        # write page
        self.coord_multiplier = 72/Settings.render_dpi # px to point converter
        page = dom_doc.createElement("page")
        page.setAttribute("Width", "%f"% (doc.page_w*self.coord_multiplier))
        page.setAttribute("Height", "%f"% (doc.page_h*self.coord_multiplier))
        try:
            # write objects
            for obj in doc.objects:
                self.createObjectNode(obj, page)
            # detect and write reaction
            components = identify_reaction_components(doc.objects)
            if components:
                self.createReactionNode(components, page)
            # MarvinJS requires BondLength attribute, otherwise all atoms are on single point.
            mols = filter(lambda o: o.class_name=="Molecule", doc.objects)
            bonds = reduce(operator.add, [list(mol.bonds) for mol in mols], [])
            bond_len = calc_average_bond_length(bonds) * self.coord_multiplier
            root.setAttribute("BondLength", "%g"%bond_len)
            # write color table (without it MarvinJS fails to read)
            # color index 0 and 1 is black and white respectively, they are not stored in
            # color table. color 2 and color 3 are default background and foreground color.
            colortable = dom_doc.createElement("colortable")
            for color in self.color_table[2:]:
                color_elm = dom_doc.createElement("color")
                colortable.appendChild(color_elm)
                for i,clr in enumerate(list("rgb")):
                    color_elm.setAttribute(clr, "%g"%(color[i]/255))
            # color table is generated while creating object elements.
            # and we also need to place colortable before page
            root.appendChild(colortable)
            root.appendChild(page)
            # set generated ids
            for obj,id in self.obj_to_id.items():
                self.obj_element_map[obj].setAttribute("id", id)
            h1 = '<?xml version="1.0" encoding="UTF-8"?>\n'
            h2 = '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd">\n'
            output = h1 + h2 + root.toprettyxml(indent="  ")
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


    def createMoleculeNode(self, molecule, parent):
        elm = parent.ownerDocument.createElement("fragment")
        parent.appendChild(elm)
        for child in molecule.children:
            self.createObjectNode(child, elm)
        return elm


    def createAtomNode(self, atom, parent):
        elm = parent.ownerDocument.createElement("n")
        parent.appendChild(elm)
        # set symbol or formula
        if not atom.is_group:
            atomic_num = periodic_table[atom.symbol]["atomic_num"]
            elm.setAttribute("Element", str(atomic_num))
        else:
            elm.setAttribute("Formula", atom.symbol)
        # set pos
        if atom.z==0:
            elm.setAttribute("p", "%f %f"%self.scaled_coord(atom.pos))
        else:
            elm.setAttribute("xyz", "%f %f %f"%self.scaled_coord(atom.pos3d))
        # explicit hydrogens
        if not atom.auto_hydrogens:
            elm.setAttribute("NumHydrogens", str(atom.hydrogens))
        # isotope
        if atom.isotope:
            elm.setAttribute("Isotope", str(atom.isotope))
        # charge
        if atom.charge:
            elm.setAttribute("Charge", str(atom.charge))
        # radical
        multi = atom.multiplicity
        if multi in (1,2,3):
            vals = ["None", "Singlet", "Doublet", "Triplet"]
            elm.setAttribute("Radical", vals[multi])
        return elm


    def createBondNode(self, bond, parent):
        elm = parent.ownerDocument.createElement("b")
        parent.appendChild(elm)
        # set atoms
        elm.setAttribute("B", self.getID(bond.atom1))
        elm.setAttribute("E", self.getID(bond.atom2))
        # set order
        type_remap = {it[1]:it[0] for it in self.bond_type_remap.items()}
        order = type_remap.get(bond.type, "1")
        if order!="1":
            elm.setAttribute("Order", order)
        stereo_remap = {it[1]:it[0] for it in self.bond_stereo_remap.items()}
        if bond.type in stereo_remap:
            elm.setAttribute("Display", stereo_remap[bond.type])
        return elm


    def createArrowNode(self, arrow, parent):
        elm = parent.ownerDocument.createElement("arrow")
        parent.appendChild(elm)
        elm.setAttribute("ArrowheadType", "Solid") # (Solid|Hollow|Angle)
        # arrow head not visible in ChemDraw JS without ArrowheadHead
        elm.setAttribute("ArrowheadHead", "Full") # (Unspecified|None|Full|HalfLeft|HalfRight)
        elm.setAttribute("HeadSize", "1600") # value is in percentage of line width
        elm.setAttribute("ArrowheadCenterSize", "1200")
        elm.setAttribute("ArrowheadWidth", "400")
        elm.setAttribute("Head3D", "%f %f 0.0"%self.scaled_coord(arrow.points[-1]))
        elm.setAttribute("Tail3D", "%f %f 0.0"%self.scaled_coord(arrow.points[0]))
        return elm


    def createPlusNode(self, plus, parent):
        elm = parent.ownerDocument.createElement("graphic")
        parent.appendChild(elm)
        elm.setAttribute("GraphicType", "Symbol")
        elm.setAttribute("SymbolType", "Plus")
        bbox = plus.bounding_box()
        elm.setAttribute("BoundingBox", "%f %f %f %f"%self.scaled_coord(bbox))
        return elm


    def createReactionNode(self, components, parent):
        reactants, products, arrows, plusses = components
        scheme_elm = parent.ownerDocument.createElement("scheme")
        parent.appendChild(scheme_elm)
        elm = parent.ownerDocument.createElement("step")
        scheme_elm.appendChild(elm)
        elm.setAttribute("ReactionStepReactants", " ".join([self.getID(o) for o in reactants]))
        elm.setAttribute("ReactionStepProducts", " ".join([self.getID(o) for o in products]))
        elm.setAttribute("ReactionStepArrows", " ".join([self.getID(o) for o in arrows]))
        elm.setAttribute("ReactionStepPlusses", " ".join([self.getID(o) for o in plusses]))
        return elm

