from atom import Atom
from bond import Bond

global molecule_id_no
molecule_id_no = 1

class Molecule:
    def __init__(self, paper):
        self.paper = paper
        self.atoms = []
        self.bonds = []
        global molecule_id_no
        self.id = 'molecule' + str(molecule_id_no)
        molecule_id_no += 1

    def newAtom(self, pos):
        atom = Atom(self, pos)
        self.atoms.append(atom)
        return atom

    def newBond(self, atom1, atom2):
        bond = Bond(atom1, atom2)
        self.bonds.append(bond)
        return bond
