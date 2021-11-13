# Project: legohdl
# Script: vhdl.py
# Author: Chase Ruskin
# Description:
#   This script inherits language.py and implements the behaviors for
#   VHDL code files (syntax, deciphering).
#
#   A VHDL file has entities.

from legohdl.language import Language
import logging as log
from .language import Language
from .unit import Unit
from .map import Map


class Vhdl(Language):


    def __init__(self, fpath, block):
        '''
        Create a VHDL language file object.

        Parameters:
            fpath (str): HDL file path
            block (Block): the Block the file belongs to
        Returns:
            None
        '''
        super().__init__(fpath, block)

        ### new important stuff
        self._seps = [':', '=', '(', ')', '>', '<', ',', '"']
        self._dual_chars = [':=', '<=', '=>']
        self._comment = '--'
        self._atomics = ['begin', 'is']

        self.spinCode()
        ###

        #run with VHDL decoder
        self.identifyDesigns()
        pass


    def __str__(self):
        dsgns = ''
        for d in self.identifyDesigns():
            dsgns = dsgns + str(d) + '\n'
        
        return super().__str__()+f'''
        designs: {dsgns}
        '''


    def identifyDesigns(self):
        '''
        Analyzes the current VHDL file to only identify design units. Does not
        complete their data. 
        
        Dynamically creates attr _designs.

        Parameters:
            None
        Returns:
            _designs ([Unit]): list of units found in this file
        '''
        if(hasattr(self, "_designs")):
            return self._designs

        #get the list of statements
        c_statements = self.spinCode()

        self._designs = []

        libs = []
        pkgs = []

        #looking for design units in each statement
        for cseg in c_statements:
            #collect library calls as going forward
            if(cseg[0].lower() == 'library'):
                #print(cseg[1])
                libs += [cseg[1]]
            #link relevant packages (resets with every entity)
            if(cseg[0].lower() == 'use'): 
                #print(cseg[1])
                #split by '.'
                pkgs += [cseg[1]]
                pass
            #declare an entity
            if(cseg[0].lower() == 'entity'):
                #log.info("Identified entity: "+cseg[1])
                self._designs += [Unit(cseg[1], self.getPath(), Unit.Design.ENTITY, self)]
                dsgn_unit = self._designs[-1]
                self.getInterface(dsgn_unit, c_statements[c_statements.index(cseg):])
                #link visible libraries and packages
                dsgn_unit.linkLibs(libs, pkgs)
                #reset package spaces
                pkgs = []
                pass
            #declare a package unit
            elif(cseg[0].lower() == 'package' and cseg[1].lower() != 'body'):
                #log.info("Identified package "+cseg[1])
                self._designs += [Unit(cseg[1], self.getPath(), Unit.Design.PACKAGE, self)]
                dsgn_unit = self._designs[-1]
                #link visible libraries and packages
                dsgn_unit.linkLibs(libs, pkgs)
                #reset package spaces
                pkgs = []
                pass
            #link a configuration
            elif(cseg[0].lower() == 'configuration'):
                #log.info("Identified configuration "+cseg[1]+" for entity: "+cseg[3])
                #get who owns this configuration
                dsgn_entity = cseg[3]
                Unit.Jar[self.getOwner().M()][self.getOwner().L()][self.getOwner().N()][dsgn_entity].linkConfig(cseg[1])
                pass
            #link an architecture
            elif(cseg[0].lower() == 'architecture'):
                #log.info("Identified architecture "+cseg[1]+" for entity: "+cseg[3])
                #get who owns this architecture
                dsgn_entity = cseg[3]
                Unit.Jar[self.getOwner().M()][self.getOwner().L()][self.getOwner().N()][dsgn_entity].linkArch(cseg[1])
                pass

        return self._designs


    def decode(self, u, recursive=True):
        '''
        Decipher and collect data on a unit's instantiated lower-level entities.
        Does not decode package designs.

        Parameters:
            u (Unit): the unit file who's interface to update
            recursive (bool): determine if to tunnel through entities
        Returns:
            None
        '''
        #get all available units availalble as components
        comps = []
        in_arch = False
        in_begin = False
        arch_name = ''
        #get all code statements
        csegs = self.spinCode()

        #do not decode unit again if already decoded
        if(u.isChecked()):
            return

        # :todo: get configurations support (similiar to find/replace)

        #collect all visible component declarations
        for pkg in u.decodePkgs():
            #print("Importing "+pkg.getTitle())
            comps += pkg.getLanguageFile().getComponents(pkg)
            #also further decode this package
            if(pkg.isChecked() == False and recursive):
                pkg.getLanguageFile().decode(pkg, recursive)
            pass

        #make sure the design unit is an entity to read architectures
        if(u.getDesign() != Unit.Design.ENTITY):
            u.setChecked(True)
            return

        for cseg in csegs:
            #determine when to enter the architecture
            if(cseg[0].lower() == 'architecture' and cseg[3].lower() == u.E().lower()):
                in_arch = True
                arch_name = cseg[1].lower() #store arch_name for exit case later
            elif(in_arch == False):
                continue
            #track scope stack to determine when maybe within the architecture implementation
            if(cseg[0].lower() == 'begin'):
                in_begin = True

            #exit case - finding 'end' with architecture or its name
            if(in_begin and len(cseg) > 1 and cseg[0].lower() == 'end'):
                if(cseg[1].lower() == 'architecture' or cseg[1].lower() == arch_name):
                    u.setChecked(True)
                    in_arch = False
                    in_begin = False
                    #use continue to go through all architectures
                    continue

            #find component declarations
            if(cseg[0].lower() == 'component'):
                #log.info("Declared component: "+cseg[1])
                comps += [cseg[1].lower()]

            #find instantiations    
            if(in_begin):
                while cseg.count(':'):
                    sp_i = cseg.index(':')
                    comp_name = cseg[sp_i+1]
                    #is it an entity style?
                    entity_style = (comp_name.lower() == 'entity')
                    if(entity_style):
                        comp_name = cseg[sp_i+2]
                    #move through the code segment
                    old_cseg = cseg
                    cseg = cseg[sp_i+1:]

                    #default not reference a library
                    lib = None
                    #determine if a library is attached to this entity name
                    comp_parts = comp_name.split('.')
                    
                    #print(comp_parts)
                    if(len(comp_parts) == 2):
                        #must have first piece be a library name
                        if(entity_style):
                            if(comp_parts[0].lower() in u.getLibs(lower_case=True)):
                                lib = comp_parts[0]
                            #reference self library if it's 'work'
                            elif(comp_parts[0].lower() == 'work'):
                                lib = self.getOwner().L()
                    #the last piece is the entity name
                    comp_name = comp_parts[-1]
                    #ensure the component name has its component declaration visible
                    if(entity_style == False):
                        if(comp_name.lower() not in comps):
                            #log.error("COMPONENT DECLARATION NOT FOUND: "+comp_name)
                            continue

                    #gather instantiated ports and generics
                    p_list, g_list = self.collectInstanceMaps(cseg)
                    #try to locate the unit with the given information
                    comp_unit = Unit.ICR(comp_name, lib=lib, ports=p_list, gens=g_list)
                    #add the unit as a requirement and decode it if exists
                    if(comp_unit != None):
                        u.addReq(comp_unit)
                        if(comp_unit.isChecked() == False and recursive):
                            comp_unit.getLanguageFile().decode(comp_unit, recursive)
                    else:
                        #print(cseg)
                        pass
                    #exit()  #exit for debugging 
                pass
        pass


    def _collectConnections(self, entity, tokens, is_port=True):
        '''
        Analyze VHDL code to gather data on ports and generics.

        Parameters:
            entity (Unit): the unit object who has this interface
            tokens ([str]): list of code tokens from a single statement
            is_port (bool): determine if to check for a mode value (direction)
        Returns:
            None
        '''
        #remove keyword if first item in tokens is signal or generic
        if((is_port and tokens[0].lower() == 'signal') or \
            (not is_port and tokens[0].lower() == 'constant')):
            tokens = tokens[1:]

        #find ':' to split the declaration
        i = tokens.index(':')
        mode = tokens[i+1]

        #capture direction mode
        if(is_port):
            print('mode',mode)
        #capture identifiers
        identifiers = tokens[:i]
        #remove all commas
        identifiers = list(filter(lambda a: a != ',', identifiers))
        print('ids',identifiers)
        #see if a assigment token exists
        j = len(tokens)
        if(tokens.count(':=')):
            j = tokens.index(':=')
        #capture the datatype (skip 'mode' also if port)
        dtype = tokens[i+1+int(is_port):j]
        print('dtype',dtype)

        #capture the intial value
        value = tokens[j+1:]
        print('value',value)

        #assign signals
        for c in identifiers:
            #pass to interface object
            entity.getInterface().addConnection(c, mode, dtype, value, is_port)
            pass
        pass


    def getInterface(self, u, csegs):
        '''
        Decipher and collect data on a unit's interface (entity code).

        Assumes `csegs` begins at the first statement that declares the entity.
        Exits on the first statement beginning with "end".

        Parameters:
            u (Unit): the unit file who's interface to update
            csegs ([[str]]): list of code statements (which are also lists)
        Returns:
            None
        '''
        in_generics = False
        in_ports = False
        pb_cnt = 0

        #iterate through code statements
        for cseg in csegs:
            #exit upon finding 'end'
            if(cseg[0].lower() == 'end'):
                #exit()
                return

            #enter generics or ports
            if(cseg[0].lower() == 'generic' or cseg[0].lower() == 'port'):
                in_generics = (cseg[0].lower() == 'generic')
                in_ports = (cseg[0].lower() == 'port')
                #skip keyword and opening '('
                cseg = cseg[2:]
                pb_cnt = 1
            
            #count up number of ( and ) tokens
            pb_cnt += cseg.count('(') - cseg.count(')')

            #trim off trailing ')' if at end of declarations
            if(pb_cnt == 0):
                cseg = cseg[:len(cseg)-1]

            if(in_ports or in_generics):
                print(pb_cnt)
                print(cseg)
                self._collectConnections(u, cseg, in_ports)
        pass


    def getComponents(self, pkg):
        '''
        Return a list of component names that are available in this package.

        Parameters:
            pkg (Unit): the Unit package object
        Returns:
            comps ([str]): lower-case entities found as component declarations in package
        '''
        #get the code statements
        csegs = self.spinCode()

        in_pkg = False
        #iterate through the code stream, identifying keywords as they come
        comps = []
        for cseg in csegs:
            #determine when entering package declaration
            if(cseg[0].lower() == 'package' and cseg[1] == pkg.E()):
                in_pkg = True
            elif(in_pkg == False):
                continue
            #exit status - finding 'end' with 'package' or package's identifier
            if(cseg[0].lower() == 'end'):
                if(cseg[1].lower() == pkg.E().lower() or cseg[1].lower() == 'package'):
                    in_pkg = False
            #add all component names as lower case for evaluation purposes
            if(cseg[0].lower() == 'component'):
                comps += [cseg[1].lower()]
            pass
        #print("Components from this package:",comps)
        return comps

    
    def collectInstanceMaps(self, cseg):
        '''
        Parse entity instantiation mappings to form a generics list and ports list from 
        an instantiation code statement.

        If a component was instantiated by position, '?' will appear in the list to get
        an appropriate length of number of ports mapped.

        Parameters:
            cseg ([str]): a vhdl code statement
        Returns:
            p_list ([str]): list of ports identified (all lower-case)
            g_list ([str]): list of generics identified (all lower-case)
        '''
        p_list = []
        g_list = []
        in_ports = False
        in_gens = False
        stack = 0 #stack of parentheses
        inst_by_name = (cseg.count('=>') > 0)
        #print(cseg)

        for i in range(1, len(cseg)-1):
            token = cseg[i].lower()
            if(token.lower() == 'port'):
                in_ports = True
                in_gens = False
            elif(token.lower() == 'generic'):
                in_gens = True
                in_ports = False
            elif(token == '=>'):
                if(in_gens):
                    g_list += [cseg[i-1].lower()]
                elif(in_ports):
                    p_list += [cseg[i-1].lower()]
            elif(token == '('):
                stack += 1
            elif(token == ')'):
                stack -= 1
            #add to respective lists
            if(inst_by_name == False):
                if((token == '(' and stack == 1) or token == ','):
                    if(in_gens):
                        g_list += ['?']
                    elif(in_ports):
                        p_list += ['?']
            pass
        #print(p_list, g_list)        
        return p_list, g_list
    

    pass