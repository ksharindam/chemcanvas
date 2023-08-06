# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>
from app_data import App
from molecule import Molecule
from arrow import Arrow
from bracket import Bracket
from text import Text, Plus

import io
import xml.dom.minidom as Dom

# the native format
def readCcmlFile(filename):
    doc = Dom.parse(filename)
    return readCcmlDom(doc)


tagname_to_class = {
    "molecule": Molecule,
    "arrow": Arrow,
    "plus": Plus,
    "text": Text,
    "bracket": Bracket,
}

def readCcmlDom(doc):
    ccmls = doc.getElementsByTagName("ccml")
    if not ccmls:
        return []
    root = ccmls[0]
    # result
    objects = []
    # read objects
    for tagname in ("molecule", "arrow", "plus", "text", "bracket"):
        elms = root.getElementsByTagName(tagname)
        for elm in elms:
            obj = tagname_to_class[tagname]()
            obj.readXml(elm)
            objects.append(obj)
    App.id_to_object_map.clear()
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
