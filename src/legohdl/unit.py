from enum import Enum
import os
from .vhdl import Vhdl
from .verilog import Verilog
from .graph import Graph
from .apparatus import Apparatus as apt

class Unit:

    #class variable storing the dependency tree
    Hierarchy = Graph()

    class Type(Enum):
        ENTITY = 1,
        PACKAGE = 2
        pass

    class Language(Enum):
        VHDL = 1,
        VERILOG = 2

    def __init__(self, filepath, dtype, lib, block, unitName):
        self._filepath = filepath
        _,ext = os.path.splitext(self.getFile())
        ext = '*'+ext.lower()
        if(ext in apt.VHDL_CODE):
            self._language = self.Language.VHDL
            self._lang = Vhdl(filepath)
        elif(ext in apt.VERILOG_CODE):
            self._language = self.Language.VERILOG
            self._lang = Verilog(filepath)

        self._dtype = dtype
        self._lib = lib
        self._block = block
        self._unit = unitName
        self._isTB = True
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

    def writePortMap(self, mapping, lib, pureEntity):
        report = '\n'
        if(self.isPKG()):
            return ''
        else:
            if(not pureEntity or mapping):
                report =  report + self.getLang().writeComponentDeclaration() + "\n"
            if(mapping or pureEntity):
                if(len(report) > 1):
                    report = report + "\n"
                report = report + self.getLang().writeComponentSignals() + "\n"
                if(mapping):
                    report = report + self.getLang().writeComponentMapping(False, lib) + "\n"
                if(pureEntity):
                    report = report + self.getLang().writeComponentMapping(pureEntity, lib) + "\n"
                pass
            if(not mapping and not pureEntity):
                report = report + "\n"
        return report

    def getLanguageType(self):
        return self._language

    def getLang(self):
        return self._lang

    def isPKG(self):
        return (self._dtype == self.Type.PACKAGE)

    def getFile(self):
        return apt.fs(self._filepath)

    def getBlock(self):
        return self._block

    def getLib(self):
        return self._lib

    def getName(self, low=True):
        if(low):
            return self._unit.lower()
        else:
            return self._unit

    def getFull(self):
        return self.getLib()+"."+self.getName(low=True)

    def unsetTB(self):
        self._isTB = False

    def isTB(self):
        return (self._dtype == self.Type.ENTITY and self._isTB)

    #add a unit as a requirement for itself
    def addRequirement(self, u):
        #add new edge
        #print(self.getFull())
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
{self._lib}.{self._block}.{self._unit} | {self._filepath} | {self._dtype} | {self._language}
requires:\n'''
        for dep in self.getRequirements():
            report = report + '-'+dep.getLib()+'.'+dep.getBlock()+'.'+dep.getName()+"\n"
        
        return report