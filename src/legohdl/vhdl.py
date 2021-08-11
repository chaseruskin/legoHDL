from .apparatus import Apparatus as apt
import logging as log
import sys

class Vhdl:

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        self._std_parsers = "(",")",":",";"
        pass

    #function to determine required modules for self units
    def decipher(self, design_book, cur_lib, verbose):
        if(verbose):
            log.info("Deciphering VHDL file...")
            log.info(self._file_path)
        #parse into words
        cs = self.generateCodeStream(False, False, *self._std_parsers)

        def splitBlock(name):
            specs = name.split('.')
            if(name.find('.') == -1):
                return '','',''
            if(specs[0] == 'work'):
                specs[0] = cur_lib
            if(name.count('.') == 2):
                return specs[0],specs[1],specs[2]
            else:
                return specs[0],specs[1],''
        #find all design unit names (package calls or entity calls) and trace it back in design_book to the
        #block that is covers, this is a dependency,

        #libraries found with the "library" keyword span over all units in the current file
        library_declarations = [] 
        #units being used with the "use" keyword span over the following unit in the file and resets
        use_packages = []

        #key: library.package, value: list of component names
        components_on_standby = dict()

        in_pkg = in_body = in_true_body = False
        in_entity = in_arch = in_true_arch = False
        unit_name = arch_name = body_name =  None
        isEnding = False

        def resetNamespace(uses):
            global components_on_standby
            #reset to no available components at disposal from any package files
            components_on_standby = dict()
            #the current unit is now complete ("checked")
            design_book[cur_lib][unit_name].setChecked(True)
            #now try to check the unit's dependencies
            for u in uses:
                if(u not in design_book[cur_lib][unit_name].getRequirements()):
                    design_book[cur_lib][unit_name].addRequirement(u)
                #only enter recursion if the unit has not already been completed ("checked")
                if(not design_book[u.getLib()][u.getName()].isChecked()):
                    u.getVHD().decipher(design_book,u.getLib(), verbose)
            uses = []
            return uses
        #print("###")
        #print(design_book)

        #iterate through the code stream, identifying keywords as they come
        for i in range(0,len(cs)):
            code_word = cs[i]

            #add to file's global library calls
            if(code_word == 'library'):
                if(cs[i+1] in design_book.keys()):
                    library_declarations.append(cs[i+1])
            elif(code_word == 'use'):
                # this is a unit being used for the current unit being evaluated
                L,U,_ = splitBlock(cs[i+1])
                if(L in design_book.keys()):
                    #add this package as a key/value pair with its components if it has the ".all"
                    if(cs[i+1].endswith(".all")):
                        components_on_standby[L+'.'+U] = self.grabComponents(design_book[L][U].getFile())
                    #add the package unit itself
                    use_packages.append(design_book[L][U])
            elif(code_word == 'entity'):
                # this is ending a entity declaration
                if(isEnding):
                    in_entity = isEnding = False
                # this is the entity declaration
                elif(not in_arch):
                    in_entity = True
                    unit_name = cs[i+1]
                # this is a component instantiation
                elif(in_arch and in_true_arch):
                    L,U,_ = splitBlock(cs[i+1])
                    #print(L,U)
                    if(L in design_book.keys()):
                        #print(design_book[L][U])
                        use_packages.append(design_book[L][U])
                    pass
                pass
            elif(code_word == 'port'):
                #this entity has a ports list and therefore is not a testbench
                if(in_entity):
                    design_book[cur_lib][unit_name].unsetTB()
            elif(code_word == ":"):
                # todo - entity instantiations from within deep architecture using full title (library.pkg.entity)
                if(in_true_arch):
                    #the instance has a package and unit with it
                    P,U,_ = splitBlock(cs[i+1])
                    for lib in library_declarations:
                        if(P in design_book[lib].keys()):
                            use_packages.append(design_book[lib][U])
                            continue
                    #the instance may belong to a previously called package that used .all
                    entity_name = cs[i+1]
                    for pkg,comps in components_on_standby.items():
                        L,U,_ = splitBlock(pkg)
                        if(entity_name in comps):
                            #now add the unit for the entity instance itself
                            use_packages.append(design_book[L][entity_name])
                pass
            elif(code_word == 'architecture'):
                # this is ending an architecture section
                if(isEnding):
                    use_packages = resetNamespace(use_packages)
                    in_arch = in_true_arch = isEnding = False
                # this is the architecture naming
                else:
                    in_arch = True
                    arch_name = cs[i+1]
                pass
            elif(code_word == "component"):
                # todo - component declarations from within shallow architecture
                #the entity exists in the current library
                if(in_arch and cs[i+1] in design_book[cur_lib].keys()):
                    use_packages.append(design_book[cur_lib][cs[i+1]])
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
                    use_packages = resetNamespace(use_packages)
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
            elif(code_word == unit_name):
                # this is ending the unit declaration
                if(isEnding):
                    if(in_true_body):
                        use_packages = resetNamespace(use_packages)
                    in_entity = in_pkg = in_body = in_true_body = isEnding = False
                else:
                    pass
            elif(code_word == arch_name):
                # this is ending the architecture section
                if(isEnding):
                    use_packages = resetNamespace(use_packages)
                    in_arch = in_true_arch = False
                else:
                    pass
            elif(code_word == body_name):
                # this is ending the package body section
                if(isEnding):
                    use_packages = resetNamespace(use_packages)
                    in_body = in_true_body = False
                else:
                    pass
            else:
                #look for a full package call
                if(in_entity or in_arch or in_pkg or in_body):
                    L,U,E = splitBlock(code_word)
                    #append if the package exists
                    if(L in design_book.keys() and U != unit_name):
                        use_packages.append(design_book[L][U])
                    #append if the entity exists (three-part unit name (library.package.entity))
                    if(L in design_book.keys() and E != unit_name and E in design_book[L].keys()):
                        use_packages.append(design_book[L][E])
            pass

        #print("===UNIT====",cur_lib,unit_name)

        #print("===USING===",use_packages)
        #print("===LIBS====",library_declarations)
        return design_book

    #return a list of components available by this package
    def grabComponents(self, filepath):
        #reassign file path so code stream comes from right file
        tmp_file = self._file_path
        self._file_path = filepath
        cs = self.generateCodeStream(False, False, *self._std_parsers)

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
        self._file_path = tmp_file
        return comps

    #append a signal/generic string to a list of its respective type
    def addSignal(self, stash, c, stream, true_stream, declare=False, isSig=False):
        names = []
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
    def writeComponentSignals(self):
        #keep cases and keep terminators
        true_code = self.generateCodeStream(True, True, *self._std_parsers,',')
        #ignore cases and keep terminators
        cs = self.generateCodeStream(False, True, *self._std_parsers,',')
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
            elif(cs[i] == "end"):
                break
            elif(in_ports):
                if(cs[i] == ';' and cs[i+1] != 'end'):
                    signals = self.addSignal(signals, i, cs, true_code, declare=True, isSig=True)
            elif(in_gens):
                #todo [complete] : add generics as constants to be written to declarations
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
            elif(cs[i] == "end"):
                break
            elif(in_ports):
                #add all ports to list
                if(cs[i] == ';' and cs[i+1] != 'end'):
                    signals = self.addSignal(signals, i, cs, true_code, declare=False)
            elif(in_gens):
                #add all generics to list
                if(cs[i] == ';' and cs[i+1] != 'port'):
                    gens = self.addSignal(gens, i, cs, true_code, declare=False)
                pass
            pass
        #print("generics",gens)
        #print("signals",signals)
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
            mapping_txt = mapping_txt + ")\n"
        if(len(signals)):
            mapping_txt = mapping_txt + "port map(\n"
            for i in range(len(signals)):
                line = "    "+signals[i]+"=>"+signals[i]
                #add a comma if not on the last signal
                if(i != len(signals)-1):
                    line = line + ","
                mapping_txt = mapping_txt + line+"\n"
            #add necessary closing
            mapping_txt = mapping_txt + ");\n"
        #print(mapping_txt)
        return mapping_txt

    #write out the entity but as a component
    def writeComponentDeclaration(self):
        declaration_txt = ''
        with open(self._file_path, 'r') as file:
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
    
    #turn a vhdl file in to a string of words
    def generateCodeStream(self, keep_case, keep_term, *extra_parsers):
        code_stream = []
        #take in a single word, return a list of the broken up words
        def chopSticks(piece):

            def computeNextIndex(w):
                min_index = sys.maxsize
                for d in extra_parsers:
                    tmp_i = w.find(d)
                    if(tmp_i > -1 and tmp_i < min_index):
                        min_index = tmp_i
                if(min_index == sys.maxsize):
                    return -1
                else:
                    return min_index

            #print(delimiters)
            index = computeNextIndex(piece)

            chopped = []
            #return if no delimiter or if word is only the delimiter
            if(piece in extra_parsers or index == -1):
                return [piece]
            else:
                while True:
                    #append the front half
                    if(index > 0):
                        chopped.append(piece[0:index])
                    #append the demiliter itself
                    chopped.append(piece[index])
                    #see if there is another delimiter in this word to split up
                    next_index = computeNextIndex(piece[index+1:])
                    #print("next:", next_index,"word:",piece[index+1:])
                    if(next_index > -1):
                        #append what will be skipped over
                        if(next_index > 0):
                            chopped.append(piece[index+1:next_index+index+1])
                        #shorten piece to what remains
                        piece = piece[index+next_index+1:]
                        #print("new piece:",piece)
                        index = 0
                    else:
                        #append the back half
                        if(index+1 < len(piece)):
                            chopped.append(piece[index+1:])
                        break
                #print(chopped)
            return chopped
        #read the vhdl file to break into words
        with open(self._file_path, 'r') as file:
            for line in file.readlines():
                #drop rest of line if comment is started
                comment_start = line.find('--')
                if(comment_start == 0):
                    continue
                elif(comment_start > -1):
                    line = line[:comment_start]

                next_line = line.split()
                #iterate through each word in the line
                for word in next_line:
                    #convert all word's to lowercase if not keeping case sensitivity
                    if(not keep_case):
                        word = word.lower()
                    #drop all semicolons
                    if(not keep_term):
                        word = word.replace(";","")
                    #perform a split on words containing "(" ")" or ":"
                    chopped = chopSticks(word)
                    #drop all parentheses
                    for sliced in chopped:
                        if(not keep_term):
                            sliced = sliced.replace("(","")
                            sliced = sliced.replace(")","")
                        if(len(sliced)):
                            code_stream = code_stream + [sliced]
        #print(code_stream)
        return code_stream

    pass