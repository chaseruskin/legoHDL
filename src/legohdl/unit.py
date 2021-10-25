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

    #2-level class container
    Bottle = Map()

    class Design(Enum):
        ENTITY = 1,
        PACKAGE = 2
        pass


    class Language(Enum):
        VHDL = 1,
        VERILOG = 2


    def __init__(self, filepath, dsgn, M, L, N, V, E, about_txt=''):
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
        self.setAbout(about_txt)

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

        self._checked = False
        self._config = None

        #create an empty interface
        self._interface = Interface(name=self.E(), library=self.L(), default_form=self.getLang())

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


        #create new library level if libray DNE
        if(self.L().lower() not in self.Bottle.keys()):
             self.Bottle[self.L()] = Map()
        #create new unit level if unit DNE
        if(self.E().lower() not in self.Bottle[self.L()].keys()):
             self.Bottle[self.L()][self.E()] = []
        #add entity to a list
        self.Bottle[self.L()][self.E()] += [self]

        pass


    def setChecked(self, c):
        #add to hierarchy if complete
        if(c == True and not self.isChecked()):
            self.Hierarchy.addLeaf(self)
        self._checked = c
        pass

    
    def setAbout(self, a_txt):
        self._about_txt = a_txt
    

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


    def readAbout(self):
        return self._about_txt


    def getLang(self):
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
    def loc(cls, u, l=None, ports=[], gens=[]):
        '''
        Locate the entity given the library and unit name. 
        
        Also uses intelligent component recognition to try and decide between 
        what entity is trying to be used.

        Parameters:
            u (str): entity name
            l (str): library name
            ports ([str]): list of ports that were instantiated
            gens ([str]): list of generics that were instantiated
        Returns:
            (Unit): unit object from the Jar
        '''

        return cls.Bottle[l][u][0]


    # :todo: fix
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
        return self.L().lower()+"."+self.N().lower()


    def setConfig(self, config_name):
        self._config = config_name


    def getConfig(self):
        return self._config


    def getInterface(self):
        return self._interface


    def isTB(self):
        # a testbench must have zero ports
        return (self._dsgn == self.Design.ENTITY and \
            len(self.getInterface().getPorts()) == 0)


    def addArchitecture(self, a):
        if(a not in self.getArchitectures()):
            self._arcs.append(a)


    #add a unit as a requirement for itself
    def addRequirement(self, u):
        '''
        Add a unit as a requirement for this object.

        Parameters:
            u (Unit): unit object that is used by unit calling the method
        Returns:
            None
        '''
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


    @classmethod
    def printList(cls, M='', L='', N='', show_all_versions=False):
        '''
        Prints formatted list for entities.

        Parameters:
            show_all_versions (bool): print every available entity even with appended version
        Returns:
            None
        '''
        # :todo: add -filter to allow for user to prefer what they want to see about each entity?
        print('{:<14}'.format("Library"),'{:<14}'.format("Unit"),'{:<8}'.format("Type"),'{:<14}'.format("Block"),'{:<10}'.format("Language"))
        print("-"*14+" "+"-"*14+" "+"-"*8+" "+"-"*14+" "+"-"*10+" ")
        for m in cls.Jar.values():
            for l in m.values():
                for n in l.values():
                    for e in n.values():
                        print('{:<14}'.format(e.L()),'{:<14}'.format(e.E()),'{:<8}'.format(e._dsgn.name),'{:<14}'.format(e.N()),'{:<10}'.format(e.getLang().name))
            pass
        pass


    def __str__(self):
        reqs = '\n'
        for dep in self.getRequirements():
            reqs = reqs + '-'+dep.M()+'.'+dep.L()+'.'+dep.N()+':'+dep.E()+" "
            reqs = reqs + hex(id(dep)) + "\n"
        return f'''
        ID: {hex(id(self))}
        full name: {self.M()}.{self.L()}.{self.N()}:{self.E()}
        file: {self._filepath}
        dsgn: {self._dsgn}
        lang: {self.getLang()}
        arch: {self._arcs}
        tb?   {self.isTB()}
        conf? {self.getConfig()}
        reqs: {reqs}
        '''
    pass


class Generic:


    def __init__(self, name, flavor, value):
        self._name = name
        self._flavor = flavor
        self._value = value
        pass


    def writeMapping(self, form, spaces=0):
        '''
        Create the compatible code for mapping a given generic.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code
            spaces (int): number of spaces required between name and '=>'
        Returns:
            m_txt (str): compatible line of code to be printed
        '''
        r_space = 1 if(spaces > 0) else 0

        if(form == Unit.Language.VHDL):
            m_txt = "    "+self._name+(spaces*' ')+"=>"+(r_space*' ')+self._name
        elif(form == Unit.Language.VERILOG):
            m_txt = "    ."+self._name+(spaces*' ')+"("+self._name+")"
        return m_txt
        

    def writeConstant(self, form, spaces=1):
        '''
        Create the compatible code for declaring a constant from the given generic.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code
            spaces (int): number of spaces required between name and ':'
        Returns:
            c_txt (str): compatible line of code to be printed
        '''
        c_txt = ''
        #write VHDL-style code
        if(form == Unit.Language.VHDL):
            #write beginning of constant declaration
            c_txt = 'constant '+self._name+(spaces*' ')+': '
            remaining = apt.listToStr(self._flavor)
            #properly format the remaining of the constant
            fc = remaining.find(',(')
            if(fc > -1):
                remaining = remaining[:fc] + remaining[fc+1:]
            remaining = remaining.replace('(,', '(')
            remaining = remaining.replace(',)', ')')
            remaining = remaining.replace(',', ' ')
            #add type
            c_txt = c_txt + remaining
            #give default value
            c_txt = c_txt + ' := ' + apt.listToStr(self._value)
            #add final ';'
            c_txt = c_txt + ';'
            pass
        #write VERILOG-style code
        elif(form == Unit.Language.VERILOG):

            pass

        return c_txt


    def getName(self):
        return self._name

    pass


