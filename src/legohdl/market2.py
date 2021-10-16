# Project: legohdl
# Script: market.py
# Author: Chase Ruskin
# Description:
#   The Market class. A Market object is directory that holds the metadata for
#   blocks that are availble for download/install. It is a special git 
#   repository that keeps the block metadata.

import os,shutil,glob
import logging as log
from .map import Map
from .git import Git
from .apparatus import Apparatus as apt


class Market2:
    #store all markets in class container
    Jar = Map()

    DIR = apt.fs(apt.HIDDEN+"markets/")
    EXT = ".mrkt"
    
    def __init__(self, name, url=None):
        '''
        Create a Market instance. If creating from a url, the `name` parameter
        will be ignored and the `name` will equal the filename of the .mrkt.
        Parameters:
            name (str): market's name
            url (str): optionally an existing market url
        Returns:
            None
        '''
        #create market if DNE
        if(name.lower() in Market2.Jar.keys()):
            log.warning("Skipping market "+name+" due to name conflict.")
            return

        self._name = name

        #create new market with new remote
        #does this market exist?
        success = True
        if(os.path.exists(self.getMarketDir()) == False):
            #are we trying to create one from an existing remote?
            if(url != None):
                success = self.loadFromURL(url)
            #proceed here if not using an existing remote
            if(success == False):
                #check again if the path exists if a new name was set in loading from URL
                if(os.path.exists(self.getMarketDir())):
                    return
                #create market directory 
                os.makedirs(self.getMarketDir())
                # create .mrkt file
                open(self.getMarketDir()+self.getName()+self.EXT, 'w').close()
            pass
        
        #create git repository object
        self._repo = Git(self.getMarketDir())

        #are we trying to attach a blank remote?
        if(success == False):
            if(Git.isBlankRepo(url)):
                self._repo.setRemoteURL(url)
            #if did not exist then must add and push new commits    
            self._repo.add(self.getName()+self.EXT)
            self._repo.commit("Initializes legohdl market")
            self._repo.push()

        #add to class container
        self.Jar[self.getName()] = self
        pass


    def loadFromURL(self, url):
        '''
        Attempts to load/add a market from an external path/url. Will not add
        if the path is not a non-empty git repository, does not have .mrkt, or
        the market name is already taken.

        Parameters:
            url (str): the external path/url that is a market to be added
        Returns:
            success (bool): if the market was successfully add to markets/ dir
        '''
        success = True

        if(Git.isValidRepo(url, remote=True) == False and Git.isValidRepo(url, remote=False) == False):
            log.error("Invalid repository "+url+".")
            return False

        #create temp dir
        os.makedirs(apt.TMP)

        #clone from repository
        if(Git.isBlankRepo(url) == False):
            tmp_repo = Git(apt.TMP, clone=url)

            #determine if a .prfl file exists
            log.info("Locating .mrkt file... ")
            files = os.listdir(apt.TMP)
            for f in files:
                mrkt_i = f.find(self.EXT)
                if(mrkt_i > -1):
                    #remove extension to get the profile's name
                    self._name = f[:mrkt_i]
                    log.info("Identified market "+self.getName()+".")
                    break
            else:
                log.error("Invalid market; could not locate "+self.EXT+" file.")
                success = False

            #try to add profile if found a name (.mrkt file)
            if(hasattr(self, '_name')):
                #do not add to profiles if name is already in use
                if(self.getName().lower() in self.Jar.keys()):
                    log.error("Cannot add market "+self.getName()+" due to name conflict.")
                    success = False
                #add to profiles folder
                else:
                    log.info("Adding market "+self.getName()+"...")
                    self._repo = Git(self.getMarketDir(), clone=apt.TMP)
                    #assign the correct url to the market
                    self._repo.setRemoteURL(tmp_repo.getRemoteURL())
        else:
            success = False

        #clean up temp dir
        shutil.rmtree(apt.TMP, onerror=apt.rmReadOnly)
        return success


    def publish(self):
        '''
        Publishes a block's new metadata to the market and syncs with remote
        repository.
        '''
        # :todo:
        pass


    def refresh(self):
        '''
        If has a remote repository, checks with it to ensure the current branch
        is up-to-date and pulls any changes.
        
        Parameters:
            None
        Returns:
            None
        '''
        log.info("Refreshing market "+self.getName()+"...")
        #check status from remote
        if(self._repo.isLatest() == False):
            log.info('Pulling new updates...')
            self._repo.pull()
            log.info("success")
        else:
            log.info("Already up-to-date.")
        pass


    def setRemoteURL(self, url):
        '''
        Grants ability to set a remote url only if it is 1) valid 2) blank and 3) a remote
        url is not already set.

        Parameters:
            url (str): the url to try and set for the given market
        Returns:
            (bool): true if the url was successfully attached under the given constraints.
        '''
        #check if remote is already set
        if(self._repo.getRemoteURL() != ''):
            log.error("Market "+self.getName()+" already has a remote URL.")
            return False
        #proceed
        #check if url is valid and blank
        if(Git.isValidRepo(url, remote=True) and Git.isBlankRepo(url)):
            log.info("Attaching remote "+url+" to market "+self.getName()+"...")
            self._repo.setRemoteURL(url)
            #push any changes to sync remote repository
            self._repo.push()
            return True
        log.error("Remote could not be added to market "+self.getName()+".")
        return False


    def remove(self):
        '''
        Removes a market from legohdl markets/ and the class container.

        Parameters:
            None
        Returns:
            None
        '''
        log.info("Deleting market "+self.getName()+"...")
        #remove directory
        shutil.rmtree(self.getMarketDir(), onerror=apt.rmReadOnly)
        #remove from Jar
        del self.Jar[self.getName()]


    @classmethod
    def tidy(cls):
        '''
        Removes all stale markets that are not found in the markets/ directory.

        Parameters:
            None
        Returns:
            None
        '''
        #list all markets
        mrkt_files = glob.glob(cls.DIR+"**/*"+cls.EXT, recursive=True)
        for f in mrkt_files:
            mrkt_name = os.path.basename(f).replace(cls.EXT,'')
            #remove a market that is not found in settings (Jar class container)
            if(mrkt_name.lower() not in cls.Jar.keys()):
                log.info("Removing stale market "+mrkt_name+"...")
                mrkt_dir = f.replace(os.path.basename(f),'')
                # :todo: uncomment next line to take effect
                #shutil.rmtree(mrkt_dir, onerror=apt.rmReadOnly)
            pass

        pass


    def getMarketDir(self):
        return apt.fs(self.DIR+self.getName())


    def getName(self):
        return self._name


    @classmethod
    def printAll(cls):
        for key,mrkt in cls.Jar.items():
            print('key:',key)
            print(mrkt)
    
    
    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        name: {self.getName()}
        dir: {self.getMarketDir()}
        remote: {self._repo.getRemoteURL()}
        '''

    pass
