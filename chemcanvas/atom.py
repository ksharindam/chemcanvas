from PyQt5.QtCore import Qt, QLineF
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsLineItem

global atom_id_no
atom_id_no = 1

class Atom:
    def __init__(self, molecule, pos):
        self.molecule = molecule
        self.pos = pos
        self.element = 'C'
        self.show_hydrogens = False
        self.is_group = False
        self.group_text = ''
        global atom_id_no
        self.id = 'atom' + str(atom_id_no)
        atom_id_no += 1
        # drawing related
        self.graphics_item = None

    def graphicsItem(self):
        if not self.graphics_item: # Draw a point
            self.graphics_item = QGraphicsLineItem(QLineF(self.pos, self.pos))
        return self.graphics_item

    def setFocus(self, focus):
        if focus:
            pen = QPen(Qt.black, 5)
            self.graphics_item.setPen(pen)
        else:
            self.graphics_item.setPen(Qt.black)
