# Project: legohdl
# Script: unit.py
# Author: Chase Ruskin
# Description:
#   This script describes the attributes and functions for a HDL design 
#   unit. In verilog, this is called a 'module', and in VHDL, this is called an 
#   'entity'. Other design units include 'packages', which are available in both
#   VHDL and verilog. Units are used to help gather data on the type of HDL
#   dependency tree that will be generated for the current design.

import os
import logging as log
from enum import Enum

from .graph import Graph
from .apparatus import Apparatus as apt
from .map import Map


class Unit:


    class Design(Enum):
        ENTITY = 1,
        PACKAGE = 2
        pass


    class Language(Enum):
        VHDL = 1,
        VERILOG = 2
        pass


    #class variable storing the dependency tree
    Hierarchy = Graph()

    #multi-level class container to store all entities
    Jar = Map()

    #2-level class container
    Bottle = Map()


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
            about_txt (str): the comment header block found at the top of its file
        Returns:
            None   
        '''
        self._filepath = apt.fs(filepath)
        self.setAbout(about_txt)

        _,ext = os.path.splitext(self.getFile())
        ext = '*'+ext.lower()

        if(ext in apt.VHDL_CODE):
            self._language = self.Language.VHDL
        elif(ext in apt.VERILOG_CODE):
            self._language = self.Language.VERILOG

        self._dsgn = dsgn
        
        self._M = M
        self._L = L
        self._N = N
        self._V = V
        self._E = E

        self._libs = []
        self._pkgs = []

        self._checked = False
        self._config = None

        #create an empty interface
        self._interface = Interface(name=self.E(), library=self.L(), default_form=self.getLang())

        # :note: printing component declarations needs to be done, as well as allowing package's to 
        # print their information like a component can

        # by default, look at the entities available in download section? or look at entities
        # in installation section.

        # add to Jar
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

        # add to Bottle - a 2-level Map with values as lists effectively binning units together
        #create new library level if libray DNE
        if(self.L().lower() not in self.Bottle.keys()):
             self.Bottle[self.L()] = Map()
        #create new unit level if unit DNE
        if(self.E().lower() not in self.Bottle[self.L()].keys()):
             self.Bottle[self.L()][self.E()] = []
        #add entity to a list
        self.Bottle[self.L()][self.E()] += [self]

        pass


    def linkLibs(self, libs, pkgs):
        '''
        Link relevant library and package files (mainly for VHDL entities).

        Parameters:
            libs ([str]): library names
            pkgs ([str]): package names with respective '.' characters
        Returns:
            None
        '''
        self._libs += libs
        self._pkgs += pkgs
        pass


    def getLibs(self, lower_case=False):
        '''
        Returns the list of linked libraries to this entity.

        Parameters:
            lower_case (bool): determine if to convert all libraries to lower case
        Returns:
            _libs ([str]): list of linked libraries
        '''
        if(lower_case == True):
            tmp = []
            #cast to all lower-case for evaluation purposes within VHDL
            for l in self._libs:
                tmp += [l.lower()]
            return tmp
        #return case-sensitive library names
        return self._libs


    def getPkgs(self):
        '''Returns list of packages as strings.'''
        return self._pkgs


    def decodePkgs(self):
        '''
        Returns the list of Unit objects that are design package types linked to this entity.

        Adds connections to all found package objects in the hierarchy graph. Dynamically
        creates _dsgn_pkgs attr to avoid doubling connections.

        Parameters:
            None
        Returns:
            _dsgn_pkgs ([Unit]): list of referenced Unit package objects
        '''
        if(hasattr(self, "_dsgn_pkgs")):
            return self._dsgn_pkgs

        dsgn_pkgs = []
        #iterate through each package string and try to find its object.
        for pkg in self._pkgs:
            print(pkg)
            pkg_parts = pkg.split('.')
            lib_name = pkg_parts[0]
            #convert library name to current if work is being used
            if(lib_name.lower() == 'work'):
                lib_name = self.L()
            pkg_name = pkg_parts[1]
            
            dsgn_pkg = Unit.ICR(pkg_name, lib=lib_name)
            #add the package object if its been found
            if(dsgn_pkg != None):
                dsgn_pkgs += [dsgn_pkg] 
                #add connection in the graph
                self.addReq(dsgn_pkg)
                pass
        print(dsgn_pkgs)
        return dsgn_pkgs


    def linkArch(self, arch):
        '''adds arch (str) to list of _archs ([str]) attr.'''
        if(hasattr(self, '_archs') == False):
            self._archs = []
        self._archs += [arch]
        pass


    def linkConfig(self, config):
        '''Sets _config (str) attr.'''
        self._config = config
        pass


    def setChecked(self, c):
        '''
        Sets _checked attr to `c`. If True, then the unit object self will be
        added to the graph as a vertex.

        Parameters:
            c (bool): determine if unit has been checked (data completed/decoded)
        Returns:
            None
        '''
        #add to hierarchy if complete
        if(c == True and not self.isChecked()):
            self.Hierarchy.addVertex(self)
        self._checked = c
        pass

    
    def setAbout(self, a_txt):
        '''Sets the _about_txt (str) attr.'''
        self._about_txt = a_txt
    

    def isChecked(self):
        '''Returns _checked (bool).'''
        return self._checked


    def readArchitectures(self):
        '''
        Formats the architectures into a string to be printed.

        Parameters:
            None
        Returns:
            (str): architecture text to print to console
        '''
        if(len(self.getArchitectures())):
            txt = "Defined architectures for "+self.getFull()+":\n"
            for arc in self.getArchitectures():
                txt = txt+'\t'+arc+'\n'
        else:
            txt = "No architectures are defined for "+self.getFull()+"!\n"
        return txt

    
    def readReqs(self, upstream=False):
        '''
        Formats the required units into a string to be printed.
        
        Parameters:
            upstream (bool): determine if to show connections below or above unit
        Returns:
            (str): dependency text to print to console
        '''
        term = 'Dependencies'
        if(upstream == True):
            term = 'Integrations'
        if(len(self.getReqs(upstream))):
            txt = term+' for '+self.getTitle()+":"+'\n'
            for req in self.getReqs(upstream):
                txt = txt+'\t'+req.getTitle()+'\n'
        elif(upstream == False):
            txt = "No dependencies are instantiated within "+self.getTitle()+"!"+'\n'
        elif(upstream == True):
            txt = "No integrations found for "+self.getTitle()+"!"+'\n'
        return txt


    def readAbout(self):
        '''Returns the already formatted _about_txt (str) attr to be printed.'''
        return self._about_txt


    def getLang(self):
        '''Returns what coding language the unit is in (Unit.Language).'''
        return self._language


    def getArchitectures(self):
        '''Returns list of identified architectures. If empty, returns ['rtl'].'''
        if(hasattr(self, "_archs")):
            return self._archs
        else:
            return ['rtl']


    def isPkg(self):
        '''Returns if the unit is PACKAGE design type.'''
        return (self._dsgn == self.Design.PACKAGE)

    
    def getDesign(self):
        '''Returns the unit's design type (Unit.Design).'''
        return self._dsgn


    def getFile(self):
        '''Return's the filepath where this unit was identified.'''
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
    def jarExists(cls, M, L, N):
        '''Returns True if the Jar has M/L/N key levels.'''
        if(M in cls.Jar.keys()):
            if(L in cls.Jar[M].keys()):
                return (N in cls.Jar[M][L].keys())
        return False


    @classmethod
    def ICR(cls, dsgn_name, lib=None, ports=[], gens=[]):
        '''
        Intelligently select the entity given the unit name and library (if exists). 
        
        Also uses intelligent component recognition to try and decide between 
        what entity is trying to be used. Updating the _reqs for a unit must be
        done outside the scope of this method.

        Returns None if the unit is not able to be identified.

        Parameters:
            u (str): entity name
            l (str): library name
            ports ([str]): list of ports that were instantiated
            gens ([str]): list of generics that were instantiated
        Returns:
            (Unit): unit object from the Jar
        '''
        #create a list of all potential design units
        potentials = []
        #if no library, get list of all units
        if(lib == '' or lib == None):
            for ul in list(cls.Bottle.values()):
                #print("searching for:",dsgn_name,"/ units:",list(ul.keys()))
                #could be any design that falls under this unit name
                if(dsgn_name.lower() in list(ul.keys())):
                    potentials += ul[dsgn_name]
        #a library was given, only pull list from that specific library.unit slot
        elif(lib.lower() in cls.Bottle.keys() and dsgn_name.lower() in cls.Bottle[lib].keys()):
            potentials = cls.Bottle[lib][dsgn_name]

        dsgn_unit = None
        #the choice is clear; only one option available to be this design unit
        if(len(potentials) == 1):
            log.info("Instantiating "+potentials[0].getTitle())
            dsgn_unit = potentials[0]
            pass
        #perform intelligent component recognition by comparing ports and generics
        elif(len(potentials) > 1):
            log.info("Performing Intelligent Component Recognition for "+dsgn_name+"...")
            #initialize scores for each potential component
            scores = [0]*len(potentials)

            #iterate through every potential component
            for i in range(len(potentials)):
                #get the real ports for this component
                interf = potentials[i].getInterface()
                challenged_ports = interf.getMappingNames(interf.getPorts(), lower_case=True)
                #compare the instance ports with the real ports
                for sig in challenged_ports:
                    #check if the true port is instantiated
                    if(sig in ports):
                        scores[i] += 1
                    #can only compare lengths
                    elif(len(ports) and ports[0] == '?'):
                        scores[i] = -abs(len(challenged_ports) - len(ports))
                        break
                    #this port was not instantiated, yet it MUST since its an input
                    elif(interf.getPorts()[sig].getRoute() == Port.Route.IN):
                        #automatically set score to 0
                        scores[i] = 0
                        break

            # :todo: rule out a unit if a gen is instantiated that's not in its true_gens

            #pick the highest score
            i = 0
            print('--- ICR SCORE REPORT ---')
            for j in range(len(scores)):
                print('{:<1}'.format(' '),'{:<40}'.format(potentials[j].getTitle()),'{:<4}'.format('='),'{:<5}'.format(round(scores[j]/len(ports)*100,2)),"%")
                if(scores[j] > scores[i]):
                    i = j
            dsgn_unit = potentials[i]
            log.info("Intelligently selected "+dsgn_unit.getTitle())
        else:
            log.error("Not a valid instance found within the bottle "+str(lib)+" "+dsgn_name)
            pass

        # :todo: remember design for next encounter?
        return dsgn_unit


    def getFull(self):
        return self.L()+"."+self.E()


    def getTitle(self):
        m = ''
        if(self.M() != ''):
            m = self.M()+'.'
        return m+self.L()+'.'+self.N()+apt.ENTITY_DELIM+self.E()


    def setConfig(self, config_name):
        self._config = config_name


    def getConfig(self):
        return self._config


    def getInterface(self):
        return self._interface


    def isTb(self):
        '''Returns true if the design is an entity and has zero ports.'''
        #testbench must have zero ports as an entity unit
        return (self._dsgn == self.Design.ENTITY and \
            len(self.getInterface().getPorts()) == 0)


    def addReq(self, req):
        '''
        Add a unit as a requirement for this object.

        Parameters:
            req (Unit): unit object that is used by unit calling the method
        Returns:
            None
        '''
        if(req == None):
            return
        #add new edge
        self.Hierarchy.addEdge(self, req)
        pass
    

    def getReqs(self, upstream=False):
        '''
        Returns a list of Unit objects directly required for this unit.

        Parameters:
            upstream (bool): determine if to return units that use this design
        Returns:
            ([Unit]): list of required Units
        '''
        return self.Hierarchy.getNeighbors(self, upstream)


    @classmethod
    @DeprecationWarning
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


    def __repr__(self):
        return f'''{self.getTitle()}'''


    def __str__(self):
        reqs = '\n'
        for dep in self.getReqs():
            reqs = reqs + '-'+dep.M()+'.'+dep.L()+'.'+dep.N()+':'+dep.E()+" "
            reqs = reqs + hex(id(dep)) + "\n"
        return f'''
        ID: {hex(id(self))}
        Completed? {self.isChecked()}
        full name: {self.getTitle()}
        file: {self.getFile()}
        dsgn: {self.getDesign()}
        lang: {self.getLang()}
        arch: {self.getArchitectures()}
        tb?   {self.isTb()}
        conf? {self.getConfig()}
        reqs: {reqs}
        '''
    pass


