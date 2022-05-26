
class Tool:
    def __init__(self):
        self.paper = None

    def setPaper(self, paper):
        self.paper = paper

    def onMousePress(self, pos):
        pass
    def onMouseRelease(self, pos):
        pass
    def onMouseMove(self, pos):
        pass


class MoveTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        print("created MoveTool")


class BondTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        self.clear()
        #print("created BondTool")

    def onMousePress(self, pos):
        print("click : x=%i, y=%i"%(pos.x(), pos.y()))
        mol = self.paper.newMolecule()
        self.atom1 = mol.newAtom(pos)
        self.paper.addDrawable(self.atom1)
        self.atom1.graphics_item.setZValue(1)

    def onMouseMove(self, pos):
        if not self.paper.mouse_pressed:
            return
        # we are clicking and dragging mouse
        if not self.atom2:
            self.atom2 = self.atom1.molecule.newAtom(pos)
        else: # move atom2
            self.atom2.pos = pos

    def onMouseRelease(self, pos):
        print("reliz : x=%i, y=%i"%(pos.x(), pos.y()))
        if self.atom2:
            bond = self.atom1.molecule.newBond(self.atom1, self.atom2)
            self.paper.addDrawable(bond)
            self.paper.addDrawable(self.atom2)
        self.clear()

    def clear(self):
        self.atom1 = None
        self.atom2 = None


class AtomTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        print("created AtomTool")

tools_class_dict = {
    "move" : MoveTool,
    "bond" : BondTool,
    "atom" : AtomTool
}

def newToolFromName(name):
    return tools_class_dict[name]()


tools_template = [
# name   title          icon
    ("move", "Move",      ":/icons/move.png"),
    ("bond", "Draw Bond", ":/icons/bond.png"),
    ("atom", "Draw Atom", ":/icons/atom.png")
]

# list of tool names
tools_list = [x[0] for x in tools_template]


