# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2024 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os
import csv


class App:
    """ Stores application wide data """
    window = None
    paper = None # selected current paper
    tool = None # selected current tool
    template_manager = None # created only once

class Settings:
    """ default values for some properties """
    render_dpi = 100 # resolution at which object on Paper is rendered
    atom_font_name = "Sans Serif"
    atom_font_size = 12# pixel
    bond_length = 32
    bond_spacing = 6
    plus_size = 18 # pixel
    text_size = 14 # pixel
    min_arrow_length = 30
    mark_size = 4
    arrow_line_width = 2
    arrow_head_dimensions = (10,4,3)# (length, width, depth)
    fishhook_head_dimensions = 6, 2.5, 2
    focus_color = (0, 255, 0)# green
    selection_color = (150,150,255)


SRC_DIR = os.path.dirname(__file__)

# TODO : use platform.system() to detect "Linux", "Windows" or "Darwin"(MacOS) system
DATA_DIR = os.path.expanduser("~/.local/share/chemcanvas")

TEMPLATE_DIRS = [SRC_DIR + "/templates"]

user_template_dir =  DATA_DIR + "/templates"
if os.path.exists(user_template_dir):
    TEMPLATE_DIRS.append(user_template_dir)

def find_template_icon(icon_name):
    """ find and return full path of an icon file. returns empty string if not found """
    for template_dir in TEMPLATE_DIRS:
        icon_path = template_dir + "/" + icon_name + ".png"
        if os.path.exists(icon_path):
            return icon_path
    return ""


periodic_table = {}

with open(SRC_DIR + "/periodic_table.csv") as csvfile:
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
