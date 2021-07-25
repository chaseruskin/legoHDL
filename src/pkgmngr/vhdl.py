from apparatus import Apparatus as apt
import logging as log
from entity import Entity

class Vhdl:

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        pass

    def decipher(self, availLibs, design_book, cur_lib):
        log.info("Deciphering VHDL file...")
        lib_headers = []
        libs_using = []
        pre_files = []
        entity_bank = dict()
        in_entity = in_arch = in_true_arch = in_pkg = False
        entity_name = arch_name = pkg_name = ent =  None
        extern_libs = list()
        port_txt = ''
        with open(self._file_path, 'r') as file:
            #read through the VHDL file code
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
                    ent = Entity(self._file_path, cur_lib+'.'+entity_name, lib_headers, pre_files)
                    ent.addExterns(extern_libs)
                    ent.setLibDeclarations(libs_using)
                    extern_libs = list()
                    pre_files = list()
                    lib_headers = list()
                #enter package
                if(words[0].lower() == "package"):
                    in_pkg = True
                    pkg_name = words[1].lower()
                    #stash all "uses" from above
                    lib_headers = list()
                #enter architecture
                if(words[0].lower() == "architecture"):
                    in_arch = True
                    arch_name = words[1]
                #find library declarations used across entire file
                if(words[0].lower() == "library" and words[1].lower().replace(";","") in availLibs):
                    libs_using.append(words[1].lower().replace(";",""))
                    pass
                #find "use" declarations
                if(words[0].lower() == "use" and not in_entity and not in_arch and not in_pkg):
                    impt = words[1].split('.')
                    #do not add if the library is not work or library is not in list of available custom libs
                    if(impt[0].lower() == 'work' or impt[0].lower() in availLibs):
                        package_name = impt[1].replace(";",'').lower()
                        if(impt[0].lower() == 'work'):
                            package_name = cur_lib+'.'+package_name
                        elif(impt[0].lower() in availLibs):
                            package_name = impt[0].lower()+'.'+package_name

                        if(impt[0].lower() in availLibs):
                            extern_libs.append((package_name,design_book[package_name]))
                            pre_files.append(design_book[package_name])
                        else:
                            #print("file needed for entity as use:",design_book[package_name])
                            pre_files.append(design_book[package_name])
                        #lib_headers.append(words[1][:len(words[1])-1])
                        comps = self.grabComponents(design_book[package_name], impt[0])
                        
                        #3 parts to word -> library.package.entity; or library.package.all;
                        if(len(impt) == 3):
                            suffix = impt[2].lower().replace(";",'')
                            if(suffix == 'all'): # add all found entities from pkg as dependencies of design
                                lib_headers = lib_headers + comps
                            else: #it is a specific component
                                lib_headers.append(impt[0]+'.'+suffix)
                        else: # a third piece was not given, check instantiations with this pkg.entity format in architecture
                            pass
                #determine if it can be a disqualified testbench entity
                if(in_entity):
                    keywords = line.lower().split()
                    if("in" in keywords or "out" in keywords or "inout" in keywords):
                        ent.setTb(False)
                    port_txt = port_txt + line

                #find component declarations
                if(words[0].lower() == "component" and in_arch):
                    ent.addDependency(cur_lib+'.'+words[1].lower())
                if(words[0].lower() == "component" and in_pkg):
                    pass
                #find in-line package usage cases from a library declaration
                if(in_entity or in_arch or in_pkg and ent != None):
                    for l in ent.getLibDeclarations():
                        for word in words:
                            #exit if we encounter a comment in this line
                            if(word.startswith("--")):
                                break
                            #try to locate where the library is used
                            foundUsage = word.find(l+".")
                            if(foundUsage > -1):
                                #find the package associated with this library call
                                nextDot = foundUsage+(len(l+"."))+word[foundUsage+(len(l+".")):].find(".")
                                package_name = word[foundUsage:nextDot]
                                if(len(package_name) > len(l)):
                                    ent.addExterns([(package_name,design_book[package_name])])
                                    ent.addPreFile(design_book[package_name])
                                pass

                if(in_arch):
                    if(words[0].lower() == 'begin'):
                        in_true_arch = True
                #find instantiations by library.package.entity
                if(len(words) > 2 and words[1] == ':' and in_arch and in_true_arch):
                    direct_entity = False
                    
                    inst = words[2]
                    inst_parts = inst.split('.')
                    
                    e_name = inst_parts[len(inst_parts)-1].lower()
                    p_name = inst_parts[len(inst_parts)-2].lower()
                    l_name = inst_parts[0].lower()
                    uniqueID = l_name+'.'+p_name
                    #direct instantiation without component declaration
                    if(words[2].lower() == 'entity'):
                        direct_entity = True
                        uniqueID = words[3].lower()
                        l_name,e_name = uniqueID.split('.')
                    
                    if(len(inst_parts) > 2 or direct_entity):
                        #add to external references if it is not from work
                        if(l_name != 'work'):
                            ent.addExterns([(uniqueID,design_book[uniqueID])])
                            ent.addPreFile(design_book[uniqueID])
                        else:
                            uniqueID = cur_lib+uniqueID[uniqueID.find('.'):]
                            l_name = cur_lib
                            ent.addPreFile(design_book[uniqueID])
                            #print("file needed for entity as use:",design_book[l_name+'.'+p_name])

                    if(uniqueID in design_book.keys()):
                        ent.addDependency(l_name+'.'+e_name)
                        #ent.appendFiles(design_book[p_name])
                        #print("file needed for entity:",ent.getName(),design_book[p_name])

                #detect when outside of entity, architecture, or package
                if(words[0].lower() == "end"):
                    if(in_entity and (entity_name+";" in words or words[1].lower().count("entity"))):
                        in_entity = False
                        ent.setPorts(port_txt)
                        port_txt = ''
                    if(in_arch and (arch_name+";" in words or words[1].lower().count("architecture"))):
                        entity_bank[cur_lib+'.'+ent.getName()] = ent
                        in_arch = in_true_arch = False
                    if(in_pkg and (pkg_name+";" in words or words[1].lower().count("package"))):
                        in_pkg = False
                pass
            file.close()
            pass
        return entity_bank
        pass

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