from enum import Enum

class Unit:
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
        pass
    pass

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
        self._requirements = self.getRequirements() + [u]
        pass
    
    #returns a list of units required for itself
    def getRequirements(self):
        if(hasattr(self, "_requirements")):
            return self._requirements
        else:
            return []

    def __repr__(self):
        return(f'''
unit: {self._unit} | library: {self._lib} | block name: {self._block} | filepath: {self._filepath} | design type: {self._dtype} | 
requires: {self.getRequirements()}
\n''')