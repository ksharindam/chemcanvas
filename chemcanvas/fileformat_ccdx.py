# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import Settings
from common import float_to_str
from drawing_parents import hex_color, hex_to_color
from marks import Charge, Electron
from delocalization import Delocalization
from arrow import Arrow
from bracket import Bracket
from text import Text, Plus
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
            version = ccdxs[0].getAttribute("version")
            if not version:
                reader = Ccdx0()
                doc = reader.read(filename)
                self.doc.objects = doc.objects
            else:
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

        for objtype in ("Molecule", "Arrow", "Plus", "Text", "Bracket"):
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
        id_, symbol, pos, isotope, H, ox_num, visible, layout, color = map(element.getAttribute, (
            "id", "symbol", "pos", "isotope", "H", "ox_num", "visible", "layout", "color"))
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
        # read show carbon
        if visible and atom.symbol=="C":
            atom.show_symbol = visible=="Yes"
        # text layout or direction
        if layout in ("Auto", "LTR"):
            atom.text_layout = layout
        # color
        if color:
            atom.color = hex_to_color(color)
        # read marks
        for objtype in ("Charge", "Lonepair", "Radical"):
            elms = element.getElementsByTagName(objtype.lower())
            for elm in elms:
                mark = getattr(self, "read%s"%objtype)(elm)
                mark.atom = atom
                atom.marks.append(mark)

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

    def readCharge(self, element):
        charge = Charge()
        id_, type_, val, pos, color = map(element.getAttribute, (
            "id", "type", "val", "offset", "color"))
        if id_:
            self.registerObjectID(charge, id_)
        # type
        if type_:
            charge.type = type_
        # value
        if val:
            charge.value = int(val)
        # relative position
        if pos:
            charge.rel_x, charge.rel_y = self.scaled_coord(map(float, pos.split(",")))

        return charge


    def readLonepair(self, element):
        electron = Electron()
        id_, val, pos = map(element.getAttribute, ("id", "val", "offset"))
        if id_:
            self.registerObjectID(electron, id_)
        electron.type = "2"
        # relative position
        if pos:
            electron.rel_x, electron.rel_y = self.scaled_coord(map(float, pos.split(",")))

        return electron


    def readRadical(self, element):
        electron = Electron()
        id_, val, pos = map(element.getAttribute, ("id", "val", "offset"))
        if id_:
            self.registerObjectID(electron, id_)
        electron.type = "1"
        # relative position
        if pos:
            electron.rel_x, electron.rel_y = self.scaled_coord(map(float, pos.split(",")))

        return electron

    def readArrow(self, element):
        arrow = Arrow()
        type_, coords, anchor, color = map(element.getAttribute, (
            "type", "coords", "anchor", "color"))
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
        # anchor
        if anchor:
            arrow.anchor =  self.getObject(anchor)

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
                pass
        # color
        if color:
            bracket.color = hex_to_color(color)

        return bracket


    # -----------------------------------------------------------------
    # --------------------------- WRITE -------------------------------
    # -----------------------------------------------------------------

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
        dom_doc = minidom.Document()
        root = dom_doc.createElement("ccdx")
        dom_doc.appendChild(root)
        # set attributes
        root.setAttribute("version", "1.0")
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
        # add marks
        for child in atom.children:
            self.createObjectNode(child, elm)

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


    def createChargeNode(self, charge, parent):
        elm = parent.ownerDocument.createElement("charge")
        if charge.type!="normal":
            elm.setAttribute("type", charge.type)
        elm.setAttribute("val", str(charge.value))
        pos = self.scaled_coord([charge.rel_x, charge.rel_y])
        elm.setAttribute("offset", ",".join(map(float_to_str, pos)))
        parent.appendChild(elm)
        return elm


    def createElectronNode(self, electron, parent):
        types = {"1":"radical", "2":"lonepair"}
        elm = parent.ownerDocument.createElement(types[electron.type])
        pos = self.scaled_coord([electron.rel_x, electron.rel_y])
        elm.setAttribute("offset", ",".join(map(float_to_str, pos)))
        parent.appendChild(elm)
        return elm


    def createArrowNode(self, arrow, parent):
        elm = parent.ownerDocument.createElement("arrow")
        if arrow.type!="normal":
            elm.setAttribute("type", arrow.type)
        points = [",".join(map(float_to_str, self.scaled_coord(pt))) for pt in arrow.points]
        elm.setAttribute("coords", " ".join(points))
        # anchor
        if arrow.anchor:
            elm.setAttribute("anchor", self.getID(arrow.anchor))
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




