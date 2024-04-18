# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App
from common import float_to_str
from drawing_parents import hex_color, hex_to_color
from molecule import Molecule
from marks import Charge, Electron
from arrow import Arrow
from bracket import Bracket
from text import Text, Plus
from fileformat import *

import io
import xml.dom.minidom as Dom

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
        self.obj_to_id = {}# for write mode
        self.atom_id_no = 1
        self.bond_id_no = 1
        self.mark_id_no = 1
        self.other_id_no = 1

    def addObject(self, obj, obj_id):
        self.id_to_obj[obj_id] = obj

    def getObject(self, obj_id):
        try:
            return self.id_to_obj[obj_id]
        except KeyError:# object not read yet
            return None

    def createObjectID(self, obj):
        if obj.class_name=="Atom":
            new_id = "a%i" % self.atom_id_no
            self.atom_id_no += 1
        elif obj.class_name=="Bond":
            new_id = "b%i" % self.bond_id_no
            self.bond_id_no += 1
        elif obj.class_name in ("Charge", "Electron"):
            new_id = "mk%i" % self.mark_id_no
            self.mark_id_no += 1
        else:
            new_id = "o%i" % self.other_id_no
            self.other_id_no += 1

        self.obj_to_id[obj] = new_id
        # add id attribute if element was already created but id not created
        if obj in obj_element_dict:
            obj_element_dict[obj].setAttribute("id", new_id)
        return new_id

    def getID(self, obj):
        try:
            return self.obj_to_id[obj]
        except KeyError:
            return self.createObjectID(obj)

    def hasObject(self, obj):
        return obj in self.obj_to_id


id_manager = IDManager()


class Ccdx(FileFormat):

    def read(self, filename):
        doc = Dom.parse(filename)
        return self.readFromDocument(doc)

    def readFromString(self, data):
        pass

    def readFromDocument(self, doc):
        ccdxs = doc.getElementsByTagName("ccdx")
        if not ccdxs:
            return []
        root = ccdxs[0]
        # result
        page = Page()
        # read objects
        for tagname, ObjClass in tagname_to_class.items():
            elms = root.getElementsByTagName(tagname)
            for elm in elms:
                obj = tagname_to_class[elm.tagName]()
                obj_read_xml_node(obj, elm)
                scale_val = elm.getAttribute("scale_val")
                if scale_val:
                    obj.scale_val = float(scale_val)
                page.objects.append(obj)
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
        if page.objects:
            document = Document()
            document.pages.append(page)
            return document
        return None

    def generateString(self, objects):
        doc = Dom.Document()
        doc.version = "1.0"
        doc.encoding = "UTF-8"
        root = doc.createElement("ccdx")
        doc.appendChild(root)
        for obj in objects:
            elm = obj_create_xml_node(obj, root)
            if obj.scale_val != 1.0:
                elm.setAttribute("scale_val", str(obj.scale_val))
        id_manager.clear()
        obj_element_dict.clear()
        return doc.toprettyxml()

    def write(self, objects, filename):
        string = self.generateString(objects)
        try:
            with io.open(filename, "w", encoding="utf-8") as out_file:
                out_file.write(string)
            return True
        except:
            return False


def obj_read_xml_node(obj, elm):
    ok = globals()[elm.tagName+"_read_xml_node"](obj, elm)
    if not ok:
        objs_to_read_again.add((obj, elm))
    uid = elm.getAttribute("id")
    if uid:
        id_manager.addObject(obj, uid)
    return ok


def obj_create_xml_node(obj, parent):
    obj_type = obj.class_name.lower()
    elm = globals()[obj_type+"_create_xml_node"](obj, parent)
    obj_element_dict[obj] = elm
    # id already created, need to save id
    if id_manager.hasObject(obj):
        elm.setAttribute("id", id_manager.getID(obj))
    return elm

# ------------- MOLECULE -------------------

def molecule_create_xml_node(molecule, parent):
    elm = parent.ownerDocument.createElement("molecule")
    if molecule.template_atom:
        elm.setAttribute("template_atom", id_manager.getID(molecule.template_atom))
    if molecule.template_bond:
        elm.setAttribute("template_bond", id_manager.getID(molecule.template_bond))
    for child in molecule.children:
        obj_create_xml_node(child, elm)
    parent.appendChild(elm)
    return elm

