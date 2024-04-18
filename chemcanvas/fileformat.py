# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024 Arindam Chaudhuri <arindamsoft94@gmail.com>

class FileFormat:
    can_read = False
    can_write = False

    def __init__(self):
        pass

    def read(self):
        """ returns a document or a molecule """
        return []

    def write(self):
        """ writes the passed document """
        pass

class Document:
    def __init__(self):
        self.pages = []

class Page:
    def __init__(self):
        self.width = 595
        self.height = 842
        self.objects = []

#__all__ = ["FileFormat", "Document", "Page"]
