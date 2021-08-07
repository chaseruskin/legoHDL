from enum import Enum
from .vhdl import Vhdl
from .graph import Graph

class Unit:

    #class variable storing the dependency tree
    Hierarchy = Graph()

    class Type(Enum):
        ENTITY = 1,
        PACKAGE = 2
        pass

    def __init__(self, filepath, dtype, lib, block, unitName):
        self._filepath = filepath
        self._dtype = dtype
        self._lib = lib
        self._block = block
        self._unit = unitName
        self._isTB = True
        self._vhdl = Vhdl(filepath)
        self._checked = False
        pass
    pass

    def setChecked(self, c):
        #add to hierarchy if complete
        if(c == True and not self.isChecked()):
            self.Hierarchy.addLeaf(self)
        self._checked = c
        pass
    
    def isChecked(self):
        return self._checked

    def writePortMap(self,mapping,lib,pureEntity):
        report = '\n'
        if(self.isPKG()):
            return ''
        else:
            if(not pureEntity or mapping):
                report =  report + self.getVHD().writeComponentDeclaration() + "\n"
            if(mapping or pureEntity):
                report = report + "\n" + self.getVHD().writeComponentSignals() + "\n"
                if(mapping):
                    report = report + self.getVHD().writeComponentMapping(False, lib) + "\n"
                if(pureEntity):
                    report = report + self.getVHD().writeComponentMapping(pureEntity, lib) + "\n"
                pass
        return report

    def getVHD(self):
        return self._vhdl

    def isPKG(self):
        return (self._dtype == self.Type.PACKAGE)

    def getFile(self):
        return self._filepath

    def getBlock(self):
        return self._block

    def getLib(self):
        return self._lib

    def getName(self):
        return self._unit

    def getFull(self):
        return self._lib+"."+self._unit

    def unsetTB(self):
        self._isTB = False

    def isTB(self):
        return (self._dtype == self.Type.ENTITY and self._isTB)

    #add a unit as a requirement for itself
    def addRequirement(self, u):
        #add new edge
        self.Hierarchy.addEdge(self.getFull(), u.getFull())
        self._requirements = self.getRequirements() + [u]
        pass
    
    #returns a list of units required for itself
    def getRequirements(self):
        if(hasattr(self, "_requirements")):
            return self._requirements
        else:
            return []

    def __repr__(self):
        report = f'''
{self._lib}.{self._block}.{self._unit} | {self._filepath} | {self._dtype}
requires:\n'''
        for dep in self.getRequirements():
            report = report + '-'+dep.getLib()+'.'+dep.getBlock()+'.'+dep.getName()+"\n"
        
        return report