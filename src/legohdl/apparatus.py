#load in settings
import copy
from genericpath import isdir, isfile
import yaml,os,logging as log
import stat
from subprocess import check_output
import shutil

class Apparatus:
    SETTINGS = dict()

    #path to registry and cachess
    HIDDEN = os.path.expanduser("~/.legohdl/")

    MARKER = "Block.lock"

    TEMPLATE = HIDDEN+"/template/"

    WORKSPACE = HIDDEN

    OPTIONS = ['active-workspace', 'multi-develop', 'author', 'template', \
               'editor', 'label', 'market', 'script', 'workspace']

    META = ['name', 'library', 'version', 'summary', 'toplevel', 'bench', 'remote', 'market', 'derives']
    
    #this is preppended to the tag to make it unique for legoHDL
    TAG_ID = ''        

    __active_workspace = None

    @classmethod
    def initialize(cls):
        os.makedirs(cls.HIDDEN, exist_ok=True)
        os.makedirs(cls.HIDDEN+"workspaces/", exist_ok=True)
        os.makedirs(cls.HIDDEN+"scripts/", exist_ok=True)
        os.makedirs(cls.HIDDEN+"registry/", exist_ok=True)
        os.makedirs(cls.HIDDEN+"template/", exist_ok=True)
        #create bare settings.yml if DNE
        if(not os.path.isfile(cls.HIDDEN+"settings.yml")):
            settings_file = open(cls.HIDDEN+"settings.yml", 'w')
            structure = ''
            for opt in cls.OPTIONS:
                structure = structure + opt
                if(opt == 'label'):
                    structure = structure + ":\n  recursive: {}\n"
                    structure = structure + "  shallow: {}\n"
                else:
                    structure = structure + ": null\n"

            settings_file.write(structure)
            settings_file.close()

    @classmethod
    def generateDefault(cls, t, *args):
        for a in args:
            if(isinstance(cls.SETTINGS[a], t) == False):
                if(t == dict):
                    cls.SETTINGS[a] = {}
                elif(t == bool):
                    cls.SETTINGS[a] = False

    @classmethod
    def load(cls):
        log.basicConfig(format='%(levelname)s:\t%(message)s', level=log.INFO)
        #ensure all necessary hidden folder structures exist
        cls.initialize()

        #load dictionary data in variable
        with open(cls.HIDDEN+"settings.yml", "r") as file:
            cls.SETTINGS = yaml.load(file, Loader=yaml.FullLoader)
        #create any missing options
        for opt in cls.OPTIONS:
            if(opt not in cls.SETTINGS.keys()):
                cls.SETTINGS[opt] = None

        #ensure all pieces of settings are correct
        cls.generateDefault(dict,"market","script","workspace")
        cls.generateDefault(bool,"multi-develop")
        
        cls.dynamicWorkspace()

        #determine current workspace currently being used
        cls.__active_workspace = cls.SETTINGS['active-workspace']

        if(not cls.inWorkspace()):
            log.warning("Active workspace not found!")
            return

        if(cls.SETTINGS['template'] is not None and os.path.isdir(cls.SETTINGS['template'])):
            cls.TEMPLATE = cls.SETTINGS['template']
            pass
        
        if(cls.SETTINGS['workspace'][cls.__active_workspace]['local'] == None):
            log.error("Please specify a local path! See \'legohdl help config\' for more details")

        cls.WORKSPACE = cls.HIDDEN+"workspaces/"+cls.SETTINGS['active-workspace']+"/"

        #ensure no dead scripts are populated in 'script' section of settings
        cls.dynamicScripts()
        pass
    
    #automatically create local paths for workspaces or delete hidden folders
    @classmethod
    def dynamicWorkspace(cls):
        acting_ws = cls.SETTINGS['active-workspace']
        for ws,val in cls.SETTINGS['workspace'].items():
            #try to make this local directory
            if("local" in val.keys() and os.path.isdir(val['local']) == False):
                os.makedirs(val['local'],exist_ok=True)
            cls.initializeWorkspace(ws)

        ws_dirs = os.listdir(cls.HIDDEN+"workspaces/")
        #remove any hidden workspace folders that are no longer in the settings.yml
        for ws in ws_dirs:
            if(ws not in cls.SETTINGS['workspace'].keys()):
                #delete if found a directory type
                if(os.path.isdir(cls.HIDDEN+"workspaces/"+ws)):
                    shutil.rmtree(cls.HIDDEN+"workspaces/"+ws, onerror=cls.rmReadOnly)
                #delete if found a file type
                else:
                    os.remove(cls.HIDDEN+"workspaces/"+ws)

        if(acting_ws != None):
            cls.SETTINGS['active-workspace'] = acting_ws
        pass
    
    #automatically manage if a script still exists and clean up non-existent scripts
    @classmethod
    def dynamicScripts(cls):
        #loop through all script entries
        deletions = []
        for key,val in cls.SETTINGS['script'].items():
            exists = False
            parsed = val.split()
            #try every part of the value as a path
            for pt in parsed:
                pt = pt.replace("\"","").replace("\'","")
                if(os.path.isfile(pt)):
                    exists = True
                    break
            #mark this pair for deletion from settings
            if(not exists):
                deletions.append(key)
        #clean dead script from scripts section
        for d in deletions:
            del cls.SETTINGS['script'][d]
            #print(d)
        cls.save()

    @classmethod
    def inWorkspace(cls):
        #determine current workspace currently being used
        cls.__active_workspace = cls.SETTINGS['active-workspace']
        if(cls.__active_workspace == None or cls.__active_workspace not in cls.SETTINGS['workspace'].keys() or \
           os.path.isdir(cls.HIDDEN+"workspaces/"+cls.__active_workspace) == False):
            return False
        else:
            return True

    @classmethod
    def initializeWorkspace(cls, name):
        workspace_dir = cls.HIDDEN+"workspaces/"+name+"/"
        if(os.path.isdir(workspace_dir) == False):
            log.info("Creating workspace directories.")
            os.makedirs(workspace_dir, exist_ok=True)
        os.makedirs(workspace_dir+"lib", exist_ok=True)
        os.makedirs(workspace_dir+"cache", exist_ok=True)
        if(not os.path.isfile(workspace_dir+"map.toml")):
            open(workspace_dir+"map.toml", 'w').write("[libraries]\n")
        
        #make sure market is a list
        if(isinstance(cls.SETTINGS['workspace'][name]['market'],list) == False):
            cls.SETTINGS['workspace'][name]['market'] = []
        #make sure local is a string 
        if(isinstance(cls.SETTINGS['workspace'][name]['local'],str) == False):
            cls.SETTINGS['workspace'][name]['local'] = None
            if(cls.SETTINGS['active-workspace'] == name):
                cls.SETTINGS['active-workspace'] = None
                return

        #if no active-workspace then set it as active
        if(not cls.inWorkspace()):
            cls.SETTINGS['active-workspace'] = name
            cls.__active_workspace = name

    @classmethod
    def confirmation(cls, prompt):
        log.warning(prompt+" [y/n]")
        verify = input().lower()
        while True:
            if(verify == 'y'):
                return True
            elif(verify == 'n'):
                return False
            verify = input("[y/n]").lower()
    
    @classmethod
    def save(cls):
        with open(cls.HIDDEN+"settings.yml", "w") as file:
            yaml.dump(cls.SETTINGS, file)
        pass

    @classmethod
    def getLocal(cls):
        return cls.SETTINGS['workspace'][cls.__active_workspace]['local']

    #return the block file metadata from a specific version tag already includes 'v'
    #if returned none then it is an invalid legohdl release point
    @classmethod
    def getBlockFile(cls, repo, tag, path="./", in_branch=True):
        #checkout repo to the version tag and dump yaml file
        repo.git.checkout(tag)
        #find Block.lock
        if(os.path.isfile(path+cls.MARKER) == False):
            #return None if Block.lock DNE at this tag
            log.warning(tag+" is an invalid block version. Cannot upload "+tag+".")
            meta = None
        #Block.lock exists so read its contents
        else:
            log.info(tag+" is a valid version not found in this market. Uploading...")
            with open(path+cls.MARKER, 'r') as f:
                meta = yaml.load(f, Loader=yaml.FullLoader)

        #revert back to latest release
        if(in_branch == True):
            #in a branch so switch back
            repo.git.switch('-')
        #in a single branch (cache) so checkout back
        else:
            repo.git.checkout('-')
        #perform additional safety measure that this tag matches the 'version' found in meta
        if(meta['version'] != tag[1:]):
            log.error("Close but not close enough")
            meta = None
        return meta

    #returns workspace-level markets or system-wide markets
    @classmethod
    def getMarkets(cls, workspace_level=True):
        returnee = dict()
        #key: name, val: url
        if(cls.inWorkspace() and workspace_level):
            for name in cls.SETTINGS['workspace'][cls.__active_workspace]['market']:
                if(name in cls.SETTINGS['market'].keys()):
                    returnee[name] = cls.SETTINGS['market'][name]
        elif(cls.inWorkspace()):
            for name in cls.SETTINGS['market'].keys():
                returnee[name] = cls.SETTINGS['market'][name]
        return returnee

    @classmethod
    def isValidURL(cls, url):
        if(url == None or url.count(".git") == 0): #quick test to pass before actually verifying url
            return False
        log.info("Checking ability to link to url...")
        try:
            check_output(["git","ls-remote",url])
        except:
            return False
        return True

    #returns true if the current workspace has some markets listed
    @classmethod
    def linkedMarket(cls):
        rem = cls.SETTINGS['workspace'][cls.__active_workspace]['market']
        return (rem != None and len(rem))

    #forward-slash fixer
    @classmethod
    def fs(cls, path):
        if(path == None):
            return None
        path = os.path.expanduser(path)
        path = path.replace('\\','/')
        dot = path.rfind('.')
        last_slash = path.rfind('/')
        if(last_slash > dot and path[len(path)-1] != '/'):
            path = path + '/'
        return path

    #merge: place1 <- place2 (place2 has precedence)
    @classmethod
    def merge(cls, place1, place2):
        tmp = copy.deepcopy(place1)
        for lib,prjs in place1.items(): #go through each current lib
            if lib in place2.keys(): #is this lib already in merging lib?
                for prj in place2[lib]:
                    tmp[lib][prj] = place2[lib][prj]
        
        for lib,prjs in place2.items(): #go through all libs not in current lib
            if not lib in place1.keys():
                tmp[lib] = dict()
                for prj in place2[lib]:
                    tmp[lib][prj] = place2[lib][prj]
        return tmp

    @classmethod
    def rmReadOnly(cls, func, path, execinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    pass