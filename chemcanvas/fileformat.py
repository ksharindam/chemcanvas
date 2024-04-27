# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>

# this module should handle loading of all fileformat plugins

# FileFormat class should contain error message, if failed to load
# It should contain the list of supported formats and file extension data

class FileFormat:
    can_read = False
    can_write = False

    def __init__(self):
        pass

    def read(self, filename):
        """ returns a document or None (if failed) """
        return None

    def write(self, doc, filename):
        """ writes the passed document """
        pass

class Document:
    def __init__(self):
        self.page_w = 595
        self.page_h = 842
        # list of top level objects
        self.objects = []


#__all__ = ["FileFormat", "Document", "Page"]
