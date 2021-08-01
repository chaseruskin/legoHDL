import os, yaml, shutil
from datetime import date
import stat
import glob, git
import logging as log
from .market import Market
from .apparatus import Apparatus as apt
from .vhdl import Vhdl


#a capsule is a package/module that is signified by having the .lego.lock
class Capsule:

    allLibs = []

    def __init__(self, title=None, path=None, remote=None, new=False, excludeGit=False, market=None):
        self.__metadata = dict()
        self.__lib = ''
        self.__name = ''
        self.__remote = remote #remote cannot be reconfigured through legohdl after setting
        self.__market = market
 
        if(title != None):
            self.__lib,self.__name = Capsule.split(title)
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
            log.debug("Placing here: "+self.__local_path)
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
        if(ver != '' and self.biggerVer(ver,self.getVersion()) == self.getVersion()):
            exit(log.error("Invalid version selection!"))
        major,minor,patch = self.sepVer(self.getVersion())
        log.info("Uploading v"+str(major)+"."+str(minor)+"."+str(patch))
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
                self.__repo.index.add(".lego.lock")
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

        major = int(ver[:first_dot])
        minor = int(ver[first_dot+1:last_dot])
        patch = int(ver[last_dot+1:])
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
        replacements = glob.glob(apt.HIDDEN+"template/**/"+templateFile, recursive=True)
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
            if(os.path.isdir(apt.HIDDEN+"template/")):
                shutil.copytree(apt.HIDDEN+"template/", self.__local_path)
            else:
                os.makedirs(self.__local_path, exist_ok=True)
        
        open(self.__local_path+".lego.lock", 'w').write(self.legoLockFile())
        
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
        self.__repo.index.add(".lego.lock")
        
        self.__repo.index.commit(msg)
        
        if(self.isLinked()):
            self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
            self.__repo.remotes.origin.push("--tags")

    #return true if the requested project folder is a valid capsule package
    def isValid(self):
        try:
            return os.path.isfile(self.metadataPath())
        except:
            return False
        pass

    def metadataPath(self):
        return self.__local_path+".lego.lock"

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
        ent = self.grabEntities()[self.getLib()+'.'+entity]
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

    def updateDerivatives(self):
        ents = self.grabEntities()
        d_set = set()
        for k,e in ents.items():
            dpndencies = e.getDependencies()
            for dep in dpndencies:
                if(dep not in ents.keys()):
                    d_set.add(dep)
        print(d_set)
        update = False
        if(len(self.__metadata['derives']) != len(d_set)):
            update = True
        for d in d_set:
            if(d not in self.__metadata['derives']):
                update = True
                break
        if(update):
            self.__metadata['derives'] = list(d_set)
            self.pushYML("Updates project derivatives")
        pass

    def gatherSources(self, ext=[".vhd"], excludeTB=False):
        srcs = []
        for e in ext:
            srcs = srcs + glob.glob(self.__local_path+"/**/*"+e, recursive=True)
        #print(srcs)
        if(excludeTB):
            for k,e in self.grabEntities().items():
                if(e.isTb() and e.getFile() in srcs):
                    srcs.remove(e.getFile())
        return srcs
        pass
    
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

    #auto detect top-level designe entity
    def identifyTop(self):
        ents = self.grabEntities()
        top_contenders = list(ents.keys())
        log.debug(top_contenders)
        top = None
        for k,e in ents.items():
            #if the entity is value under this key, it is lower-level
            if(e.isTb()):
                top_contenders.remove(e.getFull())
                continue
                
            for dep in e.getDependencies():
                if(dep in top_contenders):
                    top_contenders.remove(dep)

        if(len(top_contenders) == 0):
            log.error("No top level detected.")
        elif(len(top_contenders) > 1):
            log.warning("Multiple top levels detected. "+str(top_contenders))
            validTop = input("Enter a valid toplevel entity: ").lower()
            while validTop not in top_contenders:
                validTop = input("Enter a valid toplevel entity: ").lower()
            
            top_contenders = [validTop]
        if(len(top_contenders) == 1):
            top = ents[top_contenders[0]]

            log.info("DETECTED TOP-LEVEL ENTITY: "+top.getName())
            bench = self.identifyBench(top.getName(), save=True)
            #break up into src_dir and file name
            #add to metadata, ensure to push meta data if results differ from previously loaded
            if(top.getName() != self.getMeta("toplevel")):
                log.debug("TOPLEVEL: "+top.getName())
                self.__metadata['toplevel'] = top.getName()
                self.pushYML("Auto updates top level design module to "+self.getMeta("toplevel"))
            pass
        return top

    #determine what testbench is used for the top-level design entity
    def identifyBench(self, entity_name, save=False):
        ents = self.grabEntities()
        bench = None
        for k,e in ents.items():
            for dep in e.getDependencies():
                if(dep.lower() == self.getLib()+'.'+entity_name.lower() and e.isTb()):
                    bench = e
                    break

        if(bench != None):
            log.info("DETECTED TOP-LEVEL BENCH: "+bench.getName())
            if(save and self.getMeta("bench") != bench.getName()):
                self.__metadata['bench'] = bench.getName()
                self.pushYML("Auto updates testbench module to "+self.getMeta("bench"))
            return bench #return the entity
        else:
            log.error("No testbench configured for this top-level entity.")
            return None
        pass

    def grabEntities(self, excludeTB=False):
        if(hasattr(self, "_entity_bank")):
            return self._entity_bank
        srcs = self.gatherSources(excludeTB=excludeTB)
        self._entity_bank = dict()
        for f in srcs:
            f = apt.fs(f)
            self._entity_bank.update(Vhdl(f).decipher(self.allLibs, self.grabDesigns("cache","current"), self.getLib()))
            log.info(f)
        return self._entity_bank

    def grabDesigns(self, *args):
        design_book = dict()
        if("current" in args):
            design_book = self.grabCurrentDesigns().copy()
            pass
        if("cache" in args):
            design_book.update(self.grabCacheDesigns())
            pass
        return design_book

    #return dictionary of entities with their respective files as values
    #all possible entities or packages to be used in current project
    def grabCacheDesigns(self):
        if(hasattr(self, "_cache_designs")):
            return self._cache_designs
        self._cache_designs = dict()
        files = (glob.glob(apt.WORKSPACE+"lib/**/*.vhd", recursive=True))
        files = files + glob.glob(apt.WORKSPACE+"cache/**/*.vhd", recursive=True)

        for f in files:
            L,N = self.grabExternalProject(f)
            with open(f, 'r') as file:
                for line in file.readlines():
                    words = line.split()
                    if(len(words) == 0 or (L == self.getLib() and N == self.getName())): #skip if its a blank line
                        continue
                    if(words[0].lower() == "entity" or (words[0].lower() == "package" and words[1].lower() != 'body')):
                        self._cache_designs[L+'.'+words[1].lower()] = f
                file.close()
        #log.debug("Cache-Level designs: "+str(self._cache_designs))
        return self._cache_designs

    def grabCurrentDesigns(self):
        if(hasattr(self, "_cur_designs")):
            return self._cur_designs
        self._cur_designs = dict()
        files = self.gatherSources()
        for f in files:
            with open(f, 'r') as file:
                for line in file.readlines():
                    words = line.split()
                    if(len(words) == 0): #skip if its a blank line
                        continue
                    if(words[0].lower() == "entity" or (words[0].lower() == "package" and words[1].lower() != 'body')):
                        self._cur_designs[self.getLib()+'.'+words[1].lower()] = f
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

    def ports(self, mapp, entity=None):
        ents = self.grabEntities()
        printer = ''
        if(entity == None):
            entity = self.getMeta("toplevel")
        for k,e in ents.items():
            if(e.getName() == entity):
                printer = e.getPorts()
                if(mapp):
                    printer = printer + "\n" + e.getMapping()
                break
        return printer
    pass


def main():
    pass


if __name__ == "__main__":
    main()