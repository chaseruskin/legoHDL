# Project: legohdl
# Script: unit.py
# Author: Chase Ruskin
# Description:
#   This script describes the attributes and functions for a HDL design 
#   unit. In verilog, this is called a 'module', and in VHDL, this is called an 
#   'entity'. Other design units include 'packages', which are available in both
#   VHDL and verilog. Units are used to help gather data on the type of HDL
#   dependency tree that will be generated for the current design.

from enum import Enum
import os
import logging as log
from .graph import Graph
from .apparatus import Apparatus as apt
from .map import Map


class Unit:

    #class variable storing the dependency tree
    Hierarchy = Graph()

    #multi-level class container to store all entities
    Jar = Map()

    #mult-level class container upside-down of Jar container for shortcutting
    FlippedJar = Map()


    class Design(Enum):
        ENTITY = 1,
        PACKAGE = 2
        pass


    class Language(Enum):
        VHDL = 1,
        VERILOG = 2


    def __init__(self, filepath, dsgn, M, L, N, V, E):
        '''
        Create a design unit object.

        Parameters:
            filepath (str): the file where the design unit was found
            dsgn (Design): the design type
            M (str): the block market this unit belongs to
            L (str): the block library this unit belongs to
            N (str): the block name this unit belongs to
            E (str): the unit's name
        
        '''

        self._filepath = apt.fs(filepath)

        _,ext = os.path.splitext(self.getFile())
        ext = '*'+ext.lower()

        if(ext in apt.VHDL_CODE):
            self._language = self.Language.VHDL
            self._arcs = []
        elif(ext in apt.VERILOG_CODE):
            self._language = self.Language.VERILOG
            self._arcs = ['rtl'] #default to just rtl architecture

        self._dsgn = dsgn
        
        self._M = M
        self._L = L
        self._N = N
        self._V = V
        self._E = E

        self._isTB = True
        self._checked = False
        self._config = None

        #add to Jar!

        #create new market level if market DNE
        if(self.M().lower() not in self.Jar.keys()):
            self.Jar[self.M()] = Map()
        #create new library level if libray DNE
        if(self.L().lower() not in self.Jar[self.M()].keys()):
             self.Jar[self.M()][self.L()] = Map()
        #create new block name level if name DNE
        if(self.N().lower() not in self.Jar[self.M()][self.L()].keys()):
             self.Jar[self.M()][self.L()][self.N()] = Map()

        #store entity at this nested level
        if(self.E().lower() not in self.Jar[self.M()][self.L()][self.N()].keys()):
            self.Jar[self.M()][self.L()][self.N()][self.E()] = self
        else:
            log.error("An entity at this level already exists as: "+self.E()+"!")
            return

        #create new entity level if entity DNE
        if(self.E().lower() not in self.FlippedJar.keys()):
            self.FlippedJar[self.E()] = Map()
        #create new library level if libray DNE
        if(self.N().lower() not in self.FlippedJar[self.E()].keys()):
             self.FlippedJar[self.E()][self.N()] = Map()
        #create new block name level if name DNE
        if(self.L().lower() not in self.FlippedJar[self.E()][self.N()].keys()):
             self.FlippedJar[self.E()][self.N()][self.L()] = Map()
        #store entity at this nested level (upside-down)
        if(self.M().lower() not in self.FlippedJar[self.E()][self.N()][self.L()].keys()):
            self.FlippedJar[self.E()][self.N()][self.L()][self.M()] = self

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


    def isPKG(self):
        return (self._dtype == self.Type.PACKAGE)


    def getFile(self):
        return self._filepath
    

    def M(self):
        return self._M


    def L(self):
        return self._L


    def N(self):
        return self._N


    def E(self):
        return self._E


    @classmethod
    def allL(cls):
        'Returns a list of all library level map keys.'
        all_libs = []
        for m in cls.Jar.keys():
            all_libs += list(cls.Jar[m].keys())

        return all_libs


    @classmethod
    def shortcut(cls, e, m='', l='', n=''):
        'Try to guess the remaining fields if unambigious.'
        
        #identify name
        if(e != '' and e.lower() in cls.FlippedJar[e].keys()):
            route = list(cls.FlippedJar[e].keys())
            if(len(route) == 1):
                n = route[0]
        #identify library
        if(n != '' and n.lower() in cls.FlippedJar[e][n].keys()):
            route = list(cls.FlippedJar[n].keys())
            if(len(route) == 1):
                l = route[0]
        #identify market
        if(l != '' and l.lower() in cls.FlippedJar[e][n][l].keys()):
            route = list(cls.FlippedJar[e][n][l].keys())
            if(len(route) == 1):
                m = route[0]

        return m,l,n,e


    def getFull(self):
        return self.getLib()+"."+self.getName(low=True)


    def unsetTB(self):
        self._isTB = False


    def setConfig(self, config_name):
        self._config = config_name


    def getConfig(self):
        return self._config


    def isTB(self):
        return (self._dsgn == self.Design.ENTITY and self._isTB)


    def addArchitecture(self, a):
        if(a not in self.getArchitectures()):
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


    def __str__(self):
        reqs = '\n'
        for dep in self.getRequirements():
            reqs = reqs + '-'+dep.getLib()+'.'+dep.getBlock()+'.'+dep.getName()+"\n"
        return f'''
        ID: {hex(id(self))}
        full name: {self.M()}.{self.L()}.{self.N()}:{self.E()}
        file: {self._filepath}
        dsgn: {self._dsgn}
        lang: {self._language}
        arch: {self._arcs}
        tb?   {self.isTB()}
        conf? {self.getConfig()}
        reqs: {reqs}
        '''
        