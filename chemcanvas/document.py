# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>

from app_data import Settings

class Document:
    def __init__(self):
        self.page_w = None # or pixel
        self.page_h = None
        # list of top level objects
        self.objects = []

    def page_size(self):
        if self.page_w==None or self.page_h==None:
            return 595, 842
        return self.page_w*72/Settings.render_dpi, self.page_h*72/Settings.render_dpi

    def set_page_size(self, w, h):
        """ w & h are size in point """
        self.page_w = w/72 * Settings.render_dpi
        self.page_h = h/72 * Settings.render_dpi
