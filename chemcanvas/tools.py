
from app_data import App
from atom import Atom
from bond import Bond
from geometry import *
#import common

class Tool:
    modes = []
    selected_modes = []

    def __init__(self):
        pass

    def onMousePress(self, pos):
        pass
    def onMouseRelease(self, pos):
        pass
    def onMouseMove(self, pos):
        pass

    def clear(self):
        pass

    def selected_mode(self, index):
        return self.modes[index][self.selected_modes[index]]


class MoveTool(Tool):
    """ Selection or Move tool . Used to select or move molecules, atoms, bonds etc """
    def __init__(self):
        Tool.__init__(self)


class BondTool(Tool):
    modes = [['30', '18', '1'],
            ['normal', 'double', 'triple', 'wedge_near', 'wedge_far', 'dashed', 'dotted']]
    selected_modes = [0, 0]

    def __init__(self):
        Tool.__init__(self)
        self.clear()
        #print("created BondTool")

    def clear(self):
        self.atom1 = None
        self.atom2 = None
        self.bond = None

    def selectMode(self, index):
        for mode_index, mode in enumerate(self.modes):
            if index<len(mode):
                break
            index -= len(mode)
        self.selected_modes[mode_index] = index


    def onMousePress(self, pos):
        #print("click : x=%i, y=%i"%(pos.x(), pos.y()))
        if not App.paper.focused_obj:
            mol = App.paper.newMolecule()
            self.atom1 = mol.newAtom(pos)
            self.atom1.draw()
            App.paper.addDrawable(self.atom1)
        elif type(App.paper.focused_obj) is Atom:
            # we have clicked on existing atom, use this atom to make new bond
            self.atom1 = App.paper.focused_obj


    def onMouseMove(self, pos):
        if not App.paper.dragging:
            return
        if pos == App.paper.mouse_press_pos:
            return
        if not self.atom1: # in case we have clicked on object other than atom
            return
        angle = int(self.selected_mode(0))
        atom2_pos = point_on_circle( self.atom1.pos, App.bond_length, pos, angle)
        # we are clicking and dragging mouse
        if not self.atom2:
            self.atom2 = self.atom1.molecule.newAtom(atom2_pos)
            self.bond = self.atom1.molecule.newBond(self.atom1, self.atom2, self.selected_mode(1))
            self.atom2.draw()
            self.bond.draw()
        else: # move atom2
            if type(App.paper.focused_obj) is Atom and App.paper.focused_obj is not self.atom1:
                self.atom2.moveTo(App.paper.focused_obj.pos)
            else:
                self.atom2.moveTo(atom2_pos)


    def onMouseRelease(self, pos):
        #print("reliz : x=%i, y=%i"%(pos.x(), pos.y()))
        if not App.paper.dragging:
            self.onMouseClick(pos)
            return
        #print("mouse dragged")
        if not self.atom2:
            return
        touched_atom = App.paper.touchedAtom(self.atom2)
        if touched_atom:
            touched_atom.merge(self.atom2)
            self.atom2 = touched_atom
            self.bond.draw()
            reposition_bonds_around_atom(touched_atom)
        else:
            # we are using newly created atom2
            App.paper.addDrawable(self.atom2)

        App.paper.addDrawable(self.bond)
        reposition_bonds_around_atom(self.atom1)
        self.clear()

    def onMouseClick(self, pos):
        print("onMouseClick()")
        if type(App.paper.focused_obj) is Bond:
            # change bond type or bond order
            return
        elif self.atom1:
            self.atom2, self.bond = self.atom1.molecule.addAtomTo(self.atom1)
            self.bond.type = self.selected_mode(1)
            self.atom2.draw()
            App.paper.addDrawable(self.atom2)
            self.bond.draw()
            App.paper.addDrawable(self.bond)
        self.clear()

def reposition_bonds_around_atom(atom):
    bonds = atom.neighbor_edges
    [bond.redraw() for bond in bonds]
    #if isinstance( atom, textatom) or isinstance( atom, Atom):
    #    atom.reposition_marks()

def reposition_bonds_around_bond(bond):
    bonds = common.filter_unique( bond.atom1.neighbor_edges + bond.atom2.neighbor_edges)
    [b.redraw() for b in bonds if b.order == 2]
    # all atoms to update
    #atms = common.filter_unique( reduce( operator.add, [[b.atom1,b.atom2] for b in bs], []))
    #[a.reposition_marks() for a in atms if isinstance( a, Atom)]



class AtomTool(Tool):
    def __init__(self):
        Tool.__init__(self)



tools_class_dict = {
    "move" : MoveTool,
    "bond" : BondTool,
    "atom" : AtomTool
}

def newToolFromName(name):
    return tools_class_dict[name]()


tools_template = [
# name   title          icon    subtools
    ("move", "Move",      ":/icons/move.png", ()),
    ("bond", "Draw Bond", ":/icons/bond.png", (
            [("30", "30 degree", ":/icons/30.png"),
            ("18", "18 degree", ":/icons/18.png"),
            ("1", "1 degree", ":/icons/1.png")],
            [("normal", "Single Bond", ":/icons/single.png"),
            ("double", "Double Bond", ":/icons/double.png"),
            ("triple", "Triple Bond", ":/icons/triple.png")]
    )),
    ("atom", "Draw Atom", ":/icons/atom.png", ())
]



# list of tool names
tools_list = [x[0] for x in tools_template]


