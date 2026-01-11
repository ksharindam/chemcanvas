# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os
import csv
from PyQt5.QtCore import QStandardPaths
from PyQt5.QtGui import QIcon, QPixmap

# platform.system() can be used to detect "Linux", "Windows" or "Darwin"(MacOS) system

class App:
    """ Stores application wide data """
    window = None
    paper = None # selected current paper
    tool = None # selected current tool
    template_manager = None # created only once
    SRC_DIR = os.path.dirname(__file__)
    DATA_DIR = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/ChemCanvas"
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    dark_mode = False


class Default:
    """ default values for drawing properties.
    includes only those parameters which can be edited by settings dialog """
    atom_font_size = 12# pixel
    bond_length = 24# 0.61cm @100 render_dpi
    bond_width = 1.2
    bond_spacing = 6.0
    electron_dot_size = 2.0 # diameter
    arrow_line_width = 2.0
    arrow_head_dimensions = (5,2,1.5)# (length, width, depth)
    plus_size = 18 # pixel


class Settings:
    """ settings for some properties """
    # these settings below are fixed, and can not be changed
    basic_scale = 1.0# ratio of screen dpi and render dpi
    render_dpi = 100 # resolution at which object on Paper is rendered
    atom_font_name = "Sans Serif"
    coord_head_dimensions = 6, 2.5, 2
    min_arrow_length = 30 # 0.762cm
    text_size = 14 # pixel
    focus_color = (0, 255, 0)# green
    selection_color = (150,150,255)

# initialize Settings with Default values. (subclassing 'Default' class does not work properly)
for key,val in dict(vars(Default)).items():
    if not key.startswith("__"):
        setattr(Settings, key, val)


# colors
basic_colors = [
    "#000000", "#404040", "#6b6b6b", "#808080", "#909090", "#ffffff",
    "#790874", "#f209f1", "#09007c", "#000def", "#047f7d", "#05fef8",
    "#7e0107", "#f00211", "#fff90d", "#07e00d", "#067820", "#827d05",
]

# eye comfort colors
fill_colors = [
    "#000000", "#555555", "#808080", "#999999", "#cccccc", "#ffffff",
    "#d2b7d6", "#f1b7ba", "#c9e4a1", "#add8b7", "#f9da98", "#f7cd6f",
    "#d06ead", "#e672a0", "#8ac381", "#63b4c2", "#f19d46", "#ef924f",
    "#cc3776", "#b53387", "#55a05d", "#437fb4", "#cb662b", "#de4b32",
    "#8c1b43", "#701873", "#2b663c", "#26378f", "#8e3b18", "#ae232d"
]

# do not invert color of these icons in dark mode
non_invertible_icons = [":/icons/color"]

def get_icon(icon_name):
    """ get icon from resources, and invert color in dark mode """
    icon = QIcon(icon_name)
    if icon.isNull() or not App.dark_mode or icon_name in non_invertible_icons:
        return icon
    img = icon.pixmap(icon.availableSizes()[0]).toImage()
    img.invertPixels()
    return QIcon(QPixmap.fromImage(img))



periodic_table = {}

with open(App.SRC_DIR + "/periodic_table.csv") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        elm_dict = {
            "atomic_num": int(row['AtomicNumber']),
            "weight": float(row['AtomicMass']),
            "valency": row["Valency"] and tuple(map(int, row["Valency"].split(","))) or (),
            "isotopes": row["Isotopes"] and tuple(map(int, row["Isotopes"].split(","))) or (),
        }
        periodic_table[row["Symbol"]] = elm_dict

def atomic_num_to_symbol(atomic_num):
    try:
        return list(periodic_table.keys())[atomic_num-1]
    except:
        raise ValueError("Invalid atomic number %s" % str(atomic_num))


auto_hydrogen_elements = {"B", "C","Si", "N","P","As", "O","S", "F","Cl","Br","I"}
