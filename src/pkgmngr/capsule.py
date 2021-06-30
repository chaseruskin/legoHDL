import os

#a capsule is a package/module that is signified by having the capsule.yml
class Capsule:
    def __init__(self, pathway=''):
        
        if (isValidPackage(pathway)): #this package is already existing
            #load in metadata from YML
            pass
        else: #create a new project
            #generate new metadata
            pass 
        self.__name = ''
        self.__version = ''
        self.__metadata = dict()
        pass
    

    def push_remote(self):
        pass
    
    def load(self):
        pass

    def save(self):
        pass

    def log(self):
        pass

    pass


def isValidPackage(self, pkg):
        return os.path.isfile(self.local+"/packages/"+pkg+"/"+pkg+".yml")
        pass


def main():
    pass


if __name__ == "__main__":
    main()