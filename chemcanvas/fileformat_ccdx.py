# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App
from common import float_to_str
from drawing_parents import hex_color, hex_to_color
from marks import Charge, Electron
from delocalization import Delocalization
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
    readable_formats = [("ChemCanvas Drawing XML", "ccdx")]
    writable_formats = [("ChemCanvas Drawing XML", "ccdx")]

    def read(self, filename):
        dom_doc = Dom.parse(filename)
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


    def write(self, doc, filename):
        string = self.generateString(doc)
        try:
            with io.open(filename, "w", encoding="utf-8") as out_file:
                out_file.write(string)
            return True
        except:
            return False


    def generateString(self, doc):
        dom_doc = Dom.Document()
        root = dom_doc.createElement("ccdx")
        dom_doc.appendChild(root)
        for obj in doc.objects:
            elm = obj_create_xml_node(obj, root)
            if obj.scale_val != 1.0:
                elm.setAttribute("scale_val", str(obj.scale_val))
        id_manager.clear()
        obj_element_dict.clear()
        return dom_doc.toprettyxml(indent="  ")



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
    if molecule.name:
        elm.setAttribute("name", molecule.name)
    if molecule.variant:
        elm.setAttribute("variant", molecule.variant)
    if molecule.category:
        elm.setAttribute("category", molecule.category)
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
    variant = mol_elm.getAttribute("variant")
    if variant:
        molecule.variant = variant

    category = mol_elm.getAttribute("category")
    if category:
        molecule.category = category
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

