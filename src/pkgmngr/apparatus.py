#load in settings
import yaml,os,logging as log,shutil,git
from remote import Remote

class Apparatus:
    SETTINGS = dict()
    #defines path to working dir of 'legoHDL' tool
    PKGMNG_PATH = os.path.realpath(__file__)[:os.path.realpath(__file__).rfind('/')+1]
    #path to registry and cache
    HIDDEN = os.path.expanduser("~/.legohdl/")

    WORKSPACE = HIDDEN

    __active_workspace = None

    LOG = log.getLogger("main")

    @classmethod
    def load(cls):
        log.basicConfig(format='%(levelname)s:\t%(message)s', level=log.INFO)

        with open(cls.PKGMNG_PATH+"settings.yml", "r") as file:
            cls.SETTINGS = yaml.load(file, Loader=yaml.FullLoader)
        
        #determine current workspace currently being used
        cls.__active_workspace = cls.SETTINGS['active-workspace']

        if(cls.__active_workspace == None or cls.__active_workspace not in cls.SETTINGS['workspace'].keys()):
            exit("ERROR- Active workspace not found!")
        
        if(cls.SETTINGS['workspace'][cls.__active_workspace]['local'] == None):
            exit("ERROR- Please specify a local path! See \'legohdl help config\' for more details")

        cls.WORKSPACE = cls.HIDDEN+"workspaces/"+cls.SETTINGS['active-workspace']+"/"
        pass

    @classmethod
    def cloneRemote(cls, name, url):
        #clone new remote
        url = cls.fs(url)
        remote_dir = cls.HIDDEN+"registry/"+name
        if(os.path.exists(remote_dir)):
            shutil.rmtree(remote_dir)
        url_name = url[url.rfind('/')+1:url.rfind('.git')]
        git.Git(cls.HIDDEN+"registry/").clone(url)
        os.rename(cls.HIDDEN+"registry/"+url_name, remote_dir)
        pass

    @classmethod
    def initializeWorkspace(cls, name):
        workspace_dir = cls.HIDDEN+"workspaces/"+name+"/"
        os.makedirs(workspace_dir, exist_ok=True)
        os.mkdir(workspace_dir+"lib")
        os.mkdir(workspace_dir+"cache")
        open(workspace_dir+"map.toml", 'w').write("[libraries]\n")
    
    @classmethod
    def save(cls):
        with open(cls.PKGMNG_PATH+"settings.yml", "w") as file:
            yaml.dump(cls.SETTINGS, file)
        pass
    
    @classmethod
    def getLocal(cls):
        return cls.SETTINGS['workspace'][cls.__active_workspace]['local']

    @classmethod
    def getRemotes(cls):
        returnee = dict()
        for name in cls.SETTINGS['workspace'][cls.__active_workspace]['remote']:
            returnee[name] = (Remote(name, cls.SETTINGS['remote'][name]))
        return returnee

    @classmethod
    def linkedRemote(cls):
        rem = cls.SETTINGS['workspace'][cls.__active_workspace]['remote']
        return (rem != None and len(rem))

    #forward-slash fixer
    @classmethod
    def fs(cls, path):
        path = os.path.expanduser(path)
        path = path.replace('\\','/')
        dot = path.rfind('.')
        last_slash = path.rfind('/')
        if(last_slash > dot and path[len(path)-1] != '/'):
            path = path + '/'
        return path
    pass