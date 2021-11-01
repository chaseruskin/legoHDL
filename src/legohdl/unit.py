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

    #class variable storing the dependency tree
    Hierarchy = Graph()

    #multi-level class container to store all entities
    Jar = Map()

    #2-level class container
    Bottle = Map()

    class Design(Enum):
        ENTITY = 1,
        PACKAGE = 2,
        pass


    class Language(Enum):
        VHDL = 1,
        VERILOG = 2
        pass


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
        elif(ext in apt.VERILOG_CODE):
            self._language = self.Language.VERILOG

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

        # add to Jar! :todo: clean up (I think only a 2-level Map with values as lists will suffice)
        # effectively binning units together

        # :note: printing component declarations needs to be done, as well as allowing package's to 
        # print their information like a component can

        # by default, look at the entities available in download section? or look at entities
        # in installation section.

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
        self._libs = libs
        self._pkgs = pkgs
        pass


    def linkArch(self, arch):
        if(hasattr(self, '_archs') == False):
            self._archs = []
        self._archs += [arch]
        pass


    def linkConfig(self, config):
        self._config = config
        pass


    def setChecked(self, c):
        #add to hierarchy if complete
        if(c == True and not self.isChecked()):
            self.Hierarchy.addVertex(self)
        self._checked = c
        pass

    
    def setAbout(self, a_txt):
        self._about_txt = a_txt
    

    def isChecked(self):
        return self._checked


    @DeprecationWarning
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
        return self._about_txt


    def getLang(self):
        return self._language


    def getArchitectures(self):
        if(hasattr(self, "_archs")):
            return self._archs
        else:
            return ['rtl']


    def isPKG(self):
        return (self._dsgn == self.Design.PACKAGE)


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
    def jar_exists(cls, M, L, N):
        if(M in cls.Jar.keys()):
            if(L in cls.Jar[M].keys()):
                return (N in cls.Jar[M][L].keys())
        return False


    @classmethod
    def ICR(cls, dsgn_name, lib=None, ports=[], gens=[]):
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
        elif(dsgn_name.lower() in cls.Bottle[lib].keys()):
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

        # :todo: update requirements for unit? also... remember design for next encounter?

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
        return f'''{self.getTitle()}, '''


    def __str__(self):
        reqs = '\n'
        for dep in self.getReqs():
            reqs = reqs + '-'+dep.M()+'.'+dep.L()+'.'+dep.N()+':'+dep.E()+" "
            reqs = reqs + hex(id(dep)) + "\n"
        return f'''
        ID: {hex(id(self))}
        Completed? {self._checked}
        full name: {self.M()}.{self.L()}.{self.N()}:{self.E()}
        file: {self._filepath}
        dsgn: {self._dsgn}
        lang: {self.getLang()}
        arch: {self.getArchitectures()}
        tb?   {self.isTb()}
        conf? {self.getConfig()}
        reqs: {reqs}
        '''
    pass


class Generic:


    def __init__(self, name, dtype, value):
        self._name = name
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
            if(len(self._value)):
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


    def __init__(self, name, way, dtype, value='', bus_width=('','')):
        '''
        Construct a port object.

        Parameters:
            name (str): port identifier
            way (str): direction
            dtype (str): datatype
            value (str): initial value
            bus_width ((str, str)): the lower and upper (exclusive) ends of a bus
        Returns:
            None
        '''
        #store the port's name
        self._name = name

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
            remaining = apt.listToStr(self._dtype)
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
            flav = self._dtype
            if('reg' in self._dtype or 'wire' in self._dtype):
                flav = self._dtype[1:]
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


    def getRoute(self):
        return self._route

    
    def __repr__(self):
        return f'''\n{self.getName()} - {self.getRoute()} * {self._dtype}'''

    pass


class Interface:
    'An interface has generics and port signals. An entity will have an interface.'

    def __init__(self, name, library, default_form):
        self._name = name
        self._library = library
        self._ports = Map()
        self._generics = Map()
        self._default_form = default_form
        pass


    def addPort(self, name, way, dtype):
        #print("Port:",name,"going",way,"of type",dtype)
        self._ports[name] = Port(name, way, dtype)
        pass


    def addGeneric(self, name, dtype, value):
        #print("Generic:",name,"of type",dtype,"has value",value)
        self._generics[name] = Generic(name, dtype, value)
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


    def __str__(self):
        return f'''
        ports: {list(self.getPorts().values())}
        generics: {list(self.getGenerics().values())}
        '''

    pass