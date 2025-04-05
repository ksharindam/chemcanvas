# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os
import csv
from PyQt5.QtCore import QStandardPaths


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


class Settings:
    """ default values for some properties """
    basic_scale = 1.0# ratio of screen dpi and render dpi
    render_dpi = 100 # resolution at which object on Paper is rendered
    atom_font_name = "Sans Serif"
    atom_font_size = 12# pixel
    bond_length = 24# 0.61cm @100 render_dpi
    bond_spacing = 6
    plus_size = 18 # pixel
    text_size = 14 # pixel
    min_arrow_length = 30 # 0.762cm
    mark_size = 4
    arrow_line_width = 2
    arrow_head_dimensions = (10,4,3)# (length, width, depth)
    fishhook_head_dimensions = 6, 2.5, 2
    focus_color = (0, 255, 0)# green
    selection_color = (150,150,255)




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
