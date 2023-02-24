from app_data import App
from molecule import Molecule
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
    mol_elms = root.getElementsByTagName("molecule")
    molecules = []
    for mol_elm in mol_elms:
        mol = Molecule()
        mol.readXml(mol_elm)
        molecules.append(mol)
    App.id_to_object_map.clear()
    return molecules



def writeCcml(paper, filename):
    doc = Dom.Document()
    doc.version = "1.0"
    doc.encoding = "UTF-8"
    root = doc.createElement("ccml")
    doc.appendChild(root)
    for obj in paper.objects:
        obj.addToXmlNode(root)
    with io.open(filename, "w", encoding="utf-8") as out_file:
        out_file.write(doc.toprettyxml())