class Generic:


    def __init__(self, name, form, dtype, value=''):
        self._name = name
        self._form = form
        self._dtype = dtype
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
        

    def writeConstant(self, form, spaces=1, inc_const=True):
        '''
        Create the compatible code for declaring a constant from the given generic.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code
            spaces (int): number of spaces required between name and ':'
            inc_const (bool): determine if to include keyword 'constant' for VHDL
        Returns:
            c_txt (str): compatible line of code to be printed
        '''
        c_txt = ''
        #write VHDL-style code
        if(form == Unit.Language.VHDL):
            #write beginning of constant declaration
            if(inc_const):
                c_txt = 'constant '
            c_txt = c_txt+self._name+(spaces*' ')+': '
            remaining = apt.listToStr(self._dtype)
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
            if(self._value != None and len(self._value)):
                c_txt = c_txt + ' := ' + apt.listToStr(self._value)
            #add final ';'
            c_txt = c_txt + ';'
            pass
        #write VERILOG-style code
        elif(form == Unit.Language.VERILOG):
            print('Here is where verilog parameters would be declared.')
            pass

        return c_txt


    def getName(self):
        return self._name


    def __repr__(self):
        return f'''\n{self.getName()} * {self._dtype} = {self._value}'''

    pass


class Port:


    class Route(Enum):
        IN = 1,
        OUT = 2,
        INOUT = 3
        pass


    def __init__(self, name, form, way, dtype, value='', bus_width=('','')):
        '''
        Construct a port object.

        Parameters:
            name (str): port identifier
            form (Unit.Design): natural coding language
            way (str): direction
            dtype (str): datatype
            value (str): initial value
            bus_width ((str, str)): the lower and upper (exclusive) ends of a bus
        Returns:
            None
        '''
        #store the port's name
        self._name = name

        self._form = form
        
        if(bus_width != ('','')):
            self._bus_width = bus_width

        #store the port's direction data
        way = way.lower()
        if(way == 'inout'):
            self._route = self.Route.INOUT
        elif(way.startswith('in')):
            self._route = self.Route.IN
        elif(way.startswith('out')):
            self._route = self.Route.OUT

        #store the datatype
        self._dtype = dtype

        #store an initial value (optional)
        self._value = value
        pass


    def writeDeclaration(self, form, spaces=1):
        if(form == Unit.Language.VHDL):
            dec_txt = self.getName() +(spaces*' ')+': ' + str(self.getRoute().name).lower()+' '

            remaining = self.castDatatype(form)
            #properly format the remaining of the signal
            fc = remaining.find(',')
            if(fc > -1):
                remaining = remaining[:fc] + remaining[fc+1:]
            remaining = remaining.replace('(,', '(')
            remaining = remaining.replace(',)', ')')
            remaining = remaining.replace(',', ' ')
            dec_txt = dec_txt + remaining + ';'
        elif(form == Unit.Language.VERILOG):
            dec_txt = str(self.getRoute().name).lower()+'put ' + self.getName()+';'
        return dec_txt

    
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
            remaining = self.castDatatype(form)
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
            s_txt = self.castDatatype(form)
            s_txt = s_txt.replace(',[', ' [')
            s_txt = s_txt.replace(',', '')
            if(len(s_txt)):
                s_txt = s_txt + " "

            s_txt = s_txt + self.getName()
            #remove reg from any signals
            if(s_txt.startswith('reg')):
                s_txt = s_txt[s_txt.find('reg')+len('reg')+1:]
            #make sure all signals are declared as 'wire'
            if(s_txt.startswith('wire') == False):
                s_txt = 'wire ' + s_txt
            #add finishing ';'
            s_txt = s_txt + ';'
            pass
            
        return s_txt


    def getName(self):
        return self._name


    def getRoute(self):
        return self._route


    def castDatatype(self, form):
        '''
        Returns converted datatype.
        
        Parameters:
            form (Unit.Language): the coding language to cast to
        Returns:
            (str): proper data type for the respective coding language
        '''
        if(form == self._form):
            return apt.listToStr(self._dtype)
        #cast from verilog to vhdl
        elif(form == Unit.Language.VHDL):
            dtype = "std_logic"
            if(hasattr(self, "_bus_width")):
                dtype = dtype+"_vector("+self._bus_width[0]+" downto "+self._bus_width[1]+")"
            return dtype
        #cast from vhdl to verilog
        elif(form == Unit.Language.VERILOG):
            dtype = ''
            a = 0
            b = 1
            for word in self._dtype:
                #fix writing from LSB->MSB to MSB->LSB (swap bus width positions)
                if(word.lower() == 'to'):
                    a = 1
                    b = 0
                    break
            if(hasattr(self, "_bus_width")):
                dtype = "["+self._bus_width[a]+":"+self._bus_width[b]+"]"
            return dtype

    
    def __repr__(self):
        return f'''\n{self.getName()} - {self.getRoute()} * {self._dtype}'''

    pass


