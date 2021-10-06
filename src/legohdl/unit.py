################################################################################
#   Project: legohdl
#   Script: unit.py
#   Author: Chase Ruskin
#   Description:
#       This script describes the attributes and functions for a HDL design 
#   unit. In verilog, this is called a 'module', and in VHDL, this is called an 
#   'entity'. Other design units include 'packages', which are available in both
#   VHDL and verilog. Units are used to help gather data on the type of HDL
#   dependency tree that will be generated for the current design.
################################################################################

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

    def __init__(self, filepath, dtype, lib, block, unitName, market):
        self._filepath = filepath
        _,ext = os.path.splitext(self.getFile())
        ext = '*'+ext.lower()
        if(ext in apt.VHDL_CODE):
            self._language = self.Language.VHDL
            self._lang = Vhdl(filepath)
            self._arcs = []
        elif(ext in apt.VERILOG_CODE):
            self._language = self.Language.VERILOG
            self._lang = Verilog(filepath)
            self._arcs = ['rtl'] #default to just rtl architecture

        self._dtype = dtype
        self._lib = lib
        self._block = block
        self._market = market
        self._unit = unitName
        self._isTB = True
        self._checked = False
        self._config = None
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

    def writeArchitectures(self):
        if(len(self.getArchitectures())):
            txt = "Defined architectures for "+self.getFull()+":\n"
            for arc in self.getArchitectures():
                txt = txt+'\t'+arc+'\n'
        else:
            txt = "No architectures are defined for "+self.getFull()+"!\n"
        return txt+'\n'

    def getLanguageType(self):
        return self._language

    def getArchitectures(self):
        return self._arcs

    def getLang(self):
        return self._lang

    def isPKG(self):
        return (self._dtype == self.Type.PACKAGE)

    def getFile(self):
        return apt.fs(self._filepath)

    def getBlock(self, low=True):
        if(low):
            return self._block.lower()
        else:
            return self._block

    def getMarket(self, low=True):
        if(low and self._market != None):
            return self._market.lower()
        else:
            return self._market

    def getLib(self, low=True):
        if(low):
            return self._lib.lower()
        else:
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

    def setConfig(self, config_name):
        self._config = config_name

    def getConfig(self):
        return self._config

    def isTB(self):
        return (self._dtype == self.Type.ENTITY and self._isTB)

    def addArchitecture(self, a):
        self._arcs.append(a)

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
{self._lib}.{self._block}:{self._unit} | {self._filepath} | {self._dtype} | {self._language}
requires:\n'''
        for dep in self.getRequirements():
            report = report + '-'+dep.getLib()+'.'+dep.getBlock()+'.'+dep.getName()+"\n"
        
        return report