def molecule_read_xml_node(molecule, mol_elm):
    name = mol_elm.getAttribute("name")
    if name:
        molecule.name = name
    # create atoms
    atom_elms = mol_elm.getElementsByTagName("atom")
    for atom_elm in atom_elms:
        atom = molecule.newAtom()
        obj_read_xml_node(atom, atom_elm)
    # create bonds
    bond_elms = mol_elm.getElementsByTagName("bond")
    for bond_elm in bond_elms:
        bond = molecule.newBond()
        obj_read_xml_node(bond, bond_elm)

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

def atom_create_xml_node(atom, parent):
    elm = parent.ownerDocument.createElement("atom")
    elm.setAttribute("sym", atom.symbol)
    # atom pos in "x,y" or "x,y,z" format
    pos_attr = float_to_str(atom.x) + "," + float_to_str(atom.y)
    if atom.z != 0:
        pos_attr += "," + float_to_str(atom.z)
    elm.setAttribute("pos", pos_attr)
    if atom.isotope:
        elm.setAttribute("iso", str(atom.isotope))
    # explicit valency
    if not atom.auto_valency:
        elf.setAttribute("val", str(atom.valency))
    # explicit hydrogens. group has always zero hydrogens
    if not atom.is_group and not atom.auto_hydrogens:
        elm.setAttribute("H", str(atom.hydrogens))
    # show/hide symbol if carbon
    if atom.symbol=="C" and atom.show_symbol:
        elm.setAttribute("show_C", "1")
    # text layout
    if not atom.auto_text_layout:
        elm.setAttribute("dir", atom.text_layout)
    # color
    if atom.color != (0,0,0):
        elm.setAttribute("clr", hex_color(atom.color))

    parent.appendChild(elm)
    # add marks
    for child in atom.children:
        obj_create_xml_node(child, elm)

    return elm


def atom_read_xml_node(atom, elm):
    # read symbol
    symbol = elm.getAttribute("sym")
    if symbol:
        atom.setSymbol(symbol)
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
    # valency
    valency = elm.getAttribute("val")
    if valency:
        atom.valency = int(valency)
        atom.auto_valency = False
    # hydrogens
    hydrogens = elm.getAttribute("H")
    if hydrogens:
        atom.hydrogens = int(hydrogens)
        atom.auto_hydrogens = False
    # read show carbon
    show_symbol = elm.getAttribute("show_C")
    if show_symbol and atom.symbol=="C":
        atom.show_symbol = bool(int(show_symbol))
    # text layout or direction
    direction = elm.getAttribute("dir")
    if direction:
        atom.text_layout = direction
        atom.auto_text_layout = False
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

short_bond_types = {"normal": "1", "double": "2", "triple": "3",
        "aromatic":"a", "hbond":"h", "partial":"p", "coordinate":"c",
        "wedge":"w", "hatch":"ha", "bold":"b",
}

# short bond type to full bond type map
full_bond_types = {it[1]:it[0] for it in short_bond_types.items()}

def bond_create_xml_node(bond, parent):
    elm = parent.ownerDocument.createElement("bond")
    elm.setAttribute("typ", short_bond_types[bond.type])
    elm.setAttribute("atms", " ".join([id_manager.getID(atom) for atom in bond.atoms]))
    if not bond.auto_second_line_side:
        elm.setAttribute("side", str(bond.second_line_side))
    # color
    if bond.color != (0,0,0):
        elm.setAttribute("clr", hex_color(bond.color))
    parent.appendChild(elm)
    return elm

def bond_read_xml_node(bond, elm):
    # read bond type
    _type = elm.getAttribute("typ")
    if _type:
        bond.setType(full_bond_types[_type])
    # read connected atoms
    atom_ids = elm.getAttribute("atms")
    atoms = []
    if atom_ids:
        atoms = [id_manager.getObject(uid) for uid in atom_ids.split()]
    if len(atoms)<2 or None in atoms:# failed to get atom from id
        return False
    bond.connectAtoms(atoms[0], atoms[1])
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