# -------------------- READING OF CCDX 0.1 --------------------------


# top level object types
tagname_to_class = {
    "molecule": Molecule,
    "arrow": Arrow,
    "plus": Plus,
    "text": Text,
    "bracket": Bracket,
}

obj_element_dict = {}
objs_to_read_again = set()


class IDManager:
    def __init__(self):
        self.clear()

    def clear(self):
        self.id_to_obj = {}# for read mode

    def addObject(self, obj, obj_id):
        self.id_to_obj[obj_id] = obj

    def getObject(self, obj_id):
        try:
            return self.id_to_obj[obj_id]
        except KeyError:# object not read yet
            return None



id_manager = IDManager()


class Ccdx0(FileFormat):
    readable_formats = [("ChemCanvas Drawing XML", "ccdx")]
    writable_formats = [("ChemCanvas Drawing XML", "ccdx")]

    def read(self, filename):
        dom_doc = minidom.parse(filename)
        return self.readFromDomDocument(dom_doc)

    def readFromDomDocument(self, dom_doc):
        ccdxs = dom_doc.getElementsByTagName("ccdx")
        if not ccdxs:
            return
        root = ccdxs[0]
        # result
        doc = Document()
        # read objects
        for tagname, ObjClass in tagname_to_class.items():
            elms = root.getElementsByTagName(tagname)
            for elm in elms:
                obj = tagname_to_class[elm.tagName]()
                obj_read_xml_node(obj, elm)
                scale_val = elm.getAttribute("scale_val")
                if scale_val:
                    obj.scale_val = float(scale_val)
                doc.objects.append(obj)
        # some objects failed because dependency objects were not loaded earlier
        while objs_to_read_again:
            successful = False
            for obj, elm in list(objs_to_read_again):
                if globals()[tagname+"_read_xml_node"](obj, elm):
                    objs_to_read_again.remove((obj, elm))
                    successful = True
            if not successful:
                break
        id_manager.clear()
        objs_to_read_again.clear()
        return doc.objects and doc or None



def obj_read_xml_node(obj, elm):
    ok = globals()[elm.tagName+"_read_xml_node"](obj, elm)
    if not ok:
        objs_to_read_again.add((obj, elm))
    uid = elm.getAttribute("id")
    if uid:
        id_manager.addObject(obj, uid)
    return ok

# ------------- MOLECULE -------------------

def molecule_read_xml_node(molecule, mol_elm):
    name = mol_elm.getAttribute("name")
    if name:
        molecule.name = name

    category = mol_elm.getAttribute("category")
    if category:
        molecule.category = category
    # create atoms
    atom_elms = mol_elm.getElementsByTagName("atom")
    for atom_elm in atom_elms:
        atom = molecule.new_atom()
        obj_read_xml_node(atom, atom_elm)
    # create bonds
    bond_elms = mol_elm.getElementsByTagName("bond")
    for bond_elm in bond_elms:
        bond = molecule.new_bond()
        obj_read_xml_node(bond, bond_elm)
    # create delocallizations
    deloc_elms = mol_elm.getElementsByTagName("delocalization")
    for deloc_elm in deloc_elms:
        deloc = Delocalization()
        ok = obj_read_xml_node(deloc, deloc_elm)
        if ok:
            molecule.add_delocalization(deloc)

    t_atom_id = mol_elm.getAttribute("template_atom")
    if t_atom_id:
        t_atom = id_manager.getObject(t_atom_id)
        if not t_atom:
            return False
        molecule.template_atom = t_atom

    t_bond_id = mol_elm.getAttribute("template_bond")
    if t_bond_id:
        t_bond = id_manager.getObject(t_bond_id)
        if not t_bond:
            return False
        molecule.template_bond = t_bond

    return True



