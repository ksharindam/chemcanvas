# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import Settings
from common import float_to_str
from drawing_parents import hex_color, hex_to_color
from delocalization import Delocalization
from arrow import Arrow
from bracket import Bracket
from text import Text, Plus
from shapes import Line, Rectangle, Ellipse
from fileformat import *

import io
from xml.dom import minidom



class Ccdx(FileFormat):
    readable_formats = [("ChemCanvas Drawing XML", "ccdx")]
    writable_formats = [("ChemCanvas Drawing XML", "ccdx")]

    def reset(self):
        self.reset_status()
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

    def scaled(self, x):
        return x * self.coord_multiplier

    def scaled_coord(self, coords):
        return tuple(x*self.coord_multiplier for x in coords)


    # -----------------------------------------------------------------
    # --------------------------- READ -------------------------------
    # -----------------------------------------------------------------

    def read(self, filename):
        self.reset()
        self.coord_multiplier = Settings.render_dpi/72# point to px conversion factor
        dom_doc = minidom.parse(filename)
        # read root element
        ccdxs = dom_doc.getElementsByTagName("ccdx")
        if not ccdxs:
            self.message = "File has no ccdx element !"
            return
        self.doc = Document()
        try:
            #version = ccdxs[0].getAttribute("version")
            self.readCcdx(ccdxs[0])
            self.status = "ok"
            return self.doc.objects and self.doc or None
        except FileError as e:
            self.message = str(e)
            return


    def readCcdx(self, element):
        # get page size
        page_size = element.getAttribute("page_size")
        if page_size:
            w, h = page_size.split(",")
            self.doc.set_page_size(float(w), float(h))
        else:
            self.doc.set_page_size(595,842) # a4 size is default

        for objtype in ("Molecule", "Arrow", "Plus", "Text", "Bracket", "Shape"):
            elms = element.getElementsByTagName(objtype.lower())
            for elm in elms:
                obj = getattr(self, "read%s" % objtype)(elm)
                if obj:
                    scale_val = elm.getAttribute("scale")
                    if scale_val:
                        obj.scale_val = float(scale_val)
                    self.doc.objects.append(obj)

    def readMolecule(self, element):
        molecule = Molecule()
        for attr in ("name", "category"):
            val = element.getAttribute(attr)
            if val:
                setattr(molecule, attr, val)
        # read atoms, bonds and delocalizations
        for objtype in ("Atom", "Bond", "Delocalization"):
            elms = element.getElementsByTagName(objtype.lower())
            for elm in elms:
                obj = getattr(self, "read%s"%objtype)(elm)
                getattr(molecule, "add_%s"%objtype.lower())(obj)
        # read template atom and template bond
        for attr in ("template_atom", "template_bond"):
            obj_id = element.getAttribute(attr)
            if obj_id:
                obj = self.getObject(obj_id)
                if not obj:
                    return
                setattr(molecule, attr, obj)

        return molecule

    def readAtom(self, element):
        atom = Atom()
        id_, symbol, pos, isotope, visible, layout, color = map(element.getAttribute, (
            "id", "symbol", "pos", "isotope", "visible", "layout", "color"))
        H, ox_num, charge, lonepairs, lonepair_type, radical, circle_charge = map(element.getAttribute, (
            "H", "ox_num", "charge", "lonepairs", "lonepair_type", "radical", "circle_charge"))
        if id_:
            self.registerObjectID(atom, id_)
        # read symbol
        if symbol:
            atom.set_symbol(symbol)
        # read postion
        if pos:
            pos = list(map(float, pos.split(",")))
            atom.x, atom.y = self.scaled_coord(pos[:2])
            if len(pos)==3:
                atom.z = self.scaled(pos[2])
        # isotope
        if isotope:
            atom.isotope = int(isotope)
        # hydrogens
        if H:
            atom.hydrogens = int(H)
            atom.auto_hydrogens = False
            atom.update_hydrogens_text()
        # oxidation number
        if ox_num:
            atom.set_oxidation_num(int(ox_num))
        # charge
        if charge:
            atom.set_charge(int(charge))
            if circle_charge and circle_charge=="Yes":
                atom.circle_charge = True
        # lonepairs
        if lonepairs:
            atom.set_lonepairs(int(lonepairs))
            if lonepair_type:
                atom.lonepair_type = lonepair_type
        # radical
        if radical:
            atom.set_radical(int(radical))
        # read show carbon
        if visible and atom.symbol=="C":
            atom.show_symbol = visible=="Yes"
        # text layout or direction
        if layout in ("Auto", "LTR"):
            atom.text_layout = layout
        # color
        if color:
            atom.color = hex_to_color(color)
        # read marks for CCDXv1.0 (DEPRECATED)
        for objtype in ("Charge", "Lonepair", "Radical"):
            elms = element.getElementsByTagName(objtype.lower())
            for elm in elms:
                if objtype=="Charge":
                    type_, val = map(elm.getAttribute, ("type", "val"))
                    if type_ == "partial":
                        continue
                    atom.charge = int(val)
                    atom.circle_charge = type_=="circled"
                elif objtype=="Lonepair":
                    atom.lonepairs += 1
                elif objtype=="Radical":
                    atom.radical = 2

        return atom


    native_bond_types = {"1": "single", "2": "double", "3": "triple", "1.5": "delocalized",
            "0.5": "partial", "H": "hbond", "c": "coordinate", "EZ": "E_or_Z",
            "wv": "wavy", "sw": "wedge", "hw": "hashed_wedge", "b": "bold", "h": "hashed",
            "b2":"bold2", "SD":"1_or_2", "SA":"1_or_a", "DA":"2_or_a", "any":"any"}

    def readBond(self, element):
        bond = Bond()
        id_, type_, atoms, side, color = map(element.getAttribute, (
            "id", "type", "atoms", "side", "color"))
        if id_:
            self.registerObjectID(bond, id_)
        # bond type
        if type_:
            bond.set_type(self.native_bond_types.get(type_, "single"))
        # connect atoms
        if atoms:
            atoms = [self.getObject(uid) for uid in atoms.split()]
            bond.connect_atoms(atoms[0], atoms[1])
        else:
            return
        # second line side
        if side:
            bond.second_line_side = {"L":1, "M":0, "R":-1}.get(side)
            bond.auto_second_line_side = False
        # color
        if color:
            bond.color = hex_to_color(color)

        return bond


    def readDelocalization(self, element):
        delocalization = Delocalization()
        # read atoms
        atom_ids = element.getAttribute("atoms")
        atoms = []
        if atom_ids:
            atoms = [self.getObject(uid) for uid in atom_ids.split()]
        if not all(atoms):# failed to get atom from id
            return
        delocalization.atoms = atoms
        return delocalization


    def readArrow(self, element):
        arrow = Arrow()
        type_, coords, e_src, e_dst, color = map(element.getAttribute, (
            "type", "coords", "e_src", "e_dst", "color"))
        # type
        if type_ and type_ in Arrow.types:
            arrow.set_type(type_)
        # coordinates
        if coords:
            try:
                coords = [pt.split(",") for pt in coords.split(" ")]
                arrow.points = [self.scaled_coord((float(pt[0]), float(pt[1]))) for pt in coords]
            except:
                return
        # color
        if color:
            arrow.color = hex_to_color(color)
        # electron src for electron transfer arrows
        if e_src:
            arrow.e_src =  self.getObject(e_src)
        if e_dst:
            arrow.e_dst =  self.getObject(e_dst)

        return arrow


    def readPlus(self, element):
        plus = Plus()
        pos, font_size, color = map(element.getAttribute, ("pos", "size", "color"))
        # postion
        if pos:
            plus.x, plus.y = self.scaled_coord(map(float, pos.split(",") ))
        # font size
        if font_size:
            plus.font_size = self.scaled(float(font_size))
        # color
        if color:
            plus.color = hex_to_color(color)

        return plus


    def readText(self, element):
        text = Text()
        pos, text_str, font, size, color = map(element.getAttribute, (
            "pos", "text", "font", "size", "color"))
        # pos
        if pos:
            text.x, text.y = self.scaled_coord(map(float, pos.split(",") ))
        # text string
        if text_str:
            text.text = text_str.replace("<br>", "\n")
        # font family
        if font:
            text.font_name = font
        # font size
        if size:
            text.font_size = self.scaled(float(size))
        # color
        if color:
            text.color = hex_to_color(color)

        return text


    def readBracket(self, element):
        bracket = Bracket()
        type_, coords, color = map(element.getAttribute, ("type", "coords", "color"))
        # type
        if type_:
            bracket.type = type_
        # coords
        if coords:
            try:
                coords = [pt.split(",") for pt in coords.split(" ")]
                bracket.points = [self.scaled_coord((float(pt[0]), float(pt[1]))) for pt in coords]
            except:
                return
        # color
        if color:
            bracket.color = hex_to_color(color)

        return bracket


    def readShape(self, element):
        type_, coords, layer, width, color, fill = map(element.getAttribute, (
                            "type", "coords", "layer", "width", "color", "fill"))
        # type
        if type_ in ("line", "rect", "ellipse"):
            shape = {"line":Line, "rect":Rectangle, "ellipse":Ellipse}.get(type_)()
        else:
            return
        # coords
        if coords:
            try:
                coords = [pt.split(",") for pt in coords.split(" ")]
                shape.points = [self.scaled_coord((float(pt[0]), float(pt[1]))) for pt in coords]
            except:
                return
        # layer
        if layer=="top":
            shape.layer = 1
        # width
        if width:
            shape.line_width = float(width)
        # color
        if color:
            shape.color = hex_to_color(color)
        # fill
        if fill:
            shape.fill = hex_to_color(fill)

        return shape




    # -----------------------------------------------------------------
    # --------------------------- WRITE -------------------------------
    # -----------------------------------------------------------------

    def write(self, doc, filename):
        string = self.generate_string(doc)
        if not string:
            return
        try:
            with io.open(filename, "w", encoding="utf-8") as out_file:
                out_file.write(string)
            return
        except:
            self.status = "failed"
            self.message = "Filepath is not writable !"
            return

    def generate_string(self, doc):
        self.reset()
        dom_doc = minidom.Document()
        root = dom_doc.createElement("ccdx")
        dom_doc.appendChild(root)
        # set attributes
        root.setAttribute("version", "1.1")
        self.coord_multiplier = 72/Settings.render_dpi # px to point converter
        w, h = doc.page_size()
        if w!=595 and h!=842:# do not save default page size
            root.setAttribute("page_size", ",".join(map(float_to_str, (w,h))))
        try:
            # write objects
            for obj in doc.objects:
                elm = self.createObjectNode(obj, root)
                if obj.scale_val!=1.0:
                    elm.setAttribute("scale", float_to_str(obj.scale_val))

            # set generated ids
            for obj,id in self.obj_to_id.items():
                self.obj_element_map[obj].setAttribute("id", id)
            output = dom_doc.toprettyxml(indent="  ")
            self.status = "ok"
            return output
        except FileError as e:
            self.message = str(e)
            return


    def createObjectNode(self, obj, parent):
        method = "create%sNode" % obj.class_name
        if hasattr(self, method):
            elm = getattr(self, method)(obj, parent)
            self.obj_element_map[obj] = elm
            return elm

    def createMoleculeNode(self, molecule, parent):
        elm = parent.ownerDocument.createElement("molecule")
        parent.appendChild(elm)
        # name
        if molecule.name:
            elm.setAttribute("name", molecule.name)
        # category
        if molecule.category:
            elm.setAttribute("category", molecule.category)
        # template atom and bond
        if molecule.template_atom and molecule.template_bond:
            elm.setAttribute("template_atom", self.getID(molecule.template_atom))
            elm.setAttribute("template_bond", self.getID(molecule.template_bond))
        # write children
        for child in molecule.children:
            self.createObjectNode(child, elm)
        return elm


    def createAtomNode(self, atom, parent):
        elm = parent.ownerDocument.createElement("atom")
        elm.setAttribute("symbol", atom.symbol)
        # atom pos in "x,y" or "x,y,z" format
        pos = atom.z and atom.pos3d or atom.pos
        pos = map(float_to_str, self.scaled_coord(pos))
        elm.setAttribute("pos", ",".join(pos))
        # isotope
        if atom.isotope:
            elm.setAttribute("isotope", str(atom.isotope))
        # explicit hydrogens. group has always zero hydrogens
        if not atom.is_group and not atom.auto_hydrogens:
            elm.setAttribute("H", str(atom.hydrogens))
        # oxidation number
        if atom.oxidation_num!=None:
            elm.setAttribute("ox_num", str(atom.oxidation_num))
        # charge
        if atom.charge:
            elm.setAttribute("charge", str(atom.charge))
            if atom.circle_charge:
                elm.setAttribute("circle_charge", "Yes")
        # lonepair
        if atom.lonepairs:
            elm.setAttribute("lonepairs", str(atom.lonepairs))
            if atom.lonepair_type=="dash":
                elm.setAttribute("lonepair_type", "dash")
        # lonepair
        if atom.radical:
            elm.setAttribute("radical", str(atom.radical))
        # show/hide symbol if carbon
        if atom.symbol=="C" and atom.show_symbol:
            elm.setAttribute("visible", "Yes")
        # text layout
        if atom.text_layout!="Auto":
            elm.setAttribute("layout", atom.text_layout)
        # color
        if atom.color != (0,0,0):
            elm.setAttribute("color", hex_color(atom.color))

        parent.appendChild(elm)

        return elm


    ccdx_bond_types = {v:k for k,v in native_bond_types.items()}

    def createBondNode(self, bond, parent):
        elm = parent.ownerDocument.createElement("bond")
        if bond.type!="single":
            elm.setAttribute("type", self.ccdx_bond_types[bond.type])
        elm.setAttribute("atoms", " ".join([self.getID(atom) for atom in bond.atoms]))
        if not bond.auto_second_line_side:
            side = {1:"L", 0:"M", -1:"R"}.get(bond.second_line_side)
            elm.setAttribute("side", side)
        # color
        if bond.color != (0,0,0):
            elm.setAttribute("color", hex_color(bond.color))
        parent.appendChild(elm)
        return elm


    def createDelocalizationNode(self, delocalization, parent):
        elm = parent.ownerDocument.createElement("delocalization")
        elm.setAttribute("atoms", " ".join([self.getID(atom) for atom in delocalization.atoms]))
        parent.appendChild(elm)
        return elm


    def createArrowNode(self, arrow, parent):
        elm = parent.ownerDocument.createElement("arrow")
        if arrow.type!="normal":
            elm.setAttribute("type", arrow.type)
        points = [",".join(map(float_to_str, self.scaled_coord(pt))) for pt in arrow.points]
        elm.setAttribute("coords", " ".join(points))
        # electron source and dest
        if arrow.type in ("electron_flow", "fishhook"):
            if arrow.e_src:
                elm.setAttribute("e_src", self.getID(arrow.e_src))
            if arrow.e_dst:
                elm.setAttribute("e_dst", self.getID(arrow.e_dst))
        # color
        if arrow.color != (0,0,0):
            elm.setAttribute("color", hex_color(arrow.color))
        parent.appendChild(elm)
        return elm


    def createPlusNode(self, plus, parent):
        elm = parent.ownerDocument.createElement("plus")
        pos = self.scaled_coord((plus.x,plus.y))
        elm.setAttribute("pos", ",".join(map(float_to_str, pos)))
        elm.setAttribute("size", float_to_str(self.scaled(plus.font_size)))
        # color
        if plus.color != (0,0,0):
            elm.setAttribute("color", hex_color(plus.color))
        parent.appendChild(elm)
        return elm

    def createTextNode(self, text, parent):
        elm = parent.ownerDocument.createElement("text")
        pos = self.scaled_coord((text.x,text.y))
        elm.setAttribute("pos", ",".join(map(float_to_str, pos)))
        elm.setAttribute("text", text.text.replace("\n", "<br>"))
        elm.setAttribute("font", text.font_name)
        elm.setAttribute("size", float_to_str(self.scaled(text.font_size)))
        # color
        if text.color != (0,0,0):
            elm.setAttribute("color", hex_color(text.color))
        parent.appendChild(elm)
        return elm


    def createBracketNode(self, bracket, parent):
        elm = parent.ownerDocument.createElement("bracket")
        elm.setAttribute("type", bracket.type)
        points = [self.scaled_coord(p) for p in bracket.points]
        points = [",".join(map(float_to_str, p)) for p in points]
        elm.setAttribute("coords", " ".join(points))
        # color
        if bracket.color != (0,0,0):
            elm.setAttribute("color", hex_color(bracket.color))
        parent.appendChild(elm)
        return elm


    def createShapeNode(self, shape, parent, shape_type):
        elm = parent.ownerDocument.createElement("shape")
        elm.setAttribute("type", shape_type)
        points = [self.scaled_coord(p) for p in shape.points]
        points = [",".join(map(float_to_str, p)) for p in points]
        elm.setAttribute("coords", " ".join(points))
        # layer
        layer = {1:"top", -1:"bottom"}.get(shape.layer, "bottom")
        if layer=="top":
            elm.setAttribute("layer", "top")
        # width
        if shape.line_width!=1.0:
            elm.setAttribute("width", float_to_str(shape.line_width))
        # color
        if shape.color != (0,0,0):
            elm.setAttribute("color", hex_color(shape.color))
        # fill
        if shape.fill:
            elm.setAttribute("fill", hex_color(shape.fill))
        parent.appendChild(elm)
        return elm

    def createLineNode(self, line, parent):
        self.createShapeNode(line, parent, "line")

    def createRectangleNode(self, rect, parent):
        self.createShapeNode(rect, parent, "rect")

    def createEllipseNode(self, ellipse, parent):
        self.createShapeNode(ellipse, parent, "ellipse")


