from abc import ABC, abstractmethod
from apparatus import Apparatus as apt
import logging as log

class Entity:

    def __init__(self, file, name, deps=list(), isTB=True):
        self._req_files = [file]
        self._name = name
        self._dependencies = deps
        self._is_tb = isTB

    def setTb(self, b):
        self._is_tb = b

    def appendDeps(self, deps):
        self._dependencies.append(deps)

    def appendFiles(self, file):
        self._req_files.append(file)

    def __repr__(self):
        return(f'{self._name}, {self._req_files}, {self._dependencies} tb:{self._is_tb}\n')


class Source(ABC):

    entity_bank = list() #class var of a list of entities

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        pass
    
    @abstractmethod
    def decipher(self):
        pass

    pass



class Vhdl(Source):

    def decipher(self, aL, dbook):
        log.info("Decoding VHDL file...")
        self.grabImportsVHD(self._file_path,aL, dbook)
        pass

    def grabComponents(self, filepath):
            comp_list = list()
            with open(self._file_path, 'r') as file:
                for line in file.readlines():
                    words = line.split()
                    if(len(words) == 0): #skip if its a blank line
                        continue
                    if(words[0].lower() == "component"):
                        comp_list.append(words[1].lower())
                file.close()
            print("Components:",comp_list)
            return comp_list

    # given a VHDL file, return all of its "use"/imported packages
    def grabImportsVHD(self, filepath, availLibs, dbook):
        design_book = dbook
        lib_headers = list()
        with open(filepath, 'r') as file:
            in_entity = in_arch = in_pkg = False
            entity_name = arch_name = pkg_name =  None
            ent = None
            #read through the VHDL file
            for line in file.readlines():
                #parse line into a list of its words
                words = line.split()
                if(len(words) == 0): #skip if its a blank line
                    continue
                #find when entering an entity, architecture, or package
                if(words[0].lower() == "entity"):
                    in_entity = True
                    entity_name = words[1].lower()
                    #stash all "uses" from above
                    ent = Entity(filepath, entity_name, lib_headers)
                    lib_headers = list()
                if(words[0].lower() == "package"):
                    in_pkg = True
                    pkg_name = words[1].lower()
                    #stash all "uses" from above
                    lib_headers = list()
                if(words[0].lower() == "architecture"):
                    in_arch = True
                    arch_name = words[1]
                #find "use" declarations
                if(words[0].lower() == "use" and not in_entity and not in_arch and not in_pkg):
                    impt = words[1].split('.')
                    #do not add if the library is not work or library is not in list of available custom libs
                    if(impt[0].lower() == 'work' or impt[0].lower() in availLibs):
                        #lib_headers.append(words[1][:len(words[1])-1])
                        comps = self.grabComponents(design_book[impt[1].replace(";",'').lower()])
                        
                        if(len(impt) == 3):
                            suffix = impt[2].lower().replace(";",'')
                            if(suffix == 'all'): # add all found entities from pkg as dependencies of design
                                lib_headers = lib_headers + comps
                            else: #it is a specific component
                                lib_headers.append(suffix)
                        else: # a third piece was not given, check instantiations with this pkg.entity format in architecture
                            pass
                #determine if it can be a testbench entity
                if(in_entity and ("port" in words or "port(" in words)):
                        ent.setTb(False)

                #find component declarations
                if(words[0].lower() == "component" and in_arch):
                    ent.appendDeps(words[1])
                if(words[0].lower() == "component" and in_pkg):
                    pass
                #find instantiations by package.entity
                if(len(words) > 2 and words[1] == ':' and in_arch):
                    pkg_sect = words[2].split('.')
                    e_name = pkg_sect[len(pkg_sect)-1].lower()
                    p_name = pkg_sect[len(pkg_sect)-2].lower()

                    if(p_name in design_book.keys()):
                        ent.appendDeps(e_name)
                        #ent.appendFiles(design_book[p_name])
                        print("file needed:",design_book[p_name])

                #detect when outside of entity, architecture, or package
                if(words[0].lower() == "end"):
                    if(in_entity and (entity_name+";" in words or words[1].lower().count("entity"))):
                        in_entity = False
                    if(in_arch and (arch_name+";" in words or words[1].lower().count("architecture"))):
                        self.entity_bank.append(ent)
                        in_arch = False
                    if(in_pkg and (pkg_name+";" in words or words[1].lower().count("package"))):
                        in_pkg = False
                pass
            file.close()
            pass
            
        for e in self.entity_bank:
            print(e)
        pass

    def grabEntities(self):
        ent_list = list()
        with open(self._file_path, 'r') as file:
            for line in file.readlines():
                words = line.split()
                if(len(words) == 0): #skip if its a blank line
                    continue
                if(words[0].lower() == "entity"):
                    ent_list.append(words[1].lower())
            file.close()
        print("Project-Level Entities:",ent_list)
        return ent_list

    pass


class Verilog(Source):

    def decipher(self, al, db):
        log.info("Decoding Verilog file...")
        self.grabImportsVerilog(db)
        pass

    def grabTestbenches(self):
        tb_list = list()
        files = None#glob.glob(self.__local_path+"/**/*.vhd", recursive=True)
        for f in files:
            with open(f, 'r') as file:
                in_entity = False
                entity_name = None
                is_tb = True
                for line in file.readlines():
                    words = line.lower().split()
                    if(len(words) == 0): #skip if its a blank line
                        continue
                    if(words[0].lower() == "entity"):
                        in_entity = True
                        entity_name = words[1].lower()
                    if(in_entity and ("port" in words or "port(" in words)):
                        is_tb = False
                    if(words[0].lower() == "end"):
                        if(in_entity and (entity_name+";" in words or words[1].lower().count("entity"))):
                            in_entity = False
                if(is_tb and entity_name != None):
                    tb_list.append(entity_name)
                file.close()
        print("Project-Level Testbenches:",tb_list)
        return tb_list

    def grabImportsVerilog(self, dbook):
        mod_name = None
        in_mod = False
        in_arch = False
        in_params = False
        ent = None
        with open(self._file_path, 'r') as file:
            for line in file.readlines():
                words = line.split()
                
                if(len(words) == 0):
                    continue
                if(words[0] == 'module'):
                    in_mod = True
                    in_params = False
                    is_tb = True
                    print(words)
                    mod_name = words[1].split('(')[0].replace(";","")
                    leftover = ''
                    if(words[1].count("(")):
                        leftover = words[1].split('(')[1]
                    if(words[1].count(")")):
                        in_mod = False
                    if(len(leftover) and (leftover.startswith("input") or 
                    leftover.startswith("output") or leftover.startswith("inout"))):
                        is_tb = False
                    ent = Entity(self._file_path, mod_name, isTB=is_tb)
                #check when not in module port declaration section
                if(in_mod):
                    print(words)
                    for w in words:
                        if(w == 'input' or w == 'output' or w == 'inout'):
                            ent.setTb(False)
                        if(w == 'parameter'):
                            in_params = True
                        if(w.count(")")):
                            if(in_params):
                                in_params = False
                            else:
                                in_mod = False
                                in_arch = True
                            break
                #check for using any designs/entities
                if(in_arch):
                    if(words[0] in dbook.keys()):
                        ent.appendDeps(words[0])
                    pass
                if(words[0].startswith('endmodule')):
                    self.entity_bank.append(ent)
                    in_arch = False
        pass    
        for e in self.entity_bank:
            print(e)
    pass