class Port:


    def __init__(self, name, way, flavor, value=None):
        self._name = name
        self._way = way
        self._flavor = flavor
        self._value = value
        pass

    
    def writeMapping(self, form, spaces=0):
        '''
        Create the compatible code for mapping a given port.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code
            spaces (int): number of spaces required between name and '=>'
        Returns:
            m_txt (str): compatible line of code to be printed
        '''
        r_space = 1 if(spaces > 0) else 0

        if(form == Unit.Language.VHDL):
            m_txt = "    "+self._name+(spaces*' ')+"=>"+(r_space*' ')+self._name
        elif(form == Unit.Language.VERILOG):
            m_txt = "    ."+self._name+(spaces*' ')+"("+self._name+")"
        return m_txt


    def writeSignal(self, form, spaces=1):
        '''
        Create the compatible code for declaring a signal from the given port.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code
            spaces (int): number of spaces required between name and ':'
        Returns:
            s_txt (str): compatible line of code to be printed
        '''
        s_txt = ''
        #write VHDL-style code
        if(form == Unit.Language.VHDL):
            #write beginning of signal declaration
            s_txt = 'signal '+self._name+(spaces*' ')+': '
            remaining = apt.listToStr(self._flavor)
            #properly format the remaining of the signal
            fc = remaining.find(',')
            if(fc > -1):
                remaining = remaining[:fc] + remaining[fc+1:]
            remaining = remaining.replace('(,', '(')
            remaining = remaining.replace(',)', ')')
            remaining = remaining.replace(',', ' ')
            s_txt = s_txt + remaining + ';'
            pass
        #write VERILOG-style code
        elif(form == Unit.Language.VERILOG):
            #skip over type declaration
            if('reg' in self._flavor or 'wire' in self._flavor):
                flav = self._flavor[1:]
            if(len(flav)):
                s_txt = apt.listToStr(flav)
                s_txt = s_txt.replace(',[', ' [')
                s_txt = s_txt.replace(',', '')
                s_txt = s_txt + " "

            s_txt = 'wire ' + s_txt + self._name
            s_txt = s_txt + ';'
            pass
            
        return s_txt


    def getName(self):
        return self._name
    pass


