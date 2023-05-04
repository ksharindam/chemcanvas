# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <ksharindam@gmail.com>
import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class App:
    """ Stores application wide data """
    paper = None # selected current paper
    tool = None # selected current tool
    id_manager = None
    template_manager = None # created only once
    id_to_object_map = {}

class Settings:
    """ default values for some properties """
    bond_length = 36
    bond_width = 4
    plus_size = 14
    arrow_length = 60
    min_arrow_length = 40
    mark_size = 4
    focus_color = Qt.green
    selection_color = QColor(150,150,255)#Qt.blue



src_dir = os.path.dirname(__file__)
icon_dirs = [src_dir + "/../data/icons",
            src_dir + "/../data/icons/templates",
]

def find_icon(icon_name):
    """ find and return full path of an icon file. returns empty string if not found """
    for icon_dir in icon_dirs:
        icon_path = icon_dir + "/" + icon_name + ".png"
        if os.path.exists(icon_path):
            return icon_path
    return ""


periodic_table = {
"H"  : {"atomic_num":   1, "weight":   1.0079, "en": 2.10, "els":  1, "valency": (1,)},
"He" : {"atomic_num":   2, "weight":   4.0026, "en": 0.00, "els":  8, "valency": (0, 2)},
"Li" : {"atomic_num":   3, "weight":   6.9410, "en": 0.98, "els":  1, "valency": (1,)},
"Be" : {"atomic_num":   4, "weight":   9.0122, "en": 1.57, "els":  2, "valency": (2,)},
"B"  : {"atomic_num":   5, "weight":  10.8110, "en": 2.04, "els":  3, "valency": (3,)},
"C"  : {"atomic_num":   6, "weight":  12.0107, "en": 2.55, "els":  4, "valency": (4, 2)},
"N"  : {"atomic_num":   7, "weight":  14.0067, "en": 3.04, "els":  5, "valency": (3, 5)},
"O"  : {"atomic_num":   8, "weight":  15.9994, "en": 3.44, "els":  6, "valency": (2,)},
"F"  : {"atomic_num":   9, "weight":  18.9984, "en": 3.98, "els":  7, "valency": (1,)},
"Ne" : {"atomic_num":  10, "weight":  20.1797, "en": 0.00, "els":  8, "valency": (0, 2)},
"Na" : {"atomic_num":  11, "weight":  22.9898, "en": 0.93, "els":  1, "valency": (1,)},
"Mg" : {"atomic_num":  12, "weight":  24.3050, "en": 1.31, "els":  2, "valency": (2,)},
"Al" : {"atomic_num":  13, "weight":  26.9815, "en": 1.61, "els":  3, "valency": (3,)},
"Si" : {"atomic_num":  14, "weight":  28.0855, "en": 1.91, "els":  4, "valency": (4,)},
"P"  : {"atomic_num":  15, "weight":  30.9738, "en": 2.19, "els":  5, "valency": (3, 5)},
"S"  : {"atomic_num":  16, "weight":  32.0650, "en": 2.58, "els":  6, "valency": (2, 4, 6)},
"Cl" : {"atomic_num":  17, "weight":  35.4530, "en": 3.16, "els":  7, "valency": (1, 3, 5, 7)},
"Ar" : {"atomic_num":  18, "weight":  39.9480, "en": 0.00, "els":  8, "valency": (0, 2)},
"K"  : {"atomic_num":  19, "weight":  39.0983, "en": 0.82, "els":  1, "valency": (1,)},
"Ca" : {"atomic_num":  20, "weight":  40.0780, "en": 1.00, "els":  2, "valency": (2,)},
"Sc" : {"atomic_num":  21, "weight":  44.9559, "en": 1.36, "els":  3, "valency": (3, 1)},
"Ti" : {"atomic_num":  22, "weight":  47.8670, "en": 1.54, "els":  4, "valency": (4, 3)},
"V"  : {"atomic_num":  23, "weight":  50.9415, "en": 1.63, "els":  5, "valency": (2, 4, 5)},
"Cr" : {"atomic_num":  24, "weight":  51.9961, "en": 1.66, "els":  6, "valency": (2, 3, 6)},
"Mn" : {"atomic_num":  25, "weight":  54.9380, "en": 1.55, "els":  7, "valency": (2, 3, 4, 6, 7)},
"Fe" : {"atomic_num":  26, "weight":  55.8450, "en": 1.83, "els":  8, "valency": (0, 2, 3)},
"Co" : {"atomic_num":  27, "weight":  58.9332, "en": 1.88, "els":  8, "valency": (2, 3)},
"Ni" : {"atomic_num":  28, "weight":  58.6934, "en": 1.91, "els":  8, "valency": (2, 3)},
"Cu" : {"atomic_num":  29, "weight":  63.5460, "en": 1.90, "els":  1, "valency": (0, 1, 2)},
"Zn" : {"atomic_num":  30, "weight":  65.3900, "en": 1.65, "els":  2, "valency": (2,)},
"Ga" : {"atomic_num":  31, "weight":  69.7230, "en": 1.81, "els":  3, "valency": (3,)},
"Ge" : {"atomic_num":  32, "weight":  72.6400, "en": 2.01, "els":  4, "valency": (4,)},
"As" : {"atomic_num":  33, "weight":  74.9216, "en": 2.18, "els":  5, "valency": (3, 5)},
"Se" : {"atomic_num":  34, "weight":  78.9600, "en": 2.55, "els":  6, "valency": (2, 4, 6)},
"Br" : {"atomic_num":  35, "weight":  79.9040, "en": 2.96, "els":  7, "valency": (1, 3, 5)},
"Kr" : {"atomic_num":  36, "weight":  83.8000, "en": 0.00, "els":  8, "valency": (0, 2)},
"Rb" : {"atomic_num":  37, "weight":  85.4678, "en": 0.82, "els":  1, "valency": (1,)},
"Sr" : {"atomic_num":  38, "weight":  87.6200, "en": 0.95, "els":  2, "valency": (2,)},
"Y"  : {"atomic_num":  39, "weight":  88.9059, "en": 1.22, "els":  3, "valency": (3,)},
"Zr" : {"atomic_num":  40, "weight":  91.2240, "en": 1.33, "els":  4, "valency": (4,)},
"Nb" : {"atomic_num":  41, "weight":  92.9064, "en": 1.60, "els":  5, "valency": (3, 5)},
"Mo" : {"atomic_num":  42, "weight":  95.9400, "en": 2.16, "els":  6, "valency": (3, 5, 6)},
"Tc" : {"atomic_num":  43, "weight":  98.9063, "en": 1.90, "els":  7, "valency": (5, 7)},
"Ru" : {"atomic_num":  44, "weight": 101.0700, "en": 2.20, "els":  8, "valency": (3, 4, 6, 8)},
"Rh" : {"atomic_num":  45, "weight": 102.9055, "en": 2.28, "els":  8, "valency": (3, 4)},
"Pd" : {"atomic_num":  46, "weight": 106.4200, "en": 2.20, "els":  8, "valency": (2, 4)},
"Ag" : {"atomic_num":  47, "weight": 107.8682, "en": 1.93, "els":  1, "valency": (1,)},
"Cd" : {"atomic_num":  48, "weight": 112.4110, "en": 1.69, "els":  2, "valency": (2,)},
"In" : {"atomic_num":  49, "weight": 114.8180, "en": 1.78, "els":  3, "valency": (3,)},
"Sn" : {"atomic_num":  50, "weight": 118.7100, "en": 1.96, "els":  4, "valency": (2, 4)},
"Sb" : {"atomic_num":  51, "weight": 121.7600, "en": 2.05, "els":  5, "valency": (3, 5)},
"Te" : {"atomic_num":  52, "weight": 127.6000, "en": 2.10, "els":  6, "valency": (2, 4, 6)},
"I"  : {"atomic_num":  53, "weight": 126.9045, "en": 2.66, "els":  7, "valency": (1, 3, 5, 7)},
"Xe" : {"atomic_num":  54, "weight": 131.2930, "en": 2.60, "els":  8, "valency": (0, 2)},
"Cs" : {"atomic_num":  55, "weight": 132.9055, "en": 0.79, "els":  1, "valency": (1,)},
"Ba" : {"atomic_num":  56, "weight": 137.2370, "en": 0.89, "els":  2, "valency": (2,)},
"La" : {"atomic_num":  57, "weight": 138.9055, "en": 1.10, "els":  3, "valency": (3,)},
"Hf" : {"atomic_num":  72, "weight": 178.4900, "en": 1.30, "els":  4, "valency": (4,)},
"Ta" : {"atomic_num":  73, "weight": 180.9479, "en": 1.50, "els":  5, "valency": (5,)},
"W"  : {"atomic_num":  74, "weight": 183.8400, "en": 2.36, "els":  6, "valency": (6,)},
"Re" : {"atomic_num":  75, "weight": 186.2070, "en": 1.90, "els":  7, "valency": (7,)},
"Os" : {"atomic_num":  76, "weight": 190.2300, "en": 2.20, "els":  8, "valency": (4, 6, 8)},
"Ir" : {"atomic_num":  77, "weight": 192.2170, "en": 2.20, "els":  8, "valency": (3, 4, 6)},
"Pt" : {"atomic_num":  78, "weight": 195.0780, "en": 2.28, "els":  8, "valency": (2, 4)},
"Au" : {"atomic_num":  79, "weight": 196.9665, "en": 2.54, "els":  1, "valency": (1, 3)},
"Hg" : {"atomic_num":  80, "weight": 200.5900, "en": 2.00, "els":  2, "valency": (1, 2)},
"Tl" : {"atomic_num":  81, "weight": 204.3833, "en": 2.04, "els":  3, "valency": (1, 3)},
"Pb" : {"atomic_num":  82, "weight": 207.2000, "en": 2.33, "els":  4, "valency": (2, 4)},
"Bi" : {"atomic_num":  83, "weight": 208.9804, "en": 2.02, "els":  5, "valency": (3, 5)},
"Po" : {"atomic_num":  84, "weight": 208.9824, "en": 2.00, "els":  6, "valency": (2, 4, 6)},
"At" : {"atomic_num":  85, "weight": 209.9871, "en": 2.20, "els":  7, "valency": (1, 7)},
"Rn" : {"atomic_num":  86, "weight": 222.0176, "en": 0.00, "els":  8, "valency": (0, 2)},
"Ra" : {"atomic_num":  88, "weight": 226.0254, "en": 0.90, "els":  2, "valency": (2,)},
"U"  : {"atomic_num":  92, "weight": 238.0289, "en": 1.38, "els":  6, "valency": (3, 4, 5, 6)},
"X": {'atomic_num': 300, 'query': True, 'key': '"X"', 'weight': 0, 'valency': (1,)},          # halogen
"Q": {'atomic_num': 301, 'query': True, 'key': '"Q"', 'weight': 0, 'valency': (1, 2, 3, 4)},  # anything not H or C
"A": {'atomic_num': 302, 'query': True, 'key': '"A"', 'weight': 0, 'valency': (1, 2, 3, 4)},  # anything not H
"R": {'atomic_num': 303, 'query': True, 'key': '"R"', 'weight': 0, 'valency': (1, 2, 3, 4)},  # anything
}
