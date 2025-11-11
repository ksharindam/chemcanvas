# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>

# this module should handle loading of all fileformat plugins

# FileFormat class should contain error message, if failed to load
# It should contain the list of supported formats and file extension data

import os
import operator
from functools import reduce

from fileformat_ccdx import Ccdx
from fileformat_molfile import Molfile
from fileformat_cdxml import CDXML
from fileformat_mrv import MRV
from fileformat_smiles import Smiles
from fileformat_svg import Svg

format_classes = [Ccdx, Svg, CDXML, MRV, Molfile, Smiles]

readable_formats = reduce(operator.add, [c.readable_formats for c in format_classes], [])
writable_formats = reduce(operator.add, [c.writable_formats for c in format_classes], [])



def get_read_filters():
    """ create a file filter compatible with QFileDialog.
    first filter contains all supported extensions """
    readables = [(x[0], " *.".join(x[1].split(","))) for x in readable_formats]
    filters = ["%s (*.%s)" % x for x in readables]
    all_exts = " ".join(["*.%s"%x[1] for x in readables])
    filters.insert(0, "All Supported (%s)" % all_exts)
    return ";;".join(filters)

def get_write_filters():
    """ create a file filter compatible with QFileDialog """
    filters = ["%s (*.%s)" % x for x in writable_formats]
    return ";;".join(filters)

def create_file_reader(filename):
    """ create file reader from file extension """
    name, ext = os.path.splitext(filename)
    ext = ext.strip(".")
    for cls in format_classes:
        for filetype, _ext in cls.readable_formats:
            if ext in _ext.split(","):
                return cls()

def create_file_writer(filename):
    """ create file writer from file extension """
    name, ext = os.path.splitext(filename)
    ext = ext.strip(".")
    for cls in format_classes:
        for filetype, _ext in cls.writable_formats:
            if _ext==ext:
                return cls()

def choose_filter(filters, filename):
    """ get the filter which matches filename extension """
    name, ext = os.path.splitext(filename)
    filters = filters.split(";;")
    for filtr in filters:
        if filtr.endswith("(*%s)"%ext):
            return filtr
