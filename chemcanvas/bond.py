from PyQt5.QtCore import Qt, QLineF
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsLineItem

global bond_id_no
bond_id_no = 1

class Bond:
    bond_types = ["normal", "coordinate", "wedge_near", "wedge_far", "aromatic", "delocalized"]

    def __init__(self, atom1, atom2, multiplicity=1, bond_type='normal'):
        self.molecule = atom1.molecule
        self.atom1 = atom1
        self.atom2 = atom2
        self.multiplicity = multiplicity
        self.type = bond_type
        global bond_id_no
        self.id = 'bond' + str(bond_id_no)
        bond_id_no += 1
        # drawing related
        self.graphics_item = None

    def graphicsItem(self):
        if not self.graphics_item:
            self.graphics_item = QGraphicsLineItem(QLineF(self.atom1.pos, self.atom2.pos))
        #print("line : (%i,%i) to (%i,%i)" % (self.atom1.pos.x(), self.atom1.pos.y(), self.atom2.pos.x(), self.atom2.pos.y()))
        return self.graphics_item

    def setFocus(self, focus):
        if focus:
            pen = QPen(Qt.black, 3)
            self.graphics_item.setPen(pen)
        else:
            self.graphics_item.setPen(Qt.black)
