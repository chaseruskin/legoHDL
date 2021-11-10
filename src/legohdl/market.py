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
from .cfgfile import CfgFile as cfg


class Market:
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
        if(name.lower() in Market.Jar.keys()):
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


    def publish(self, block):
        '''
        Publishes a block's new metadata to the market and syncs with remote
        repository.

        Parameters:
            block (Block): the block to publish to this market
        Returns:
            None
        '''
        log.info("Publishing "+block.getFull(inc_ver=True)+" to market "+self.getName()+"...")
        
        #make sure the market is up-to-date
        self.refresh(quiet=True)

        #make sure the path exists in market
        path = self.getMarketDir()+block.L()+'/'+block.N()+'/'
        os.makedirs(path, exist_ok=True)

        meta_path = path+apt.MARKER
        
        #add more information to the metadata before publishing to market
        meta = block.getMeta(every=True).copy()

        meta['block']['versions'] = block.sortVersions(block.getTaggedVersions())

        #write metadata to marker file in market for this block
        with open(meta_path, 'w') as meta_file:
            cfg.save(meta, meta_file, ignore_depth=True, space_headers=True)
            pass

        #stage changes
        self._repo.add(block.L()+'/'+block.N()+'/'+apt.MARKER)

        self._repo.commit("Publishes "+block.getFull(inc_ver=True))

        #synchronize changes with its remote
        self._repo.push()

        log.info("Success.")
        pass


    def refresh(self, quiet=False):
        '''
        If has a remote repository, checks with it to ensure the current branch
        is up-to-date and pulls any changes.
        
        Parameters:
            quiet (bool): determine if to display information to user or keep quiet
        Returns:
            None
        '''
        if(self._repo.remoteExists()):
            log.info("Refreshing market "+self.getName()+"...")
            #check status from remote
            if(self._repo.isLatest() == False):
                log.info('Pulling new updates...')
                self._repo.pull()
                log.info("success")
            else:
                log.info("Already up-to-date.")
        elif(quiet == False):
            log.info("Market "+self.getName()+" is local and does not require refresh.")
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
    def load(cls):
        '''Load all markets from settings.'''

        mrkts = apt.SETTINGS['market']
        for name,url in mrkts.items():
            url = None if(url == cfg.NULL) else url
            Market(name, url=url)
        pass


    @classmethod
    def save(cls):
        '''Save markets to settings.'''

        serialize = {}
        for mrkt in cls.Jar.values():
            serialize[mrkt.getName()] = mrkt._repo.getRemoteURL()
            
        apt.SETTINGS['market'] = serialize
        apt.save()
        pass


    @classmethod
    def printList(cls, active_markets=[]):
        '''
        Prints formatted list for markets with availability to active-workspace
        and their remote connection, and number of available blocks.

        Parameters:
            active_markets ([Market]): list of market objects belonging to active workspace
        Returns:
            None
        '''
        print('{:<15}'.format("Market"),'{:<48}'.format("Remote Repository"),'{:<7}'.format("Blocks"),'{:<7}'.format("Active"))
        print("-"*15+" "+"-"*48+" "+"-"*7+" "+"-"*7)
        for mrkt in cls.Jar.values():
            active = 'yes' if(mrkt in active_markets) else '-'
            val = mrkt._repo.getRemoteURL() if(mrkt.isRemote()) else 'local'
            print('{:<15}'.format(mrkt.getName()),'{:<48}'.format(val),'{:<7}'.format(mrkt.getBlockCount()),'{:<7}'.format(active))
            pass

        pass


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


    def getBlockCount(self):
        '''
        Returns the amount of block marker files found within the market's
        directory.

        Dynamically creates _block_count attr for faster future reference.

        Parameters:
            None
        Returns:
            _block_count (int): number of blocks hosted in the market
        '''
        if(hasattr(self, "_block_count")):
            return self._block_count
        #compute the block count by finding how many cfg block files are in market
        self._block_count = len(glob.glob(self.getMarketDir()+"**/*"+apt.MARKER, recursive=True))
        return self._block_count


    def isRemote(self):
        '''Determine if the market has an existing remote connection (bool).'''
        return self._repo.remoteExists()
        

    def getMarketDir(self):
        '''Returns the market directory (str).'''
        return apt.fs(self.DIR+self.getName())


    def getName(self):
        '''Returns _name (str).'''
        return self._name


    @classmethod
    def printAll(cls):
        for key,mrkt in cls.Jar.items():
            print('key:',key)
            print(mrkt)
    
    
    def __str__(self):
        '''Returns string object translation.'''
        return f'''
        ID: {hex(id(self))}
        name: {self.getName()}
        dir: {self.getMarketDir()}
        remote: {self._repo.getRemoteURL()}
        '''

    pass
