from .apparatus import Apparatus as apt
import logging as log
from .entity import Entity
from .unit import Unit
import sys
from .signal import Signal

class Vhdl:

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        self.writePortFormat()
        pass


    def writePortFormat(self):
        true_code = self.generateCodeStream(keep_case=True, keep_terminators=True)
        cs = self.generateCodeStream(keep_case=False, keep_terminators=True)
        print(true_code)
        in_ports = in_gens = False
        signals = []
        names = []
        for i in range(0,len(cs)):
            if(cs[i] == "generic"):
                names = []
                in_ports = False
                in_gens = True
            elif(cs[i] == "port"):
                names = []
                in_gens = False
                in_ports = True
                while true_code[i+1] != ':':
                    if(true_code[i+1] != '('):
                        names.append(true_code[i+1])
                    i = i + 1
                for n in names:
                    signals.append(n)
            elif(cs[i] == "end"):
                break
            elif(in_ports):
                if(cs[i] == ';' and cs[i+1] != 'end'):
                    signals.append(true_code[i+1])
            elif(in_gens):
                pass
        pass
        print(signals)
    
    #turn a vhdl file in to a string of words
    def generateCodeStream(self, keep_case=False, keep_terminators=False):
        code_stream = []
        #take in a single word, return a list of the broken up words
        def chopSticks(piece, *delimiters):

            def computeNextIndex(w):
                min_index = sys.maxsize
                for d in delimiters:
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
            if(piece in delimiters or index == -1):
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
                    if(not keep_terminators):
                        word = word.replace(";","")
                    #perform a split on words containing "(" ")" or ":"
                    chopped = chopSticks(word, "(",")",":",";")
                    #drop all parentheses
                    for sliced in chopped:
                        if(not keep_terminators):
                            sliced = sliced.replace("(","")
                            sliced = sliced.replace(")","")
                        if(len(sliced)):
                            code_stream = code_stream + [sliced]
        #print(code_stream)
        return code_stream

    #function to determine required modules for self units
    def decipher(self, design_book, cur_lib):
        log.info("Deciphering VHDL file...")
        log.info(self._file_path)
        #parse into words
        cs = self.generateCodeStream()

        def splitBlock(name):
            specs = name.split('.')
            if(name.find('.') == -1):
                return '',''
            if(specs[0] == 'work'):
                specs[0] = cur_lib
            return specs[0],specs[1]
        #find all design unit names (package calls or entity calls) and trace it back in design_book to the
        #block that is covers, this is a dependency,

        #libraries found with the "library" keyword span over all units in the current file
        library_declarations = [] 
        #units being used with the "use" keyword span over the following unit in the file and resets
        use_packages = []

        in_pkg = in_body = in_true_body = False
        in_entity = in_arch = in_true_arch = False
        unit_name = arch_name = body_name =  None
        isEnding = False

        def resetNamespace(uses):
            for u in uses:
                design_book[cur_lib][unit_name].addRequirement(u)
            uses = []
            return uses

        #iterate through the code stream, identifying keywords as they come
        for i in range(0,len(cs)):
            cur_word = cs[i]
            #add to file's global library calls
            if(cur_word == 'library'):
                if(cs[i+1] in design_book.keys()):
                    library_declarations.append(cs[i+1])
            elif(cur_word == 'use'):
                # this is a unit being used for the current unit being evaluated
                L,U = splitBlock(cs[i+1])
                if(L in design_book.keys()):
                    use_packages.append(design_book[L][U])
            elif(cur_word == 'entity'):
                # this is ending a entity declaration
                if(isEnding):
                    in_entity = isEnding = False
                # this is the entity declaration
                elif(not in_arch):
                    in_entity = True
                    unit_name = cs[i+1]
                # this is a component instantiation
                elif(in_arch and in_true_arch):
                    L,U = splitBlock(cs[i+1])
                    if(L in design_book.keys()):
                        use_packages.append(design_book[L][U])
                    pass
                pass
            elif(cur_word == 'port'):
                #this entity has a ports list and therefore is not a testbench
                if(in_entity):
                    design_book[cur_lib][unit_name].unsetTB()
            elif(cur_word == ":"):
                # todo - entity instantiations from within deep architecture
                if(in_true_arch):
                    P,U = splitBlock(cs[i+1])
                    for lib in library_declarations:
                        if(P in design_book[lib].keys()):
                            use_packages.append(design_book[lib][U])
                pass
            elif(cur_word == 'architecture'):
                # this is ending an architecture section
                if(isEnding):
                    use_packages = resetNamespace(use_packages)
                    in_arch = in_true_arch = isEnding = False
                # this is the architecture naming
                else:
                    in_arch = True
                    arch_name = cs[i+1]
                pass
            elif(cur_word == "component"):
                # todo - component declarations from within shallow architecture
                pass
            elif(cur_word == "begin"):
                # this is entering the deep architecture
                if(in_arch):
                    in_true_arch = True
                # this is entering the deep package body
                elif(in_body):
                    in_true_body = True
            elif(cur_word == 'package'):
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
            elif(cur_word == 'end'):
                isEnding = True
                pass
            elif(cur_word == unit_name):
                # this is ending the unit declaration
                if(isEnding):
                    if(in_true_body):
                        use_packages = resetNamespace(use_packages)
                    in_entity = in_pkg = in_body = in_true_body = isEnding = False
                else:
                    pass
            elif(cur_word == arch_name):
                # this is ending the architecture section
                if(isEnding):
                    use_packages = resetNamespace(use_packages)
                    in_arch = in_true_arch = False
                else:
                    pass
            elif(cur_word == body_name):
                # this is ending the package body section
                if(isEnding):
                    use_packages = resetNamespace(use_packages)
                    in_body = in_true_body = False
                else:
                    pass
            pass

        #print("===UNIT====",cur_lib,unit_name)

        #print("===USING===",use_packages)
        #print("===LIBS====",library_declarations)
        return design_book

    def grabComponents(self, filepath, lib):
        comp_list = list()
        with open(filepath, 'r') as file:
            for line in file.readlines():
                words = line.split()
                if(len(words) == 0): #skip if its a blank line
                    continue
                if(words[0].lower() == "component"):
                    comp_list.append(lib+'.'+words[1].lower())
            file.close()
        #print("Components:",comp_list)
        return comp_list

    pass