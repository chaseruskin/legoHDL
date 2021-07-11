#load in settings
import yaml,os

class Apparatus:
    SETTINGS = dict()
    #defines path to working dir of 'legoHDL' tool
    PKGMNG_PATH = os.path.realpath(__file__)[:os.path.realpath(__file__).rfind('/')+1]
    #path to registry and cache
    HIDDEN = os.path.expanduser("~/.legohdl/") 

    __active_workspace = None

    @classmethod
    def load(cls):
        with open(cls.PKGMNG_PATH+"settings.yml", "r") as file:
            cls.SETTINGS = yaml.load(file, Loader=yaml.FullLoader)
        
        #determine current workspace currently being used
        cls.__active_workspace = cls.SETTINGS['active-workspace']

        if(cls.__active_workspace == None or cls.__active_workspace not in cls.SETTINGS['workspace'].keys()):
            exit("ERROR- Active workspace not found!")
        
        cls.SETTINGS['local'] = cls.SETTINGS['workspace'][cls.__active_workspace]['local']
        cls.SETTINGS['remote'] = cls.SETTINGS['workspace'][cls.__active_workspace]['remote']

        if(len(cls.SETTINGS['remote']) == 0):
            cls.SETTINGS['remote'] = None
        
        if(cls.SETTINGS['local'] == None):
            exit("ERROR- Please specify a local path! See \'legohdl help config\' for more details")
        pass
    
    @classmethod
    def save(cls):
        with open(cls.PKGMNG_PATH+"settings.yml", "w") as file:
            yaml.dump(cls.SETTINGS, file)
        pass

    @classmethod
    def linkedRemote(cls):
        return cls.SETTINGS['remote'] != None

    @classmethod
    def localPath(cls):
        return cls.SETTINGS['local']

    #forward-slash fixer
    @classmethod
    def fs(cls, path):
        return path.replace('\\','/')

    pass