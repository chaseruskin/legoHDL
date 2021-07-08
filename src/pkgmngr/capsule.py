import os, yaml, git, shutil
from datetime import date
import collections, stat
import glob
try:
    from pkgmngr import repo
except:
    import repo

#a capsule is a package/module that is signified by having the capsule.yml
class Capsule:
    settings = None
    pkgmngPath = ''
    hidden = os.path.expanduser("~/.legohdl/")

    #initialze capsule from a repo obj
    def absorbRepo(self, rp):
        self.__name = rp.name
        self.__lib = rp.library
        self.__localPath = rp.local_path
        try:
            self.__repo = git.Repo(self.__localPath)
        except:
            #repo DNE
            pass
        if(self.linkedRemote()):
            self.__remoteURL = self.settings['remote']+'/'+self.__lib+"/"+self.__name+".git"
        if(self.isValid()):
            self.loadMeta()
        else:
            #self.__metadata['id'] = key
            self.__metadata['version'] = rp.last_version
        pass

    def getPath(self):
        return self.__localPath

    def __init__(self, name='', new=False, rp=None):
        self.__metadata = dict()
        self.__repo = None
        self.__remoteURL = None

        if(rp != None):
            self.absorbRepo(rp)
            return
        
        dot = name.find('.')
        self.__lib = ''
        self.__name = name
        if(dot > -1):
            self.__lib = name[:dot]
            self.__name = name[dot+1:]
        
        self.__localPath = Capsule.settings['local']+"/"+self.__lib+"/"+self.__name+'/'

        #configure remote url
        if(self.linkedRemote()):
            self.__remoteURL = self.settings['remote']+'/'+self.__lib+"/"+self.__name+".git"

        if(self.isValid()): #this package is already existing locally
            self.__repo = git.Repo(self.__localPath)
            if(new):
                print('This project already locally exists')
            #load in metadata from YML
            self.loadMeta()
            pass
        elif(new): #create a new project
            if(self.linkedRemote()):
                try:
                    git.Git(self.route).clone(self.__remoteURL)
                    print('Project already exists on remote code base; downloading now...')
                    return
                except:
                    pass
            self.create() #create the repo and directory structure
        pass

    def saveID(self, id):
        self.__metadata['id'] = id
        self.pushYML("Adds ID to YML file")
        pass

    def cache(self, cache_dir):
        git.Git(cache_dir).clone(self.__remoteURL)
        pass

    def getTitle(self):
        return self.__lib+'.'+self.__name

    def __del__(self):
        if(self.isValid() and len(self.__metadata)):
            self.save()
        pass

    def clone(self):
        #grab library level path
        n = self.__localPath.rfind(self.getName())
        libPath = self.__localPath[:n]
        os.makedirs(libPath, exist_ok=True)
        self.__repo = git.Git(libPath).clone(self.__remoteURL)
        self.loadMeta()

    def getVersion(self):
        return self.getMeta('version')

    def release(self, ver='', options=None):
        first_dot = self.getVersion().find('.')
        last_dot = self.getVersion().rfind('.')

        major = int(self.getVersion()[:first_dot])
        minor = int(self.getVersion()[first_dot+1:last_dot])
        patch = int(self.getVersion()[last_dot+1:])
        print("Uploading ",end='')
        print("v"+str(major),minor,patch,sep='.',end='')
        if(ver == ''):
            if(options[0] == "maj"):
                major += 1
                minor = patch = 0
                pass
            elif(options[0] == "min"):
                minor += 1
                patch = 0
                pass
            elif(options[0] == "fix"):
                patch += 1
                pass
            else:
                return
            ver = 'v'+str(major)+'.'+str(minor)+'.'+str(patch)
        else:
            ver = ver[1:]
            try:
                r_major = int(ver[:first_dot])
            except:
                return
            try:
                r_minor = int(ver[first_dot+1:last_dot])
            except:
                r_minor = 0
            try:
                r_patch = int(ver[last_dot+1:])
            except:
                r_patch = 0
                
            if(r_major < major):
                return
            elif(r_major == major and r_minor < minor):
                return
            elif(r_major == major and r_minor == minor and r_patch <= patch):
                return
            ver = 'v'+str(r_major)+'.'+str(r_minor)+'.'+str(r_patch)
        print(" -> ",end='')
        print(ver)
        if(ver != '' and ver[0] == 'v'):
            self.__metadata['version'] = ver[1:]
            self.save()
            self.__repo.git.add(update=True)
            self.__repo.index.commit("Release version -> "+self.getVersion())
            self.__repo.create_tag(ver)
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
        pass

    def getID(self):
        return self.getMeta("id")


    def create(self):
        print('Initializing new project')

        shutil.copytree(self.pkgmngPath+"template/", self.__localPath)
        self.__repo = git.Repo.init(self.__localPath)
    
        if(self.linkedRemote()):
            self.__repo.create_remote('origin', self.__remoteURL) #attach to remote code base
            
        #run the commands to generate new project from template
        #file to find/replace word 'template'
        file_swaps = [(self.__localPath+'.template.yml',self.metadataPath()),(self.findPath('template.vhd'), self.findPath('template.vhd').replace('template', self.__name)),
        (self.findPath('template_tb.vhd'), self.findPath('template_tb.vhd').replace("template", self.__name))]

        today = date.today().strftime("%B %d, %Y")
        for x in file_swaps:
            file_in = open(x[0], "r")
            file_out = open(x[1], "w")
            for line in file_in:
                line = line.replace("template", self.__name)
                line = line.replace("%DATE%", today)
                line = line.replace("%AUTHOR%", self.settings["author"])
                line = line.replace("%PROJECT%", self.__name)
                file_out.write(line) #insert date into template
            file_in.close()
            file_out.close()
            os.remove(x[0])

        self.loadMeta() #generate fresh metadata fields
        self.__metadata['library'] = self.__lib
        self.save() #save current progress into yaml
        self.__repo.index.add(self.__repo.untracked_files)
        self.__repo.index.commit("Initializes project")
        if(self.linkedRemote()):
            print('Generating new remote repository...')
            # !!! set it up to track
            print(str(self.__repo.head.reference))
            self.__repo.git.push("-u","origin",str(self.__repo.head.reference))
            #self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
        else:
            print('No remote code base attached to local repository')
        pass

    #generate new link to remote if previously unestablished
    def genRemote(self):
        if(self.linkedRemote()):
            try: #attach to remote code base
                self.__repo.create_remote('origin', self.__remoteURL) 
            except: #relink origin to new remote url
                print(self.__repo.remotes.origin.url)
                with self.__repo.remotes.origin.config_writer as cw:
                    cw.set("url", self.__remoteURL)
                #now set it up to track
                # !!!
            self.__repo.git.push("-u","origin",str(self.__repo.head.reference))
            #self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
        pass

    def pushRemote(self):
        self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
        self.__repo.remotes.origin.push("--tags")

    def getName(self):
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
        self.__repo.remotes.origin.pull()

    def pushYML(self, msg):
        self.save()
        self.__repo.index.add("."+self.__name+".yml")
        
        self.__repo.index.commit(msg)
        if(self.linkedRemote()):
            self.__repo.remotes.origin.push(refspec='{}:{}'.format(self.__repo.head.reference, self.__repo.head.reference))
            #self.__repo.remotes.origin.push()

    #return true if the requested project folder is a valid capsule package
    def isValid(self):
        try:
            return os.path.isfile(self.metadataPath())
        except:
            return False
        pass

    @classmethod
    def linkedRemote(cls):
        return (cls.settings['remote'] != None)

    def metadataPath(self):
        return self.__localPath+"."+self.__name+".yml"

    def push_remote(self):
        pass

    def show(self):
        with open(self.metadataPath(), 'r') as file:
            for line in file:
                print(line,sep='',end='')
    
    def load(self):
        cmd = self.settings['editor']+" "+self.__localPath
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

    def install(self, cache_dir, ver, src_url=None):
        #CMD: git clone (rep.git_url) (location) --branch (rep.last_version) --single-branch
        if(ver == None):
            ver = "v"+self.getVersion()
        
        if(ver == 'v0.0.0'):
            print('error- no available version')
            exit()
        
        if(src_url == None):
            src_url = self.__remoteURL

        self.__localPath = cache_dir+self.getName()+"/"
        try:
            git.Git(cache_dir).clone(src_url,"--branch",ver,"--single-branch")
        except:
            pass
        self.__repo = git.Repo(self.__localPath)
        self.__repo.git.checkout(ver)
        self.loadMeta()
        return

    def scanDependencies(self, yml=True, vhd_file=None):
        vhd_file = self.findPath(self.getMeta("toplevel")) #find top-level
        s = vhd_file.rfind('/')
        src_dir = vhd_file[:s+1] #print(src_dir)
        #open every src file and inspect lines for using libraries
        derivatives = set()
        for vhd in os.listdir(src_dir):
            with open(src_dir+vhd) as file:
                for line in file:
                    line = line.lower()
                    z = line.find("use")
                    c = line.find('--')
                    if(z >= 0 and (c == -1 or z < c)):
                        derivatives.add(line[z+3:].strip())
                    if(line.count("entity") > 0):
                        break
                file.close()
            #print(vhd)
        #option to keep all library usages (for gen package files)
        if(yml == False):
            return src_dir,derivatives
        
        #if the pkg does not exist in the lib folder, remove it!
        tmp = derivatives.copy()
        for d in tmp:
            l,n = self.siftLibName(d)
            print(l,n)
            if(not os.path.isfile(self.hidden+"lib/"+l+"/"+n+".vhd")):
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
    
    #auto detect the toplevel file
    def autoDetectTop(self):
        #find all possible files
        vhd_files = glob.glob(self.__localPath+"/**/*.vhd", recursive=True)
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
                        if(line.count("use") and not in_entity and line.count("work")):
                            l,n = self.siftLibName(line)
                            if(n in comps.keys()):
                                vhd_files.remove(comps[n])
                                #print("REMOVE:",comps[n])
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
    def siftLibName(cls, dep):
        dot = dep.find('.')
        lib = dep[:dot]
        dot2 = dep[dot+1:].find('.')
        if(dot2 == -1):
            #use semi-colon if only 1 dot is marked
            dot2 = dep[dot+1:].find(';') 
        name = dep[dot+1:dot+1+dot2]
        return lib,name
    
    #auto detect testbench file
    def autoDetectBench(self, comp=None):
        #print("DETECTING TOP-LEVEL TESTBENCH")
        #based on toplevel, find which file instantiates a component of toplevel
        #find all possible files
        vhd_files = glob.glob(self.__localPath+"/**/*.vhd", recursive=True)
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
            print("ERROR- Could not resolve top-level testbench")
            return
        print("TESTBENCH:",bench)
        s = bench.rfind('/')
        d = bench.rfind('.')
        benchName = bench[s+1:d]
        benchPath = bench[:s+1]
        
        if(benchName+".vhd" != self.getMeta("bench")):
            self.__metadata['bench'] = benchName+".vhd"
        pass

    def findPath(self, file="*.vhd"):
        vhd_files = glob.glob(self.__localPath+"/**/"+file, recursive=True)
        if(len(vhd_files) > 0):
            return vhd_files[0]
        else:
            return None
        pass

    def ports(self, mapp):
        vhd_file = glob.glob(self.__localPath+"/**/"+self.getMeta("toplevel"), recursive=True)[0]
        
        port_txt = ''
        rolling_entity = False
        with open(vhd_file, 'r') as f:
            for line in f:
                line = line.lower()
                #discover when the entity block begins
                if(line == ('entity '+self.getName().lower()+' is\n')):
                    rolling_entity = True
                
                if(rolling_entity):
                    port_txt = port_txt + line
                #handle the 3 variations of how to end a entity block
                if(line == "end entity "+self.getName().lower()+";\n" or \
                    line == "end entity;\n" or \
                    line == "end "+self.getName().lower()+";\n"):
                    rolling_entity = False
                    break
            f.close()
        port_txt = port_txt.replace("entity", "component")

        #manipulate port list into port map if mapp=True
        if(mapp):
            print()
            print(port_txt,end='')

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
            print()
            for sig,pts in signals.items():
                line = "signal "
                for p in pts:
                    line = line + p +', '
                line = line[:len(line)-2] + ' : ' + sig
                print(line)
        print()
        return port_txt
        pass

    pass


def main():
    pass


if __name__ == "__main__":
    main()