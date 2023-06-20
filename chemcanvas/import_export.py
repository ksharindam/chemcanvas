# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App
from molecule import Molecule
from arrow import Arrow
from text import Text, Plus

import io
import xml.dom.minidom as Dom

# the native format
def readCcmlFile(filename):
    doc = Dom.parse(filename)
    return readCcmlDom(doc)


def readCcmlDom(doc):
    ccmls = doc.getElementsByTagName("ccml")
    if not ccmls:
        return []
    root = ccmls[0]
    # result
    objects = []
    # read molecules
    elms = root.getElementsByTagName("molecule")
    for elm in elms:
        mol = Molecule()
        mol.readXml(elm)
        objects.append(mol)
    App.id_to_object_map.clear()
    # read arrows
    elms = root.getElementsByTagName("arrow")
    for elm in elms:
        arr = Arrow()
        arr.readXml(elm)
        objects.append(arr)
    # read texts
    elms = root.getElementsByTagName("text")
    for elm in elms:
        text = Text()
        text.readXml(elm)
        objects.append(text)
    # read plus
    elms = root.getElementsByTagName("plus")
    for elm in elms:
        plus = Plus()
        plus.readXml(elm)
        objects.append(plus)
    return objects



def writeCcml(paper, filename):
    doc = Dom.Document()
    doc.version = "1.0"
    doc.encoding = "UTF-8"
    root = doc.createElement("ccml")
    doc.appendChild(root)
    for obj in paper.objects:
        obj.addToXmlNode(root)
    try:
        with io.open(filename, "w", encoding="utf-8") as out_file:
            out_file.write(doc.toprettyxml())
        return True
    except:
        return False
