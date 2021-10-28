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
from .apparatus import Apparatus as apt
from .unit import Unit
from .map import Map

class Vhdl(Language):


    def __init__(self, fpath, M='', L='', N='', V=''):
        '''
        Create a VHDL language file object.

        Parameters:
            fpath (str): HDL file path
            M (str): the legohdl block market the file belongs to
            L (str): the legohdl block library the file belongs to
            N (str): the legohdl block name the file belongs to
            V (str): the legohdl block version the file belongs to
        Returns:
            None
        '''
        super().__init__(fpath, M, L, N, V)
        self._comment = "--"
        self._multi_comment = None
        self._std_delimiters = "(",")",":",";",","

        self._about_txt = self.getCommentBlock()

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
        Analyzes the current VHDL file to only identify design units and not
        complete their data. Dynamically creates self._designs attribute.

        Parameters:
            None
        Returns:
            self._designs ([Unit]): list of units found in this file
        '''
        if(hasattr(self, "_designs")):
            return self._designs

        cs = self.generateCodeStream(True, False, *self._std_delimiters)
        self._designs = []

        #looking for design units
        in_scope = False
        arch_name = ''
        for i in range(len(cs)-1):
            token = cs[i].lower()
            #search for entities           
            if(token == 'end'):
                if(in_scope and cs[i+1].lower() == name.lower()):
                    in_scope = False
                if(cs[i+1].lower() == arch_name.lower() or cs[i+1] == 'architecture'):
                    arch_name = ''
                    in_scope = False
            #skip while inside an architecture
            elif(arch_name != ''):
                continue
            elif(token == 'entity' and cs[i+1] != ':'): #ensure its not a entity instaniation
                if(not in_scope): 
                    name = cs[i+1]
                    self._designs += [Unit(self.getPath(), Unit.Design.ENTITY, self.M(), self.L(), self.N(), self.V(), cs[i+1], about_txt=self._about_txt)]
                in_scope = not in_scope
            elif(token == 'architecture'):
                arch_name = cs[i+1]
                in_scope = True
            #search for packages
            elif(token == 'package' and cs[i+1].lower() != 'body'): #ensure its not a package body
                if(not in_scope):
                    name = cs[i+1]
                    self._designs += [Unit(self.getPath(), Unit.Design.PACKAGE, self.M(), self.L(), self.N(), self.V(), cs[i+1], about_txt=self._about_txt)]
                in_scope = not in_scope

        return self._designs


    #function to determine required modules for self units
    def decipher(self, verbose=False):
        '''
        Analyzes the current VHDL file to collect data for all identified design 
        units.
        '''
        current_map = Unit.Jar[self.M()][self.L()][self.N()]


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
                        components_on_standby[L+'.'+U] = self.grabComponents(Unit.loc(u=U, l=L).getFile())
                    #add the package unit itself
                    # [!] :todo: use a "locate" method using shortcutting and prompting user if multiple components are in question
                    using_units.append(Unit.loc(u=U, l=L))
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
                    self.collectGenerics(current_map[unit_name], cs[i+1:i+end_i])  
            elif(code_word == 'port'):
                #this entity has a ports list and therefore is not a testbench
                if(in_entity):
                    # iterate through from here to collect data on an interface
                    if('end' in cs[i:]):
                        end_i = cs[i:].index('end')
                    if('generic' in cs[i:] and cs[i:].index('generic') < end_i):
                        end_i = cs[i:].index('generic')
                    #update unit's interface
                    self.collectPorts(current_map[unit_name], cs[i+1:i+end_i])
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
                            using_units.append(Unit.loc(u=entity_name, l=L, ports=pl, gens=gl))
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
                    current_map[whos_arch].addArchitecture(arch_name)
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


    def grabComponents(self, filepath):
        '''
        Return a list of components (entity names) that are available in this package.

        Parameters:
            filepath (str): path to VHDL package unit (assumed to already have apt.fs() applied)
        Returns:
            comps ([str]): entity names found as component declarations in package
        '''
        #get the vhdl file object that uses this file
        vhd = self.ProcessedFiles[filepath]
        #generate the code stream
        cs = vhd.generateCodeStream(False, False, *self._std_delimiters)

        in_pkg = False
        entity_name = pkg_name = None
        #iterate through the code stream, identifying keywords as they come
        comps = []
        for i in range(0,len(cs)):
            code_word = cs[i]
            if(code_word == 'package'):
                in_pkg = (cs[i+1] != 'body')
                if(in_pkg):
                    pkg_name = cs[i+1]
            elif(code_word == 'component'):
                if(in_pkg and cs[i-1] != 'end'):
                    #snag to entity name
                    entity_name = cs[i+1]
                    comps.append(entity_name)
            elif(code_word == 'end'):
                if(cs[i+1] == 'package' or cs[i+1] == pkg_name):
                    break
            pass
        #print("Components from this package:",comps)
        #restore file path back to its original assignment
        return comps


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


    def collectInstanceMaps(self, words):
        '''
        Parse entity instantiation mappings to form a generics list and ports list.

        Parameters:
            words ([str]): list of vhdl words to parse
        Returns:
            p_list ([str]): list of ports identified
            g_list ([str]): list of generics identified
        '''
        p_list = []
        g_list = []
        in_ports = False
        in_gens = False
        stack = 0 #stack of parentheses
        for i in range(len(words)):
            token = words[i].lower()
            if(token == 'map'):
                if(words[i-1].lower() == 'port'):
                    in_ports = True
                elif(words[i-1].lower() == 'generic'):
                    in_gens = True
                continue
            elif(token == '=>'):
                if(in_gens):
                    g_list += [words[i-1]]
                elif(in_ports):
                    p_list += [words[i-1]]
            elif(token == '('):
                stack += 1
            elif(token == ')'):
                stack -= 1
            #exit if stack is all popped
            if(stack == 0):
                in_gens = False
                if(in_ports):
                    break
                
        return p_list, g_list












# ==============================================================================
# ==============================================================================
# ==============================================================================

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