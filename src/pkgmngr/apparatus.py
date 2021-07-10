#load in settings
import yaml,os

class Apparatus:
    SETTINGS = dict()
    #defines path to working dir of 'legoHDL' tool
    PKGMNG_PATH = os.path.realpath(__file__)[:os.path.realpath(__file__).rfind('/')+1]
    #path to registry and cache
    HIDDEN = os.path.expanduser("~/.legohdl/") 

    @classmethod
    def load(cls):
        with open(cls.PKGMNG_PATH+"settings.yml", "r") as file:
            cls.SETTINGS = yaml.load(file, Loader=yaml.FullLoader)
        if(cls.SETTINGS['local'][len(cls.SETTINGS['local'])-1] != '/'):
            cls.SETTINGS['local']+"/"
        pass
    
    @classmethod
    def save(cls):
        with open(cls.PKGMNG_PATH+"settings.yml", "w") as file:
            yaml.dump(cls.SETTINGS, file)
        pass

    @classmethod
    def linkedRemote(cls):
        return cls.SETTINGS['remote'] != None

    #forward-slash fixer
    @classmethod
    def fs(cls, path):
        return path.replace('\\','/')

    pass