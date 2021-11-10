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
        identifiers = []

        for cseg in csegs:
            entry = False
            #exit upon finding 'end'
            if(cseg[0].lower() == 'end'):
                return

            #enter generics or ports
            if(cseg[0].lower() == 'generic' or cseg[0].lower() == 'port'):
                in_generics = (cseg[0].lower() == 'generic')
                in_ports = (cseg[0].lower() == 'port')
                entry = True

            #count up number of ( and ) tokens
            pb_cnt = cseg.count('(') - cseg.count(')')
            p_i = -1
            #skip initial opening parenthesis bracket
            if(entry):
                p_i = cseg.index('(')
            #print(cseg)
            #make sure an idenifier is in this statement
            if(cseg.count(':') == 0):
                continue
            c_i = cseg.index(':')

            #get the port names
            identifiers = cseg[p_i+1:c_i]
            #print("IDS:",identifiers)
            #adjust pb_cnt if generics/ports are on one statement
            if(entry and pb_cnt == 0):
                pb_cnt = -1
            end = len(cseg)+pb_cnt

            if(in_ports):
                #get the port direction
                route = cseg[c_i+1]
                #print("ROUTE:",route)
                #get the port data type
                dtype = cseg[c_i+2:end]
                #print("DATA TYPE:",dtype)
                l = ''
                r = ''
                tokens = ('(',')')
                for i in range(len(dtype)):
                    #switch tokens if specifying 'range'
                    if(dtype[i].lower() == 'range'):
                        tokens = (dtype[i], ':=')
                    if(dtype[i].lower() == 'to' or dtype[i].lower() == 'downto'):
                        l,r = self.getBounds(dtype, i, tokens=tokens)

                for port in identifiers:
                    if(port != ','):
                        u.getInterface().addPort(port, route, dtype, (l,r))
                pass
            elif(in_generics):
                #find if an initial value is being set
                val = []
                v_i = end
                if(cseg.count(':=')):
                    v_i = cseg.index(':=')
                    #get the generic value
                    val = cseg[v_i+1:end]
                    #print("VALUE:",val)
                #get the generic data type
                dtype = cseg[c_i+1:v_i]

                # :todo: get width/range of generic (similiar to that of port)
                
                for gen in identifiers:
                    if(gen != ','):
                        u.getInterface().addGeneric(gen, dtype, val)
            #print(cseg)
            pass
        #print(u.getInterface())
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












