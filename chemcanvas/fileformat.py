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
        self.pages = []

# except ChemDraw, other programs does not support multi page. So it will be removed later
class Page:
    def __init__(self):
        self.width = 595
        self.height = 842
        self.objects = []

#__all__ = ["FileFormat", "Document", "Page"]