# -------- ATOM -----------

def atom_read_xml_node(atom, elm):
    # read symbol
    symbol = elm.getAttribute("sym")
    if symbol:
        atom.set_symbol(symbol)
    # read postion
    pos = elm.getAttribute("pos")
    if pos:
        pos = list(map(float, pos.split(",")))
        atom.x, atom.y = pos[:2]
        if len(pos)==3:
            atom.z = pos[2]
    # isotope
    isotope = elm.getAttribute("iso")
    if isotope:
        atom.isotope = int(isotope)
    # hydrogens
    hydrogens = elm.getAttribute("H")
    if hydrogens:
        atom.hydrogens = int(hydrogens)
        atom.auto_hydrogens = False
    # read show carbon
    show_symbol = elm.getAttribute("show_C")
    if show_symbol and atom.symbol=="C":
        atom.show_symbol = bool(int(show_symbol))
    # color
    color = elm.getAttribute("clr")
    if color:
        atom.color = hex_to_color(color)
    # create marks
    marks_class_dict = {"charge" : Charge, "electron" : Electron}
    for tagname, MarkClass in marks_class_dict.items():
        elms = elm.getElementsByTagName(tagname)
        for elm in elms:
            mark = MarkClass()
            obj_read_xml_node(mark, elm)
            mark.atom = atom
            atom.marks.append(mark)

    return True

# ----------- end atom --------------------


# -------------- BOND --------------------

short_bond_types = {"single": "1", "double": "2", "triple": "3",
        "delocalized":"a", "partial":"p", "hbond":"h", "coordinate":"c",
        "wedge":"w", "hashed_wedge":"ha", "bold":"b",
}

# short bond type to full bond type map
full_bond_types = {it[1]:it[0] for it in short_bond_types.items()}

def bond_read_xml_node(bond, elm):
    # read bond type
    _type = elm.getAttribute("typ")
    if _type:
        bond.set_type(full_bond_types[_type])
    # read connected atoms
    atom_ids = elm.getAttribute("atms")
    atoms = []
    if atom_ids:
        atoms = [id_manager.getObject(uid) for uid in atom_ids.split()]
    if len(atoms)<2 or None in atoms:# failed to get atom from id
        return False
    bond.connect_atoms(atoms[0], atoms[1])
    # read second line side
    side = elm.getAttribute("side")
    if side:
        bond.second_line_side = int(side)
        bond.auto_second_line_side = False
    # color
    color = elm.getAttribute("clr")
    if color:
        bond.color = hex_to_color(color)

    return True

# -------------------- end of bond ----------------------


# ------------------ DELOCALIZATION ---------------------

def delocalization_read_xml_node(delocalization, elm):
    # read atoms
    atom_ids = elm.getAttribute("atms")
    atoms = []
    if atom_ids:
        atoms = [id_manager.getObject(uid) for uid in atom_ids.split()]
    if not all(atoms):# failed to get atom from id
        return False
    delocalization.atoms = atoms
    return True

# ---------------- end of delocalization ----------------


# -------------------- Marks ----------------------------

def mark_read_xml_node(mark, elm):
    pos = elm.getAttribute("rel_pos")
    if pos:
        mark.rel_x, mark.rel_y = map(float, pos.split(","))
    size = elm.getAttribute("size")
    if size:
        mark.size = float(size)


