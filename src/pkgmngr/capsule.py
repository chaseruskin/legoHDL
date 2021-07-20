import os, yaml, shutil
from datetime import date
import collections, stat
import glob
from market import Market
from apparatus import Apparatus as apt
import git
from source import Vhdl
import logging as log

#a capsule is a package/module that is signified by having the .lego.lock
class Capsule:

    def __init__(self, title=None, path=None, remote=None, new=False, excludeGit=False, market=None):
        self.__metadata = dict()
        self.__lib = ''
        self.__name = ''
        self.__remote = remote #remote cannot be reconfigured through legohdl after setting
        self.__market = market
 
        if(title != None):
            self.__lib,self.__name = self.split(title)
        if(path != None):
            self.__local_path = path
            #print(path)
            if(self.isValid()):
                self.loadMeta()
                if(not excludeGit):
                    self.__repo = git.Repo(self.__local_path)
                self.__name = self.getMeta("name")
            return

        if(remote != None):
            self.__remote = remote #pass in remote object
        
        self.__local_path = apt.getLocal()+"/"+self.__lib+"/"+self.__name+'/'

        #configure remote url
        #if(apt.linkedRemote()):
            #self.__remote_url = apt.SETTINGS['remote']+'/'+self.__lib+"/"+self.__name+".git"
        if(self.isValid()):
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

    def clone(self):
        local = apt.getLocal()+"/"+self.getLib()+"/"
        src = self.__remote
        #grab library level path (default location)
        n = local.rfind(self.getName())
        dst = local[:n] 
        print(dst)
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
        print(self.getVersion())
        print("Uploading ",end='')
        print("v"+str(major),minor,patch,sep='.',end='')
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
            elif(self.getMeta("market") != None):
                self.__market = Market(self.__metadata['market'], apt.SETTINGS['market'][self.__metadata['market']])
        pass

    def create(self, fresh=True, git_exists=False):
        log.info('Initializing new project')
        if(fresh):
            shutil.copytree(apt.PKGMNG_PATH+"template/", self.__local_path)
        else:
            shutil.copy(apt.PKGMNG_PATH+"template/.lego.lock", self.__local_path+".lego.lock")
        
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
                    line = line.replace("%PROJECT%", self.__name)
                    file_out.write(line) #insert date into template
                file_in.close()
                file_out.close()
                os.remove(x[0])
        
        self.loadMeta() #generate fresh metadata fields
        self.__metadata['name'] = self.__name
        self.__metadata['library'] = self.__lib
        self.__metadata['version'] = '0.0.0'
        self.autoDetectTop()
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
                with self.__repo.remotes.origin.config_writer as cw:
                    cw.set("url", self.__remote_url)
            #now set it up to track
            self.__repo.git.push("-u","origin",str(self.__repo.head.reference))
        pass

    def pushRemote(self):
        self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
        self.__repo.remotes.origin.push("--tags")

    def getName(self):
        return self.__name

    def getDesignBook(self):
        pass

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

    #return true if the requested project folder is a valid capsule package
    def isValid(self):
        try:
            return os.path.isfile(self.metadataPath())
        except:
            return False
        pass

    def metadataPath(self):
        return self.__local_path+".lego.lock"

    def push_remote(self):
        pass

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
        tmp = collections.OrderedDict(self.__metadata)
        tmp.move_to_end('derives')
        tmp.move_to_end('name', last=False)
        #a little magic to save YAML in custom order for easier readability
        with open(self.metadataPath(), "w") as file:
            while len(tmp):
                #pop off front key/val pair of yaml data
                it = tmp.popitem(last=False)
                single_dict = {}
                single_dict[it[0]] = it[1]
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

        log.debug("version",ver)
        
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

    def scanDependencies(self, file_target, update=True):
        found_files = self.fileSearch(file_target)
        s = found_files[0].rfind('/')
        src_dir = found_files[0][:s+1] #print(src_dir)
        #open every src file and inspect lines for using libraries
        derivatives = set()
        for match in found_files:
            if os.path.isfile(match):
                with open(match) as file:
                    if(self.getExt(match) == 'vhd'): #source file
                        for line in file:
                            line = line.lower()
                            z = line.find("use") #look for library use calls
                            c = line.find('--') #is is a comment?
                            if(z >= 0 and (c == -1 or z < c)):
                                derivatives.add(line[z+3:].strip())
                            if(line.count("entity") > 0):
                                break
                    file.close()
            #print(vhd)
        #option to keep all library usages (for gen package files)
        if(update == False):
            return src_dir,derivatives
        
        #if the pkg does not exist in the lib folder, remove it!
        tmp = derivatives.copy()
        for d in tmp:
            l,n = self.split(d)
            print(l,n)
            if(not os.path.isfile(apt.HIDDEN+"lib/"+l+"/"+n+".vhd")):
                derivatives.remove(d)

        print(derivatives)
        update = False
        if(len(self.__metadata['derives']) != len(derivatives)):
            update = True
        for d in derivatives:
            if(d not in self.__metadata['derives']):
                update = True
                break
        if(update):
            self.__metadata['derives'] = list(derivatives)
            self.pushYML("Updates module derivatives")
        return src_dir, derivatives
        pass

    def gatherSources(self, ext=[".vhd"]):
        srcs = []
        for e in ext:
            srcs = srcs + glob.glob(self.__local_path+"/**/*"+e, recursive=True)
        print(srcs)
        return srcs
        pass
    
    #auto detect the toplevel file
    def autoDetectTop(self):
        #find all possible files
        vhd_files = glob.glob(self.__local_path+"/**/*.vhd", recursive=True)
        #remove all files containing "tb_" or "_tb"
        comps = dict() #store a dict of all components to look for that are instantiated
        toplvl = None
        tmplist = vhd_files.copy()
        for vhd in tmplist:
            if (vhd.count("tb_") + vhd.count("_tb") > 0):
                vhd_files.remove(vhd)
            else:
                s = vhd.rfind('/')
                d = vhd.rfind('.')
                comps[vhd[s+1:d]] = vhd

        if(len(vhd_files) == 1):
            toplvl = vhd_files[0]
        
        #go through every file, if a file contains one of the keys in comps, the file named with that key is removed
        #print("DETECTING TOPLEVEL DESIGN MODULE")
        if(toplvl == None):
            for comp,vhd in comps.items():
                with open(vhd, 'r') as file:
                    in_entity = in_arch = False #reset detectors

                    for line in file.readlines():
                        if(line.count("entity") > 0):
                            in_entity = not in_entity

                        if(line.count("architecture") > 0):
                            in_arch = not in_arch
                        #remove file attached to key if...
                        #if before entity, the key is found in line starting with "use"
                        #checking for any user package files that contain this module's name
                        if(line.count("use") and not in_entity and line.count("work")):
                            l,n = self.split(line)
                            for val in comps.keys():
                                if(n.count(val)): #the package file contains this name
                                    vhd_files.remove(comps[n])
                                    break
                        #if inside architecture and before begin, the key is found in line with "component"
                        if(line.count("component") and in_arch):
                            t = line.find("component")+len("component")+1
                            while line[t] == ' ':
                                t = t+1
                            spc = (line[t:]).find(' ')
                            n = line[t:t+spc]
                            if(n in comps.keys()):
                                #print("REMOVE:",comps[n])
                                vhd_files.remove(comps[n])
                                break
                    file.close()
                    pass
        #grab contender's name
        if(len(vhd_files) == 1):
            toplvl = vhd_files[0]
        else:
            print("ERROR- Could not resolve toplevel design module.")
            return
        
        s = toplvl.rfind('/')
        d = toplvl.rfind('.')
        toplvlName = toplvl[s+1:d]
        toplvlPath = toplvl[:s+1]
    
        #break up into src_dir and file name
        #add to metadata, ensure to push meta data if results differ from previously loaded
        if(toplvlName+".vhd" != self.getMeta("toplevel")):
            print("TOPLEVEL:",toplvlName)
            self.__metadata['toplevel'] = toplvlName+".vhd"
            self.autoDetectBench()
            self.pushYML("Auto updates top level design module to "+self.getMeta("toplevel"))
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

    # given a VHDL file, return all of its "use"/imported packages
    def grabImportsVHD(self, filepath, availLibs):
        design_book = self.grabDesigns("cache","current")
        import_dict = dict() #associate entities/packages with particular entities
        lib_headers = list()
        with open(filepath, 'r') as file:
            in_entity = in_arch = in_pkg = False
            entity_name = arch_name = pkg_name =  None
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
                    import_dict[entity_name] = lib_headers #stash all "uses" from above
                    lib_headers = list()
                if(words[0].lower() == "package"):
                    in_pkg = True
                    pkg_name = words[1].lower()
                    #import_dict[pkg_name] = lib_headers #stash all "uses" from above
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
                        comps = self.grabComponents(self.grabDesigns("cache","current")[impt[1].replace(";",'').lower()])
                        
                        if(len(impt) == 3):
                            suffix = impt[2].lower().replace(";",'')
                            if(suffix == 'all'): # add all found entities from pkg as dependencies of design
                                lib_headers = lib_headers + comps
                            else: #it is a specific component
                                lib_headers.append(suffix)
                        else: # a third piece was not given, check instantiations with this pkg.entity format in architecture
                            pass

                #find component declarations
                if(words[0].lower() == "component" and in_arch):
                    import_dict[entity_name].append(words[1])
                if(words[0].lower() == "component" and in_pkg):
                    #import_dict[pkg_name].append(words[1])
                    pass
                #find instantiations by package.entity
                if(len(words) > 2 and words[1] == ':' and in_arch):
                    pkg_sect = words[2].split('.')
                    e_name = pkg_sect[len(pkg_sect)-1].lower()
                    p_name = pkg_sect[len(pkg_sect)-2].lower()

                    if(p_name in design_book.keys()):
                        import_dict[entity_name].append(e_name)
                        print("file needed:",design_book[p_name])

                #detect when outside of entity, architecture, or package
                if(words[0].lower() == "end"):
                    if(in_entity and (entity_name+";" in words or words[1].lower().count("entity"))):
                        in_entity = False
                    if(in_arch and (arch_name+";" in words or words[1].lower().count("architecture"))):
                        in_arch = False
                    if(in_pkg and (pkg_name+";" in words or words[1].lower().count("package"))):
                        in_pkg = False
                pass
            file.close()
            pass
        print(import_dict)
        return(import_dict)
        pass
    
    #auto detect testbench file
    def autoDetectBench(self, comp=None):
        #print("DETECTING TOP-LEVEL TESTBENCH")
        #based on toplevel, find which file instantiates a component of toplevel
        #find all possible files
        vhd_files = self.fileSearch()
        #keep only files containing "tb_" or "_tb"
        if(comp == None):
            comp = self.getMeta("toplevel") #looking for a testbench that uses this component
        ext_i = comp.find(".vhd")
        if(ext_i > -1):
            comp = comp[:ext_i]
        #print("LOOKING:",comp)
        bench = None
        tmplist = vhd_files.copy()
        for vhd in tmplist:
            if (vhd.count("tb_") + vhd.count("_tb") == 0):
                vhd_files.remove(vhd)
            elif(vhd.count(comp)):
                bench = vhd
                break

        if(len(vhd_files) == 1):
            bench = vhd_files[0]
        
        if(bench == None):
            for vhd in vhd_files:
                with open(vhd, 'r') as file:
                    for line in file.readlines():
                        if(line.count("use") and line.count(comp) and line.count("work")):
                            bench = vhd
                            break
                        if(line.count("component") and line.count(comp)):
                            bench = vhd
                            break
                    file.close()
                    if(bench != None):
                        break
                    pass
        
        if(bench == None):
            log.error("Could not resolve top-level testbench")
            return
        log.debug("TESTBENCH: "+bench)
        s = bench.rfind('/')
        d = bench.rfind('.')
        benchName = bench[s+1:d]
        benchPath = bench[:s+1]
        
        if(benchName+".vhd" != self.getMeta("bench")):
            self.__metadata['bench'] = benchName+".vhd"
        pass

    #return dictionary of entities with their respective files as values
    #all possible entities or packages to be used in current project
    def grabCacheDesigns(self):
        if(hasattr(self, "_cache_designs")):
            return self._cache_designs
        self._cache_designs = dict()
        files = (glob.glob(apt.WORKSPACE+"lib/**/*.vhd", recursive=True))
        for f in files:
            with open(f, 'r') as file:
                for line in file.readlines():
                    words = line.split()
                    if(len(words) == 0): #skip if its a blank line
                        continue
                    if(words[0].lower() == "entity" or (words[0].lower() == "package" and words[1].lower() != 'body')):
                        self._cache_designs[words[1].lower()] = f
                file.close()
        log.debug("Cache-Level designs:",self._cache_designs)
        return self._cache_designs

    #determine what testbench is used for the top-level design entity
    def identifyBench(self, entity_name, availLibs, save=False):
        ents = self.grabEntities(availLibs)
        bench = None
        for e in ents:
            for dep in e.getDerivs():
                if(dep.lower() == entity_name.lower()):
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

    def grabEntities(self, availLibs):
        if(hasattr(self, "_entity_bank")):
            return self._entity_bank
        srcs = self.gatherSources()
        for f in srcs:
            Vhdl(f).decipher(availLibs,self.grabDesigns("cache","current"))
        self._entity_bank = Vhdl.entity_bank
        for e in self._entity_bank:
            print(e)
        return self._entity_bank
    
    #auto detect top-level designe entity
    def identifyTop(self, availLibs):
        ents = self.grabEntities(availLibs)
        top_contenders = []
        top = None
        for e in ents:
            top_contenders.append(e.getName())
        for e in ents:
            #if the entity is value under this key, it is lower-level
            if(e.isTb()):
                top_contenders.remove(e.getName())
                continue
                
            for dep in e._derivs:
                if(dep in top_contenders):
                    top_contenders.remove(dep)

        if(len(top_contenders) == 1):
            for e in ents:
                if(e.getName() == top_contenders[0]):
                    top = e
                    break
            log.info("DETECTED TOP-LEVEL ENTITY: "+top.getName())
            bench = self.identifyBench(top.getName(), availLibs, save=True)
            #break up into src_dir and file name
            #add to metadata, ensure to push meta data if results differ from previously loaded
            if(top.getName() != self.getMeta("toplevel")):
                log.debug("TOPLEVEL: "+top.getName())
                self.__metadata['toplevel'] = top.getName()
                self.pushYML("Auto updates top level design module to "+self.getMeta("toplevel"))
            pass
        elif(len(top_contenders) == 0):
            log.error("No top level detected.")
        else:
            log.error("Multiple top levels detected. Please be explicit when exporting.")
        return top

    def grabTestbenches(self):
        tb_list = list()
        files = glob.glob(self.__local_path+"/**/*.vhd", recursive=True)
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

    def grabDesigns(self, *args):
        design_book = dict()
        if("current" in args):
            design_book = self.grabCurrentDesigns()
            pass
        if("cache" in args):
            design_book.update(self.grabCacheDesigns())
            pass
        return design_book

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
                        self._cur_designs[words[1].lower()] = f
                file.close()
        print("Project-Level Designs:",self._cur_designs)
        return self._cur_designs

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

    def fileSearch(self, file="*.vhd"):
        return glob.glob(self.__local_path+"/**/"+file, recursive=True)
        pass

    def ports(self, mapp, availLibs):
        ents = self.grabEntities(availLibs)
        printer = ''
        for e in ents:
            if(e.getName() == self.getMeta("toplevel")):
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