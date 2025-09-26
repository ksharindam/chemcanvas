# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
import io
from xml.dom import minidom

from app_data import App, Settings
from fileformat import *
from fileformat_ccdx import Ccdx



class Svg(FileFormat):
    """ for read-write of editable svg file """
    readable_formats = [("SVG (editable)", "svg")]
    writable_formats = [("SVG (editable)", "svg")]

    def read(self, filename):
        self.reset_status()
        dom_doc = minidom.parse(filename)
        # read root element
        svgs = dom_doc.getElementsByTagName("svg")
        if not svgs:
            self.message = "File has no svg element !"
            return
        ccdxs = svgs[0].getElementsByTagName("ccdx")
        if not ccdxs:
            self.message = "This is not an editable Svg.\nIt has no structure data !"
            return
        self.doc = Document()
        try:
            ccdx = Ccdx()
            ccdx.reset()
            ccdx.coord_multiplier = Settings.render_dpi/72# point to px conversion factor
            ccdx.doc = Document()
            ccdx.readCcdx(ccdxs[0])
            self.status = "ok"
            return ccdx.doc.objects and ccdx.doc or None
        except FileError as e:
            self.message = str(e)
            return


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
        self.reset_status()
        try:
            # generate svg string
            svg = App.paper.getSvg()
            # generate ccdx string
            ccdx = Ccdx()
            ccdx_string = ccdx.generate_string(doc)
            # insert ccdx into svg
            pos = ccdx_string.find("<ccdx")
            output = svg[:-6] + ccdx_string[pos:] + "</svg>"
            self.status = "ok"
            return output
        except FileError as e:
            self.message = str(e)
            return