class Interface:
    'An interface has generics and port signals. An entity will have an interface.'

    def __init__(self, name, library, default_form):
        self._name = name
        self._library = library
        # :todo: use map or dictionary? map will make ports of same name incompatible using verilog
        self._ports = Map()
        self._generics = Map()
        self._default_form = default_form
        pass


    def addPort(self, name, way, dtype, width=('','')):
        #print("Port:",name,"going",way,"of type",dtype)
        self._ports[name] = Port(name, self._default_form, way, dtype, bus_width=width)
        pass


    def addGeneric(self, name, dtype, value):
        #print("Generic:",name,"of type",dtype,"has value",value)
        self._generics[name] = Generic(name, self._default_form, dtype, value)
        pass


    def getPorts(self):
        '''Returns _ports (Map).'''
        return self._ports


    def getGenerics(self):
        '''Returns _generics (Map).'''
        return self._generics


    def getName(self):
        '''Returns _name (str).'''
        return self._name


    def getLibrary(self):
        '''Returns _library (str).'''
        return self._library


    def getMappingNames(self, mapping, lower_case=False):
        'Return a list of the collected dictionary keys for the mapping parameter.'

        m_list = list(mapping.keys())
        if(lower_case):
            for i in range(len(m_list)):
                m_list[i] = m_list[i].lower()
        return m_list


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
        #default selection is to write in original coding language
        if(form == None):
            form = self._default_form

        connect_txt = ''
        #default number of spaces when not aligning
        spaces = 1 
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
        
        #add new-line between generics and signals
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
        #default selection is to write in original coding language
        if(form == None):
            form = self._default_form

        mapping_txt = ''
        #default number of spaces when not aligning
        spaces = 0 
        #do not write anything if no interface!
        if(len(self.getGenerics()) == 0 and len(self.getPorts()) == 0):
                return mapping_txt
        
        #write VHDL-style code
        if(form == Unit.Language.VHDL):
            #write the instance name and entity name
            mapping_txt = inst_name + " : "+self.getName()+"\n"
            #re-assign beginning of mapping to be a pure entity instance
            if(entity_inst):
                mapping_txt = inst_name+" : entity "+self.getLibrary()+"."+self.getName()+"\n"

            #generics to map
            if(len(self.getGenerics())):
                mapping_txt = mapping_txt + "generic map(\n"

                gens = self.getMappingNames(self.getGenerics())
                farthest = self.computeLongestWord(self.getMappingNames(self.getGenerics()))
                #iterate through every generic
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
                    #append to entire text
                    mapping_txt = mapping_txt + line+"\n"
                    pass
                #add necessary closing
                mapping_txt = mapping_txt + ")"
                pass

            #ports to map
            if(len(self.getPorts())):
                #add new line if generics were written
                if(len(self.getGenerics())):
                    mapping_txt = mapping_txt + "\n"

                mapping_txt = mapping_txt + "port map(\n"

                ports = self.getMappingNames(self.getPorts())
                farthest = self.computeLongestWord(self.getMappingNames(self.getPorts()))
                #iterate through every port
                for i in range(len(ports)):
                    if(align):
                        spaces = farthest - len(ports[i]) + 1
                    line = self._ports[ports[i]].writeMapping(form, spaces)
                    #add a comma if not on the last port
                    if(i != len(ports)-1):
                        line = line + ","
                    #don't add \n to last map if hang_end
                    elif(hang_end == False):
                        mapping_txt = mapping_txt + line
                        continue
                    #append to the entire text
                    mapping_txt = mapping_txt + line+"\n"
                    pass
                #add necessary closing
                mapping_txt = mapping_txt + ")"
                pass

            #add final ';'
            mapping_txt = mapping_txt + ";\n"
            pass
        #write VERILOG-style code
        elif(form == Unit.Language.VERILOG):
            #start with entity's identifier
            mapping_txt = self.getName()
            #write out parameter section
            params = self.getMappingNames(self.getGenerics())
            if(len(params)):
                farthest = self.computeLongestWord(params)
                mapping_txt = mapping_txt + ' #(\n'
                for p in params:
                    if(align):
                        spaces = farthest - len(p) + 1
                    mapping_txt = mapping_txt + self.getGenerics()[p].writeMapping(form, spaces)
                    #don't add ',\n' if on last generic
                    if(p == params[-1]): 
                        if(hang_end == True):
                            mapping_txt = mapping_txt + "\n"
                        mapping_txt = mapping_txt + ")\n" + inst_name
                    else:
                        mapping_txt = mapping_txt + ",\n"
            #no generics...so begin with instance name
            else:
                mapping_txt = mapping_txt + " " + inst_name

            #write out port section
            ports = self.getMappingNames(self.getPorts())
            if(len(ports)):
                mapping_txt = mapping_txt + ' (\n'
                farthest = self.computeLongestWord(ports)
                #iterate through every port
                for p in ports:
                    if(align):
                        spaces = farthest - len(p) + 1
                    mapping_txt = mapping_txt + self.getPorts()[p].writeMapping(form, spaces)

                    #don't add ,\n if on last port
                    if(p == ports[-1]):
                        #add newline if hanging end
                        if(hang_end == True):
                            mapping_txt = mapping_txt + "\n"
                        mapping_txt = mapping_txt + ")"
                    else:
                        mapping_txt = mapping_txt +",\n"
                    pass
                pass

            #add final ';'
            mapping_txt = mapping_txt + ';'
            pass
        #print(mapping_txt)
        return mapping_txt

    
    def writeDeclaration(self, form, align=True, hang_end=True, tabs=0):
        '''
        Write the correct compatible code for a component declaration of the given
        entity. For VERILOG, it will return the module declaration statement.

        Parameters:
            form (Unit.Language): VHDL or VERILOG compatible code style
            align (bool): determine if identifiers should be all equally spaced
            hand_end (bool): true if ) deserves its own line
        Returns:
            comp_txt (str): the compatible code to be printed
        '''
        #default selection is to write in original coding language
        if(form == None):
            form = self._default_form

        comp_txt = ''
        #default number of spaces when not aligning
        spaces = 1
        #write VHDL-style code
        if(form == Unit.Language.VHDL):
            comp_txt = (tabs*'\t')+'component ' + self.getName() + '\n'
            #write generics
            gens = list(self.getGenerics().values())
            if(len(gens)):
                farthest = self.computeLongestWord(self.getMappingNames(self.getGenerics()))
                comp_txt  = comp_txt + (tabs*'\t')+'generic(' + '\n'
                #write every generic
                for gen in gens:
                    if(align):
                        spaces = farthest - len(gen.getName()) + 1
                    comp_line = gen.writeConstant(form, spaces=spaces, inc_const=False)
                    comp_txt = comp_txt + ((tabs+1)*'\t')+comp_line[:len(comp_line)-1] #trim off ';'
                    if(gen != gens[-1]):
                        comp_txt = comp_txt + ';\n'
                    elif(hang_end):
                         comp_txt = comp_txt + '\n'
                #add final generic closing token
                comp_txt = comp_txt + (tabs*'\t')+');\n'
            #write ports
            ports = list(self.getPorts().values())
            if(len(ports)):
                farthest = self.computeLongestWord(self.getMappingNames(self.getPorts()))
                comp_txt = comp_txt + (tabs*'\t')+'port(' + '\n'
                #write every port
                for port in ports:
                    if(align):
                        spaces = farthest - len(port.getName()) + 1
                    comp_line = port.writeDeclaration(form, spaces)
                    comp_txt = comp_txt + ((tabs+1)*'\t')+comp_line[:len(comp_line)-1] #trim off ';'
                    if(port != ports[-1]):
                        comp_txt = comp_txt + ';\n'
                    elif(hang_end):
                        comp_txt = comp_txt + '\n'
                #add final port closing token
                comp_txt = comp_txt + (tabs*'\t')+');\n'
            #add final closing segment
            comp_txt = comp_txt + (tabs*'\t')+'end component;'
            pass
        #write VERILOG-style code
        elif(form == Unit.Language.VERILOG):
            comp_txt = 'module '+self.getName()
            pass

        return comp_txt


    def __str__(self):
        return f'''
        ports: {list(self.getPorts().values())}
        generics: {list(self.getGenerics().values())}
        '''

    pass