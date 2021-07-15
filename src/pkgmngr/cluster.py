import os,shutil,git
import logging as log
from apparatus import Apparatus as apt
import yaml

class Cluster:

    def __init__(self, name, url):
        self._name = name
        self.url = url
        self._local_path = apt.HIDDEN+"registry/"+self._name
        #is there not a git repository here? if so, need to init
        if(not os.path.isdir(self._local_path+"/.git")):
            valid_remote = apt.isValidURL(url)
            url_name = url[url.rfind('/')+1:url.rfind('.git')]
            if(valid_remote):
                git.Git(apt.HIDDEN+"registry/").clone(url)
                log.info("Found and linked remote repository to "+self._name)
            else:
                git.Repo.init(self._local_path)
                log.warning("No remote repository configured for "+self._name)
                url_name = self._name
            os.rename(apt.HIDDEN+"registry/"+url_name, self._local_path)

        self._repo = git.Repo(self._local_path)
        pass

    def getName(self):
        return self._name

    def delete(self):
         if(os.path.exists(self._local_path)):
                shutil.rmtree(self._local_path)

    def setRemote(self, url):
        if((self.isRemote() and self._repo.remotes.origin.url != self.url) or (not self.isRemote())):
            if(url == "local"):
                if(self.isRemote()): #unlink remote
                    log.info("Removing link for "+self._name+" to "+self.url+"...")
                    self._repo.git.remote("rm","origin")
                return
            valid_remote = apt.isValidURL(url)
            #is this a valid remote path? if it is and we have no origin, make it linked!
            if(not self.isRemote() and valid_remote):
                self._repo.create_remote('origin', self.url)
                log.info("Creating link for "+self._name+" to "+self.url+"...")
            elif(self.isRemote() and valid_remote):
            #is this a valid remote path? do we already have one? if we already have a remote path, delete folder
                log.info("Swapping link for "+self._name+" to "+self.url+"...")
                if(os.path.exists(self._local_path)):
                    shutil.rmtree(self._local_path)
                git.Git(apt.HIDDEN+"registry/").clone(url) #and clone from new valid remote path
                url_name = url[url.rfind('/')+1:url.rfind('.git')]
                os.rename(apt.HIDDEN+"registry/"+url_name, self._local_path)
            else:
                log.error("Invalid link- setting could not be changed")
                if(self.isRemote()):
                    self.url = self._repo.remotes.origin.url

    def publish(self, meta, options):
        #create new directory
        fp = self._local_path+"/"+meta['library']+"/"+meta['name']+"/"+meta['version']+"/"
        #save yaml file
        os.makedirs(fp)
        with open(fp+".lego.lock", 'w') as file:
            yaml.dump(meta, file)
        #save changes to repository
        self._repo.index.add(self._repo.untracked_files)
        self._repo.index.commit("Adds "+meta['library']+'.'+meta['name']+" v"+meta['version'])
        if(self.url != 'local'):
            active_branch = self._repo.active_branch
            if(options.count("request")):
                self._repo.git.checkout("-b",meta['library']+"."+meta['name']+"-"+meta['version'])
            self._repo.git.push("-u","origin",str(self._repo.head.reference))
            self._repo.git.checkout(active_branch)
        pass


    def isRemote(self):
        return len(self._repo.remotes)

    def getPath(self):
        return self._local_path

    def __str__(self):
        return f"{self._name}, {self.url}"
    pass