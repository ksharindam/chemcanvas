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
        self.page_w = None # or pixel
        self.page_h = None
        self.pages = [Page()] # list of Page class

    @property
    def objects(self):
        """ for legacy support. TODO : remove when ccdx is ready """
        return self.pages[0].objects

    @property
    def pages_count(self):
        return len(self.pages)

    def page_size(self):
        """ return page size in points """
        if self.page_w==None or self.page_h==None:
            return 595, 842
        return self.page_w*72/Settings.render_dpi, self.page_h*72/Settings.render_dpi

    def set_page_size(self, w, h):
        """ w & h are size in point """
        self.page_w = w/72 * Settings.render_dpi
        self.page_h = h/72 * Settings.render_dpi

    def set_pages_count(self, num):
        self.pages = [Page()] * num

    def add_new_page(self):
        self.pages.append(Page())


class Page:
    def __init__(self):
        # list of top level objects
        self.objects = []
