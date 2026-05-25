# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>

from app_data import Settings

class Page:
    def __init__(self, page_w=None, page_h=None, margins=None, objects=None):
        self.page_w = page_w
        self.page_h = page_h
        self.margins = margins or (0, 0, 0, 0)  # (top, right, bottom, left) in pixels
        self.objects = objects or []

class Document:
    def __init__(self):
        self.page_w = None # in pixel (render_dpi scaled)
        self.page_h = None
        # list of top level objects
        self.objects = []
        # multipage (new): list[Page]
        self.pages = []

    def page_size(self):
        """ Return page size in points (1/72 inch). """
        if self.page_w==None or self.page_h==None:
            return 595, 842
        return self.page_w*72/Settings.render_dpi, self.page_h*72/Settings.render_dpi

    def set_page_size(self, w, h):
        """ w & h are size in point """
        self.page_w = w/72 * Settings.render_dpi
        self.page_h = h/72 * Settings.render_dpi

    def ensure_pages(self):
        """Backward compatibility: if pages are missing, convert single-page fields to pages."""
        if self.pages:
            return
        page = Page(page_w=self.page_w, page_h=self.page_h, margins=(0, 0, 0, 0), objects=self.objects[:])
        self.pages = [page]
