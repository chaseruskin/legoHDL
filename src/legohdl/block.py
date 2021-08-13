from genericpath import isdir
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

    def __init__(self, title=None, path=None, remote=None, new=False, excludeGit=False, market=None):
        self.__metadata = dict()
        self.__lib,self.__name = Block.split(title)

        self.__remote = remote #remote cannot be reconfigured through legohdl after setting
        self.__market = market
        self.__local_path = apt.fs(path)
        if(path != None):
            #print(path)
            if(self.isValid()):
                if(not excludeGit):
                    self._repo = git.Repo(self.__local_path)
                self.loadMeta()
                self.__name = self.getMeta("name")
            return

        if(path == None):
            self.__local_path = apt.fs(apt.getLocal()+"/"+self.__lib+"/"+self.__name+'/')

        #try to see if this directory is indeed a git repo
        try:
            self._repo = git.Repo(self.__local_path)
        except:
            self._repo = None

        if(remote != None):
            self.grabGitRemote(remote)

        if(self.isValid()):
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
            self.create(remote=remote) #create the repo and directory structure
        pass

    def getPath(self):
        return self.__local_path

    def downloadFromURL(self, rem):
        rem = apt.fs(rem)
        new_path = apt.fs(apt.getLocal()+"/"+self.getLib()+"/")
        os.makedirs(new_path, exist_ok=True)
        git.Git(new_path).clone(rem)
        if(rem.endswith(".git")):
            url_name = rem[rem.rfind('/')+1:rem.rfind('.git')]
            os.rename(new_path+url_name, new_path+self.getName())

    def cache(self):
        os.makedirs(apt.WORKSPACE+"cache/"+self.getMeta("library")+"/", exist_ok=True)
        cache_dir = apt.WORKSPACE+"cache/"+self.getMeta("library")+"/"
        git.Git(cache_dir).clone(self.__remote)
        pass

    def getTitle(self):
        return self.getLib()+'.'+self.getName()

    #download a block
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
        self._repo = git.Git(dst).clone(src)
        self.loadMeta()
        self._repo = git.Repo(dst+"/"+self.getName())

        #todo : 
        #clone that correct version from market
        if(self._market != None):
            pass
        #if downloaded from cache, make a master branch if no remote  
        elif(len(self._repo.heads) == 0):
            self._repo.git.checkout("-b","master")

    def getVersion(self):
        return self.getMeta('version')

    def release(self, ver='', options=[]):
        major,minor,patch = self.sepVer(self.getVersion())
        if(ver != '' and self.biggerVer(ver,self.getVersion()) == self.getVersion()):
            next_min_version = "v"+str(major)+"."+str(minor)+"."+str(patch+1)
            exit(log.error("Invalid version selected! Next minimum version is: "+next_min_version))
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
            #add only changes made to Block.lock file
            if(options.count('strict')):
                self._repo.index.add(apt.MARKER)
            #add all untracked changes to be included in the release commit
            else:   
                self._repo.git.add(update=True)
                self._repo.index.add(self._repo.untracked_files)
            self._repo.index.commit("Release version -> "+self.getVersion())
            #create a tag with this version
            self._repo.create_tag(ver)

            #in order to release to market, we must have a valid git remote url
            url = self.grabGitRemote()
            if(url == None):
                if(self.__market != None):
                    log.warning("Could not release to market "+self.__market.getName()+" because this block is not tied to a remote.")
                return
            #push to remote codebase!! (we have a valid remote url to use)
            else:
                self.pushRemote()

            #publish on market/bazaar!
            if(self.__market != None):
                #todo : publish every version that DNE on market?
                self.__market.publish(self.__metadata, options)
            elif(self.getMeta("market") != None):
                log.warning("Market "+self.getMeta("market")+" is no longer attached to this workspace.")
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

    def bindMarket(self, mkt):
        log.info("Tying "+mkt+" as the market for "+self.getTitle())
        self.__metadata['market'] = mkt
        self.save()
        pass

    def setRemote(self, rem):
        log.info("Setting "+rem+"as the remote git url for "+self.getTitle())
        self.grabGitRemote(rem)
        self.__metadata['remote'] = rem
        self._remote = rem
        self.genRemote()
        self.save()
        pass

    def loadMeta(self):
        with open(self.metadataPath(), "r") as file:
            self.__metadata = yaml.load(file, Loader=yaml.FullLoader)
            file.close()

        if(self.getMeta('derives') == None):
            self.__metadata['derives'] = dict()

        if('remote' in self.__metadata.keys()):
            #upon every boot up, try to grab the remote from this git repo if it exists
            self.grabGitRemote()
            if(self._remote != None):
                self.__metadata['remote'] = self._remote
            else:
                self.__remote = self.__metadata['remote']
        if('market' in self.__metadata.keys()):
            #did an actual market object already get passed in?
            if(self.__market != None):
                self.__metadata['market'] = self.__market.getName()
            #see if the market is bound to your workspace
            elif(self.getMeta("market") != None and self.getMeta("market") in apt.getMarkets().keys()):
                self.__market = Market(self.__metadata['market'], apt.SETTINGS['market'][self.__metadata['market']])
        pass


    def fillTemplateFile(self, newfile, templateFile):
        #find the template file to use
        
        #grab name of file
        filename = os.path.basename(newfile)
        file,_ = os.path.splitext(filename)
        
        #ensure this file doesn't already exist
        if(os.path.isfile(newfile)):
            log.info("File already exists")
            return
        log.info("Creating new file...")

        replacements = glob.glob(apt.TEMPLATE+"**/"+templateFile, recursive=True)
        #copy the template file into the proper location
        if(len(replacements) < 1):
            exit(log.error("Could not find "+templateFile+" file in template project"))
        else:
            templateFile = replacements[0]
        #make any necessary directories
        os.makedirs(newfile.replace(filename,""), exist_ok=True)
        #copy file to the new location
        shutil.copyfile(templateFile, self.__local_path+newfile)
        #reassign file to be the whole path
        newfile = self.__local_path+newfile
        today = date.today().strftime("%B %d, %Y")
        file_in = open(newfile, "r")
        lines = []
        #write blank if no author configured
        author = apt.SETTINGS["author"]
        if(author == None):
            author = ''
        #find and replace all proper items
        for line in file_in.readlines():
            line = line.replace("template", file)
            line = line.replace("%DATE%", today)
            line = line.replace("%AUTHOR%", author)
            line = line.replace("%PROJECT%", self.getTitle())
            lines.append(line)
            file_in.close()
        file_out = open(newfile, "w")
        #rewrite file to have new lines
        for line in lines:
            file_out.write(line)
        file_out.close()
        pass

    def create(self, fresh=True, git_exists=False, remote=None):
        log.info('Initializing new project')
        if(fresh):
            if(os.path.isdir(apt.TEMPLATE)):
                #copy all files from template project
                shutil.copytree(apt.TEMPLATE, self.__local_path)
                #delete any previous git repository that was attached to template
                if(os.path.isdir(self.__local_path+"/.git/")):
                    shutil.rmtree(self.__local_path+"/.git/")
            else:
                os.makedirs(self.__local_path, exist_ok=True)
        
        open(self.__local_path+apt.MARKER, 'w').write(self.legoLockFile())
        
        if(not git_exists):
            self._repo = git.Repo.init(self.__local_path)
        else:
            self._repo = git.Repo(self.__local_path)
    

        #run the commands to generate new project from template
        #file to find/replace word 'template'
        if(fresh):
            replacements = glob.glob(self.__local_path+"/**/*template*", recursive=True)
            file_swaps = list()
            for f in replacements:
                if(os.path.isfile(f)):
                    file_swaps.append((f,f.replace('template', self.__name)))
            author = apt.SETTINGS["author"]
            if(author == None):
                author = ''
            today = date.today().strftime("%B %d, %Y")
            for x in file_swaps:
                file_in = open(x[0], "r")
                file_out = open(x[1], "w")
                for line in file_in:
                    line = line.replace("template", self.__name)
                    line = line.replace("%DATE%", today)
                    line = line.replace("%AUTHOR%", author)
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
        if(remote != None):
            self.setRemote(remote)
        self.save() #save current progress into yaml
        self._repo.index.add(self._repo.untracked_files)
        self._repo.index.commit("Initializes block")
        if(self.grabGitRemote() != None):
            log.info('Generating new remote repository...')
            # !!! set it up to track
            print(str(self._repo.head.reference))
            self._repo.git.push("-u","origin",str(self._repo.head.reference))
        else:
            log.warning('No remote code base attached to local repository')
        pass

    #dynamically grab the origin url if it has been changed/added by user using git
    def grabGitRemote(self, newValue=None):
        if(hasattr(self, "_remote")):
            return self._remote
        if(hasattr(self, "_repo") == False or self._repo == None):
            self._remote = None
            return self._remote
        if(newValue != None):
            self._remote = newValue
            return self._remote
        #try to grab from git repo object
        self._remote = None
        #print(self._repo.remotes)
        if(len(self._repo.remotes)):
            origin = self._repo.remotes
            for o in origin:
                if(o.url == self.__local_path):
                    continue
                elif(o.url.endswith(".git")):
                    self._remote = o.url
                    break
        #print(self.getTitle(),self._remote)
        #make sure to save if it differs
        if(self.getMeta("remote") != self._remote):
            self.__metadata['remote'] = self._remote
            self.save()
        return self._remote

    #generate new link to remote if previously unestablished (only for creation)
    def genRemote(self):
        if(self.isLinked()):
            remote_url = self.getMeta("remote")
            try: #attach to remote code base
                self._repo.create_remote('origin', remote_url) 
            except: #relink origin to new remote url
                print(self._repo.remotes.origin.url)
            if(remote_url == None):
                return
            with self._repo.remotes.origin.config_writer as cw:
                cw.set("url", remote_url)
        pass

    def pushRemote(self):
        self._repo.remotes.origin.push(refspec='{}:{}'.format(self._repo.head.reference, self._repo.head.reference))
        self._repo.remotes.origin.push("--tags")

    def getName(self):
        try:
            if(self.getMeta("name") == None):
                return ''
            return self.getMeta("name")
        except:
            return self.__name

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
        if(self.grabGitRemote() != None):
            log.info("Block already exists in local workspace- pulling from remote...")
            self._repo.remotes.origin.pull()
        else:
            log.info("Block already exists in local workspace")

    #return true if the requested project folder is a valid Block
    def isValid(self):
        return os.path.isfile(self.metadataPath())

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
        order = ['name', 'library', 'version', 'summary', 'toplevel', 'bench', 'remote', 'market', 'derives']
        #write values with respect to order
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
        return self.grabGitRemote() != None

    def install(self, cache_dir, ver=None, src=None):
        #CMD: git clone (rep.git_url) (location) --branch (rep.last_version) --single-branch
        if(ver == None):
            ver = self.getVersion()
        
        if(ver == 'v0.0.0'):
            log.error('No available version')
            return

        log.debug("version "+ver)
        
        if(src == None and self.__remote != None):
            src = self.__remote
        elif(src == None):
            src = self.__local_path

        ver = "v"+ver
        git.Git(cache_dir).clone(src,"--branch",ver,"--single-branch")
        self.__local_path = cache_dir+self.getName()+"/"
        self._repo = git.Repo(self.__local_path)
        self._repo.git.checkout(ver)
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
        if(self.getTitle() in block_list):
            block_list.remove(self.getTitle())
        if(len(self.__metadata['derives']) != len(block_list)):
            update = True
        for b in block_list:
            if(b not in self.__metadata['derives']):
                update = True
                break
        if(update):
            self.__metadata['derives'] = list(block_list)
            self.save()
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
            return file_path[dot+1:].lower()
    
    @classmethod
    def split(cls, dep):
        if(dep == None):
            return '',''
        dot = dep.find('.')
        lib = dep[:dot]
        dot2 = dep[dot+1:].find('.')
        if(dot2 == -1):
            #use semi-colon if only 1 dot is marked
            dot2 = dep[dot+1:].find(';')
        if(dot2 == -1):
            dot2 = len(dep)
        name = dep[dot+1:dot+1+dot2]
        return lib.lower(),name.lower()

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
                self.save()

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
                self.save()
            #return the entity
            return self._bench 
        else:
            log.warning("No testbench detected.")
            return None

    #determine what unit is utmost highest, whether it be a testbench (if applicable) or entity
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
            
        #get all possible units (units are incomplete (this is good))
        self._unit_bank = self.grabDesigns(override, "cache","current")
       
        #todo : only start from top-level unit if it exists
        #gather all project-level units
        project_level_units = self.grabDesigns(False, "current")[self.getLib()]
        for unit in project_level_units.values():
            #start with top-level unit and complete all required units in unit bank
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

    #return an updated dictionary object with any blank units found in the file
    def skimVHDL(self, designs, filepath, L, N):
        with open(filepath, 'r') as file:
            for line in file.readlines():
                words = line.split()
                #skip if its a blank line
                if(len(words) == 0): 
                    continue
                #create new library dictionary if DNE
                if(L not in designs.keys()):
                    designs[L] = dict()
                #add entity units
                if(words[0].lower() == "entity"):
                    designs[L][words[1].lower()] = Unit(filepath,Unit.Type.ENTITY,L,N,words[1].lower())
                #add package units
                elif((words[0].lower() == "package" and words[1].lower() != 'body')):
                    designs[L][words[1].lower()] = Unit(filepath,Unit.Type.PACKAGE,L,N,words[1].lower())
        file.close()
        return designs

    #return dictionary of entities with their respective files as values
    #all possible entities or packages to be used in current project
    def grabCacheDesigns(self, override=False):
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
            #print(f)
            self._cache_designs = self.skimVHDL(self._cache_designs, f, L, N)

        #print("Cache-Level designs: "+str(self._cache_designs))

        #if multi-develop is enabled, overwrite the units with those found in the local path
        #also allow to work with unreleased blocks? -> yes
        if(apt.SETTINGS['multi-develop'] == True):
            log.info("Multi-develop is enabled")
            #1. first find all Block.lock files (roots of blocks)
            files = glob.glob(apt.getLocal()+"**/"+apt.MARKER, recursive=True)
            #print(files)
            #2. go through each recursive search within these roots for vhd files (skip self block root)
            for f in files:
                f_dir = f.replace(apt.MARKER,"")
                with open(f, 'r') as file:
                    yml = yaml.load(file, Loader=yaml.FullLoader)
                L = yml['library']
                N = yml['name']
                #skip self block
                if(L == self.getLib() and N == self.getName()):
                    continue
                #3. open each found vhdl file and insert units into cache design
                vhd_files = glob.glob(f_dir+"**/*.vhd", recursive=True)
                for v in vhd_files:
                    #print(v)
                    self._cache_designs = self.skimVHDL(self._cache_designs, v, L, N)
        #print("Cache-Level designs: "+str(self._cache_designs))
        return self._cache_designs

    def grabCurrentDesigns(self, override=False):
        if(hasattr(self, "_cur_designs") and not override):
            return self._cur_designs
        self._cur_designs = dict()

        L,N = self.split(self.getTitle())

        #create new library dictionary if DNE
        if(L not in self._cur_designs.keys()):
            self._cur_designs[L] = dict()

        files = self.gatherSources()
        for f in files:
            self._cur_designs = self.skimVHDL(self._cur_designs, f, L, N)
        #log.debug("Project-Level Designs: "+str(self._cur_designs))
        return self._cur_designs
    
    #search for the projects attached to the external package
    def grabExternalProject(cls, path):
        #use its file to find out what block uses it
        path_parse = apt.fs(path).split('/')
        # if in lib {library}/{block}_pkg.vhd
        if("lib" in path_parse):
            i = path_parse.index("lib")
            pass
        #if in cache {library}/{block}/../.vhd
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