# -------------------- Marks ----------------------------

def mark_add_attributes_to_xml_node(mark, elm):
    pos_attr = float_to_str(mark.rel_x) + "," + float_to_str(mark.rel_y)
    elm.setAttribute("rel_pos", pos_attr)
    elm.setAttribute("size", float_to_str(mark.size))

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


def charge_create_xml_node(charge, parent):
    elm = parent.ownerDocument.createElement("charge")
    mark_add_attributes_to_xml_node(charge, elm)
    elm.setAttribute("typ", short_charge_types[charge.type])
    elm.setAttribute("val", str(charge.value))
    parent.appendChild(elm)
    return elm

def charge_read_xml_node(charge, elm):
    mark_read_xml_node(charge, elm)
    type = elm.getAttribute("typ")
    if type:
        charge.type = full_charge_types[type]
    val = elm.getAttribute("val")
    if val:
        charge.value = int(val)
    return True


def electron_create_xml_node(electron, parent):
    elm = parent.ownerDocument.createElement("electron")
    mark_add_attributes_to_xml_node(electron, elm)
    elm.setAttribute("typ", electron.type)
    elm.setAttribute("rad", float_to_str(electron.radius))
    parent.appendChild(elm)
    return elm

def electron_read_xml_node(electron, elm):
    mark_read_xml_node(electron, elm)
    type = elm.getAttribute("typ")
    if type:
        electron.type = type
    radius = elm.getAttribute("rad")
    if radius:
        electron.radius = float(radius)
    return True


# ----------------- end marks -----------------------


# ------------------ ARROW ---------------------------

short_arrow_types = { "normal": "n", "equilibrium": "eq", "retrosynthetic": "rt",
    "resonance": "rn", "electron_shift": "el", "fishhook": "fh",
}
# short arrow type to full arrow type map
full_arrow_types = {it[1]:it[0] for it in short_arrow_types.items()}

def arrow_create_xml_node(arrow, parent):
    elm = parent.ownerDocument.createElement("arrow")
    elm.setAttribute("typ", short_arrow_types[arrow.type])
    points = ["%s,%s" % (float_to_str(pt[0]), float_to_str(pt[1])) for pt in arrow.points]
    elm.setAttribute("pts", " ".join(points))
    # color
    if arrow.color != (0,0,0):
        elm.setAttribute("clr", hex_color(arrow.color))
    # anchor
    if arrow.anchor:
        elm.setAttribute("anchor", id_manager.getID(arrow.anchor))
    # TODO : add head dimensions here. because, arrow may be scaled
    parent.appendChild(elm)
    return elm

def arrow_read_xml_node(arrow, elm):
    type = elm.getAttribute("typ")
    if type:
        arrow.setType(full_arrow_types[type])
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

def plus_create_xml_node(plus, parent):
    elm = parent.ownerDocument.createElement("plus")
    elm.setAttribute("pos", float_to_str(plus.x) + "," + float_to_str(plus.y))
    elm.setAttribute("size", float_to_str(plus.font_size))
    # color
    if plus.color != (0,0,0):
        elm.setAttribute("clr", hex_color(plus.color))
    parent.appendChild(elm)
    return elm

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

def text_create_xml_node(text, parent):
    elm = parent.ownerDocument.createElement("text")
    elm.setAttribute("pos", float_to_str(text.x) + "," + float_to_str(text.y))
    elm.setAttribute("text", text.text)
    elm.setAttribute("font", text.font_name)
    elm.setAttribute("size", float_to_str(text.font_size))
    # color
    if text.color != (0,0,0):
        elm.setAttribute("clr", hex_color(text.color))
    parent.appendChild(elm)
    return elm

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

def bracket_create_xml_node(bracket, parent):
    elm = parent.ownerDocument.createElement("bracket")
    elm.setAttribute("typ", short_bracket_types[bracket.type])
    points = ["%s,%s" % (float_to_str(pt[0]), float_to_str(pt[1])) for pt in bracket.points]
    elm.setAttribute("pts", " ".join(points))
    # color
    if bracket.color != (0,0,0):
        elm.setAttribute("clr", hex_color(bracket.color))
    parent.appendChild(elm)
    return elm

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

