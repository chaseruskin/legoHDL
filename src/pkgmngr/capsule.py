import os, yaml, git, shutil
from datetime import date
import collections

#a capsule is a package/module that is signified by having the capsule.yml
class Capsule:
    settings = None
    pkgmngPath = ''
    def __init__(self, name='', new=False):
        self.__name = name
        self.__version = '0.0.0'
        self.__metadata = dict()
        self.__remoteURL = None
        self.__localPath = Capsule.settings['local']+self.__name+'/'
        self.__repo = None

        if(self.isValid()): #this package is already existing
            if(new):
                print('This project already locally exists')
            #configure remote url
            if(self.linkedRemote()):
                self.__remoteURL = self.settings['remote']+self.__name+".git"
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
            self.loadMeta() #generate fresh metadata fields
        pass

    def loadMeta(self):
        with open(self.metadataPath(), "r") as file:
            self.metadata = yaml.load(file, Loader=yaml.FullLoader)
            file.close()
        
        self.__version = self.metadata['version']
        if(self.metadata['derives'] == None):
            self.metadata['derives'] = dict()
        if(self.metadata['integrates'] == None):
            self.metadata['integrates'] = dict()

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

        self.__repo.index.add(self.__repo.untracked_files)
        self.__repo.index.commit("Initializes project.")
        if(self.linkedRemote()):
            print('Generating new remote repository...')
            self.__repo.remotes.origin.push(refspec='{}:{}'.format('master', 'master'))
        else:
            print('No remote code base attached to local repository')
        pass

    #return true if the requested project folder is a valid capsule package
    def isValid(self):
        try:
            return os.path.isfile(self.metadataPath())
        except:
            return False
        pass

    def linkedRemote(self):
        return (self.settings['remote'] != None)

    def metadataPath(self):
        return self.__localPath+"."+self.__name+".yml"

    def push_remote(self):
        pass
    
    def load(self):
        pass

    def save(self):
        #write back YAML info
        print(self.__version)
        tmp = collections.OrderedDict(self.metadata)
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
        pass

    def log(self):
        pass

    pass


def main():
    pass


if __name__ == "__main__":
    main()