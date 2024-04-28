# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>

# this module should handle loading of all fileformat plugins

# FileFormat class should contain error message, if failed to load
# It should contain the list of supported formats and file extension data
import os
import operator
from functools import reduce

class FileFormat:
    readable_formats = []# a list of (filetype, extension) tuple
    writable_formats = []# if empty, it does not support writing

    def read(self, filename):
        """ returns a Document or None (if failed) """
        return None

    def write(self, doc, filename):
        """ writes the passed Document """
        pass

class Document:
    def __init__(self):
        self.page_w = 595
        self.page_h = 842
        # list of top level objects
        self.objects = []


from fileformat_ccdx import Ccdx
from fileformat_molfile import Molfile
from fileformat_cdxml import CDXML

format_classes = [Ccdx, CDXML, Molfile]

readable_formats = reduce(operator.add, [c.readable_formats for c in format_classes], [])
writable_formats = reduce(operator.add, [c.writable_formats for c in format_classes], [])



def get_read_filters():
    """ create a file filter compatible with QFileDialog.
    first filter contains all supported extensions """
    filters = ["%s (*.%s)" % x for x in readable_formats]
    all_exts = " ".join(["*.%s"%x[1] for x in readable_formats])
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
            if _ext==ext:
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
