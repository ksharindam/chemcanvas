# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os, time
import re
import io

from tool_helpers import place_molecule
from fileformat import *

# Supported Features
# read-write of only V2000 connection table. V3000 not supported
# - Atom symbol, charges, lone-pair, radical
# - single, double, triple, aromatic, wedge and hashed wedge bond

# TODO :
# - read radical in atom block
# - Need to expand functional group

class Molfile(FileFormat):
    readable_formats = [("MDL Molfile", "mol"), ("MDL SDfile", "sdf")]
    writable_formats = [("MDL Molfile", "mol")]

    def __init__(self):
        self.molecule = None
        self.filename = ""# output filename

    def read(self, filename):
        self.reset_status()
        f = open(filename)
        try:
            doc = self.read_file(f)
            self.status = "ok"
            return doc
        except FileError as e:
            self.message = str(e)
            return

    def readFromString(self, text):
        self.reset_status()
        f = io.StringIO(text)
        try:
            doc = self.read_file(f)
            self.status = "ok"
            return doc
        except FileError as e:
            self.message = str(e)
            return

    def read_file(self, f):
        doc = Document()
        while True:
            if not self.read_header(f):
                break
            mol = self.read_connection_table(f)
            if not mol:
                break
            place_molecule(mol) # scale so that it have default bond length
            doc.objects.append(mol)
            data = self.read_structure_data(f)
            if data:
                mol.data = data
        return doc if doc.objects else None


    def read_header(self, f):
        # header consists of title line, Program/timestamp line, and comment line
        header = []
        for i in range(3):
            line = f.readline()
            if not line:
                return
            header.append(line.strip())
        return header

    def read_connection_table(self, f):
        """ also called CTAB """
        # read counts line
        atom_count = read_value(f, 3, int)
        bond_count = read_value(f, 3, int)
        # remaining part of counts line
        f.readline()
        # read the structure
        mol = Molecule()
        # read atom block
        for i in range( atom_count):
            a = self.read_atom_line(f)
            mol.add_atom(a)
        # read bond block
        for k in range( bond_count):
            bond, a1, a2 = self.read_bond_line(f)
            mol.add_bond(bond)
            bond.connect_atoms(mol.atoms[a1], mol.atoms[a2])
        # read properties block
        for line in f:
            if line.strip() == "M  END":
                break
            if line.strip().startswith( "M  "):
                self._read_property( line.strip(), mol)

        for atom in mol.atoms:
            if "charge" in atom.properties_:
                charge = atom.properties_["charge"]
                mark = Charge()
                mark.setValue(charge)
                atom.add_mark(mark)
                atom.properties_.pop("charge")

        return mol


    def read_atom_line(self, f):
        x = read_value(f, 10, float)
        y = read_value(f, 10, float)
        z = read_value(f, 10, float)
        read_value(f, 1) # empty space
        symbol = read_value(f, 3)
        mass_diff = read_value(f, 2)
        charge = read_charge(f)
        f.readline() # read remaining part of line
        atom = Atom(symbol)
        atom.x, atom.y, atom.z = x,-y,z
        if charge:
            atom.properties_["charge"] = charge
        return atom


    def read_bond_line(self, f):
        a1 = read_value(f, 3, int) - 1 # molfiles index from 1
        a2 = read_value(f, 3, int) - 1
        typ = read_value(f, 3, int)
        stereo = read_value(f, 3, int)
        f.readline() # next line please
        # 1 = Single, 2 = Double, 3 = Triple, 4 = Aromatic, 5 = Single or Double,
        # 6 = Single or Aromatic, 7 = Double or Aromatic, 8 = Any
        type_remap = { 1: "single", 2: "double", 3: "triple", 4: "delocalized"}
        typ = type_remap.get(typ, "single")
        if typ=="single":
            stereo_remap = { 0: "single", 1: "wedge", 6: "hashed_wedge"}
            typ = stereo_remap.get(stereo, "single")
        bond = Bond()
        bond.set_type(typ)
        return bond, a1, a2


    def _read_property(self, text, mol):
        # read charge info
        if text.startswith("M  CHG"):
            m = re.match( "M\s+CHG\s+(\d+)(.*)", text)
            if m:
                for at,chg in re.findall( "([-+]?\d+)\s+([-+]?\d+)", m.group( 2)):
                    #print(at,chg)
                    atom = mol.atoms[int(at)-1]
                    mark = Charge()
                    mark.setValue(int(chg))
                    atom.add_mark(mark)
        # read radical info
        elif text.startswith("M  RAD"):
            # M  RADnn8 aaa vvv aaa vvv ...
            m = re.match( "M\s+RAD\s+(\d+)(.*)", text)
            if m:
                for at,rad in re.findall( "(\d+)\s+(\d+)", m.group( 2)):
                    atom = mol.atoms[int(at)-1]
                    multi = int(rad)
                    marks = []
                    if multi==1:# singlet
                        marks = [Electron("2")]
                    elif multi==2:# doublet
                        marks = [Electron("1")]
                    elif multi==3:# triplet
                        marks = [Electron("1"), Electron("1")]
                    [atom.add_mark(mark) for mark in marks]


    def write(self, doc, filename):
        """ write molecule to filename """
        self.filename = filename# required in header
        string = self.generate_string(doc)
        if not string:
            return False
        try:
            with open(filename, "w") as out_file:
                out_file.write(string)
            return True
        except:
            self.message = "Filepath is not writable !"
            return False

    def generate_string(self, doc):
        self.reset_status()
        # TODO : if multiple molecules present, show message to select a molecule
        molecules = [o for o in doc.objects if o.class_name=="Molecule"]
        if not molecules:
            return
        self.molecule = molecules[-1]# take the last molecule
        # get header
        title = os.path.splitext(os.path.basename(self.filename))[0]
        line2 = "ASChemCanv%s2D" % time.strftime("%y%m%d%H%M")
        comment = ""
        header = "%s\n%s\n%s\n" % (title, line2, comment)
        try:
            # get connection table
            ctab = self._get_connection_table()
            output = header + ctab
            self.status = "ok"
            return output
        except FileError as e:
            self.message = str(e)
            return ""


    def _get_connection_table(self):
        """ create V2000 connection table """
        lines = []
        # add counts line
        lines.append( self._get_counts_line())
        # create atoms block
        for a in self.molecule.atoms:
            lines.append( self._get_atom_line( a))
        # create bonds block
        for b in self.molecule.bonds:
            lines.append( self._get_bond_line( b))
        # create properties block
        # get charges
        charges = [(i+1, a.charge) for i,a in enumerate(self.molecule.atoms) if a.charge]
        while charges:
            chgs, charges = charges[:8], charges[8:]
            chgs_str = " ".join( ["%3d %3d" % c for c in chgs])
            lines.append( "M  CHG%3d %s" % (len(chgs), chgs_str) )
        # get radicals
        radicals = [(i+1, a.multiplicity) for i,a in enumerate(self.molecule.atoms) if a.multiplicity]
        while radicals:
            rads, radicals = radicals[:8], radicals[8:]
            rads_str = " ".join( ["%3d %3d" % x for x in rads])
            lines.append( "M  RAD%3d %s" % (len(rads), rads_str) )
        # end of properties
        lines.append("M  END")

        return '\n'.join(lines) + '\n'


    def _get_counts_line(self):
        atoms = len(self.molecule.atoms)
        bonds = len(self.molecule.bonds)
        atom_lists = 0
        fff = 0 # obsolete
        chiral = 0
        stexts = 0
        obsolete = "  0  0  0  0"
        extras = 999
        mol_version = " V2000"
        #         1  2 3 4 5 6 7 8 9
        return "%3d%3d%3d%3d%3d%3d%s%s%s" % (atoms,bonds,atom_lists,fff,chiral,stexts,obsolete,extras,mol_version)


    def _get_atom_line(self, atom):
        # xxxxx.xxxxyyyyy.yyyyzzzzz.zzzz aaaddcccssshhhbbbvvvHHHrrriiimmmnnneee
        # x,y,z are coordinates. aaa=atom symbol, dd=mass diff, ccc=charge
        # sss=atom stereo parity, hhh=hydrogen count, bbb=stereo care, vvv=valence
        x, y, z = atom.pos3d
        symbol = atom.symbol
        mass_diff = 0
        charge = 0# actual charge will be written in properties block
        rest = "  0  0  0  0  0  0  0  0  0  0"
        #            1    2     3     4  5  6 7
        return "%10.4f%10.4f%10.4f %-3s%2d%3d%s" % (x,-y,z,symbol,mass_diff,charge,rest)


    def _get_bond_line(self, bond):
        # 111222tttsssxxxrrrccc
        # 111 = atom1, 222 = atom2, ttt=bond type, sss=bond stereo, xxx=not used
        # rrr=bond topology(ring or chain), ccc=reacting center status
        a1 = self.molecule.atoms.index(bond.atom1) + 1
        a2 = self.molecule.atoms.index(bond.atom2) + 1
        type_remap = {"single": 1, "double": 2, "triple": 3, "delocalized": 4}
        typ = type_remap.get( bond.type, 0)
        stereo_remap = {"wedge": 1, "hashed_wedge": 6}
        stereo = stereo_remap.get( bond.type, 0)
        rest = "  0  0  0"
        #         1  2  3  4 5
        return "%3d%3d%3d%3d%s" % (a1,a2,typ,stereo,rest)

    def read_structure_data(self, f):
        p = re.compile("> .*<(.*)>.*")
        data_dict = {}

        while (line := f.readline()):
            if line.startswith("$$$$"):
                return data_dict
            if (m := p.match(line)):
                field_name = m.group(1)
                data = []
                while (line := f.readline().strip()):
                    data.append(line)
                if len(data)==1:
                    data = data[0]
                if data:
                    data_dict[field_name] = data

# 1,2,3,5,6,7 in atom block denotes +3,+2,+1, -1,-2,-3 charge respectively
# 4 denotes a radical
def read_charge(f):
    val = read_value(f, 3, int)
    return val and (4-val) or 0



def read_value(file, length, convert_func=None):
    """ reads specified number of characters. return None if failed.
    the convert_func converts str to int, float etc types """
    s = file.read( length)
    if len(s)<length:# failed to read
        return
    s = s.strip()
    if s and convert_func:
        return convert_func(s)
    return s
