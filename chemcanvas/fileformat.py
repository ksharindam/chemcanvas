# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2024-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>

# import these objects here, so that fileformat plugins dont need to import them
from molecule import Molecule
from atom import Atom
from bond import Bond
from marks import Charge, Electron
from document import Document

class FileFormat:
    readable_formats = []# a list of (filetype, extension) tuple
    writable_formats = []# if empty, it does not support writing

    def reset_status(self):
        """ resets status end error message. all subclass must call this before read/write """
        self.status = "failed" # values are "ok" | "warning" | "failed"
        self.message = ""

    def read(self, filename):
        """ returns a Document or None (if failed) """
        return None

    def write(self, doc, filename):
        """ writes the passed Document """
        pass


class FileError(RuntimeError):
    def __init__(self, message="FileError !"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"FileError: {self.message}"