# ==============================================================================
# ==============================================================================
# ==============================================================================

    #function to determine required modules for self units
    @DeprecationWarning
    def decipher(self, verbose=False):
        '''
        Analyzes the current VHDL file to collect data for all identified design 
        units.
        '''
        current_map = Unit.Jar[self.M()][self.L()][self.N()]
        return
        for u in self.identifyDesigns():
            self.getRequirements(u)
        return


        def splitBlock(name):
            'Splits a string into 3 separate strings based on ".".'

            specs = name.split('.')
            if(name.find('.') == -1):
                return '','',''
            #replace with current library if name is 'work'
            if(specs[0] == 'work'):
                specs[0] = self.L()
            if(name.count('.') == 2):
                return specs[0],specs[1],specs[2]
            else:
                return specs[0],specs[1],''


        #key: library.package, value: list of component names
        components_on_standby = Map()

        def resetNamespace(uses):
            'Log all collected information to the correct design unit as exiting its scope.'
            global components_on_standby

            #reset to no available components at disposal from any package files
            components_on_standby = Map()
            #the current unit is now complete ("checked")
            current_map[unit_name].setChecked(True)
            #now try to check the unit's dependencies
            for u in uses:
                if(u not in current_map[unit_name].getRequirements()):
                    current_map[unit_name].addRequirement(u)
                #only enter recursion if the unit has not already been completed ("checked")
                if(not Unit.Jar[u.M()][u.L()][u.N()][u.E()].isChecked()):
                    #find out what Language file object has this design?
                    self.ProcessedFiles[u.getFile()].decipher()
                    
            uses = []
            return uses
        

        if(verbose or True):
            log.info("Deciphering VHDL file... "+self.getPath())

        #parse into words
        cs = self.generateCodeStream(False, False, *self._std_delimiters)
        #true_cs = self.generateCodeStream(True, False, *self._std_delimiters)

        #find all design unit names (package calls or entity calls) and trace it back in Unit.Bottle to the
        #block that is covers, this is a dependency,

        #libraries found with the "library" keyword span over all units in the current file
        library_declarations = [] 
        #units being used with the "use" keyword span over the following unit in the file and resets
        #STORES ANY DEPENDENCIES AS UNIT OBJECTS
        using_units = []

        in_pkg = in_body = in_true_body = False
        in_entity = in_arch = in_true_arch = in_config = False
        unit_name = arch_name = body_name = config_name =  ''
        isEnding = False

        #print("###")
        #print(Unit.Bottle)

        #iterate through the code stream, identifying keywords as they come
        for i in range(0,len(cs)):
            code_word = cs[i]

            #add to file's global library calls
            if(code_word == 'library'):
                if(cs[i+1] in Unit.allL()):
                    library_declarations.append(cs[i+1])
            elif(code_word == 'use'):
                # this is a unit being used for the current unit being evaluated
                L,U,_ = splitBlock(cs[i+1])
                if(L in Unit.allL()):
                    #add this package as a key/value pair with its components if it has the ".all"
                    if(cs[i+1].endswith(".all")):
                        # [!] :todo: use a "locate" method using shortcutting and prompting user if multiple components are in question
                        components_on_standby[L+'.'+U] = self.grabComponents(Unit.loc(dsgn_name=U, l=L).getFile())
                    #add the package unit itself
                    # [!] :todo: use a "locate" method using shortcutting and prompting user if multiple components are in question
                    using_units.append(Unit.loc(dsgn_name=U, lib=L))
            elif(code_word == 'entity'):
                # this is ending a entity declaration
                if(isEnding):
                    in_entity = isEnding = False
                #elif(i > 0 and cs[i-1] == 'use')
                # this is the entity declaration
                elif(not in_arch):
                    print('here2')
                    in_entity = True
                    unit_name = cs[i+1]
                    #print("ENTITY:",unit_name)
                # this is a component instantiation
                elif(in_arch and in_true_arch):
                    L,U,_ = splitBlock(cs[i+1])
                    #print(L,U)
                    print('or')
                    if(L in Unit.allL()):
                        #print(Unit.Bottle[L][U])
                        if(U in Unit.Bottle[L].keys()): #:todo:
                            using_units.append(Unit.loc(u=U, l=L))
                    pass
                pass
            elif(code_word == 'configuration'):
                #exiting the configuration section
                if(isEnding):
                    in_config = isEnding = False
                #this is a configuration declaration
                elif(not in_config):
                    in_config = True
                    config_name = cs[i+1]
                    current_map[unit_name].setConfig(config_name)
                pass
            elif(code_word == 'generic'):
                #this entity has generics
                if(in_entity):
                    # iterate through from here to collect data on an interface
                    if('end' in cs[i:]):
                        end_i = cs[i:].index('end')
                    if('port' in cs[i:] and cs[i:].index('port') < end_i):
                        end_i = cs[i:].index('port')
                    #update unit's interface
                    #self.collectGenerics(current_map[unit_name], cs[i+1:i+end_i])  
            elif(code_word == 'port'):
                #this entity has a ports list and therefore is not a testbench
                if(in_entity):
                    # iterate through from here to collect data on an interface
                    if('end' in cs[i:]):
                        end_i = cs[i:].index('end')
                    if('generic' in cs[i:] and cs[i:].index('generic') < end_i):
                        end_i = cs[i:].index('generic')
                    #update unit's interface
                    #self.collectPorts(current_map[unit_name], cs[i+1:i+end_i])
            elif(code_word == ":"):
                # :todo: entity instantiations from within deep architecture using full title (library.pkg.entity)
                if(in_true_arch):
                    #the instance has a package and unit with it
                    P,U,_ = splitBlock(cs[i+1])
                    #print(P,U)
                    for L in library_declarations:
                        if(P in Unit.Bottle[L].keys()):
                            using_units.append(Unit.loc(u=U, l=L))
                            continue
                    #the instance may belong to a previously called package that used .all
                    entity_name = cs[i+1]

                    for pkg,comps in components_on_standby.items():
                        L,U,_ = splitBlock(pkg)
                        if(entity_name in comps):
                            #now add the unit for the entity instance itself
                            if(entity_name in Unit.Bottle[L].keys()): #:todo:
                                pl, gl = self.collectInstanceMaps(cs[i:])
                                using_units.append(Unit.loc(u=entity_name, l=L, ports=pl, gens=gl))
                            else:
                                log.warning("No entity "+entity_name+" is found in source code.")
                    #or if the plain old entity name is indeed with a library
                    for L in Unit.allL():
                        if(entity_name in Unit.Bottle[L].keys()):
                            pl, gl = self.collectInstanceMaps(cs[i:])
                            using_units.append(Unit.loc(dsgn_name=entity_name, lib=L, ports=pl, gens=gl))
                pass
            elif(code_word == 'architecture'):
                # this is ending an architecture section
                if(isEnding):
                    print('ending',arch_name)
                    using_units = resetNamespace(using_units)
                    in_arch = in_true_arch = isEnding = False
                # this is the architecture naming
                else:
                    in_arch = True
                    arch_name = cs[i+1] 
                    #who's architecture is this?
                    #ex: architecture rtl of entity1
                    #skip 'of' keyword and identify entity name
                    whos_arch = cs[i+3]
                    #uncomment if running into problems with multiple entities/archs in one file
                    #unit_name = whos_arch 
                    print("beginning",arch_name)
                    #current_map[whos_arch].addArchitecture(arch_name)
                pass
            elif(code_word == "component"):
                # :todo: - component declarations from within shallow architecture
                #the entity exists in the current library
                if(in_arch and cs[i+1] in current_map.keys()):
                    using_units.append(current_map[cs[i+1]])
                pass
            elif(code_word == "begin"):
                # this is entering the deep architecture
                if(in_arch):
                    in_true_arch = True
                # this is entering the deep package body
                elif(in_body):
                    in_true_body = True
            elif(code_word == 'package'):
                if(isEnding):
                    using_units = resetNamespace(using_units)
                    in_pkg = in_body = in_true_body = isEnding = False
                else:
                    in_pkg = True
                    # this is a package declaration
                    if(cs[i+1] != 'body'):
                        unit_name = cs[i+1]
                    # this is a package body
                    else:
                        in_body = True
                        # skip over 'body' keyword to get to body name
                        body_name = cs[i+2]
            elif(code_word == 'end'):
                isEnding = True
                pass
            elif(code_word == unit_name.lower()):
                # this is ending the unit declaration
                if(isEnding):
                    if(in_true_body):
                        using_units = resetNamespace(using_units)
                    in_entity = in_pkg = in_body = in_true_body = isEnding = False
                else:
                    pass
            elif(code_word == arch_name.lower()):
                # this is ending the architecture section
                if(isEnding):
                    print('ending',arch_name)
                    using_units = resetNamespace(using_units)
                    in_arch = in_true_arch = isEnding = False
                else:
                    pass
            elif(code_word == body_name.lower()):
                # this is ending the package body section
                if(isEnding):
                    using_units = resetNamespace(using_units)
                    in_body = in_true_body = isEnding = False
                else:
                    pass
            elif(code_word == config_name.lower()):
                # this is ending the configuration section
                if(isEnding):
                    in_config = isEnding = False
                else:
                    pass
            # :todo: needs better parsing
            elif(i > 0 and cs[i-1].lower() == 'end'):
                if(isEnding):
                    print('here',in_entity,unit_name)
                    if(in_true_body == True or in_true_arch == True):
                        using_units = resetNamespace(using_units)
                    in_entity = False if(in_entity) else in_entity
                    in_arch = False if(in_arch and in_true_arch) else in_arch
                    in_true_arch = False if(in_arch and in_true_arch) else in_true_arch
                    in_pkg = False if(in_pkg) else in_pkg
                    isEnding = False
            else:
                #look for a full package call
                if(in_entity or in_arch or in_pkg or in_body):
                    L,U,E = splitBlock(code_word)
                    #append if the package exists
                    if(L in Unit.Bottle.keys() and U != unit_name.lower()):
                        if(U in Unit.Bottle[L].keys()):
                            using_units.append(Unit.loc(u=U, l=L))
                    #append if the entity exists (three-part unit name (library.package.entity))
                    if(L in Unit.Bottle.keys() and E != unit_name.lower()):
                        if(E in Unit.Bottle[L].keys()):
                            using_units.append(Unit.loc(u=E, l=L))
            pass

        #print("===USING===",using_units)
        #print("===LIBS====",library_declarations)
        pass

    @DeprecationWarning
    def collectPorts(self, unit, words):
        '''
        From a subset of the code stream, parse through and create HDL Port
        objects. Modifies unit's _interface attribute.

        Parameters:
            unit (Unit): the unit who's interface the ports belong to
            words ([str]): the subset of code stream
        Returns:
            None
        '''
        #trim off surrounding '(' ')'
        words = words[1:len(words)-1]
        #pivot on every ':'
        s_cnt = words.count(':')
        for s in range(s_cnt):
            sep = words.index(':')
            #name is one position before ':'
            sig_name = words[sep-1]
            #way is one position after ':'
            sig_way = words[sep+1]
            #go up to the next seperator - 1 for the port type
            stop_bit = len(words)
            if(':' in words[sep+2:]):
                stop_bit = sep+2 + words[sep+2:].index(':')-1
            #get the list of remaining things for this port's type
            sig_type = words[sep+2:stop_bit]
            #proceed to next delimiter
            unit.getInterface().addPort(sig_name, sig_way, sig_type)
            words = words[sep+1:]
        pass

    @DeprecationWarning
    def collectGenerics(self, unit, words):
        '''
        From a subset of the code stream, parse through and create HDL Generic
        objects. Modifies unit's _interface attribute.

        Parameters:
            unit (Unit): the unit who's interface the generics belong to
            words ([str]): the subset of code stream
        Returns:
            None
        '''

        #trim off surrounding '(' ')'
        words = words[1:len(words)-1]
        #print(words)
        while (words.count(':') > 0):
            sep = words.index(':')
            #store the generic's name
            gen_name = words[sep-1]
            #extract the generic's type
            stop_bit = len(words)
            next_sep = 1
            if(words[sep+1:].count('=')):
                next_sep = words[sep+1:].index('=') - 1
            stop_bit = sep+1 + next_sep

            #store the generic's type
            gen_type = words[sep+1:stop_bit]
            #continue to next delimiter
            words = words[stop_bit+2:]

            #extract the initial value for the generic
            stop_bit = len(words)
            if(':' in words):
                stop_bit = words.index(':') - 1
            gen_value = words[:stop_bit]

            unit.getInterface().addGeneric(gen_name, gen_type, gen_value)
            pass
        pass
    #append a signal/generic string to a list of its respective type
    @DeprecationWarning
    def addSignal(self, stash, c, stream, true_stream, declare=False, isSig=False):
        names = []
        #no signals are found on this line if ':' is not present
        if(':' not in true_stream):
            return stash

        while true_stream[c+1] != ':':
            if(true_stream[c+1] != '(' and true_stream[c+1] != ','):
                names.append(true_stream[c+1])
            c = c + 1

        #go through all names found for this signal type
        for n in names:
            line = n
            #add details needed for signal declaration
            if(declare):
                #modifications if declaring constant
                t_type = 'constant'
                z = 2
                #modifications if declaring signal
                if(isSig):
                    t_type = 'signal'
                    z = 3
                #formulate the line to declare the signal/constant
                line = t_type+' ' + line + ' :'
                #find the index where this port declaration ends (skip over ':' and direction keyword)
                i_term = true_stream[c+z:].index(';')
                #this was the last port declaration so truncate off the extra ')'
                if(stream[c+z+i_term+1] == 'end' or stream[c+z+i_term+1] == 'port'):
                    i_term = i_term-1
                #write out each word
                prev_w = ''
                for w in true_stream[c+z:c+z+i_term]:
                    #don't add a surround ' ' if w is a parenthese
                    if(w != '(' and w != ')' and prev_w != '(' and prev_w != ')' and w != '='):
                        line = line + ' '
                    line = line + w
                    prev_w = w
                line = line + ';'
            stash.append(line)
        return stash


    #generate string of component's signal declarations to be interfaced with the port
    @DeprecationWarning
    def writeComponentSignals(self):
        #keep cases and keep terminators
        true_code = self.generateCodeStream(True, True, *self._std_delimiters)
        #ignore cases and keep terminators
        cs = self.generateCodeStream(False, True, *self._std_delimiters)

        in_ports = in_gens = False
        signals = []
        constants = []
        #iterate through all important code words
        for i in range(0,len(cs)):
            if(cs[i] == "generic"):
                in_ports = False
                in_gens = True
                constants = self.addSignal(constants, i, cs, true_code, declare=True, isSig=False)
            elif(cs[i] == "port"):
                in_gens = False
                in_ports = True
                signals = self.addSignal(signals, i, cs, true_code, declare=True, isSig=True)
            elif(cs[i] == "end" or cs[i] == 'component' or cs[i] == 'package'):
                break
            elif(in_ports):
                if(cs[i] == ';' and cs[i+1] != 'end'):
                    signals = self.addSignal(signals, i, cs, true_code, declare=True, isSig=True)
            elif(in_gens):
                # :done: add generics as constants to be written to declarations
                if(cs[i] == ';' and cs[i+1] != 'end' and cs[i+1] != 'port'):
                    constants = self.addSignal(constants, i, cs, true_code, declare=True, isSig=False)
                pass
        pass
        signals_txt = ''
        #write all identified constants
        for const in constants:
            signals_txt = signals_txt + const + "\n"
        #write an extra new line to separate constants from signals
        if(len(constants)):
            signals_txt = signals_txt + "\n"
        #write all identified signals
        for sig in signals:
            signals_txt = signals_txt + sig + '\n'
        #print(signals_txt)
        return signals_txt


    #write out the mapping instance of an entity (can be pure instance using 'entity' keyword also)
    @DeprecationWarning
    def writeComponentMapping(self, pureEntity=False, lib=''):
        true_code = self.generateCodeStream(True, True, "(",")",":",";",',')
        cs = self.generateCodeStream(False, True, "(",")",":",";",',')
        #store names of all generics
        gens = []
        #store names of all ports
        signals = []
        in_ports = in_gens = False
        entity_name = ''
        for i in range(0,len(cs)):
            if(cs[i] == 'entity'):
                entity_name = true_code[i+1]
            if(cs[i] == "generic"):
                in_ports = False
                in_gens = True
                #add first line of generics
                gens = self.addSignal(gens, i, cs, true_code, declare=False)
            elif(cs[i] == "port"):
                in_gens = False
                in_ports = True
                #add first line of signals
                signals = self.addSignal(signals, i, cs, true_code, declare=False)
            elif(cs[i] == "end" or cs[i] == 'component' or cs[i] == 'package'):
                break
            elif(in_ports):
                #add all ports to list
                if(cs[i] == ';' and cs[i+1] != 'end'):
                    signals = self.addSignal(signals, i, cs, true_code, declare=False)
            elif(in_gens):
                #add all generics to list
                if(cs[i] == ';' and cs[i+1] != 'port' and cs[i+1] != 'end'):
                    gens = self.addSignal(gens, i, cs, true_code, declare=False)
                pass
            pass
        #print("generics",gens)
        #print("signals",signals)
        
        if(len(gens) == 0 and len(signals) == 0):
            return ''

        mapping_txt = "uX : "+entity_name+"\n"
        #reassign beginning of mapping of it will be a pure entity instance
        if(pureEntity):
            mapping_txt = "uX : entity "+lib+"."+entity_name+"\n"

        #if we have generics to map
        if(len(gens)):
            mapping_txt = mapping_txt + "generic map(\n"
            for i in range(len(gens)):
                line =  "    "+gens[i]+"=>"+gens[i]
                #add a comma if not on last generic
                if(i != len(gens)-1):
                    line = line + ","
                mapping_txt = mapping_txt + line+"\n"
            #add necessary closing
            mapping_txt = mapping_txt + ")"
        if(len(signals)):
            if(len(gens)):
                mapping_txt = mapping_txt + "\n"
            mapping_txt = mapping_txt + "port map(\n"
            for i in range(len(signals)):
                line = "    "+signals[i]+"=>"+signals[i]
                #add a comma if not on the last signal
                if(i != len(signals)-1):
                    line = line + ","
                mapping_txt = mapping_txt + line+"\n"
            #add necessary closing
            mapping_txt = mapping_txt + ")"
        #print(mapping_txt)
        mapping_txt = mapping_txt + ";\n"
        return mapping_txt


    #write out the entity but as a component
    @DeprecationWarning
    def writeComponentDeclaration(self):
        declaration_txt = ''
        with open(self.getPath(), 'r') as file:
            in_entity = False
            #iterate through file lines
            for line in file.readlines():
                words = line.split()
                if(len(words) == 0):
                    continue
                if(words[0].lower() == 'entity'):
                    in_entity = True
                    declaration_txt = 'component'
                    line = line[len('entity'):]
                if(words[0].lower() == 'end'):
                    declaration_txt = declaration_txt + 'end component;'
                    break
                if(in_entity):
                    declaration_txt = declaration_txt + line
        #print(declaration_txt)
        return declaration_txt

    pass