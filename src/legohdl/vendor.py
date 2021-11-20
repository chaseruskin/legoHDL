# ------------------------------------------------------------------------------
# Project: legohdl
# Script: vendor.py
# Author: Chase Ruskin
# Description:
#   The Vendor class. A Vendor object is directory that holds the metadata for
#   blocks that are availble for download/install. It is a special git 
#   repository that keeps the block metadata.
# ------------------------------------------------------------------------------

import os,shutil,glob
import logging as log
from .map import Map
from .git import Git
from .apparatus import Apparatus as apt
from .cfgfile import CfgFile as cfg


class Vendor:
    #store all vendors in class container
    Jar = Map()

    DIR = apt.fs(apt.HIDDEN+"vendors/")
    EXT = ".vndr"
    
    def __init__(self, name, url=None):
        '''
        Create a Vendor instance. If creating from a url, the `name` parameter
        will be ignored and the `name` will equal the filename of the .vndr.
        Parameters:
            name (str): vendor's name
            url (str): optionally an existing vendor url
        Returns:
            None
        '''
        #create vendor if DNE
        if(name.lower() in Vendor.Jar.keys()):
            log.warning("Skipping vendor "+name+" due to name conflict.")
            return

        self._name = name

        #create new vendor with new remote
        #does this vendor exist?
        success = True
        if(os.path.exists(self.getVendorDir()) == False):
            #are we trying to create one from an existing remote?
            if(url != None):
                success = self.loadFromURL(url)
            else:
                success = False
            #proceed here if not using an existing remote
            if(success == False):
                #check again if the path exists if a new name was set in loading from URL
                if(os.path.exists(self.getVendorDir())):
                    return
                #create vendor directory 
                os.makedirs(self.getVendorDir())
                # create .vndr file
                open(self.getVendorDir()+self.getName()+self.EXT, 'w').close()
            pass
        
        #create git repository object
        self._repo = Git(self.getVendorDir())

        #are we trying to attach a blank remote?
        if(success == False):
            log.info("Creating new vendor "+self.getName()+"...")
            if(url != None and Git.isBlankRepo(url)):
                self._repo.setRemoteURL(url)
            #if did not exist then must add and push new commits    
            self._repo.add(self.getName()+self.EXT)
            self._repo.commit("Initializes legohdl vendor")
            self._repo.push()

        #add to class container
        self.Jar[self.getName()] = self
        pass


    def loadFromURL(self, url):
        '''
        Attempts to load/add a vendor from an external path/url. Will not add
        if the path is not a non-empty git repository, does not have .vndr, or
        the vendor name is already taken.

        Parameters:
            url (str): the external path/url that is a vendor to be added
        Returns:
            success (bool): if the vendor was successfully add to vendors/ dir
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
            log.info("Locating .vndr file... ")
            files = os.listdir(apt.TMP)
            for f in files:
                vndr_i = f.find(self.EXT)
                if(vndr_i > -1):
                    #remove extension to get the profile's name
                    self._name = f[:vndr_i]
                    log.info("Identified vendor "+self.getName()+".")
                    break
            else:
                log.error("Invalid vendor; could not locate "+self.EXT+" file.")
                success = False

            #try to add profile if found a name (.vndr file)
            if(success and hasattr(self, '_name')):
                #do not add to profiles if name is already in use
                if(self.getName().lower() in self.Jar.keys()):
                    log.error("Cannot add vendor "+self.getName()+" due to name conflict.")
                    success = False
                #add to profiles folder
                else:
                    log.info("Adding vendor "+self.getName()+"...")
                    self._repo = Git(self.getVendorDir(), clone=apt.TMP)
                    #assign the correct url to the vendor
                    self._repo.setRemoteURL(tmp_repo.getRemoteURL())
        else:
            success = False

        #clean up temp dir
        shutil.rmtree(apt.TMP, onerror=apt.rmReadOnly)
        return success


    def publish(self, block):
        '''
        Publishes a block's new metadata to the vendor and syncs with remote
        repository.

        Parameters:
            block (Block): the block to publish to this vendor
        Returns:
            None
        '''
        log.info("Publishing "+block.getFull(inc_ver=True)+" to vendor "+self.getName()+"...")
        
        #make sure the vendor is up-to-date
        self.refresh(quiet=True)

        #make sure the path exists in vendor
        path = self.getVendorDir()+block.L()+'/'+block.N()+'/'
        os.makedirs(path, exist_ok=True)

        meta_path = path+apt.MARKER
        
        #add more information to the metadata before publishing to vendor
        meta = block.getMeta(every=True).copy()

        #add what versions are available
        meta['block']['versions'] = block.sortVersions(block.getTaggedVersions())

        #add the size of latest project (kilobytes)
        meta['block']['size'] = block.getSize()

        #add VHDL units and Verilog units
        vhdl_units = block.loadHDL(lang='vhdl', returnnames=True)
        vlog_units = block.loadHDL(lang='vlog', returnnames=True)

        if(len(vhdl_units)):
            meta['block']['vhdl-units'] = vhdl_units
        if(len(vlog_units)):
            meta['block']['vlog-units'] = vlog_units

        #write metadata to marker file in vendor for this block
        with open(meta_path, 'w') as meta_file:
            cfg.save(meta, meta_file, ignore_depth=True, space_headers=True)
            pass

        #write changelog in vendor for this block (if exists)
        if(block.getChangelog() != None):
            #get the changelog name
            _,cl_file = os.path.split(block.getChangelog())
            #copy changelog into vendor
            shutil.copyfile(block.getChangelog(), path+cl_file)
            #stage changelog change
            self._repo.add(block.L()+'/'+block.N()+'/'+cl_file)

        #stage meta changes
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
            log.info("Refreshing vendor "+self.getName()+"...")
            #check status from remote
            if(self._repo.isLatest() == False):
                log.info('Pulling new updates...')
                self._repo.pull()
                log.info("success")
            else:
                log.info("Already up-to-date.")
        elif(quiet == False):
            log.info("Vendor "+self.getName()+" is local and does not require refresh.")
        pass


    def setRemoteURL(self, url):
        '''
        Grants ability to set a remote url only if it is 1) valid 2) blank and 3) a remote
        url is not already set.

        Parameters:
            url (str): the url to try and set for the given vendor
        Returns:
            (bool): true if the url was successfully attached under the given constraints.
        '''
        #check if remote is already set
        if(self._repo.getRemoteURL() != ''):
            log.error("Vendor "+self.getName()+" already has a remote URL.")
            return False
        #proceed
        #check if url is valid and blank
        if(Git.isValidRepo(url, remote=True) and Git.isBlankRepo(url)):
            log.info("Attaching remote "+url+" to vendor "+self.getName()+"...")
            self._repo.setRemoteURL(url)
            #push any changes to sync remote repository
            self._repo.push()
            return True
        log.error("Remote could not be added to vendor "+self.getName()+".")
        return False


    def remove(self):
        '''
        Removes a vendor from legohdl vendors/ and the class container.

        Parameters:
            None
        Returns:
            None
        '''
        log.info("Deleting vendor "+self.getName()+"...")
        #remove directory
        shutil.rmtree(self.getVendorDir(), onerror=apt.rmReadOnly)
        #remove from Jar
        del self.Jar[self.getName()]


    @classmethod
    def load(cls):
        '''Load all vendors from settings.'''

        vndrs = apt.SETTINGS['vendor']
        for name,url in vndrs.items():
            url = None if(url == cfg.NULL) else url
            Vendor(name, url=url)
        pass


    @classmethod
    def save(cls):
        '''Save vendors to settings.'''

        serialize = {}
        for vndr in cls.Jar.values():
            serialize[vndr.getName()] = vndr._repo.getRemoteURL()
            
        apt.SETTINGS['vendor'] = serialize
        apt.save()
        pass


    @classmethod
    def printList(cls, active_vendors=[]):
        '''
        Prints formatted list for vendors with availability to active-workspace
        and their remote connection, and number of available blocks.

        Parameters:
            active_vendors ([Vendor]): list of vendor objects belonging to active workspace
        Returns:
            None
        '''
        print('{:<15}'.format("Vendor"),'{:<48}'.format("Remote Repository"),'{:<7}'.format("Blocks"),'{:<7}'.format("Active"))
        print("-"*15+" "+"-"*48+" "+"-"*7+" "+"-"*7)
        for vndr in cls.Jar.values():
            active = 'yes' if(vndr in active_vendors) else '-'
            val = vndr._repo.getRemoteURL() if(vndr.isRemote()) else 'local'
            print('{:<15}'.format(vndr.getName()),'{:<48}'.format(val),'{:<7}'.format(vndr.getBlockCount()),'{:<7}'.format(active))
            pass

        pass


    @classmethod
    def tidy(cls):
        '''
        Removes all stale vendors that are not found in the vendors/ directory.

        Parameters:
            None
        Returns:
            None
        '''
        #list all vendors
        vndr_files = glob.glob(cls.DIR+"**/*"+cls.EXT, recursive=True)
        for f in vndr_files:
            vndr_name = os.path.basename(f).replace(cls.EXT,'')
            #remove a vendor that is not found in settings (Jar class container)
            if(vndr_name.lower() not in cls.Jar.keys()):
                log.info("Removing stale vendor "+vndr_name+"...")
                vndr_dir = f.replace(os.path.basename(f),'')
                # delete the vendor directory
                shutil.rmtree(vndr_dir, onerror=apt.rmReadOnly)
            pass

        pass


    def getBlockCount(self):
        '''
        Returns the amount of block marker files found within the vendor's
        directory.

        Dynamically creates _block_count attr for faster future reference.

        Parameters:
            None
        Returns:
            _block_count (int): number of blocks hosted in the vendor
        '''
        if(hasattr(self, "_block_count")):
            return self._block_count
        #compute the block count by finding how many cfg block files are in vendor
        self._block_count = len(glob.glob(self.getVendorDir()+"**/*"+apt.MARKER, recursive=True))
        return self._block_count


    def isRemote(self):
        '''Determine if the vendor has an existing remote connection (bool).'''
        return self._repo.remoteExists()
        

    def getVendorDir(self):
        '''Returns the vendor directory (str).'''
        return apt.fs(self.DIR+self.getName())


    def getName(self):
        '''Returns _name (str).'''
        return self._name


    @classmethod
    def printAll(cls):
        for key,vndr in cls.Jar.items():
            print('key:',key)
            print(vndr)
    

    # uncomment to use for debugging 
    # def __str__(self):
    #     '''Returns string object translation.'''
    #     return f'''
    #     ID: {hex(id(self))}
    #     name: {self.getName()}
    #     dir: {self.getVendorDir()}
    #     remote: {self._repo.getRemoteURL()}
    #     '''


    pass
