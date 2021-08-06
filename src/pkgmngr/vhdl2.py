from .apparatus import Apparatus as apt
import logging as log
from .entity import Entity
from .unit import Unit

class Vhdl:

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        pass

    def generateCodeStream(self):
        if(hasattr(self, "_code_stream")):
            return self._code_stream
        self._code_stream = []
        with open(self._file_path, 'r') as file:
            for line in file.readlines():
                next_line = line.split()
                for word in next_line:
                    word = word.lower()
                    word = word.replace(";","")
                    l_parenth = word.find("(")
                    r_parenth = word.find(")")
                    if(l_parenth > -1):
                        if(r_parenth > -1):
                            word = word.replace("(","").replace(")","")
                        sub_words_l = word.split("(")
                        for codeword in sub_words_l:
                                if(len(codeword)):
                                    self._code_stream = self._code_stream + [codeword]
                    elif(r_parenth > -1):
                            sub_words_r = word.split(")")
                            for codeword in sub_words_r:
                                if(len(codeword)):
                                    self._code_stream = self._code_stream + [codeword]
                    else:
                        self._code_stream = self._code_stream + [word]

        #print(self._code_stream)
        return self._code_stream

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