short_charge_types = { "normal": "n", "circled": "c", "partial": "p" }
# short charge type to full charge type map
full_charge_types = {it[1]:it[0] for it in short_charge_types.items()}


def charge_read_xml_node(charge, elm):
    mark_read_xml_node(charge, elm)
    type = elm.getAttribute("typ")
    if type:
        charge.type = full_charge_types[type]
    val = elm.getAttribute("val")
    if val:
        charge.value = int(val)
    return True

def electron_read_xml_node(electron, elm):
    mark_read_xml_node(electron, elm)
    type = elm.getAttribute("typ")
    if type:
        electron.type = type
    radius = elm.getAttribute("rad")
    if radius:
        electron.dot_size = float(radius)*2
    return True


# ----------------- end marks -----------------------


# ------------------ ARROW ---------------------------

short_arrow_types = { "normal": "n", "equilibrium": "eq", "retrosynthetic": "rt",
    "resonance": "rn", "electron_flow": "el", "fishhook": "fh",
}
# short arrow type to full arrow type map
full_arrow_types = {it[1]:it[0] for it in short_arrow_types.items()}

def arrow_read_xml_node(arrow, elm):
    type = elm.getAttribute("typ")
    if type:
        if type in ("el", "fh"):# no longer supports curved arrow from ccdx 0.1
            return False
        arrow.set_type(full_arrow_types[type])
    points = elm.getAttribute("pts")
    if points:
        try:
            pt_list = points.split(" ")
            pt_list = [pt.split(",") for pt in pt_list]
            arrow.points = [(float(pt[0]), float(pt[1])) for pt in pt_list]
        except:
            return False
    # color
    color = elm.getAttribute("clr")
    if color:
        arrow.color = hex_to_color(color)
    # anchor
    anchor_id = elm.getAttribute("anchor")
    if anchor_id:
        anchor =  id_manager.getObject(anchor_id)
        if not anchor:
            return False
        arrow.anchor = anchor
    return True

# --------------- end of arrow ---------------------


# ----------------- PLUS -----------------------

def plus_read_xml_node(plus, elm):
    pos = elm.getAttribute("pos")
    if pos:
        plus.x, plus.y = map(float, pos.split(",") )
    font_size = elm.getAttribute("size")
    if font_size:
        plus.font_size = float(font_size)
    # color
    color = elm.getAttribute("clr")
    if color:
        plus.color = hex_to_color(color)
    return True

# ------------------- end of plus -----------------------


# ---------------------- TEXT -----------------------

def text_read_xml_node(text, elm):
    pos = elm.getAttribute("pos")
    if pos:
        text.x, text.y = map(float, pos.split(",") )
    text_str = elm.getAttribute("text")
    if text_str:
        text.text = text_str
    font_name = elm.getAttribute("font")
    if font_name:
        text.font_name = font_name
    font_size = elm.getAttribute("size")
    if font_size:
        text.font_size = float(font_size)
    # color
    color = elm.getAttribute("clr")
    if color:
        text.color = hex_to_color(color)
    return True

# ---------------------- end of text ---------------------


# --------------------- BRACKET -------------------

short_bracket_types = { "square": "s", "curly": "c", "round": "r" }
# short bracket type to full bracket type map
full_bracket_types = {it[1]:it[0] for it in short_bracket_types.items()}


def bracket_read_xml_node(bracket, elm):
    type = elm.getAttribute("typ")
    if type:
        bracket.type = full_bracket_types[type]
    points = elm.getAttribute("pts")
    if points:
        try:
            pt_list = points.split(" ")
            pt_list = [pt.split(",") for pt in pt_list]
            bracket.points = [(float(pt[0]), float(pt[1])) for pt in pt_list]
        except:
            pass
    # color
    color = elm.getAttribute("clr")
    if color:
        bracket.color = hex_to_color(color)
    return True

# -------------------------- end of bracket ----------------------