short_bond_types = {"single": "1", "double": "2", "triple": "3",
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


# ------------------ DELOCALIZATION ---------------------

def delocalization_create_xml_node(delocalization, parent):
    elm = parent.ownerDocument.createElement("delocalization")
    elm.setAttribute("atms", " ".join([id_manager.getID(atom) for atom in delocalization.atoms]))
    parent.appendChild(elm)
    return elm

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



class CCDX(FileFormat):

    def reset(self):
        # for read mode
        self.id_to_obj = {}
        # for write mode
        self.obj_to_id = {}
        #self.obj_element_map = {}

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

    def read(self, filename):
        self.reset()
        dom_doc = Dom.parse(filename)
        # read root element
        ccdxs = dom_doc.getElementsByTagName("ccdx")
        if not ccdxs:
            return
        self.doc = Document()
        self.readCcdx(ccdxs[0])

        return self.doc.objects and self.doc or None


    def readCcdx(self, element):
        # get page size
        w, h = map(element.getAttribute, ('width','height'))
        if w and h:
            self.doc.setPageSize(float(w), float(h))
        else:
            self.doc.setPageSize(595,842) # a4 size is default

        for objtype in ("Molecule", "Arrow", "Plus", "Text", "Bracket"):
            elms = element.getElementsByTagName(objtype.lower())
            for elm in elms:
                obj = getattr(self, "read%s" % objtype)()
                if obj:
                    self.doc.objects.append(obj)

    def readMolecule(self, element):
        molecule = Molecule()
        for attr in ("name", "variant", "category"):
            val = element.getAttribute(attr)
            if val:
                setattr(molecule, attr, val)
        # read atoms, bonds and delocalizations
        for objtype in ("Atom", "Bond", "Delocalization"):
            elms = element.getElementsByTagName(objtype.lower())
            for elm in elms:
                obj = getattr(self, "read%s"%objtype)()
                getattr(molecule, "add%s"%objtype)()
        # read template atom and template bond
        for attr in ("template_atom", "template_bond"):
            obj_id = element.getAttribute(attr)
            if obj_id:
                obj = self.getObject(val)
                if not obj:
                    return
                setattr(molecule, attr, obj)

        return molecule

    def readAtom(self, element):
        atom = Atom()
        uid, symbol, pos, isotope, valency, H, visible, layout, color = map(element.getAttribute, (
            "id", "symbol", "pos", "isotope", "valency", "H", "visible", "layout", "color"))
        # read symbol
        if symbol:
            atom.setSymbol(symbol)
        # read postion
        if pos:
            pos = list(map(float, pos.split(",")))
            atom.x, atom.y = pos[:2]
            if len(pos)==3:
                atom.z = pos[2]
        # isotope
        if isotope:
            atom.isotope = int(isotope)
        # valency
        if valency:
            atom.valency = int(valency)
            atom.auto_valency = False
        # hydrogens
        if H:
            atom.hydrogens = int(H)
            atom.auto_hydrogens = False
        # read show carbon
        if visible and atom.symbol=="C":
            atom.show_symbol = bool(int(visible))
        # text layout or direction
        if layout:
            atom.text_layout = layout
            atom.auto_text_layout = False
        # color
        if color:
            atom.color = hex_to_color(color)
        # read marks
        for objtype in ("Charge", "Lonepair", "Radical"):
            elms = element.getElementsByTagName(objtype.lower())
            for elm in elms:
                mark = getattr(self, "read%s"%objtype)()
                mark.atom = atom
                atom.marks.append(mark)

        return atom


    def readBond(self, element):
        bond = Bond()
        type_, atoms, double_bond_side, color = map(element.getAttribute, (
            "type", "atoms", "double_bond_side", "color"))
        # bond type
        if type_:
            bond.setType(full_bond_types[type_])
        # connect atoms
        if atoms:
            atoms = [self.getObject(uid) for uid in atoms.split()]
            bond.connectAtoms(atoms[0], atoms[1])
        else:
            return
        # second line side
        if double_bond_side:
            bond.second_line_side = int(double_bond_side)
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
        type_, val, rel_pos, size, color = map(element.getAttribute, (
            "type", "val", "pos", "size", "color"))
        # type
        if type_:
            charge.type = full_charge_types[type_]
        # value
        if val:
            charge.value = int(val)
        # relative position
        if pos:
            charge.rel_x, charge.rel_y = map(float, pos.split(","))
        # size
        if size:
            charge.size = float(size)

        return charge

    def readLonepair(self, element):
        electron = Electron()
        val, pos, size = map(element.getAttribute, ("val", "pos", "size"))
        electron.type = "2"
        # relative position
        if pos:
            electron.rel_x, electron.rel_y = map(float, pos.split(","))
        # dot size
        if size:
            electron.radius = float(size)

        return electron


    def readRadical(self, element):
        electron = Electron()
        val, pos, size = map(element.getAttribute, ("val", "pos", "size"))
        electron.type = "1"
        # relative position
        if pos:
            electron.rel_x, electron.rel_y = map(float, pos.split(","))
        # dot size
        if size:
            electron.radius = float(size)

        return electron

    def readArrow(self, element):
        arrow = Arrow()
        type_, coords, anchor, color = map(element.getAttribute, (
            "type", "coords", "anchor", "color"))
        # type
        if type_:
            arrow.setType(type_)
        # coordinates
        if coords:
            try:
                coords = [pt.split(",") for pt in coords.split(" ")]
                arrow.points = [(float(pt[0]), float(pt[1])) for pt in coords]
            except:
                return False
        # color
        if color:
            arrow.color = hex_to_color(color)
        # anchor
        if anchor:
            anchor =  self.getObject(anchor)
            if not anchor:
                return False
            arrow.anchor = anchor

        return arrow


    def readPlus(self, element):
        plus = Plus()
        pos, font_size, color = map(element.getAttribute, ("pos", "size", "color"))
        # postion
        if pos:
            plus.x, plus.y = map(float, pos.split(",") )
        # font size
        if font_size:
            plus.font_size = float(font_size)
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
            text.x, text.y = map(float, pos.split(",") )
        # text string
        if text_str:
            text.text = text_str
        # font family
        if font:
            text.font_name = font
        # font size
        if size:
            text.font_size = float(size)
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
                bracket.points = [(float(pt[0]), float(pt[1])) for pt in coords]
            except:
                pass
        # color
        if color:
            bracket.color = hex_to_color(color)

        return bracket
