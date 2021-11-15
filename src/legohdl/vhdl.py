# Project: legohdl
# Script: vhdl.py
# Author: Chase Ruskin
# Description:
#   This script inherits language.py and implements the behaviors for
#   VHDL code files (syntax, deciphering).
#
#   A VHDL file has entities.

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
                entity_name = cseg[3]
                #get who owns this configuration
                dsgn_unit = Unit.Jar[self.getOwner().M()][self.getOwner().L()][self.getOwner().N()][entity_name]
                dsgn_unit.setConfig(cseg[1])
                #decode the configuration and assign it the entity
                self._getConfigurations(dsgn_unit, cseg[1])
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
        #do not decode unit again if already decoded
        if(u.isChecked()):
            return

        #get all available units availalble as components
        comps = []
        #mapping of identifiers to find and replace with value
        configurations = Map()

        in_arch = False
        in_begin = False
        arch_name = ''
        #get all code statements
        csegs = self.spinCode()

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
                #store arch_name for exit case later
                arch_name = cseg[1].lower() 
                #reset configurations (get configurations frome entity's configuration unit)
                configurations = u.getConfig(arch=arch_name)
            elif(in_arch == False):
                continue
            #inside architecture declaration section
            elif(in_begin == False):
                #detect in-line architecture configurations
                if(cseg[0].lower() == 'for'):
                    #find first ':'
                    if(cseg.count(':') == 0):
                        continue
                    #find what instances should be used for this configuration
                    inst_name = cseg[1]                    

                    i = cseg.index(':')
                    #store what identifier should be found in the architecture
                    search_for = cseg[i+1]
                    #print(inst_name)
                    #find what identifier is to replace and configure an instance
                    for j in range(i+1, len(cseg)):
                        if(cseg[j].lower() == 'use'):
                            #skip over 'entity' is that was the following keyword
                            replace_with = cseg[j+1+int(cseg[j+1].lower() == 'entity')]
                            break
                    #check if this component name has aleady been added to the Map
                    if(search_for.lower() not in configurations.keys()):
                        configurations[search_for] = Map()
                    #add configuration
                    configurations[search_for][inst_name] = replace_with
                    pass
                pass

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
                    inst_name = cseg[sp_i-1]
                    #is it an entity style?
                    entity_style = (comp_name.lower() == 'entity')
                    if(entity_style):
                        comp_name = cseg[sp_i+2]
                    #move through the code segment
                    cseg = cseg[sp_i+1:]

                    #check if this component name is to be replaced by configuration
                    if(comp_name.lower() in configurations.keys()):
                        #swap with configuration this component has specific instance name
                        if(inst_name.lower() in configurations[comp_name].keys()):
                            comp_name = configurations[comp_name][inst_name]
                            entity_style = True
                        #swap with configuration this component to be configured for 'all'
                        elif('all' in configurations[comp_name].keys()):
                            comp_name = configurations[comp_name]['all']
                            entity_style = True
                        pass

                    #default not reference a library
                    lib = None
                    #determine if a library is attached to this entity name
                    comp_parts = comp_name.split('.')
                    
                    #print(comp_parts)
                    if(len(comp_parts) == 2):
                        #must have first piece be a library name
                        if(entity_style):
                            #reference self library if it's 'work'
                            if(comp_parts[0].lower() == 'work'):
                                lib = self.getOwner().L()
                            #try to find the external library name
                            elif(comp_parts[0].lower() in u.getLibs(lower_case=True)):
                                lib = comp_parts[0]
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
                        pass

                    pass
                pass
            
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
        #capture direction mode
        mode = tokens[i+1]
        #print('mode',mode)
        #capture identifiers
        identifiers = tokens[:i]
        #remove all commas
        identifiers = list(filter(lambda a: a != ',', identifiers))
        #print('ids',identifiers)
        #see if a assigment token exists
        j = len(tokens)
        if(tokens.count(':=')):
            j = tokens.index(':=')
        #capture the datatype (skip 'mode' also if port)
        dtype = tokens[i+1+int(is_port):j]
        #print('dtype',dtype)

        #capture the intial value
        value = tokens[j+1:]
        #print('value',value)

        #determine lower and upper range bounds
        pivot = -1
        for k in range(len(dtype)):
            if(dtype[k].lower() == 'to' or dtype[k].lower() == 'downto'):
                pivot = k
                break
        bounds = self.getBounds(dtype,pivot, ('(',')'))

        #print("BOUNDS:",bounds)
        #assign signals
        for c in identifiers:
            #pass to interface object
            entity.getInterface().addConnection(c, mode, dtype, value, is_port, bounds)
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
            #print(cseg)
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

            #print(cseg)

            if(len(cseg) and in_ports or in_generics):
                #print(pb_cnt)
                #print(cseg)
                self._collectConnections(u, cseg, in_ports)
                pass
        pass


    def _getConfigurations(self, entity, cfg_name):
        '''
        Decode the translation between finding indentifiers and what they
        should be replaced with within the entity's architectures.

        Parameters:
            entity (Unit): the entity who has this configuration
            cfg_name (str): name of the configuration
        Returns:
            (Map): configurations architectures in the entity
        '''
        #print("Decoding configuration for",entity)
        #print(entity)
        
        csegs = self.spinCode()
        in_config = False
        arch = None

        for cseg in csegs:
            if(cseg[0].lower() == 'configuration' and cseg[1] == cfg_name):
                in_config = True
            elif(in_config == False):
                continue
            #determine when to exit the configuration code
            if(len(cseg) > 1 and cseg[0].lower() == 'end' and (cseg[1].lower() == 'configuration' or \
                cseg[1].lower() == cfg_name.lower())):
                break
            #print(cseg)
            if(cseg[0].lower() == 'for' and cseg.count(':')):
                inner_for = (cseg[2].lower() == 'for')
                if(inner_for):
                    #identify the architecture
                    arch = cseg[1].lower()
                
                #idenfity the instance name
                inst_name = cseg[1+(2*int(inner_for))].lower()

                #idenfity the entity to replace with
                i = cseg.index(':')
                #store what identifier should be found in the architecture
                search_for = cseg[i+1]
                #find what identifier is to replace and configure an instance
                for j in range(i+1, len(cseg)):
                    if(cseg[j].lower() == 'use'):
                        #skip over 'entity' is that was the following keyword
                        replace_with = cseg[j+1+int(cseg[j+1].lower() == 'entity')]
                        break
                #print("CONFIG:",arch,inst_name,search_for,replace_with)
                entity.linkConfig(arch, inst_name, search_for, replace_with)
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
        an instantiation code statement (all lower-case).

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

        #iterate through every token of the entity instance
        for i in range(1, len(cseg)-1):
            token = cseg[i].lower()
            #entering ports
            if(token == 'port'):
                in_ports = True
                in_gens = False
            #entering generics
            elif(token == 'generic'):
                in_gens = True
                in_ports = False
            #get the connection name
            elif(i > 1 and cseg[i-2].lower() == 'map' or cseg[i-1] == ','):
                if(in_gens):
                    g_list += [token]
                elif(in_ports):
                    p_list += [token]
            pass

        #check if positional mapping is used
        positional = (cseg.count('=>') < len(g_list)+len(p_list))

        #add to respective lists
        if(positional):
            g_list = ['?']*len(g_list)
            p_list = ['?']*len(p_list)
            pass
        #print(p_list, g_list)        
        return p_list, g_list
    

    pass