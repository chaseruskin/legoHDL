import os, yaml, shutil
from datetime import date
import stat
import glob, git
import logging as log
from .market import Market
from .apparatus import Apparatus as apt
from .graph import Graph 
from .unit import Unit


#a Block is a package/module that is signified by having the marker file
class Block:

    allLibs = []

    def __init__(self, title=None, path=None, remote=None, new=False, excludeGit=False, market=None):
        self.__metadata = dict()
        self.__lib = ''
        self.__name = ''
        self.__remote = remote #remote cannot be reconfigured through legohdl after setting
        self.__market = market
 
        if(title != None):
            self.__lib,self.__name = Block.split(title)
        if(path != None):
            self.__local_path = apt.fs(path)
            #print(path)
            if(self.isValid()):
                self.loadMeta()
                if(not excludeGit):
                    self.__repo = git.Repo(self.__local_path)
                self.__name = self.getMeta("name")
            return

        if(remote != None):
            self.__remote = remote #pass in remote object
        
        self.__local_path = apt.fs(apt.getLocal()+"/"+self.__lib+"/"+self.__name+'/')
        #configure remote url
        #if(apt.linkedRemote()):
            #self.__remote_url = apt.SETTINGS['remote']+'/'+self.__lib+"/"+self.__name+".git"
        if(self.isValid()):
            log.debug("Checking block here: "+self.__local_path)
            self.__repo = git.Repo(self.__local_path)
            #load in metadata from YML
            self.loadMeta()
        elif(new): #create a new project
            if(self.isLinked() and False):
                try:
                    lp = self.__local_path.replace(self.__name, "")
                    os.makedirs(lp, exist_ok=True)
                    git.Git(lp).clone(self.__remote)
                    url_name = self.__remote[self.__remote.rfind('/')+1:self.__remote.rfind('.git')]
                    os.rename(lp+url_name, lp+self.__name)
                    log.info('Project already exists on remote code base; downloading now...')
                    return
                except:
                    log.warning("could not clone")
                    pass
            self.create() #create the repo and directory structure
        pass

    def getPath(self):
        return self.__local_path

    def cache(self):
        os.makedirs(apt.WORKSPACE+"cache/"+self.getMeta("library")+"/", exist_ok=True)
        cache_dir = apt.WORKSPACE+"cache/"+self.getMeta("library")+"/"
        git.Git(cache_dir).clone(self.__remote)
        pass

    def getTitle(self):
        return self.getLib()+'.'+self.getName()

    def clone(self, src=None, dst=None):
        local = apt.getLocal()+"/"+self.getLib()+"/"
        #grab library level path (default location)
        n = local.rfind(self.getName())
        
        if(src == None):
            src = self.__remote
        if(dst == None):
            dst = local[:n]
    
        log.debug(dst)
        os.makedirs(dst, exist_ok=True)
        self.__repo = git.Git(dst).clone(src)
        self.loadMeta()
        self.__repo = git.Repo(dst+"/"+self.getName())
        #if downloaded from cache, make a master branch
        if(len(self.__repo.heads) == 0):
            self.__repo.git.checkout("-b","master")

    def getVersion(self):
        return self.getMeta('version')

    def release(self, ver='', options=None):
        major,minor,patch = self.sepVer(self.getVersion())
        if(ver != '' and self.biggerVer(ver,self.getVersion()) == self.getVersion()):
            next_min_version = "v"+str(major)+"."+str(minor)+"."+str(patch+1)
            exit(log.error("Invalid version selection! Next minimum version is: "+next_min_version))
        print("Uploading v"+str(major)+"."+str(minor)+"."+str(patch),end='')
        if(ver == ''):
            if(options.count("maj")):
                major += 1
                minor = patch = 0
            elif(options.count("min")):
                minor += 1
                patch = 0
            elif(options.count("fix")):
                patch += 1
            else:
                return
            ver = 'v'+str(major)+'.'+str(minor)+'.'+str(patch)
        else:
            ver = ver[1:]
            r_major,r_minor,r_patch = self.sepVer(ver)

            ver = 'v'+str(r_major)+'.'+str(r_minor)+'.'+str(r_patch)
        print(" -> ",end='')
        print(ver)
        if(ver != '' and ver[0] == 'v'):
            self.__metadata['version'] = ver[1:]
            self.save()
            log.info("Saving...")
            if(options != None and options.count('strict')):
                self.__repo.index.add(apt.MARKER)
            else:   
                self.__repo.git.add(update=True)
                self.__repo.index.add(self.__repo.untracked_files)
            self.__repo.index.commit("Release version -> "+self.getVersion())
            self.__repo.create_tag(ver)
            #push to remote codebase!!
            if(self.__remote):
                self.pushRemote()
            #publish on market/bazaar!
            if(self.__market):
                self.__market.publish(self.__metadata, options)
        pass

    def legoLockFile(self):
        body = """
name:
library:
version:
summary:
toplevel:
bench:
remote:
market:
derives: {}
integrates: {}
        """
        return body

    @classmethod
    def biggerVer(cls, lver, rver):
        l1,l2,l3 = cls.sepVer(lver)
        r1,r2,r3 = cls.sepVer(rver)
        if(l1 < r1):
            return rver
        elif(l1 == r1 and l2 < r2):
            return rver
        elif(l1 == r1 and l2 == r2 and l3 <= r3):
            return rver
        return lver
    
    @classmethod
    def sepVer(cls, ver):
        if(ver == ''):
            return 0,0,0
        if(ver[0] == 'v'):
            ver = ver[1:]

        first_dot = ver.find('.')
        last_dot = ver.rfind('.')

        try:
            r_major = int(ver[:first_dot])
        except:
            r_major = 0
        try:
            r_minor = int(ver[first_dot+1:last_dot])
        except:
            r_minor = 0
        try:
            r_patch = int(ver[last_dot+1:])
        except:
            r_patch = 0
        return r_major,r_minor,r_patch

    def loadMeta(self):
        #print("-",self.getName(),'-',end='')
        with open(self.metadataPath(), "r") as file:
            self.__metadata = yaml.load(file, Loader=yaml.FullLoader)
            file.close()

        if(self.getMeta('derives') == None):
            self.__metadata['derives'] = dict()

        if(self.getMeta('integrates') == None):
            self.__metadata['integrates'] = dict()
        if('remote' in self.__metadata.keys()):
            if(self.__remote != None):
                self.__metadata['remote'] = self.__remote
            else:
                self.__remote = self.__metadata['remote']
        if('market' in self.__metadata.keys()):
            if(self.__market != None):
                self.__metadata['market'] = self.__market.getName()
            elif(self.getMeta("market") != None and self.getMeta("market") in apt.SETTINGS['market'].keys()):
                self.__market = Market(self.__metadata['market'], apt.SETTINGS['market'][self.__metadata['market']])
        pass


    def fillTemplateFile(self, newfile, templateFile):
        #ensure this file doesn't already exist
        newfile = apt.fs(newfile)
        if(os.path.isfile(newfile)):
            log.info("File already exists")
            return
        log.info("Creating new file...")
        #find the template file to use
        extension = '.'+self.getExt(newfile)
        fileName = ''
        last_slash = newfile.rfind('/')
        if(extension == '.'):
            fileName = newfile[last_slash+1:]
        else:
            i = newfile.rfind(extension)
            fileName = newfile[last_slash+1:i]

        template_ext = self.getExt(templateFile)
        if(template_ext == ''):
            templateFile = templateFile + extension
        replacements = glob.glob(apt.TEMPLATE+"**/"+templateFile, recursive=True)
        #copy the template file into the proper location
        if(len(replacements) < 1):
            exit(log.error("Could not find "+templateFile+" file in template project"))
        else:
            templateFile = replacements[0]

        shutil.copy(templateFile, self.__local_path+newfile)
        newfile = self.__local_path+newfile
        today = date.today().strftime("%B %d, %Y")
        file_in = open(newfile, "r")
        lines = []
        #find and replace all proper items
        for line in file_in.readlines():
            line = line.replace("template", fileName)
            line = line.replace("%DATE%", today)
            line = line.replace("%AUTHOR%", apt.SETTINGS["author"])
            line = line.replace("%PROJECT%", self.getTitle())
            lines.append(line)
            file_in.close()
        file_out = open(newfile, "w")
        #rewrite file to have new lines
        for line in lines:
            file_out.write(line)
        file_out.close()
        pass

    def create(self, fresh=True, git_exists=False):
        log.info('Initializing new project')
        if(fresh):
            if(os.path.isdir(apt.TEMPLATE)):
                shutil.copytree(apt.TEMPLATE, self.__local_path)
            else:
                os.makedirs(self.__local_path, exist_ok=True)
        
        open(self.__local_path+apt.MARKER, 'w').write(self.legoLockFile())
        
        if(not git_exists):
            self.__repo = git.Repo.init(self.__local_path)
        else:
            self.__repo = git.Repo(self.__local_path)
    
        if(self.isLinked()):
            self.__repo.create_remote('origin', self.__remote) #attach to remote code base

        #run the commands to generate new project from template
        #file to find/replace word 'template'
        if(fresh):
            replacements = glob.glob(self.__local_path+"/**/*template*", recursive=True)
            file_swaps = list()
            for f in replacements:
                if(os.path.isfile(f)):
                    file_swaps.append((f,f.replace('template', self.__name)))

            today = date.today().strftime("%B %d, %Y")
            for x in file_swaps:
                file_in = open(x[0], "r")
                file_out = open(x[1], "w")
                for line in file_in:
                    line = line.replace("template", self.__name)
                    line = line.replace("%DATE%", today)
                    line = line.replace("%AUTHOR%", apt.SETTINGS["author"])
                    line = line.replace("%PROJECT%", self.getTitle())
                    file_out.write(line) #insert date into template
                file_in.close()
                file_out.close()
                os.remove(x[0])
        
        self.loadMeta() #generate fresh metadata fields
        self.__metadata['name'] = self.__name
        self.__metadata['library'] = self.__lib
        self.__metadata['version'] = '0.0.0'
        self.identifyTop()
        log.debug(self.getName())
        self.save() #save current progress into yaml
        self.__repo.index.add(self.__repo.untracked_files)
        self.__repo.index.commit("Initializes project")
        if(self.__remote != None):
            log.info('Generating new remote repository...')
            # !!! set it up to track
            print(str(self.__repo.head.reference))
            self.__repo.git.push("-u","origin",str(self.__repo.head.reference))
            #self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
        else:
            log.warning('No remote code base attached to local repository')
        pass

    #generate new link to remote if previously unestablished
    def genRemote(self):
        if(self.isLinked()):
            try: #attach to remote code base
                self.__repo.create_remote('origin', self.__remote) 
            except: #relink origin to new remote url
                print(self.__repo.remotes.origin.url)
                remote_url = self.getMeta("remote")
                if(remote_url == None):
                    return
                with self.__repo.remotes.origin.config_writer as cw:
                    cw.set("url", remote_url)
            #now set it up to track
            self.__repo.git.push("-u","origin",str(self.__repo.head.reference))
            self.__repo.remotes.origin.push("--tags")
        pass

    def pushRemote(self):
        self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
        self.__repo.remotes.origin.push("--tags")

    def getName(self):
        return self.__name

    @classmethod
    def fetchLibs(cls, reg_libs):
        cls.allLibs = reg_libs

    def getLib(self):
        try:
            if(self.getMeta("library") == None):
                return ''
            return self.getMeta("library")
        except:
            return self.__lib

    def getMeta(self, key=None):
        if(key == None):
            return self.__metadata
        else:
            return self.__metadata[key]

    def pull(self):
        self.__repo.remotes.origin.pull()

    def pushYML(self, msg):
        self.save()
        self.__repo.index.add(apt.MARKER)
        
        self.__repo.index.commit(msg)
        
        if(self.isLinked()):
            self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
            self.__repo.remotes.origin.push("--tags")

    #return true if the requested project folder is a valid Block package
    def isValid(self):
        try:
            return os.path.isfile(self.metadataPath())
        except:
            return False
        pass

    def metadataPath(self):
        return self.__local_path+apt.MARKER

    def show(self):
        with open(self.metadataPath(), 'r') as file:
            for line in file:
                print(line,sep='',end='')
    
    def load(self):
        cmd = apt.SETTINGS['editor']+" "+self.__local_path
        os.system(cmd)
        pass

    def save(self):
        #unlock metadata to write to it
        os.chmod(self.metadataPath(), stat.S_IWOTH | stat.S_IWGRP | stat.S_IWUSR | stat.S_IWRITE)
        #write back YAML info
        order = ['name', 'library', 'version', 'summary', 'toplevel', 'bench', 'remote', 'market', 'derives', 'integrates']
        #a little magic to save YAML in custom order for easier readability
        with open(self.metadataPath(), "w") as file:
            for key in order:
                #pop off front key/val pair of yaml data
                single_dict = {}
                single_dict[key] = self.getMeta(key)
                yaml.dump(single_dict, file)
                pass
            pass
            file.close()
        #lock metadata into read-only mode
        os.chmod(self.metadataPath(), stat.S_IROTH | stat.S_IRGRP | stat.S_IREAD | stat.S_IRUSR)
        pass

    def isLinked(self):
        return self.__remote != None

    def install(self, cache_dir, ver=None, src=None):
        #CMD: git clone (rep.git_url) (location) --branch (rep.last_version) --single-branch
        if(ver == None):
            ver = self.getVersion()
        
        if(ver == 'v0.0.0'):
            exit(log.error('No available version'))

        log.debug("version "+ver)
        
        if(src == None and self.__remote != None):
            src = self.__remote
        elif(src == None):
            src = self.__local_path

        ver = "v"+ver
        git.Git(cache_dir).clone(src,"--branch",ver,"--single-branch")
        self.__local_path = cache_dir+self.getName()+"/"
        self.__repo = git.Repo(self.__local_path)
        self.__repo.git.checkout(ver)
        self.loadMeta()
        return

    def scanLibHeaders(self, entity):
        ent = self.grabUnits()[self.getLib()][entity]
        filepath = ent.getFile()

        #open top-level file and inspect lines for using libraries
        lib_headers = list()
        with open(filepath) as file:
            for line in file:
                line = line.lower()
                words = line.split()
                if(len(words) == 0):
                    continue
                if(words[0] == 'library' or words[0] == 'use'):
                    lib_headers.append(line)
                if(words[0] == "entity"):
                    break
            file.close()
        return lib_headers

    def updateDerivatives(self, block_list):
        #print("Derives:",block_list)
        update = False
        if(len(self.__metadata['derives']) != len(block_list)):
            update = True
        for b in block_list:
            if(b not in self.__metadata['derives']):
                update = True
                break
        if(update):
            self.__metadata['derives'] = list(block_list)
            self.pushYML("Updates project derivatives")
        pass

    def gatherSources(self, ext=[".vhd"]):
        srcs = []
        for e in ext:
            srcs = srcs + glob.glob(self.__local_path+"/**/*"+e, recursive=True)
        #print(srcs)
        return srcs
    
    @classmethod
    def getExt(cls, file_path):
        dot = file_path.rfind('.')
        if(dot == -1):
            return ''
        else:
            return file_path[dot+1:]
    
    @classmethod
    def split(cls, dep):
        dot = dep.find('.')
        lib = dep[:dot]
        dot2 = dep[dot+1:].find('.')
        if(dot2 == -1):
            #use semi-colon if only 1 dot is marked
            dot2 = dep[dot+1:].find(';')
        if(dot2 == -1):
            dot2 = len(dep)
        name = dep[dot+1:dot+1+dot2]
        return lib,name

    #auto detect top-level design entity
    def identifyTop(self):
        if(hasattr(self, "_top")):
            return self._top
        units = self.grabUnits()
        top_contenders = list(units[self.getLib()].keys())
        #log.debug(top_contenders)
        self._top = None
        for name,unit in list(units[self.getLib()].items()):
            #if the entity is value under this key, it is lower-level
            if(unit.isTB() or unit.isPKG()):
                top_contenders.remove(name)
                continue
                
            for dep in unit.getRequirements():
                if(dep._unit in top_contenders):
                    top_contenders.remove(dep._unit)

        if(len(top_contenders) == 0):
            log.error("No top level detected.")
        elif(len(top_contenders) > 1):
            log.warning("Multiple top levels detected. "+str(top_contenders))
            validTop = input("Enter a valid toplevel entity: ").lower()
            while validTop not in top_contenders:
                validTop = input("Enter a valid toplevel entity: ").lower()
            
            top_contenders = [validTop]
        if(len(top_contenders) == 1):
            self._top = units[self.getLib()][top_contenders[0]]

            log.info("DETECTED TOP-LEVEL ENTITY: "+self._top.getName())
            self.identifyBench(self._top.getName(), save=True)
            #break up into src_dir and file name
            #add to metadata, ensure to push meta data if results differ from previously loaded
            if(self._top.getName() != self.getMeta("toplevel")):
                log.debug("TOPLEVEL: "+self._top.getName())
                self.__metadata['toplevel'] = self._top.getName()
                self.pushYML("Auto updates top level design module to "+self.getMeta("toplevel"))
            pass
        return self._top

    #determine what testbench is used for the top-level design entity
    def identifyBench(self, entity_name, save=False):
        if(hasattr(self, "_bench")):
            return self._bench
        units = self.grabUnits()
        benches = []
        for unit in units[self.getLib()].values():
            #print(unit)
            for dep in unit.getRequirements():
                if(dep.getLib() == self.getLib() and dep.getName() == entity_name and unit.isTB()):
                    benches.append(unit)
        self._bench = None    
        if(len(benches) == 1):
            self._bench = benches[0]
        elif(len(benches) > 1):
            top_contenders = []
            for b in benches:
                top_contenders.append(b.getName())
            log.warning("Multiple top level testbenches detected. "+str(top_contenders))
            validTop = input("Enter a valid toplevel testbench: ").lower()
            #force ask for the required testbench choice
            while validTop not in top_contenders:
                validTop = input("Enter a valid toplevel testbench: ").lower()
            #assign the testbench entered by the user
            self._bench = units[self.getLib()][validTop]

        if(self._bench != None):
            log.info("DETECTED TOP-LEVEL BENCH: "+self._bench.getName())
            if(save and self.getMeta("bench") != self._bench.getName()):
                self.__metadata['bench'] = self._bench.getName()
                self.pushYML("Auto updates testbench module to "+self.getMeta("bench"))
            return self._bench #return the entity
        else:
            log.warning("No testbench configured for "+entity_name)
            return None

    def identifyTopDog(self, top, tb):
        #override auto detection
        if(top == None):
            top_ent = self.identifyTop()
            if(top_ent != None):
                top = top_ent.getName()
        top_dog = top
        #find the top's testbench
        bench_ent = self.identifyBench(top)
        #override auto detection if manually set testbench
        if(tb != None):
            top_dog = tb
        #set auto detected testbench
        elif(bench_ent != None):
            #print(bench_ent)
            tb = bench_ent.getName()
            top_dog = tb
        return top_dog,top,tb

    #helpful for readable debugging
    def printUnits(self):
        print("===UNIT BOOK===")
        for L in self.grabUnits().keys():
            print("===LIBRARY===",L)
            for U in self.grabUnits()[L]:
                print(self.grabUnits()[L][U])
        print("===END UNIT BOOK===")
        pass

    def grabUnits(self, toplevel=None, override=False):
        if(hasattr(self, "_unit_bank") and not override):
            return self._unit_bank
        elif(override):
            #reset graph
            Unit.Hierarchy = Graph()
            
        #get all possible units (status: incomplete)
        self._unit_bank = self.grabDesigns(override, "cache","current")
       
        #todo : only start from top-level unit if it exists
        #gather all project-level units
        project_level_units = self.grabDesigns(False, "current")[self.getLib()]
        for unit in project_level_units.values():
            if(unit.getName() == toplevel or toplevel == None):
                self._unit_bank = unit.getVHD().decipher(self._unit_bank, self.getLib(), override)
        #self.printUnits()
        return self._unit_bank

    #return incomplete unit objects from cache and/or current block
    def grabDesigns(self, override, *args):
        design_book = dict()
        if("current" in args):
            design_book = self.grabCurrentDesigns(override).copy()
            pass
        if("cache" in args):
            design_book = apt.merge(self.grabCacheDesigns(override),design_book)
            pass
        return design_book

    #return dictionary of entities with their respective files as values
    #all possible entities or packages to be used in current project
    def grabCacheDesigns(self, override):
        if(hasattr(self, "_cache_designs") and not override):
            return self._cache_designs
        self._cache_designs = dict()
        files = (glob.glob(apt.WORKSPACE+"lib/**/*.vhd", recursive=True))
        files = files + glob.glob(apt.WORKSPACE+"cache/**/*.vhd", recursive=True)

        for f in files:
            L,N = self.grabExternalProject(f)
            #do not add the cache files of the current level project
            if(L == self.getLib() and N == self.getName()):
                continue
            with open(f, 'r') as file:
                for line in file.readlines():
                    words = line.split()
                    #skip if its a blank line
                    if(len(words) == 0): 
                        continue
                    #create new library dictionary if DNE
                    if(L not in self._cache_designs.keys()):
                        self._cache_designs[L] = dict()
                    #add entity units
                    if(words[0].lower() == "entity"):
                        self._cache_designs[L][words[1].lower()] = Unit(f,Unit.Type.ENTITY,L,N,words[1].lower())
                    #add package units
                    elif((words[0].lower() == "package" and words[1].lower() != 'body')):
                        self._cache_designs[L][words[1].lower()] = Unit(f,Unit.Type.PACKAGE,L,N,words[1].lower())
                file.close()
        #log.debug("Cache-Level designs: "+str(self._cache_designs))
        return self._cache_designs

    def grabCurrentDesigns(self, override):
        if(hasattr(self, "_cur_designs") and not override):
            return self._cur_designs
        self._cur_designs = dict()

        L,N = self.split(self.getTitle())

        #create new library dictionary if DNE
        if(L not in self._cur_designs.keys()):
            self._cur_designs[L] = dict()
        files = self.gatherSources()
        for f in files:
            with open(f, 'r') as file:
                for line in file.readlines():
                    words = line.split()
                    #skip if its a blank line
                    if(len(words) == 0): 
                        continue
                    #add entity units
                    if(words[0].lower() == "entity"):
                        self._cur_designs[L][words[1].lower()] = Unit(f,Unit.Type.ENTITY,L,N,words[1].lower())
                    #add package units
                    elif((words[0].lower() == "package" and words[1].lower() != 'body')):
                        self._cur_designs[L][words[1].lower()] = Unit(f,Unit.Type.PACKAGE,L,N,words[1].lower())
                file.close()
        #log.debug("Project-Level Designs: "+str(self._cur_designs))
        return self._cur_designs
    
    #search for the projects attached to the external package
    @classmethod
    def grabExternalProject(cls, path):
        #use its file to find out what project uses it
        path_parse = apt.fs(path).split('/')
        # if in lib {library}/{project}_pkg.vhd
        if("lib" in path_parse):
            i = path_parse.index("lib")
            pass
        #if in cache {library}/{project}/../.vhd
        elif("cache" in path_parse):
            i = path_parse.index("cache")
            pass
        else:
            return '',''
        L = path_parse[i+1]
        N = path_parse[i+2].replace("_pkg.vhd", "")
        return L,N

    def ports(self, mapp, lib, pure_entity, entity=None):
        units = self.grabUnits()
        info = ''
        if(entity == None):
            entity = self.getMeta("toplevel")
        if(entity == None):
            return info
        
        info = units[self.getLib()][entity].writePortMap(mapp, lib, pure_entity)
        return info
    pass


def main():
    pass


if __name__ == "__main__":
    main()