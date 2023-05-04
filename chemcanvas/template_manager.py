# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>
from import_export import readCcmlFile
from geometry import Transform, point_distance
from app_data import Settings
import math

class TemplateManager:
    def __init__(self):
        self.templates = {}
        self.template_names = []
        self.current = None
        self.readTemplates("templates.xml")

    def readTemplates(self, filename):
        objects = readCcmlFile(filename)
        mols = [obj for obj in objects if obj.object_type=="Molecule"]
        for mol in mols:
            if mol.name and mol.template_atom and mol.template_bond:
                self.templates[mol.name] = mol
                self.template_names.append(mol.name)


    def getTransformedTemplate(self, coords, place_on="Paper"):
        current = self.current.deepcopy()
        scale_ratio = 1
        trans = Transform()
        # just place the template on paper
        if place_on == "Paper":
            xt1, yt1 = current.template_atom.pos
            xt2, yt2 = current.template_atom.neighbors[0].pos
            scale_ratio = Settings.bond_length / math.sqrt( (xt1-xt2)**2 + (yt1-yt2)**2)
            trans.translate( -xt1, -yt1)
            trans.scale(scale_ratio)
            trans.translate( coords[0], coords[1])
        else:
            if place_on == "Bond":
                xt1, yt1 = current.template_bond.atom1.pos
                xt2, yt2 = current.template_bond.atom2.pos
            else:# place_on == "Atom"
                xt1, yt1 = current.template_atom.pos
                xt2, yt2 = current.findPlace(current.template_atom, point_distance(current.template_atom.pos, current.template_atom.neighbors[0].pos))
            x1, y1, x2, y2 = coords
            scale_ratio = math.sqrt( ((x1-x2)**2 + (y1-y2)**2) / ((xt1-xt2)**2 + (yt1-yt2)**2) )
            trans.translate( -xt1, -yt1)
            trans.rotate( math.atan2( xt1-xt2, yt1-yt2) - math.atan2( x1-x2, y1-y2))
            trans.scale(scale_ratio)
            trans.translate(x1, y1)

        for a in current.atoms:
            a.x, a.y = trans.transform(a.x, a.y)
            #a.scale_font( scale_ratio)
        #for b in current.bonds:
        #    if b.order != 1:
        #        b.second_line_distance *= scale_ratio
        # update template according to current default values
        #App.paper.applyDefaultProperties( [temp], template_mode=1)
        return current

    def selectTemplate(self, name):
        self.current = self.templates[name]

    def getTemplateValency(self):
        return self.current.template_atom.occupied_valency

