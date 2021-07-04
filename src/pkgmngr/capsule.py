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
        file_swaps = [(self.__localPath+'.template.yml',self.metadataPath()),(self.__localPath+'design/template.vhd', self.__localPath+'design/'+self.__name+'.vhd'),
        (self.__localPath+'testbench/template_tb.vhd', self.__localPath+'testbench/'+self.__name+'_tb.vhd')]

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

    def install(self, cache_dir):
        #CMD: git clone (rep.git_url) (location) --branch (rep.last_version) --single-branch
        try:
            git.Git(cache_dir).clone(self.__remoteURL,"--branch","v"+self.getVersion(),"--single-branch")
        except:
            pass
            self.__localPath = cache_dir+self.getName()+"/"
            self.loadMeta()
        return

    def scanDependencies(self):
        vhd_file = glob.glob(self.__localPath+"/**/"+self.getMeta("toplevel"), recursive=True)[0]
        s = vhd_file.rfind('/')
        src_dir = vhd_file[:s+1]
        print(src_dir)
        #open every src file and inspect lines for using libraries
        derivatives = list()
        for vhd in os.listdir(src_dir):
            with open(src_dir+vhd) as file:
                for line in file:
                    line = line.lower()
                    z = line.find("use")
                    if(z >= 0):
                        derivatives.append(line[z+3:].strip())
                    if(line.count("entity") > 0):
                        break
                file.close()
            print(vhd)
            print(derivatives)
            self.__metadata['derives'] = derivatives
        return src_dir
        pass

    def ports(self):
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
        return port_txt
        pass

    pass


def main():
    pass


if __name__ == "__main__":
    main()