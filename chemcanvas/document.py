# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>

from app_data import Settings

class Document:
    """ This provides an interface for file format handlers. file format
    handlers can read file and output a Document containing objects. Or can take
    Document and write a file format into disk.
    After reading a file, coordinates of all objects must be in pixel unit @ render dpi.
    And page size also must be converted to pixel unit.
    """
    def __init__(self):
        # cdxml format uses point as coordinate unit
        self.page_size = (None, None) # in pixel
        self.pages = [] # list of Page class

    @property
    def has_page_size(self):
        return not (None in self.page_size)

    @property
    def pages_count(self):
        return len(self.pages)

    @property
    def page_size_pt(self):
        w = self.page_size[0]*72/Settings.render_dpi
        h = self.page_size[1]*72/Settings.render_dpi
        return (w, h)

    def set_page_size_pt(self, w_pt, h_pt):
        page_w = int(round(w_pt*Settings.render_dpi/72))
        page_h = int(round(h_pt*Settings.render_dpi/72))
        self.page_size = (page_w, page_h)

    def set_pages_count(self, num):
        self.pages = [Page(self) for i in range(num)]

    def add_new_page(self):
        self.pages.append(Page(self))
        return self.pages[-1]



class Page:
    def __init__(self, doc):
        self.doc = doc # parent Document object
        # list of top level objects
        self.objects = []
        self.pos = (0,0)

    @property
    def page_size_pt(self):
        return self.doc.page_size_pt
