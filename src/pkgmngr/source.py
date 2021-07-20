from abc import ABC, abstractmethod
from apparatus import Apparatus as apt
import logging as log

class Entity:

    def __init__(self, file, name, deps=list(), isTB=True):
        self._req_files = [file]
        self._name = name
        self._derivs = deps
        self._integrals = list()
        self._is_tb = isTB

    def setPorts(self, port_txt):
        self._ports = ''
        lineCount = len(port_txt.split('\n'))
        counter = 1
        for line in port_txt.split('\n'):
            if(line.lower().count("entity")):
                line = line.lower().replace("entity","component")
            self._ports = self._ports + line
            if(counter < lineCount):
                self._ports = self._ports + "\n"
            counter = counter + 1

        self.getMapping() 

    def getPorts(self):
        if(hasattr(self, '_ports')):
            return self._ports
        else:
            return ''

    def getMapping(self):
        if(hasattr(self, "_mapping")):
            return self._mapping
        self._mapping = ''
        port_txt = self.getPorts()

        signals = dict() #store all like signals together to output later

        nl = port_txt.find('\n')
        txt_list = list()
        while nl > -1:
            txt_list.append(port_txt[:nl])
            port_txt = port_txt[nl+1:]
            nl = port_txt.find('\n')
        #format header
        port_txt = txt_list[0].replace("component", "uX :")
        port_txt = port_txt.replace("is", "")+"\n"
        
        #format ports
        isGens = False
        for num in range(1, len(txt_list)-2):
            line = txt_list[num]
            if(line.count("port")):
                port_txt = port_txt + line.replace("port", "port map").strip()+"\n"
                continue
            if(line.count("generic")):
                port_txt = port_txt + line.replace("generic", "generic map").strip()+"\n"
                isGens = True
                continue
            col = line.find(':')
            if(isGens and line.count(')')):
                isGens = False
                port_txt = port_txt+")\n"
                continue

            sig_dec = line[col+1:].strip()
            spce = sig_dec.find(' ')
            sig_type = sig_dec[spce:].strip()
            if(sig_type.count(';') == 0):
                sig_type = sig_type + ';'
            sig = line[:col].strip()
            if(not isGens):
                if(not sig_type in signals):
                    signals[sig_type] = list()
                signals[sig_type].append(sig)
            
            line = "    "+line[:col].strip()+"=>"+sig
            if((not isGens and num < len(txt_list)-3) or (isGens and txt_list[num+1].count(')') == 0)):
                line = line + ',' #only append ',' to all ports but last
            port_txt = port_txt+line+"\n"
        
        #format footer
        port_txt = port_txt + txt_list[len(txt_list)-2].strip()+"\n"

        #print signal declarations
        for sig,pts in signals.items():
            line = "signal "
            for p in pts:
                line = line + p +', '
            line = line[:len(line)-2] + ' : ' + sig
            self._mapping = self._mapping + line + '\n'

        self._mapping = self._mapping + '\n' + port_txt
        if(len(signals) == 0):
            self._mapping = ''
        return self._mapping

    def isTb(self):
        return self._is_tb

    def getName(self):
        return self._name

    def getDerivs(self):
        return self._derivs

    def setTb(self, b):
        self._is_tb = b

    def addDependency(self, deps):
        if(deps.lower() not in self._derivs):
            self._derivs.append(deps)

    def addFile(self, file):
        self._req_files.append(file)

    def __repr__(self):
        return(f'''
entity: {self._name}
files: {self._req_files}
dependencies: {self._derivs}
tb: {self._is_tb}
ports: 
{self._ports}
map:
{self._mapping}
        ''')


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
            with open(filepath, 'r') as file:
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
            port_txt = ''
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
                #determine if it can be a disqualified testbench entity
                if(in_entity):
                    keywords = line.lower().split()
                    if("in" in keywords or "out" in keywords or "inout" in keywords):
                        ent.setTb(False)
                    port_txt = port_txt + line

                #find component declarations
                if(words[0].lower() == "component" and in_arch):
                    ent.addDependency(words[1])
                if(words[0].lower() == "component" and in_pkg):
                    pass
                #find instantiations by package.entity
                if(len(words) > 2 and words[1] == ':' and in_arch):
                    pkg_sect = words[2].split('.')
                    e_name = pkg_sect[len(pkg_sect)-1].lower()
                    p_name = pkg_sect[len(pkg_sect)-2].lower()

                    if(p_name in design_book.keys()):
                        ent.addDependency(e_name)
                        #ent.appendFiles(design_book[p_name])
                        print("file needed:",design_book[p_name])

                #detect when outside of entity, architecture, or package
                if(words[0].lower() == "end"):
                    if(in_entity and (entity_name+";" in words or words[1].lower().count("entity"))):
                        in_entity = False
                        ent.setPorts(port_txt)
                        port_txt = ''
                    if(in_arch and (arch_name+";" in words or words[1].lower().count("architecture"))):
                        self.entity_bank.append(ent)
                        in_arch = False
                    if(in_pkg and (pkg_name+";" in words or words[1].lower().count("package"))):
                        in_pkg = False
                pass
            file.close()
            pass
            

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