class Interface:
    'An interface has generics and port signals. An entity will have an interface.'

    def __init__(self, name, library, default_form):
        self._name = name
        self._library = library
        self._ports = {}
        self._generics = {}
        self._default_form = default_form
        pass


    def addPort(self, name, way, flavor):
        #print("Port:",name,"going",way,"of type",flavor)
        self._ports[name] = Port(name, way, flavor)
        pass


    def addGeneric(self, name, flavor, value):
        #print("Generic:",name,"of type",flavor,"has value",value)
        self._generics[name] = Generic(name, flavor, value)
        pass


    def getPorts(self):
        return self._ports


    def getGenerics(self):
        return self._generics


    def getName(self):
        return self._name


    def getLibrary(self):
        return self._library


    def getMappingNames(self, mapping, lower_case=False):
        'Return a list of the collected dictionary keys for the mapping parameter.'

        g_list = list(mapping.keys())
        if(lower_case):
            for i in range(len(g_list)):
                g_list[i] = g_list[i].lower()
        return g_list


    def computeLongestWord(self, words):
        '''
        Computes the longest word length from a list of words. Returns -1 if
        no words are in the list.

        Parameters:
            words ([str]): list of words to compare
        Returns:
            farthest (int): length of longest word in the list
        '''
        farthest = -1
        for s in words:
            if(len(s) > farthest):
                farthest = len(s)
        return farthest


    def writeConnections(self, form=None, align=True):
        '''
        Write the necessary constants (from generics) and signals (from ports)
        for the given entity.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code style
            align (bool): determine if names should be all equally spaced
        Returns:
            connect_txt (str): compatible code to be printed
        '''
        if(form == None):
            form = self._default_form
        connect_txt = ''
        spaces = 1 #default number of spaces when not aligning
        #do not write anything if no interface!
        if(len(self.getGenerics()) == 0 and len(self.getPorts()) == 0):
                return connect_txt
        
        #determine farthest reach constant name
        farthest = self.computeLongestWord(self.getMappingNames(self.getGenerics()))
                
        #write constants
        for g in self.getGenerics().values():
            if(align):
                spaces = farthest - len(g.getName()) + 1
            connect_txt = connect_txt + g.writeConstant(form, spaces) +'\n'
        
        #add spacer between generics and signals
        if(len(self.getGenerics())):
            connect_txt = connect_txt + '\n'

        #determine farthest reach signal name
        farthest = self.computeLongestWord(self.getMappingNames(self.getPorts()))

        #write signals
        for p in self.getPorts().values():
            if(align):
                spaces = farthest - len(p.getName()) + 1
            connect_txt = connect_txt + p.writeSignal(form, spaces) +'\n'

        return connect_txt
    

    def writeInstance(self, form=None, entity_inst=False, inst_name='uX', align=False, hang_end=True):
        '''
        Write the correct compatible code for an instantiation of the given
        entity.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code style
            entity_inst (bool): if VHDL, use entity instantiation
            inst_name (str): the name to give the instance
            align (bool): determine if names should be all equally spaced
            hand_end (bool): true if ) deserves its own line
        Returns:
            mapping_txt (str): the compatible code to be printed
        '''
        if(form == None):
            form = self._default_form
        mapping_txt = ''
        spaces = 0 #default number of spaces when not aligning
        #do not write anything if no interface!
        if(len(self.getGenerics()) == 0 and len(self.getPorts()) == 0):
                return mapping_txt
        
        #write VHDL-style code
        if(form == Unit.Language.VHDL):
            mapping_txt = inst_name + " : "+self.getName()+"\n"
            #reassign beginning of mapping to be a pure entity instance
            if(entity_inst):
                mapping_txt = inst_name+" : entity "+self.getLibrary()+"."+self.getName()+"\n"

            #generics to map
            if(len(self.getGenerics())):
                mapping_txt = mapping_txt + "generic map(\n"

                gens = self.getMappingNames(self.getGenerics())
                farthest = self.computeLongestWord(self.getMappingNames(self.getGenerics()))

                for i in range(len(gens)):
                    if(align):
                        spaces = farthest - len(gens[i]) + 1
                    line =  self._generics[gens[i]].writeMapping(form, spaces)
                    #add a comma if not on last generic
                    if(i != len(gens)-1):
                        line = line + ","
                    #don't add \n to last map if hang_end
                    elif(hang_end == False):
                        mapping_txt = mapping_txt + line
                        continue
                    mapping_txt = mapping_txt + line+"\n"
                #add necessary closing
                mapping_txt = mapping_txt + ")"

            #ports to map
            if(len(self.getPorts())):
                #add new line if generics were written
                if(len(self.getGenerics())):
                    mapping_txt = mapping_txt + "\n"
                mapping_txt = mapping_txt + "port map(\n"

                ports = self.getMappingNames(self.getPorts())
                farthest = self.computeLongestWord(self.getMappingNames(self.getPorts()))
                
                for i in range(len(ports)):
                    if(align):
                        spaces = farthest - len(ports[i]) + 1
                    line = self._ports[ports[i]].writeMapping(form, spaces)
                    #add a comma if not on the last signal
                    if(i != len(ports)-1):
                        line = line + ","
                    #don't add \n to last map if hang_end
                    elif(hang_end == False):
                        mapping_txt = mapping_txt + line
                        continue
                    mapping_txt = mapping_txt + line+"\n"
                #add necessary closing
                mapping_txt = mapping_txt + ")"

            mapping_txt = mapping_txt + ";\n"
            pass
        #write VERILOG-style code
        elif(form == Unit.Language.VERILOG):
            mapping_txt = self.getName()
            #write out parameter section
            params = self.getMappingNames(self.getGenerics())
            if(len(params)):
                farthest = self.computeLongestWord(params)
                mapping_txt = mapping_txt + ' #(\n'
                for p in params:
                    if(align):
                        spaces = farthest - len(p) + 1
                    if(p == params[-1]):
                        mapping_txt = mapping_txt + self.getGenerics()[p].writeMapping(form, spaces)
                        if(hang_end == True):
                            mapping_txt = mapping_txt + "\n"
                        mapping_txt = mapping_txt + ")\n" + inst_name
                    else:
                        mapping_txt = mapping_txt + self.getGenerics()[p].writeMapping(form, spaces)+",\n"
            else:
                mapping_txt = mapping_txt + " " + inst_name
            #write out port section
            ports = self.getMappingNames(self.getPorts())
            if(len(ports)):
                mapping_txt = mapping_txt + ' (\n'
                farthest = self.computeLongestWord(ports)
                for p in ports:
                    if(align):
                        spaces = farthest - len(p) + 1
                    if(p == ports[-1]):
                        mapping_txt = mapping_txt + self.getPorts()[p].writeMapping(form, spaces)
                        if(hang_end == True):
                            mapping_txt = mapping_txt + "\n"
                        mapping_txt = mapping_txt + ")"
                    else:
                        mapping_txt = mapping_txt + self.getPorts()[p].writeMapping(form, spaces)+",\n"
            mapping_txt = mapping_txt + ';'
            pass
        #print(mapping_txt)
        return mapping_txt
    pass