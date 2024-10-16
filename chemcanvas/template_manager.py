# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2022-2024 Arindam Chaudhuri <arindamsoft94@gmail.com>
from fileformat import Ccdx
from app_data import Settings, TEMPLATE_DIRS
import geometry as geo

import os
import math
import operator
from functools import reduce


class TemplateManager:
    def __init__(self):
        self.templates = {}
        self.current = None # current selected template
        # ordered list of template names
        self.basic_templates = [] # basic set
        self.extended_templates = [] # full extended set
        self.user_templates = [] # user defined templates

        for template_dir in TEMPLATE_DIRS:
            files = os.listdir(template_dir)
            files = [ template_dir+"/"+f for f in files if f.endswith(".cctf") ]
            for template_file in files:
                self.readTemplates(template_file)

    def readTemplates(self, filename):
        ccdx_reader = Ccdx()
        doc = ccdx_reader.read(filename)
        if not doc:
            return
        mols = [obj for obj in doc.objects if obj.class_name=="Molecule"]
        for mol in mols:
            if mol.name and mol.template_atom and mol.template_bond:
                self.templates[mol.name] = mol
                self.basic_templates.append(mol.name)


    def getTransformedTemplate(self, coords, place_on="Paper"):
        current = self.current.deepcopy()
        scale_ratio = 1
        trans = geo.Transform()
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
                #find appropriate side of bond to append template to
                atom1, atom2 = current.template_bond.atoms
                atms = atom1.neighbors + atom2.neighbors
                atms = set(atms) - set([atom1,atom2])
                points = [a.pos for a in atms]
                if reduce( operator.add, [geo.line_get_side_of_point( (xt1,yt1,xt2,yt2), xy) for xy in points], 0) < 0:
                    xt1, yt1, xt2, yt2 = xt2, yt2, xt1, yt1
            else:# place_on == "Atom"
                xt1, yt1 = current.template_atom.pos
                xt2, yt2 = current.findPlace(current.template_atom, geo.point_distance(current.template_atom.pos, current.template_atom.neighbors[0].pos))
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

