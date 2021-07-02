import os, yaml, git, shutil
from datetime import date
import collections, stat
import glob

#a capsule is a package/module that is signified by having the capsule.yml
class Capsule:
    settings = None
    pkgmngPath = ''
    def __init__(self, name='', new=False):
        self.__name = name
        self.__metadata = dict()
        self.__remoteURL = None
        self.__localPath = Capsule.settings['local']+"/"+self.__name+'/'
        self.__repo = None

        #configure remote url
        if(self.linkedRemote()):
            self.__remoteURL = self.settings['remote']+self.__name+".git"

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

    def __del__(self):
        if(self.isValid() and len(self.__metadata)):
            self.save()
        pass

    def clone(self):
        self.__repo = git.Git(self.__localPath).clone(self.__remoteURL)

    def getVersion(self):
        return self.getMeta('version')

    def release(self, ver='', options=None):
        first_dot = self.getVersion().find('.')
        last_dot = self.getVersion().rfind('.')

        major = int(self.getVersion()[:first_dot])
        minor = int(self.getVersion()[first_dot+1:last_dot])
        patch = int(self.getVersion()[last_dot+1:])
        print('last version:',major,minor,patch)
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
        print(ver)
        if(ver != '' and ver[0] == 'v'):
            self.__metadata['version'] = ver[1:]
            self.save()
            self.__repo.git.add(update=True)
            self.__repo.index.commit("Release version -> "+self.getVersion())
            self.__repo.create_tag(ver)
        pass

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
 
        self.save() #save current progress into yaml

        self.__repo.index.add(self.__repo.untracked_files)
        self.__repo.index.commit("Initializes project")
        if(self.linkedRemote()):
            print('Generating new remote repository...')
            self.__repo.remotes.origin.push(refspec='{}:{}'.format('master', 'master'))
        else:
            print('No remote code base attached to local repository')
        pass

    def getName(self):
        return self.__name

    def getMeta(self, key=None):
        if(key == None):
            return self.__metadata
        else:
            return self.__metadata[key]

    def pull(self):
        self.__repo.remotes.origin.pull(refspec='{}:{}'.format('master', 'master'))

    def pushYML(self, msg):
        self.save()
        self.__repo.index.add("."+self.__name+".yml")
        self.__repo.index.commit(msg)
        if(self.linkedRemote()):
            self.__repo.remotes.origin.push(refspec='{}:{}'.format('master', 'master'))

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

    def ports(self):
        vhd_files = glob.glob(self.__localPath+"/**/*"+".vhd", recursive=True)
        port_file = None
        for vhd in vhd_files:
            if(vhd.count(self.getMeta("toplevel")) > 0):
                port_file = vhd
                break
        
        port_txt = ''
        rolling_entity = False
        with open(port_file, 'r') as f:
            for line in f:
                #discover when the entity block begins
                if(line.lower() == ('entity '+self.getName().lower()+' is\n')):
                    rolling_entity = True
                
                if(rolling_entity):
                    port_txt = port_txt + line
                #handle the 3 variations of how to end a entity block
                if(line.lower() == "end entity "+self.getName().lower()+";\n" or \
                    line.lower() == "end entity;\n" or \
                    line.lower() == "end "+self.getName().lower()+";\n"):
                    rolling_entity = False
                    break
            f.close()
        print(port_txt)
        pass

    def log(self):
        pass

    pass


def main():
    pass


if __name__ == "__main__":
    main()