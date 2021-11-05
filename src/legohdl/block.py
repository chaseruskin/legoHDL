# Project: legohdl
# Script: block.py
# Author: Chase Ruskin
# Description:
#   This script describes the attributes and behaviors for a "block" within
#   the legohdl framework. A block is a HDL project with a marker file at the 
#   root folder.

import os, shutil, stat, glob
from datetime import date

from .graph import Graph
from .vhdl import Vhdl
from .verilog import Verilog
import logging as log
from .market import Market
from enum import Enum
from .cfgfile import CfgFile as cfg
from .apparatus import Apparatus as apt
from .unit import Unit
from .language import Language
from .git import Git
from .map import Map


#a Block is a package/module that is signified by having the marker file
class Block:

    #define the various places a block can exist
    class Level(Enum):
        DNLD  = 0
        INSTL = 1
        AVAIL = 2
        VER   = 3
        pass


    LAYOUT = {'block' : {
                'name' : cfg.NULL,
                'library' : cfg.NULL,
                'version' : cfg.NULL,
                'summary' : cfg.NULL,
                'toplevel' : cfg.NULL,
                'bench' : cfg.NULL,
                'remote' : cfg.NULL,
                'market' : cfg.NULL,
                'derives' : []}
            }

    #class attribute that is a block object found on current path
    _Current = None

    #class container listing storing all created blocks
    Inventory = Map()

    #class container storing the relationships between blocks
    Hierarchy = Graph()


    def __init__(self, path, ws, lvl=Level.DNLD):
        '''
        Create a legohdl Block object. 
        
        If a valid Block.cfg file is found as the path or within the direct
        path directory, title is ignored and data is loaded from metadata.

        Parameters:
            path (str): the filepath to the Block's root directory
            ws (Workspace): the workspace this block belongs to
            lvl (Block.Level): the level at which the block exists
        '''
        #store the block's workspace
        self._ws = ws
        
        self._path = apt.fs(path)
        #is this a valid Block marker?
        fname = os.path.basename(path)

        self._lvl = lvl
        
        if(fname == apt.MARKER):
            self._path,_ = os.path.split(path)
            self._path = apt.fs(self._path)
            pass
        #try to see if a Block marker is within this directory
        elif(os.path.isdir(path)):
            files = os.listdir(path)
            for f in files:
                if(f == apt.MARKER):
                    self._path = apt.fs(path)
                    break
        #check if valid
        if(self.isValid()):
            #create Git object if not a VER
            if(self._lvl != Block.Level.VER):
                self._repo = Git(self.getPath())
            #are the two paths equal to each other? then this is the current block
            if(apt.isEqualPath(self.getPath(), os.getcwd())):
                self.setCurrent(self)
            #load from metadata
            self.loadMeta()
            #add the block to the inventory
            success = self.addToInventory()

            #store specifc installation versions in a map
            if(success and self._lvl == Block.Level.INSTL):
                self.getInstalls()
            pass
        pass


    @classmethod
    def setCurrent(cls, b):
        cls._Current = b


    def getLvl(self, to_int=True):
        '''Casts _lvl (Block.Level) to (int).'''
        if(to_int):
            return int(self._lvl.value)
        else:
            return self._lvl


    def addToInventory(self):
        '''
        Adds the self block object to the class container at the correct level.

        Blocks of level VER are skipped when trying to add to the Inventory.

        Parameters:
            None
        Returns:
            (bool): determine if the block was successfully added (spot empty)
        '''
        #make sure appropriate scopes exists in inventory
        if(self.M() not in Block.Inventory.keys()):
            Block.Inventory[self.M()] = Map()
        if(self.L() not in Block.Inventory[self.M()].keys()):
            Block.Inventory[self.M()][self.L()] = Map()
        #define empty tuple for all of a block's levels
        if(self.N() not in Block.Inventory[self.M()][self.L()].keys()):
            Block.Inventory[self.M()][self.L()][self.N()] = [None, None, None]
        #check if the level location is empty
        if(self.getLvl() < len(Block.Inventory[self.M()][self.L()][self.N()])):
            if(Block.Inventory[self.M()][self.L()][self.N()][self.getLvl()] != None):
                log.error("Block "+self.getFull()+" already exists at level "+str(self.getLvl())+"!")
                return False
            #add to inventory if spot is empty
            else:
                Block.Inventory[self.M()][self.L()][self.N()][self.getLvl()] = self

        #update graph
        Block.Hierarchy.addVertex(self.getFull(inc_ver=True))
        for d in self.getMeta('derives'):
            Block.Hierarchy.addEdge(self.getFull(inc_ver=True), d)

        return True


    @classmethod
    def getCurrent(cls, bypass=False):
        if(bypass == False and cls._Current == None):
            exit(log.error("Not in a valid block!"))
        return cls._Current


    def getWorkspace(self):
        '''Returns the block's workspace _ws (Workspace).'''
        return self._ws


    #return the block's root path
    def getPath(self, low=False):
        if(low):
            return self._path.lower()
        else:
            return self._path


    def getInstalls(self, returnvers=False):
        '''
        Dynamically creates and returns map of block objects that are found
        in cache as specific installations.

        The Map uses the version number (folder name) as the key and the block
        object as the value.

        Parameters:
            returnvers (bool): determine if to only return keys (versions)
        Returns:
            _instls [Map(Block)]: list of specific block installations
            or
            [str]: list of version keys when returnvers is set
        '''
        if(hasattr(self, '_instls')):
            if(returnvers):
                return list(self._instls.keys())
            return self._instls
        
        self._instls = Map()

        #print(self.getPath())
        #get all folders one path below
        base_path,_ = os.path.split(self.getPath()[:len(self.getPath())-1])
        base_path = apt.fs(base_path)
        dirs = os.listdir(base_path)
        for d in dirs:
            if(Block.validVer(d, maj_place=True) or Block.validVer(d, maj_place=False)):
                path = apt.fs(base_path+d+'/')
                self._instls[d] = Block(path, self.getWorkspace(), lvl=Block.Level.VER)

        if(returnvers):
                return list(self._instls.keys())
        return self._instls


    def delete(self):
        '''
        Deletes the block object. Removes its path. Does not update any variables like
        the graph.
        
        Parameters:
            None
        Returns:
            None
        '''
        shutil.rmtree(self.getPath(), onerror=apt.rmReadOnly)
        pass


    def getLvlBlock(self, lvl):
        '''
        Tries to get the block of same M.L.N but at the request level.

        Returns None if the block does not exist at that level.

        Parameters:
            lvl (Block.Level): which level to get self block from
        Returns:
            (Block): the block from requested level
        '''
        return Block.Inventory[self.M()][self.L()][self.N()][int(lvl.value)]


    #download block from a url (can be from cache or remote)
    def downloadFromURL(self, rem, in_place=False):
        tmp_dir = apt.HIDDEN+"tmp/"
        if(in_place):
            #self._repo = git.Repo(self.getPath())
            #self.pull()
            exit(print("TODO"))
            return True

        success = True

        rem = apt.fs(rem)
        #new path is default to local/library/
        new_path = None #apt.fs(Workspace.getActive().getPath()+"/"+self.getLib(low=False)+"/")
        os.makedirs(new_path, exist_ok=True)
        #create temp directory to clone project into
        os.makedirs(tmp_dir, exist_ok=True)
        #clone project
        #git.Git(tmp_dir).clone(rem)

        exit(print("TODO"))
        self._path = new_path+self.getName(low=False)

        #this is a remote url, so when it clones we must make sure to rename the base folder
        if(rem.endswith(".git")):
            url_name = rem[rem.rfind('/')+1:rem.rfind('.git')]
        #this was cloned from a cached folder
        else:
            path_prts = rem.strip('/').split('/')
            url_name = path_prts[len(path_prts)-1]
        #rename the cloned folder to the case sensitive name of the block
        try:
            shutil.copytree(tmp_dir+url_name, self.getPath())
        #remove a folder that exists here because its not a block!
        except(OSError, FileExistsError):
            try:
                shutil.rmtree(self.getPath(), onerror=apt.rmReadOnly)
                shutil.copytree(tmp_dir+url_name, self.getPath())
            except:
                log.error("Download failed. A block is blocking the download path "+self.getPath()+".")
                success = False

        #assign the repo of the newly downloaded block
        #self._repo = git.Repo(self.getPath())
        #remove temp directory
        shutil.rmtree(tmp_dir, onerror=apt.rmReadOnly)
        
        #if downloaded from cache, make a master branch if no remote  
        if(len(self._repo.heads) == 0):
            #self._repo.git.checkout("-b","master")
            pass

        return success

    
    def getTitle(self, index, dist=0):
        '''
        Returns partial or full block title M.L.N. index 2 corresponds to the
        the N, 1 corresponds to L, and 0 corresponds to M.

        Parameters:
            index (int): 0-2 to indicate what section to start at
            dist (int): 0-2 indicates how many additional sections to include
        Returns:
            ((str)): tuple of requested title sections where 0 = M, 1 = L, 2 = N
        '''
        sects = (self.M(), self.L(), self.N())
        return sects[index-dist:index+1]


    def getTitle_old(self, low=True, mrkt=False):
        '''
        Returns the full block title combined.
        
        Parameters:
            low (bool): enable case-sensitivity
            mrkt (bool): prepend market name, if available
        Returns:
            (str): M.L.N format
        '''
        m = ''
        if(mrkt and self.getMeta('market') != None):
            m = self.getMeta('market')+'.'
            
        return m+self.L()+'.'+self.N()


    #return the version as only digit string, ex: 1.2.3
    def getVersion(self):
        return self.getMeta('version')


    #return highest tagged version for this block's repository
    def getHighestTaggedVersion(self):
        all_vers = self.getTaggedVersions()
        highest = '0.0.0'
        for v in all_vers:
            if(self.biggerVer(highest,v[1:]) == v[1:]):
                highest = v[1:]
        return highest


    def waitOnChangelog(self):
        change_file = self.getPath()+apt.CHANGELOG
        #check that a changelog exists for this block
        if(os.path.exists(change_file)):
            with open(change_file, 'r+') as f:
                data = f.read()
                f.seek(0)
                f.write("## v"+self.getVersion()+'\n\n'+data)
                f.close()
            #print(change_file)
            #open the changelog and wait for the developer to finish writing changes
            apt.execute(apt.getEditor(), change_file)
            try:
                resp = input("Enter 'k' when done writing CHANGELOG.md to proceed...")
            except KeyboardInterrupt:
                exit('\nExited prompt.')
            while resp.lower() != 'k':
                try:
                    resp = input()
                except KeyboardInterrupt:
                    exit('\nExited prompt.')
        return


    def release(self, msg=None, ver=None, options=[]):
        '''
        Release the block as a new version.
        '''
        if(self._repo.getRemoteURL() != ''):
            log.info("Verifying remote origin is up to date...")
            self._repo.git('remote','update')
            resp,_ = self._repo.git('status','-uno')
            if(resp.count('Your branch is up to date with') == 0 and resp.count('Your branch is ahead of') == 0):
                exit(log.error("Your branch conflicts with the remote; release failed."))

        #get current version numbers of latest valid tag
        highestVer = self.getHighestTaggedVersion()
        major,minor,patch = self.sepVer(highestVer)
        #ensure the requested version is larger than previous if it was manually set
        if(ver != None and (self.validVer(ver) == False or self.biggerVer(ver,highestVer) == highestVer)):
            next_min_version = "v"+str(major)+"."+str(minor)+"."+str(patch+1)
            exit(log.error("Invalid version. Next minimum version is: "+next_min_version))
        #capture the actual legohdl version to print to console
        b_major,b_minor,b_patch = self.sepVer(self.getVersion())
        oldVerInfo = "Releasing v"+str(b_major)+"."+str(b_minor)+"."+str(b_patch)
        #determine next version if not manually set but set by 1 of 3 flags
        if(ver == None):
            #increment version numbering according to flag
            if(options.count("maj")):
                major += 1
                minor = patch = 0
            elif(options.count("min")):
                minor += 1
                patch = 0
            elif(options.count("fix")):
                patch += 1
            #no correct flag was found
            else:
                exit(log.error("No valid version flag was identified."))
        #get version numbering from manual set
        else:
            ver = ver[1:]
            major,minor,patch = self.sepVer(ver)
        #update string syntax for new version
        ver = 'v'+str(major)+'.'+str(minor)+'.'+str(patch)
        log.info(oldVerInfo+" -> "+ver)
        
        if(ver == '' or ver[0] != 'v'):
            return
        #in order to release to market, we must have a valid git remote url
        url = self.getMeta('remote')
        if(url == ''):
            if(True): #:todo:
                cont = apt.confirmation("legohdl will not release to market "+self.__market.getName()+" because this block is not tied to a remote. Proceed anyway?")
                #user decided that is not OKAY, exiting release
                if(cont == False):
                    exit(log.info("Did not release "+ver))

        #user decided to proceed with release
        self.setMeta('version', ver[1:])
        self.save()

        #try to allow user to edit changelog before proceeding
        self.waitOnChangelog()

        log.info("Saving...")
        #add only changes made to Block.cfg file
        if(options.count('strict')):
            self._repo.add(apt.MARKER)
            if(os.path.exists(self.getPath()+apt.CHANGELOG)):
                self._repo.add(apt.CHANGELOG)
        #add all untracked changes to be included in the release commit
        else:   
            self._repo.add('.')
        #default message
        if(msg == None):
            msg = "Releases version "+self.getVersion()
        #commit new changes with message
        self._repo.commit(msg)
        #create a tag with this version
        self._repo.git('tag',ver+apt.TAG_ID)

        sorted_versions = self.sortVersions(self.getTaggedVersions())
        
        #push to remote codebase
        self._repo.push()

        #publish on market/bazaar! (also publish all versions not found)
        # :todo:
        # if(self.__market != None):
        #     changelog_txt = self.getChangeLog(self.getPath())
        #     self.__market.publish(self.getMeta(every=True), options, sorted_versions, changelog_txt)
        # elif(self.getMeta("market") != None):
        #     log.warning("Market "+self.getMeta("market")+" is not attached to this workspace.")
        pass
    

    def sortVersions(self, unsorted_vers):
        '''
        Returns a list from highest to lowest using merge sort.
        '''


        def mergeSort(l1, r1):
            '''
            Mergesort (2/2) - begin merging lists.
            '''
            sorting = []
            while len(l1) and len(r1):
                if(Block.biggerVer(l1[0],r1[0]) == r1[0]):
                    sorting.append(r1.pop(0))
                else:
                    sorting.append(l1.pop(0))
            if(len(l1)):
                sorting = sorting + l1
            if(len(r1)):
                sorting = sorting + r1
            return sorting


        #split list
        midpoint = int(len(unsorted_vers)/2)
        l1 = unsorted_vers[:midpoint]
        r1 = unsorted_vers[midpoint:]
        #recursive call to continually split list
        if(len(unsorted_vers) > 1):
            return mergeSort(self.sortVersions(l1), self.sortVersions(r1))
        else:
            return unsorted_vers


    def getTaggedVersions(self):
        '''
        Returns a list of all version #'s that had a valid TAG_ID appended from
        the git repository tags. Dynamically creates attr _tags to be used again.

        Parameters:
            None
        Returns:
            _tags ([str]): list of version values like 'v0.0.0'
        '''
        if(hasattr(self, '_tags')):
            return self._tags

        all_tags,_ = self._repo.git('tag','-l')
        #print(all_tags)
        #split into list
        all_tags = all_tags.split("\n")
        self._tags = []
        #only add any tags identified by legohdl
        for t in all_tags:
            if(t.endswith(apt.TAG_ID)):
                #trim off identifier
                t = t[:t.find(apt.TAG_ID)]
                #ensure it is valid version format
                if(self.validVer(t)):
                    self._tags.append(t)
        #print(tags)
        #return all tags
        return self._tags


    @classmethod
    def stdVer(cls, ver):
        '''
        Standardize the version argument by swapping _ with .
        '''
        return ver.replace("_",".")


    @classmethod
    def biggerVer(cls, lver, rver):
        '''
        Compare two versions. Retuns the higher version, or RHS if both equal.

        Parameters:
            lver (str): lhs version
            rver (str): rhs version
        Returns:
            ver (str): version of higher values MAJOR.MINOR.PATCH
        '''
        l1,l2,l3 = cls.sepVer(lver)
        r1,r2,r3 = cls.sepVer(rver)
        if(l1 < r1):
            return rver
        elif(l1 == r1 and l2 < r2):
            return rver
        elif(l1 == r1 and l2 == r2 and l3 <= r3):
            return rver
        return lver


    def __str__(self):
        return f'''
        id: {hex(id(self))}
        block: {self.M()+'.'+self.L()+'.'+self.N()+'('+self.V()+')'}
        path: {self.getPath()}
        '''


    @classmethod
    def validVer(cls, ver, maj_place=False):
        '''
        Returns true if can be separated into 3 numeric values and starts with 'v'.
        '''
        ver = cls.stdVer(ver)
        #must have 2 dots and start with 'v'
        if(not maj_place and (ver == None or ver.count(".") != 2 or ver.startswith('v') == False)):
            return False
        #must have 0 dots and start with 'v' when only evaluating major value
        elif(maj_place and (ver == None or ver.count(".") != 0 or ver.startswith("v") == False)):
            return False
        #trim off initial 'v'
        ver = ver[1:]
        f_dot = ver.find('.')
        l_dot = ver.rfind('.')
        #the significant value (major) must be a digit
        if(maj_place):
            return ver.isdecimal()
        #all sections must only contain digits
        return (ver[:f_dot].isdecimal() and \
                ver[f_dot+1:l_dot].isdecimal() and \
                ver[l_dot+1:].isdecimal())
    

    @classmethod
    def sepVer(cls, ver):
        '''
        Separate a version into 3 integer values.

        Parameters:
            ver (str): any type of string, can also be None
        Returns:
            r_major (int): biggest version number
            r_minor (int): middle version number
            r_patch (int): smallest version number
        '''
        ver = cls.stdVer(ver)
        if(ver == '' or ver == None):
            return 0,0,0
        if(ver[0] == 'v'):
            ver = ver[1:]

        first_dot = ver.find('.')
        last_dot = ver.rfind('.')

        try:
            r_major = int(ver[:first_dot])
        except:
            r_major = 0
        try:
            r_minor = int(ver[first_dot+1:last_dot])
        except:
            r_minor = 0
        try:
            r_patch = int(ver[last_dot+1:])
        except:
            r_patch = 0
        return r_major,r_minor,r_patch


    def isMarket(self):
        return apt.isSubPath(apt.MARKETS, self.getPath())

    def isLocal(self):
        return apt.isSubPath(self.getWorkspace().getPath(), self.getPath())

    def bindMarket(self, mkt):
        if(mkt != None):
            log.info("Tying "+mkt+" as the market for "+self.getTitle_old(low=False))
        self.setMeta('market', mkt)
        self.save()
        pass


    def getAvailableVers(self):
        return ['v'+self.getHighestTaggedVersion()]


    def secureMeta(self):
        '''
        Performs safety measures on the block's metadata. Only runs once before
        dynamically creating an attr.

        Parameters:
            None
        Returns:
            None
        '''
        if(hasattr(self, "_is_secure")):
            return

        #ensure all pieces are there
        for key in self.LAYOUT['block'].keys():
            if(key not in self.getMeta().keys()):
                #will force to save the changed file
                self._meta_backup = self.getMeta().copy()
                self.setMeta(key, '')

        #remember what the metadata looked like initially to compare for determining
        #  if needing to write file for saving
        if(hasattr(self, "_meta_backup") == False):
            self._meta_backup = self.getMeta().copy()

        #ensure derives is a proper list format
        if(self.getMeta('derives') == cfg.NULL):
            self.setMeta('derives',list())

        if(hasattr(self, "_repo")):
            #grab list of available versions
            avail_vers = self.getAvailableVers()     
            #dynamically determine the latest valid release point
            self.setMeta('version', avail_vers[0][1:])

            #set the remote correctly
            self.setMeta('remote', self._repo.getRemoteURL())
            pass

        #ensure the market is valid
        if(self.getMeta('market') != ''):
            m = self.getMeta('market')
            if(m.lower() not in self.getWorkspace().getMarkets(returnnames=True)):
                log.warning("Market "+m+" is removed from "+self.getTitle_old()+" because the market is not available in this workspace.")
                self.setMeta('market', '')
            pass

        #dynamically create attr to only allow operation to occur once
        self._is_secure = True
        return
      

    def loadMeta(self):
        '''
        Load the metadata from the Block.cfg file into the _meta dictionary.

        Also creates backup data _meta_backup for later comparison to determine
        if to save (write to file). Only performs safety checks (like reading a remote
        url) if the block loaded is the current working directory block

        Parameters:
            None
        Returns:
            None
        '''
        with open(self.getMetaFile(), "r") as file:
            self._meta = cfg.load(file, ignore_depth=True)
            file.close()
                
        #performs safety checks only on the block that is current directory
        if(self == self.getCurrent(bypass=True)):
            self.secureMeta()

        self.save()
        pass


    def newFile(self, fpath, tmplt_fpath=None, force=False):
        '''
        Create a new file from a template file to an already existing block.

        Parameters:
            fpath (str): the file to create
            tmpltfpath (str): the file to copy from
            force (bool): determine if to overwrite an existing file of same desired name
        Returns:
            success (bool): determine if operation was successful
        '''
        fpath = apt.fs(fpath)

        #make sure path will be used from current directory
        if(fpath.startswith('./') == False):
            fpath = './'+fpath

        base_path,fname = os.path.split(fpath)
        #remove extension from file's name to get template placeholder value
        fname,_ = os.path.splitext(fname)

        #make sure file doesn't already exist
        if(force == False and os.path.exists(fpath)):
            log.error("File already exists.")
            return False
        #make sure if using template file that it does exist
        if(tmplt_fpath != None and tmplt_fpath not in apt.getTemplateFiles(returnlist=True)):
            log.error(tmplt_fpath+" does not exist in the current template.")
            return False

        #create any non-existing directory paths
        os.makedirs(base_path, exist_ok=True)

        #only create a new empty file
        if(tmplt_fpath == None):
            log.info("Creating empty file "+fpath+"...")
            with open(fpath, 'w') as f:
                f.close()
            return True
        #get full path for template file
        tmplt_fpath = apt.fs(apt.getTemplatePath()+tmplt_fpath)
        #create file from template file
        log.info("Creating file "+fpath+" from "+tmplt_fpath+"...")

        #copy file
        shutil.copyfile(tmplt_fpath, fpath)
        #fill in placeholder values
        return self.fillPlaceholders(fpath, template_val=fname)

    
    def create(self, title, cp_template=True, remote=None):
        '''
        Create a new block at _path. Creates git repository if DNE and the Block.cfg
        file.

        Parameters:
            title (str): M.L.N.V format
            cp_template (bool): determine if to copy in the template to this location
            remote (str): a git url to try to hook up with the new block
            fork (bool): determine if to drop the given remote url from the block
        Returns:
            success (bool): determine if the operation executed with no flaws
        '''
        #make sure block is invalid here
        if(self.isValid()):
            log.info("Block already exists here!")
            return False

        #make sure path is within the workspace path
        if(apt.isSubPath(self.getWorkspace().getPath(), self.getPath()) == False):
            log.info("Path is not within the workspace!")
            return False

        #make sure a git repository is empty if passing in a remote
        if(remote != None and Git.isBlankRepo(remote) == False):
            if(Git.isValidRepo(remote, remote=True)):
                log.error("Cannot create a new block from an existing remote repository; see the 'init' command.")
                return False
            else:
                log.warning("Skipping invalid remote repository "+remote+"...")
        
        #will create path if DNE and copy in template files
        if(cp_template and os.path.exists(self.getPath()) == False):
            log.info("Copying in template...")
            template = apt.getTemplatePath()
            shutil.copytree(template, self.getPath())
            #delete any previous git repository that was attached to template
            if(Git.isValidRepo(self.getPath())):
                shutil.rmtree(self.getPath()+"/.git/", onerror=apt.rmReadOnly)
            #delete all folders that start with '.'
            dirs = os.listdir(self.getPath())
            for d in dirs:
                if(os.path.isdir(self.getPath()+d) and d[0] == '.'):
                    shutil.rmtree(self.getPath()+d, onerror=apt.rmReadOnly)
        #ensure this path exists before beginning to create the block
        else:
            os.makedirs(self.getPath(), exist_ok=True)

        #create the Block.cfg file if DNE
        if(self.isValid() == False):
            with open(self.getPath()+apt.MARKER, 'w') as mdf:
                cfg.save(self.LAYOUT, mdf, ignore_depth=True, space_headers=True)

        #fill in data for Block.cfg :todo:
        #load in empty meta
        self.loadMeta()

        #break into 4 title sections
        M,L,N,_ = Block.snapTitle(title)

        #check if market is in an allowed market
        if(M != ''):
            if(M.lower() in self.getWorkspace().getMarkets(returnnames=True)):
                self.setMeta("market", M)
            else:
                log.warning("Skipping invalid market name "+M+"...")

        self.setMeta('library', L)
        self.setMeta('name', N)
        self.setMeta('version', '0.0.0')
        #determine top-level and bench designs
        # :todo:

        #fill in placeholders
        if(cp_template):
            template_files = glob.glob(self.getPath()+"/**/*", recursive=True)
            for tf in template_files:
                if(os.path.isfile(tf)):
                    self.fillPlaceholders(tf, self.N())

        #configure the remote repository to be origin for new git repo
        self._repo = Git(self.getPath(), clone=remote)

        #update meta's remote url
        self.setMeta('remote', self._repo.getRemoteURL())

        print(self.getMeta(every=True))
        #save all changes to meta
        self.save(force=True)

        #commit all file changes
        self._repo.add('.')
        self._repo.commit('Creates legohdl block')

        #push to remote repository
        self._repo.push()
        #operation was successful
        return True


    def initialize(self, title, remote=None, fork=False, summary=None):
        '''
        Initializes an existing remote repository or current working directory
        into a legohdl block.

        Parameters:
            remote (str): a git url to try to hook up with the new block
            fork (bool): determine if to drop the given remote url from the block
        Returns:
            success (bool): determine if initialization was successful
        '''
        #make sure the current path is within the workspace path
        if(apt.isSubPath(self.getWorkspace().getPath(), self.getPath()) == False):
            log.error("Cannot initialize a block outside of the workspace path.")
            return False

        #make sure Block.cfg files do not exist beyond the current directory
        md_files = glob.glob(self.getPath()+"**/"+apt.MARKER, recursive=True)
        if(len(md_files) > 0 and self.isValid() == False):
            log.error("Cannot initialize a block when sub-directories are blocks.")
            return False

        #two scenarios: block exists already or block does not exist
        already_valid = self.isValid()
        #block currently exists at this folder
        if(already_valid):
            #check if trying to configure remote (must be empty)
            if(remote != None):
                if(Git.isBlankRepo(remote)):
                    success = self._repo.setRemoteURL(remote)
                    #update metadata if successfully set the url
                    if(success):
                        self.setMeta("remote",remote)
                        self._repo.push()
                else:
                    log.error("Cannot set existing block to a non-empty remote.")
                    return False
        #block does not currently exist at this folder
        else:
            exists = False
            #check if trying to use code from a remote repository
            if(remote != None):
                #make sure repository is not empty
                if(Git.isValidRepo(remote, remote=True) and Git.isBlankRepo(remote) == False):
                    #create and clone to temporary spot
                    tmp = apt.makeTmpDir()
                    Git(tmp, clone=remote)

                    #check if there is a block.cfg file here
                    for f in os.listdir(tmp):
                        if(f == apt.MARKER):
                            #print('a block file exists!')
                            exists = True
                            break

                    #check to make sure a valid title was given (repo coverage)
                    if(exists == False and self.validTitle(title) == False):
                            return False

                    #move folder contents to metadata
                    self._repo = Git(self.getPath(), clone=tmp)
                    #clean up temporary spot
                    apt.cleanTmpDir()
                    pass

            #check to make sure a valid title was given (non-remote coverage)
            if(exists == False and self.validTitle(title) == False):
                return False

            #create a Block.cfg file
            if(exists == False):
                with open(self.getPath()+apt.MARKER, 'w') as mdf:
                    cfg.save(self.LAYOUT, mdf, ignore_depth=True, space_headers=True)

            #load the new metadata
            self.loadMeta()

            #input all title components into metadata
            if(exists == False):
                M,L,N,_ = Block.snapTitle(title)
                self.setMeta('market', M)
                self.setMeta('library', L)
                self.setMeta('name', N)
            pass

        #create a git repository if DNE
        if(Git.isValidRepo(self.getPath()) == False):
            self._repo = Git(self.getPath())

        #perform safety measurements
        self.secureMeta()

        #check if trying to configure the remote for not already initialized block
        if(remote != None and already_valid == False):
            #set the remote URL
            if(fork == False):
                self._repo.setRemoteURL(remote)
                #update metadata if successfully set the url
                self.setMeta("remote", self._repo.getRemoteURL())
            #clear the remote url from this repository
            else:
                self._repo.setRemoteURL('', force=True)
                #update metadata if successfully cleared the url
                self.setMeta("remote", self._repo.getRemoteURL())
                pass

        #check if trying to configure the summary
        if(summary != None):
            self.setMeta("summary", summary)
        
        self.save(force=True)

        #if not previously already valid, add and commit all changes
        if(already_valid == False):
            self._repo.add('.')
            self._repo.commit('Initializes legohdl block')
            self._repo.push()

        #operation was successful
        return True


    def fillPlaceholders(self, path, template_val, extra_placeholders=[]):
        '''
        Replace all placeholders in a given file.

        Parameters:
            path (str): the file path who's data to be transformed
            template_val (str): the value to replace the word "template"
            extra_placeholders ([(str, str)]]): additional placeholders to find/replace
        Returns:
            success (bool): determine if operation was successful
        '''
        #make sure the file path exists
        if(os.path.isfile(path) == False):
            log.error(path+" does not exist.")
            return False
    
        #determine the author
        author = apt.getAuthor()
        #determine the date
        today = date.today().strftime("%B %d, %Y")

        placeholders = [("TEMPLATE", template_val), ("%DATE%", today), \
            ("%AUTHOR%", author), ("%BLOCK%", self.getFull())] + extra_placeholders

        #go through file and update with special placeholders
        fdata = []
        with open(path, 'r') as rf:
            lines = rf.readlines()
            for l in lines:
                for ph in placeholders:
                    #print(ph[0], ph[1])
                    l = l.replace(ph[0], ph[1])
                fdata.append(l)
            rf.close()
        
        #write new lines
        with open(path, 'w') as wf:
            for line in fdata:
                wf.write(line)
            wf.close()

        #replace all file name if contains the word 'TEMPLATE'
        #get the file name
        base_path,fname = os.path.split(path)

        #replace 'template' in file name
        fname_new = fname.replace('TEMPLATE', template_val)
        if(fname != fname_new):
            os.rename(base_path+"/"+fname, base_path+"/"+fname_new)

        #operation was successful
        return True


    @classmethod
    def validTitle(cls, title):
        '''
        Checks if the given title is valid; i.e. it has a least a library and
        name, and it is not already taken.

        Parameters:
            title (str): M.L.N.V format
        Returns:
            valid (bool): determine if the title can be used
        '''
        valid = True

        M,L,N,V = Block.snapTitle(title)

        if(valid and N == ''):
            log.error("Block must have a name component.")
            valid = False
        if(valid and L == ''):
            log.error("Block must have a library component.")
            valid = False

        return valid


    #dynamically grab the origin url if it has been changed/added by user using git
    @DeprecationWarning
    def grabGitRemote(self, newValue=None, override=False):
        if(hasattr(self, "_remote") and not override):
            return self._remote
        if(hasattr(self, "_repo") == False or self._repo == None):
            self._remote = None
            return self._remote
        if(newValue != None):
            self._remote = newValue
            return self._remote
        #try to grab from git repo object
        self._remote = None
        #print(self._repo.remotes)
        if(len(self._repo.remotes)):
            origin = self._repo.remotes
            for o in origin:
                if(o.url == self.getPath()):
                    continue
                elif(o.url.endswith(".git")):
                    self._remote = o.url
                    break
        #make sure to save if it differs
        if("remote" in self.getMeta().keys() and self.getMeta("remote") != self._remote):
            self.setMeta('remote', self._remote)
            self.save()
        return self._remote

    #generate new link to remote if previously unestablished (only for creation)
    @DeprecationWarning
    def genRemote(self, push):
        if(self.isLinked()):
            remote_url = self.getMeta("remote")
            if(remote_url == None):
                remote_url = self.grabGitRemote()
            try: #attach to remote code base
                self._repo.create_remote('origin', remote_url) 
            except: #relink origin to new remote url
                pass
            if(remote_url == None):
                return
            log.info("Writing "+remote_url+" as remote origin...")
            with self._repo.remotes.origin.config_writer as cw:
                cw.set("url", remote_url)
            if(push):
                pass
                #self._repo.git.push("-u","origin",str(self._repo.head.reference))
        pass

    #push to remote repository
    @DeprecationWarning
    def pushRemote(self):
        self._repo.remotes.origin.push(refspec='{}:{}'.format(self._repo.head.reference, self._repo.head.reference))
        self._repo.remotes.origin.push("--tags")

    #push to remote repository if exists
    @DeprecationWarning
    def pull(self):
        if(self.grabGitRemote() != None):
            log.info(self.getTitle_old()+" already exists in local path; pulling from remote...")
            self._repo.remotes.origin.pull()
        else:
            log.info(self.getTitle_old()+" already exists in local path")

    #has ability to return as lower case for comparison within legoHDL
    @DeprecationWarning
    def getName(self, low=True):
        if(self.getMeta("name") != None):
            if(low):
                return self.getMeta("name").lower()
            else:
                return self.getMeta("name")
        if(low):
            return self.__name.lower()
        else:
            return self.__name

    #has ability to return as lower case for comparison within legoHDL
    @DeprecationWarning
    def getLib(self, low=True):
        if(self.getMeta("library") != None):
            if(low):
                return self.getMeta("library").lower()
            else:
                return self.getMeta("library")
        if(low):
            return self.__lib.lower()
        else:
            return self.__lib


    def getMeta(self, key=None, every=False, sect='block'):
        '''
        Returns the value stored in the block metadata, else retuns None if
        DNE.

        Parameters:
            key (str): the case-sensitive key to the cfg dictionary
            all (bool): return entire dictionary
            sect (str): the cfg header that key belongs to in the dictionary
        Returns:
            val (str): the value behind the corresponding key
        '''
        #return everything, even things outside the block: scope
        if(every):
            return self._meta

        if(key == None):
            return self._meta[sect]
        #check if the key is valid
        elif(sect in self._meta.keys() and key in self._meta[sect].keys()):
            return self._meta[sect][key]
        else:
            return None


    def setMeta(self, key, value, sect='block'):
        '''
        Updates the block metatdata dictionary.
        
        Parameters:
            key (str): key within sect that covers the value in dictionary
            value (str): value to be at location key
            sect (str): the cfg section header that key belongs to
        Returns:
            None
        '''
        self._meta[sect][key] = value
        pass


    def isValid(self):
        '''Returns true if the requested project folder is a valid block.'''
        return os.path.isfile(self.getMetaFile())


    def getMetaFile(self):
        '''Return the path to the marker file.'''
        return self.getPath()+apt.MARKER


    def getChangeLog(self, path):
        '''
        Return the contents of the changelog, if exists. Returns None otherwise.

        Parameters:
            path (str): path that should lead to the changelog file
        Returns:
            (str): contents of the changelog lines
        '''
        path = path+"/"+apt.CHANGELOG
        if(os.path.isfile(path)):
                with open(path,'r') as f:
                    return f.readlines()
        else:
            return None


    #print out the metadata for this block
    @DeprecationWarning
    def show(self, listVers=False, ver=None, dispChange=False):
        cache_path = apt.HIDDEN+"workspaces/"+apt.SETTINGS['general']['active-workspace']+"/cache/"+self.getLib()+"/"+self.getName()+"/"
        install_vers = []
        #display the changelog if available
        if(dispChange):
            changelog_txt = self.getChangeLog(self.getPath())
            if(changelog_txt != None):
                for l in changelog_txt:
                    print(l,end='')
                print()
            else:

                exit(log.error("No CHANGELOG.md file exists for "+self.getTitle_old()+". Add one in the next release."))
            return
        #grab all installed versions in the cache
        if(os.path.isdir(cache_path)):
            install_vers = os.listdir(cache_path)

        #print out the block's current metadata (found in local path)
        if(listVers == False and ver == None):
            #print(self.getMeta(every=True))
            with open(self.getMetaFile(), 'r') as file:
                for line in file:
                    print(line,sep='',end='')
        #print out specific metadata about version if installed in cache
        elif(listVers == False and ver != None):
            if(ver in install_vers):
                with open(cache_path+ver+"/"+apt.MARKER, 'r') as file:
                    for line in file:
                        print(line,sep='',end='')
            else:
                exit(log.error("The flagged version is not installed to the cache"))
        #list all versions available for this block
        else:
            #a file exists if in market called version.log
            if(self.isMarket()):
                with open(self.getPath()+apt.VER_LOG, 'r') as file:
                    for line in file.readlines():
                        v = line.split()[0]
                        print(v)
            else:
                ver_sorted = self.sortVersions(self.getTaggedVersions())
                # :done: also * the installed versions
                #soln : grab list dir of all valid versions in cache, and match them with '*'
                # :todo : show 'x' amount at a time? then use 'f' and 'b' to paginate
                #track what major versions have been identified
                maj_vers = []
                for x in ver_sorted:
                    #constrain the list to what the user inputted
                    if(ver != None and x.startswith(ver) == False):
                        continue
                    print(x,end='\t')
                    #notify user of the installs in cache
                    if(x in install_vers):
                        print("*",end='')
                        #notify that it is a parent version
                        parent_ver = x[:x.find('.')]
                        if(parent_ver in install_vers and parent_ver not in maj_vers):
                            print("\t"+parent_ver,end='')
                        maj_vers.append(parent_ver)
                        
                    #this is the current version
                    if(x[1:] == self.getMeta("version") and not self.isLocal()):
                        print("\tlatest",end='')

                    print()
    

    def openInEditor(self):
        '''Opens this block with the configured text-editor.'''
        log.info("Opening "+self.getTitle_old()+" at... "+self.getPath())
        apt.execute(apt.getEditor(), self.getPath())
        pass
    

    def save(self, meta=None, force=False):
        '''
        Write the metadata back to the marker file only if the data has changed
        since initializing this block as an object in python.

        Parameters:
            meta (dict): :todo:
            force (bool): determine if to save no matter _meta_backup status
        Returns:
            success (bool): returns True if the file was written and saved.
        '''
        #do no rewrite meta data if nothing has changed
        if(meta == None and force == False):
            if(hasattr(self, "_meta_backup")):
                #do not save if backup metadata is the same at the current metadata
                if(self._meta_backup == self.getMeta()):
                    return False
            #do not save if no backup metadata was created (save not necessary)
            else:
                return False

        #default is to load the block's metadata
        if(meta == None):
            meta = self.getMeta(every=True)

        if(hasattr(self, "_meta_backup")):
            if(self._meta_backup != self.getMeta()):
                #print("its different!") #use for debugging
                pass

        #write back cfg values with respect to order
        with open(self.getMetaFile(), 'w') as file:
            cfg.save(meta, file, ignore_depth=True, space_headers=True)
            file.close()
        return True


    def isLinked(self):
        '''Returns true if a remote repository is linked/attached to this block.'''
        return self._repo.remoteExists()


    def copyVersionCache(self, ver, folder):
        '''
        Copies new folder to cache from base installation path and updates
        entity names within the block to have the correct appened "_v". Assumes
        to be a valid release point before entering this method.
        '''
        #checkout version
        self._repo.git('checkout',ver+apt.TAG_ID)  
        #copy files
        version_path = self.getPath()+"../"+folder+"/"
        base_path = self.getPath()
        shutil.copytree(self.getPath(), version_path)
        #log.info(version_path)
        #delete the git repository for saving space and is not needed
        shutil.rmtree(version_path+"/.git/", onerror=apt.rmReadOnly)
        #temp set local path to be inside version
        self._path = version_path
        #enable write permissions
        self.modWritePermissions(enable=True)
        #now get project sources, rename the entities and packages
        prj_srcs = self.grabCurrentDesigns(override=True)
        #create the string version of the version
        str_ver = "_"+folder.replace(".","_")
        for lib in prj_srcs.values():
            #generate list of tuple pairs of (old name, new name)
            name_pairs = {'VHDL' : [], 'VERILOG' : []}
            for u in lib.values():
                n = u.getName(low=False)
                if(u.getLanguageType() == Unit.Language.VHDL):
                    #sort from shortest to highest
                    for i in range(len(name_pairs['VHDL'])):
                        if(len(name_pairs) == 0 or len(name_pairs['VHDL'][i][0]) > len(n)):
                            name_pairs['VHDL'].insert(i, (n.lower(), (n+str_ver).lower()))
                            break
                    else:
                        name_pairs['VHDL'].append((n.lower(), (n+str_ver).lower()))
              
                elif(u.getLanguageType() == Unit.Language.VERILOG):
                    #sort from shortest to highest
                    for i in range(len(name_pairs['VERILOG'])):
                        if(len(name_pairs) == 0 or len(name_pairs['VERILOG'][i][0]) > len(n)):
                            name_pairs['VERILOG'].insert(i, (n, n+str_ver))
                            break
                    else:
                        name_pairs['VERILOG'].append((n, n+str_ver))

            #start with shortest names first
    
            #go through each unit file to update unit names in VHDL files
            for u in lib.values():
                u.getLang().setUnitName(name_pairs)

        #update the metadata file here to reflect changes
        with open(self.getPath()+apt.MARKER, 'r') as f:
            ver_meta = cfg.load(f, ignore_depth=True)
        if(ver_meta['block']['toplevel'] != cfg.NULL):
            ver_meta['block']['toplevel'] = ver_meta['block']['toplevel']+str_ver
        if(ver_meta['block']['bench'] != cfg.NULL):
            ver_meta['block']['bench'] = ver_meta['block']['bench']+str_ver

        #save metadata adjustments
        self.save(meta=ver_meta)

        #disable write permissions
        self.modWritePermissions(enable=False)

        #change local path back to base install
        self._path = base_path

        #switch back to latest version in cache
        if(ver[1:] != self.getMeta("version")):
            self._repo.git('checkout','-')
        pass


    def modWritePermissions(self, enable, path=None):
        '''
        Disable modification/write permissions of all files specified on this
        block's path.

        Parameters:
            enable (bool): determine if files to have write permissions
            path (str): path to file or directory to change (default = block's path)
        Returns:
            None
        '''
        if(path == None):
            path = self.getPath()
        else:
            path = apt.fs(path)

        all_files = glob.glob(path+"**/*.*", recursive=True)

        for f in all_files:
            #get current file permissions
            cur_permissions = stat.S_IMODE(os.lstat(f).st_mode)
            if(enable):
                #get write masks and OR with current permissions
                w_permissions = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
                os.chmod(f, cur_permissions | w_permissions)
            else:
                #flip write masks and AND with current permissions
                w_permissions = ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH
                os.chmod(f, cur_permissions & w_permissions)
            pass
        pass


    def install(self, cache_dir, ver=None, src=None):
        '''
        Install from cache (copy files) unless 'src' is set to a remote for git
        cloning. Also updates the parent (major version) if the newly installed
        version is higher.
        '''
        #create cache directory
        cache_dir = apt.fs(cache_dir)
        cache_dir = cache_dir+self.getLib()+"/"+self.getName()+"/"
        os.makedirs(cache_dir, exist_ok=True)
                
        base_cache_dir = cache_dir
        #log.debug("Cache directory: "+cache_dir)
        specific_cache_dir = base_cache_dir+self.getName()+"/"

        base_installed = (src == None and os.path.exists(specific_cache_dir))

        #ensure version is good
        if(ver == None):
            ver = 'v'+self.getVersion()
        if(ver[0] != 'v'):
            ver = 'v'+ver
        if(ver == 'v0.0.0'):
            (log.error("Version "+ver+" is not available to install."))
            return

        log.info("Installing block "+self.getTitle_old(low=False)+" version "+ver+"...")
        # 1. first download from remote if the base installation DNE or tag DNE
        if(not base_installed):
            #print("cache dir",cache_dir)
            #print(src)
            #remove old branch folder if exists
            if(os.path.exists(specific_cache_dir)):
                shutil.rmtree(specific_cache_dir, onerror=apt.rmReadOnly)
            #clone and checkout specific version tag
            Git.git('-C',cache_dir,'clone',src,'--branch',ver+apt.TAG_ID,'--single-branch')
            #git.Git(cache_dir).clone(src,"--branch",ver+apt.TAG_ID,"--single-branch")
            #url name is the only folder here that's not a valid version
            src = src.lower().replace(".git","")
            for folder in os.listdir(cache_dir):
                if(src.endswith(folder.lower())):
                    url_name = folder
                    break
            else:
                cut_slash = self.getPath()[:len(self.getPath())-1]
                url_name = cut_slash[cut_slash.rfind('/'):]

            shutil.move(cache_dir+url_name, specific_cache_dir)
            self._path = specific_cache_dir+"/"
            base_installed = True

            # :todo: 1a. modify all project files to become read-only
            self.modWritePermissions(enable=False)
 
        self._repo = Git(self.getPath())
        self.loadMeta()

        #2. now perform install from cache
        instl_vers = os.listdir(base_cache_dir)       
        if(self.validVer(ver)):
            #ensure this version is actually tagged
            if(ver in self.getTaggedVersions()):
                self._repo.git('checkout',ver+apt.TAG_ID)
                #copy files and move them to correct spot
                if(ver[1:] == self.getMeta("version")):
                    meta = self.getMeta(every=True)
                else:
                    meta = apt.getBlockFile(self._repo, ver, specific_cache_dir, in_branch=False)
                
                #check if version is actually already installed
                if ver in instl_vers:
                    log.info("Version "+ver+" is already installed.")
                else:  
                    if(meta != None):
                        #install to its version number
                        self.copyVersionCache(ver=ver, folder=ver)
                    else:
                        log.error("whomp whomp")
                        return

                #now that we have a valid version and the meta is good, try to install to major ver
                #get "major" value
                maj = ver[:ver.find('.')]
                maj_path = cache_dir+maj+"/"
                #make new path if does not exist
                if(os.path.isdir(maj_path) == False):
                    log.info("Installing block "+self.getTitle_old(low=False)+" version "+maj+"...")
                    self.copyVersionCache(ver=ver, folder=maj)
                #check the version that is living in this folder
                else:
                    with open(maj_path+apt.MARKER,'r') as f:
                        maj_meta = cfg.load(f, ignore_depth=True)
                        f.close()
                        pass
                    if(self.biggerVer(maj_meta['block']['version'], meta['block']['version']) == meta['block']['version']):
                        log.info("Updating block "+self.getTitle_old(low=False)+" version "+maj+"...")
                        #remove old king
                        shutil.rmtree(maj_path, onerror=apt.rmReadOnly)
                        #replace with new king for this major version
                        self.copyVersionCache(ver="v"+meta['block']['version'], folder=maj)
                    pass
            else:
                log.error("Version "+ver+" is not available to install.")
        pass


    def updateDerivatives(self, block_list):
        '''
        Updates the metadata section 'derives' for required blocks needed by
        the current block.

        Parameters:
            block_list ([str]): a list of block titles
        Returns:
            None
        '''
        #print("Derives:",block_list)
        update = False
        #remove itself from the block list dependencies
        if(self.getTitle_old(mrkt=True) in block_list):
            block_list.remove(self.getTitle_old(mrkt=True))
        if(len(self.getMeta('derives')) != len(block_list)):
            update = True
        for b in block_list:
            if(b not in self.getMeta('derives')):
                update = True
                break
        if(update):
            self.setMeta('derives', list(block_list))
            self.save()
        pass


    def gatherSources(self, ext=apt.SRC_CODE, path=None):
        '''
        Return all files associated with the given extensions from the specified
        path.

        Parameters:
            ext  ([str]): a list of extensions (use * to signify all files of given ext)
            path (str) : where to begin searching for files. Defaults to block's path.
        Returns:
            srcs ([str]): a list of files matching the given ext's
        '''
        srcs = []
        if(path == None):
            path = self.getPath()
        for e in ext:
            srcs = srcs + glob.glob(path+"/**/"+e, recursive=True)
        #print(srcs)
        return srcs


    @classmethod
    def snapTitle(cls, title, inc_ent=False):
        '''
        Break a title into its 4 components, if possible. Returns M,L,N,V as
        strings. Returns '' for each missing part.

        Parameters:
            title (str): the string to be parsed into title components
            inc_ent (bool): also return the entity name if found
        Returns:
            M (str): block market
            L (str): block library
            N (str): block name
            V (str): block version
            E (str): entity in the title if inc_ent is True
        '''
        delimiter = '.'
        def parseDelimiter(t):
            '''
            Returns component, remaining string.
            '''
            tmp = ''
            #locate right-most delimiter
            d_i = t.rfind(delimiter)
            #if it exists, split and return value
            if(d_i > -1):
                tmp = t[d_i+1:]
                t = t[:d_i]
                return tmp,t
            else:
                return t,''

        if(title == None):
            if(inc_ent):
                return '','','','','' #return 5 blanks
            return '','','','' #return 4 blanks
        V = ''
        #:todo: will not work if (v1.0.0):adder (version and entity together)
        #find version label if possible
        v_index = title.find('(v')
        if(v_index > -1):
            V = cls.stdVer(title[v_index+1:-1])
            title = title[:v_index]

        #split into pieces
        pieces = title.split('.')
        sects = ['']*3
        diff = 3 - len(pieces)
        for i in range(len(pieces)-1, -1, -1):
            sects[diff+i] = pieces[i]
        #check final piece if it has an entity attached
        entity = ''
        if(sects[2].count(apt.ENTITY_DELIM)):
            i = sects[2].find(apt.ENTITY_DELIM)
            entity = sects[2][i+1:]
            sects[2] = sects[2][:i]
        #assume only name given is actually the entity
        elif(inc_ent):
            entity = sects[2]
            sects[2] = ''
        if(inc_ent):
            return sects[0],sects[1],sects[2],V,entity

        return sects[0],sects[1],sects[2],V


    def identifyTop(self):
        '''
        Auto-detects the top-level design entity. Returns None if not found.

        Parameters:
            None
        Returns:
            self._top (Unit): unit object that is the top-level for this block
        '''
        #return if already identified
        if(hasattr(self, "_top")):
            return self._top
    
        self._top = None
        #constrain to only current block's units and fill out data on each unit
        units = self.getUnits(recursive=False)
        #get the names of each unit available
        top_contenders = list(units.keys())
        #iterate through each unit and eliminate unlikely top-levels
        for name,unit in units.items():
            #if the entity is value under this key, it is lower-level
            if(unit.isTb() or unit.isPkg()):
                if(name in top_contenders):
                    top_contenders.remove(name)
                continue
                
            for dep in unit.getReqs():
                if(dep.E().lower() in top_contenders):
                    top_contenders.remove(dep.E().lower())

        if(len(top_contenders) == 0):
            log.warning("No top level detected.")
        elif(len(top_contenders) > 1):
            log.warning("Multiple top levels detected. "+str(top_contenders))
            try:
                validTop = input("Enter a valid toplevel entity: ").lower()
            except KeyboardInterrupt:
                exit("\nExited prompt.")
            while validTop not in top_contenders:
                try:
                    validTop = input("Enter a valid toplevel entity: ").lower()
                except KeyboardInterrupt:
                    exit("\nExited prompt.")
            
            top_contenders = [validTop]
        #detected a single top-level design unit
        if(len(top_contenders) == 1):
            self._top = units[top_contenders[0]]

            log.info("DETECTED TOP-LEVEL ENTITY: "+self._top.E())
            self.identifyBench(self._top.E(), save=True)

            #update metadata and will save if different
            if(self._top.E() != self.getMeta("toplevel")):
                self.setMeta('toplevel', self._top.E())
                self.save()

        return self._top


    def identifyBench(self, entity_name, save=False):
        '''
        Determine what testbench is used for the top-level design entity (if 
        found). Returns None if not found.

        Parameters:
            entity_name (str): name of entity to be under test
            save (bool): determine if to record the changes to the metadata
        Returns:
            self._bench (Unit): testbench unit object
        '''
        #return if already identified
        if(hasattr(self, "_bench")):
            return self._bench

        self._bench = None 
        #load all project-level units
        units = self.getUnits(recursive=False)
        benches = []
        #iterate through each available unit and eliminate it
        for unit in units.values():
            for dep in unit.getReqs():
                if(dep.E().lower() == entity_name and unit.isTb()):
                    benches.append(unit)
        #perfect; only 1 was found  
        if(len(benches) == 1):
            self._bench = benches[0]
        #prompt user to select a testbench
        elif(len(benches) > 1):
            top_contenders = []
            for b in benches:
                top_contenders.append(b.E())
            log.warning("Multiple top level testbenches detected. "+str(top_contenders))
            try:
                validTop = input("Enter a valid toplevel testbench: ").lower()
            except KeyboardInterrupt:
                exit("\nExited prompt.")
            #force ask for the required testbench choice
            while validTop not in top_contenders:
                try:
                    validTop = input("Enter a valid toplevel testbench: ").lower()
                except KeyboardInterrupt:
                    exit("\nExited prompt.")
            #assign the testbench entered by the user
            self._bench = units[validTop]
        #print what the detected testbench is
        if(self._bench != None):
            log.info("DETECTED TOP-LEVEL BENCH: "+self._bench.E())
        else:
            log.warning("No testbench detected.")
        #update the metadata is saving
        if(save):
            if(self._bench == None):
                self.setMeta('bench', None)
            else:
                self.setMeta('bench', self._bench.E())
            self.save()
        #return the entity
        return self._bench


    def identifyTopDog(self, top=None, inc_tb=True):
        '''
        Determine what unit is utmost highest, whether it be a testbench
        (if applicable) or entity. Returns None if DNE.

        Parameters:
            top (str): a unit identifier
            inc_tb (bool): determine if to include testbench files
        Returns:
            top_dog (Unit): top-level everything
            top_dsgn (Unit): top-level design unit
            top_tb (Unit): top-level testbench for top unit
        '''
        #make sure entities exist to search for
        units = self.getUnits(recursive=False)
        if((top == None or top == '') and len(units) == 0):
            exit(log.error("There are no available units in this block."))

        top_dog = top_dsgn = top_tb = None
        #find top if given
        if(top != None and top != '' and top.lower() in units.keys()):
            top_dog = units[top]
            #assign as testbench if it is one
            if(top_dog.isTb()):
                top_tb = top_dog
            #assign as design otherwise
            elif(top_dog != None):
                top_dsgn = top_dog
                #auto-detect the testbench
                top_tb = self.identifyBench(top_dsgn.E())
                #set top_dog as the testbench if found one and allowed to be included
                if(top_tb != None and inc_tb):
                    top_dog = top_tb

            #reset graph
            Unit.resetHierarchy()
            return top_dog,top_dsgn,top_tb
        elif(top != None and top != ''):
            exit(log.error("Entity "+top+" does not exist within this block."))

        #auto-detect the top level design
        top_dsgn = self.identifyTop()
        
        if(top_dsgn != None):
            #auto-detect the top level's testbench
            top_tb = self.identifyBench(top_dsgn.E())

        #set top_dog as the testbench if found one and allowed to be included
        if(top_tb != None and inc_tb):
            top_dog = top_tb
        else:
            top_dog = top_dsgn

        #reset graph
        Unit.resetHierarchy()
        # :todo: save appropiate changes to Block.cfg file?
        return top_dog,top_dsgn,top_tb


    # :todo: store MLNV as tuple and use single function for full-access
    def getFull(self, inc_ver=False):
        title = ''
        #prepend market if not blank
        if(self.M() != ''):
            title = self.M()+'.'
        #join together library and name
        title = title+self.L()+'.'+self.N()
        #append version if requested
        if(inc_ver):
            title = title+"("+self.V()+")"
        return title


    def M(self):
        if(hasattr(self, "_M")):
            return self._M 
        #read from metadata
        self._M = self.getMeta('market')
        return self._M if(self._M != None) else ''


    def L(self):
        if(hasattr(self, "_L")):
            return self._L
        #read from metadata
        self._L = self.getMeta('library')
        return self._L 
    

    def N(self):
        if(hasattr(self, "_N")):
            return self._N 
        #read from metadata
        self._N = self.getMeta('name')
        return self._N


    def V(self):
        if(hasattr(self, "_V")):
            return self._V
        #read from metadata
        self._V = 'v'+self.getMeta('version')
        return self._V

    
    def getLangUnitCount(self):
        '''
        Returns the amount of units coded in either VHDL or VERILOG.
        
        Parameters:
            None
        Returns:
            vhdl_cnt (int): number of vhdl units
            vlog_cnt (int): number of vlog units
        '''
        dsgns = self.loadHDL().values()

        vhdl_cnt = 0
        vlog_cnt = 0
        #iterate through each design and tally if the unit is VHDL
        for dsgn in dsgns:
            if(dsgn.getLang() == Unit.Language.VHDL):
                vhdl_cnt += 1
            elif(dsgn.getLang() == Unit.Language.VERILOG):
                vlog_cnt += 1

        return vhdl_cnt, vlog_cnt


    def loadHDL(self, returnnames=False):
        '''
        Identify all HDL files within the block and all designs in each file.

        Only loads from HDL once and then will dynamically return its attr _units.
        
        Parameters:
            returnnames (bool): determine if to return list of names
        Returns:
            self._units (Map): the Unit Map object down to M/L/N level
            or
            ([str]): list of unit names if returnnames is True
        '''
        if(hasattr(self, "_units")):
            if(returnnames):
                return list(self._units.keys())
            return self._units
        #open each found source file and identify their units
        #load all VHDL files
        vhd_files = self.gatherSources(apt.VHDL_CODE, path=self.getPath())
        for v in vhd_files:
            Vhdl(v, M=self.M(), L=self.L(), N=self.N())
        #load all VERILOG files
        verilog_files = self.gatherSources(apt.VERILOG_CODE, path=self.getPath())
        for v in verilog_files:
            Verilog(v, M=self.M(), L=self.L(), N=self.N())

        #check if the level exists in the Jar
        if(Unit.jarExists(self.M(), self.L(), self.N())):
            self._units = Unit.Jar[self.M()][self.L()][self.N()]
        else:
            self._units = Map()
            
        if(returnnames):
            return list(self._units.keys())
        return self._units

    
    def getUnits(self, top=None, recursive=True):
        '''
        Returns a map for all filled HDL units found within the given block.
        
        If a top is specified, it will start deciphering from that Unit. Else, all
        HDL files within the block will be deciphered.

        If recursive is set, it will recursively decode entities upon finding them
        when decoding an architecture.

        Parameters:
            top (Unit): unit object to start with
            recursive (bool): determine if to tunnel through entities
        Returns:
            units (Map): the Unit Map object down to M/L/N level
        '''
        units = self.loadHDL()

        if(top != None and top in units.values()):
            if(top.isChecked() == False):
                Language.ProcessedFiles[top.getFile()].decode(top, recursive)
        else:
            for u in units.values():
                if(u.isChecked() == False):
                    Language.ProcessedFiles[u.getFile()].decode(u, recursive)
        #self.printUnits()
        return units


    def printUnits(self):
        for u in self._units.values():
            print(u)


    @classmethod
    def getAllBlocks(cls):
        if(hasattr(cls, '_all_blocks')):
            return cls._all_blocks
        cls._all_blocks = []
        for mrkts in cls.Inventory.values():
            for libs in mrkts.values():
                for blks in libs.values():
                    for lvl in blks:
                        if(lvl != None):
                            cls._all_blocks += [lvl]
                            break
                        pass
        return cls._all_blocks


    def get(self, entity, about, list_arch, inst, comp, lang, edges):
        '''
        Get various pieces of information about a given entity as well as any
        compatible code for instantiations.

        Parameters:
            entity (str): name of entity to be fetched
            about (bool): determine if to print the comment header
            list_arch (bool): determine if to list the architectures
            inst (bool): determine if to print instantiation
            comp (bool): determine if to print component declaration
            lang (str): VHDL or VLOG style language
            edges (bool): determine if to print graph information
        Returns:
            success (bool): determine if operation was successful
        '''
        #get quick idea of what units exist for this block
        units = self.loadHDL()
        if(entity.lower() not in units.keys()):
            log.error("Entity "+entity+" not found in this block!")
            return False

        #determine the language for outputting compatible code
        if(lang != None):
            if(lang.lower() == 'vhdl'):
                lang = Unit.Language.VHDL
            elif(lang.lower() == 'vlog'):
                lang = Unit.Language.VERILOG
            pass

        #collect data about requested entity
        self.getUnits(top=units[entity])
        #grab the desired entity from the Map
        ent = units[entity]

        #print comment header (about)
        print(ent.readAbout())
        #print dependencies
        if(edges):
            print(ent.readReqs())
            print(ent.readReqs(upstream=True))
        #print list of architectures
        if(list_arch):
            print(ent.readArchitectures())
        if(comp):
            #:todo: write component declaration code for verilog modules
            print(ent.getInterface().writeDeclaration(form=lang))
            print()
        if(inst):
            print(ent.getInterface().writeConnections(form=lang))
            lib = None
            #determine the entity's library name
            if(comp == False):
                lib = ent.L()
                #try to see if within the current block (skip error)
                if(Block.getCurrent(bypass=True) != None):
                    #use 'work' if the entity is in from the current block 
                    if(ent in (Block.getCurrent().loadHDL().values())):
                        lib = 'work'

            print(ent.getInterface().writeInstance(lang=lang, entity_lib=lib))

        return True


    def readInfo(self, readall, stats=False, versions=False):
        '''
        Return information relevant to the current block (metadata).

        Parameters:
            readall (bool): determine if to print ALL metadata
            stats (bool): determine if to print additional stats
            versions (bool): determine if to print the available versions
        Returns:
            info_txt (str): information text to be printed to console
        '''
        #make sure the metadata is properly formatted
        self.secureMeta()
        #get the metadata
        info_txt = '--- METADATA ---\n'
        with open(self.getMetaFile(), 'r') as file:
            for line in file:
                info_txt = info_txt + line
                #stop reading :todo:
                if(not readall and False):
                    break

        #read relevant stats
        if(stats):
            info_txt = info_txt + '\n--- STATS ---'
            info_txt = info_txt + '\nIntegrated into:\n'
            info_txt = info_txt + '\t'+apt.listToStr(Block.Hierarchy.getNeighbors(self.getFull(inc_ver=True), upstream=True),'\n\t')
            vhdl_units = []
            vlog_units = []
            for u in self.loadHDL().values():
                if(u.getLang() == Unit.Language.VHDL):
                    vhdl_units += [u.E()]
                elif(u.getLang() == Unit.Language.VERILOG):
                    vlog_units += [u.E()]

            if(len(vhdl_units) > 0):
                txt = '\nVHDL units:\n\t'+apt.listToStr(vhdl_units,'\n\t')
                info_txt = info_txt + txt
            if(len(vlog_units) > 0):
                txt = '\nVERILOG units:\n\t'+apt.listToStr(vlog_units,'\n\t')
                info_txt = info_txt + txt
        #read the list of versions implemented and obtainable
        if(versions):
            info_txt = ''
            #get installation versions
            instl_versions = []
            instller = self.getLvlBlock(Block.Level.INSTL)
            if(instller != None):
                instl_versions = instller.getInstalls(returnvers=True)
            #sort the versions available in cache
            instl_versions = self.sortVersions(instl_versions)
            
            #sort the versions found on the self block
            all_versions = self.sortVersions(self.getTaggedVersions())
            #track what major versions have been identified
            maj_vers = []
            #iterate through all versions
            for x in all_versions:
                #constrain the list to what the user inputted
                #if(ver != None and x.startswith(ver) == False):
                    #continue
                info_txt = info_txt + x + '\t'
                #notify user of the installs in cache
                if(x in instl_versions):
                    info_txt = info_txt + '*'
                    #notify that it is a parent version
                    parent_ver = x[:x.find('.')]
                    if(parent_ver in instl_versions and parent_ver not in maj_vers):
                        info_txt = info_txt + '\t' + parent_ver
                    maj_vers.append(parent_ver)
                    
                    #get the highest version from instl_versions (that is what's called latest) :todo:
                    if(x == instl_versions[0]):
                        info_txt = info_txt + '\t' + 'latest'
                pass
                #add new line for next version to be formatted
                info_txt = info_txt + '\n'
        return info_txt



# ==============================================================================
# ==============================================================================
# === ARCHIVED CODE... TO DELETE ===============================================
# ==============================================================================
# ==============================================================================
    @DeprecationWarning
    def grabUnits(self, toplevel=None, override=False):
        '''
        Color in (fill/complete) all units found in the design book.
        '''
        if(hasattr(self, "_unit_bank") and not override):
            return self._unit_bank
        elif(override):
            pass
            #reset graph
           # Unit.Hierarchy = Graph()
        
        #get all possible units (units are incomplete (this is intended))
        #self.grabDesigns(override, "current")
        #self.printUnits()
        #gather all project-level units
        #project_level_units = self.grabCurrentDesigns()
        
        # for name,unit in project_level_units.items():
        #    start with top-level unit and complete all required units in unit bank
            # if(toplevel == None or name == toplevel.lower()):
                # Language.ProcessedFiles[unit.getFile()].decipher()
                
        #self.printUnits()
        print(Unit.printList())
        pass

    @DeprecationWarning
    def grabDesigns(self, override, *args):
        '''
        Return incomplete (blank) unit objects from current project or cache
        (not mutually exclusive). Override is passed to the grabCurrent and
        grabCache methods.
        '''
        if("current" in args):
            self.grabCurrentDesigns(override)
            pass
        if("cache" in args):
            self.grabCacheDesigns(override)
            pass
        pass

    #return dictionary of entities with their respective files as values
    #all possible entities or packages to be used in current project
    # :todo: remove this and merge it into workspace
    @DeprecationWarning
    def grabCacheDesigns(self, override=False):
        '''
        Gathers all VHDL and verilog source files found at cache
        level and skims through them to identify design units. Skips the cache
        location if it is for the current project.
        '''
        if(hasattr(self, "_cache_designs") and not override):
            return self._cache_designs

        self._cache_designs = []
        #locate VHDL cache files
        files = self.gatherSources(apt.VHDL_CODE, apt.WORKSPACE+"cache/")
        for f in files:
            M,L,N = self.grabExternalProject(f)
            #do not add the cache files of the current level project
            if(L == self.getLib() and N == self.getName()):
                continue
            #print(f)
            vhd = Vhdl(f, M=M, L=L, N=N)
            self._cache_designs += vhd.identifyDesigns()
        
        #locate verilog cache files
        files = self.gatherSources(apt.VERILOG_CODE, apt.WORKSPACE+"cache/")
        for f in files:
            M,L,N = self.grabExternalProject(f)
            #do not add the cache files of the current level project
            if(L == self.getLib() and N == self.getName()):
                continue
            #print(f)
            vlg = Verilog(f, M=M, L=L, N=N)
            self._cache_designs += vlg.identifyDesigns()

        print("Cache-Level designs: "+str(self._cache_designs))

        #if multi-develop is enabled, overwrite the units with those found in the local path
        #also allow to work with unreleased blocks? -> yes
        if(apt.SETTINGS['general']['multi-develop'] == True):
            log.info("Multi-develop is enabled")
            #1. first find all Block.cfg files (roots of blocks)
            files = []#glob.glob(Workspace.getActive().getPath()+"**/"+apt.MARKER, recursive=True)
            #print(files)
            #2. go through each recursive search within these roots for vhd files (skip self block root)
            for f in files:
                f_dir = f.replace(apt.MARKER,"")
                with open(f, 'r') as file:
                    cfg_data = cfg.load(file, ignore_depth=True)
                M = cfg_data['block']['market']
                L = cfg_data['block']['library'].lower()
                N = cfg_data['block']['name'].lower()
                #skip self block
                if(L == self.getLib() and N == self.getName()):
                    continue
                #3. open each found source file and insert units into cache design
                vhd_files = self.gatherSources(apt.VHDL_CODE, path=f_dir)
                for v in vhd_files:
                    vhd = Vhdl(v, M=M, L=L, N=N)
                    self._cache_designs += vhd.identifyDesigns()
                
                verilog_files = self.gatherSources(apt.VERILOG_CODE, path=f_dir)
                for v in verilog_files:
                    vlg = Verilog(v, M=M, L=L, N=N)
                    self._cache_designs += vlg.identifyDesigns()

        #print("Cache-Level designs: "+str(self._cache_designs))
        return self._cache_designs


    @DeprecationWarning
    def grabCurrentDesigns(self, override=False):
        '''
        Gathers all VHDL and verilog source files found at current
        project level and skims through them to identify design units.
        '''
        if(hasattr(self, "_cur_designs") and not override):
            return self._cur_designs

        self._cur_designs = []
        
        #locate vhdl sources
        files = self.gatherSources(apt.VHDL_CODE)
        for f in files:
            vhd = Vhdl(f, M=self.M(), L=self.L(), N=self.N())
            self._cur_designs += vhd.identifyDesigns()
        #locate verilog sources
        files = self.gatherSources(apt.VERILOG_CODE)
        for f in files:
            vlg = Verilog(f, M=self.M(), L=self.L(), N=self.N())
            self._cur_designs += vlg.identifyDesigns()

        self._cur_designs = Unit.Jar[self.M()][self.L()][self.N()]

        print("Project-Level Designs: "+str(self._cur_designs))
        return self._cur_designs
    
    @DeprecationWarning
    def grabExternalProject(cls, path):
        '''
        Uses the file path to determine what block owns this file in the cache.
        Returns M,L,N (N also has '(v0.0.0)') appended.
        '''
        #print(path)
        #break up path into into its parts
        path_parse = apt.fs(path).split('/')
        #if in cache /cache/{library}/{block}/../.vhd
        if("cache" in path_parse):
            i = path_parse.index("cache")
            pass
        else:
            return '','',''
        M = None
        #next part is {library}
        L = path_parse[i+1].lower()
        #next next part is {name}
        N = path_parse[i+2].lower()
        #next next next part is either {version #} (for specific version) or {name} (for latest)
        V = path_parse[i+3].lower()
        
        last_p = ''
        #determine when to cut off the path to get to root of block project directory
        path_to_block_file = ''
        for p in path_parse:
            #append next path part
            path_to_block_file = path_to_block_file + p + '/'
            #stop if this part is the version # and its not the name
            if(p == V and p != N):
                break
            #stop if this part is the 'version #' and the last part was also the 'vesion #' (name)
            if(p == V and last_p == V):
                break
            #track what the last part appended was
            last_p = p
            pass

        #the latest version is found here
        latest_block_path = apt.WORKSPACE+"cache/"+L+"/"+N+"/"+N+"/"

        #open and read what the version number is for this current project
        with open(path_to_block_file+apt.MARKER, 'r') as f:
            meta = cfg.load(f, ignore_depth=True)
            N = N+"(v"+meta['block']['version']+")"
            cur_M = meta['block']['market']
            if(cur_M != cfg.NULL and cur_M.lower() in apt.getMarketNames().keys()):
                M = cur_M

        #determine what the latest market being used is for this block
        with open(latest_block_path+apt.MARKER, 'r') as f:
            meta = cfg.load(f, ignore_depth=True)
            latest_M = meta['block']['market']
            if(latest_M != cfg.NULL and latest_M.lower() in apt.getMarketNames().keys()):
                M = latest_M
 
        return M,L,N

    @DeprecationWarning
    def ports(self, mapp, lib, pure_entity, entity=None, ver=None, showArc=False):
        #self.getUnits(top=entity)
        info = ''
        if(entity == None):
            entity = self.getMeta("toplevel")
        if(entity == None):
            return info
        #tack on version number if given as arg
        if(ver != None):
            entity = entity+"_"+ver.replace(".","_")
            
        if(entity.lower() in Unit.Bottle[self.L()].keys()):
            #display the various defined architectures
            if(showArc):
                #fill out decipher to get architectures
                u = Unit.Bottle[self.L()][entity]
                Language.ProcessedFiles[u.getFile()].decipher()
                info = u.writeArchitectures()
            #display the port interface
            else:
                info = Unit.Bottle[self.L()][entity].readAbout()      
        else:
            exit(log.error("Cannot locate entity "+entity+" in block "+self.getTitle_old(low=False)))
        
        if(len(info.strip()) == 0):
            exit(log.error("Empty ports list for entity "+entity+"!"))
        return info


    @DeprecationWarning
    def create2(self, fresh=True, git_exists=False, remote=None, fork=False, inc_template=True):
        '''
        Create a new block using the template and attempt to set up a remote.

        Parameters:
            fresh (bool): if creating a block from scratch (no existing files)
            git_exists (bool): if the current folder already has a git repository
            remote (str): the url to the remote repository (None if DNE)
            fork (bool): if wanting to not attach the remote that was used to initialize
            inc_template (bool): determine if to copy the template files
        Returns:
            None
        '''
        log.info('Initializing new block...')
        #copy template folder to new location if its a fresh project
        if(fresh):
            if(os.path.isdir(apt.TEMPLATE)):
                if(inc_template):
                    log.info("Copying template...")
                    #copy all files from template project
                    shutil.copytree(apt.TEMPLATE, self.getPath())
                    #delete any previous git repository that was attached to template
                    if(os.path.isdir(self.getPath()+"/.git/")):
                        shutil.rmtree(self.getPath()+"/.git/", onerror=apt.rmReadOnly)
                    #delete all folders that start with '.'
                    dirs = os.listdir(self.getPath())
                    for d in dirs:
                        if(os.path.isdir(self.getPath()+'/'+d) and d[0] == '.'):
                            shutil.rmtree(self.getPath()+'/'+d, onerror=apt.rmReadOnly)
                else:
                    log.info("Skipping template...")
            else:
                os.makedirs(self.getPath(), exist_ok=True)

        #clone from existing remote repo
        if(not fresh and self.grabGitRemote() != None and ((self._repo != None and not apt.isRemoteBare(self.grabGitRemote()))  or self._repo == None)):
            log.info("Cloning project from remote url...")
            self.downloadFromURL(self.grabGitRemote(), in_place=True)
        #make a new repo
        elif(not git_exists):
            #self._repo = git.Repo.init(self.getPath())
            pass
        #there is already a repo here
        elif(fresh):
            #self._repo = git.Repo(self.getPath())
            pass
            #does a remote exist?
            if(self.grabGitRemote(override=True) != None):
                #ensure we have the latest version before creating marker file
                #self._repo.git.pull()
                pass

        #create the marker file
        with open(self.getPath()+apt.MARKER, 'w') as f:
            cfg.save(self.LAYOUT, f, ignore_depth=True, space_headers=True)

        #search through all templated files and fill in placeholders
        if(fresh):
            #replace all file names that contain the word 'template'
            replacements = glob.glob(self.getPath()+"/**/*template*", recursive=True)
            for f in replacements:
                if(os.path.isfile(f)):
                    os.rename(f, f.replace('template', self.getName(low=False)))
            #determine the author
            author = apt.SETTINGS['general']["author"]
            if(author == None):
                author = ''
            #determie the date
            today = date.today().strftime("%B %d, %Y")

            #go through all files and update with special placeholders
            allFiles = glob.glob(self.getPath()+"/**/*", recursive=True)
            for f in allFiles:
                file_data = []
                #store and transform lines into file dictionary
                if(os.path.isfile(f) == False):
                    continue
                with open(f, 'r') as read_file:
                    for line in read_file.readlines():
                        line = line.replace("template", self.getName(low=False))
                        line = line.replace("%DATE%", today)
                        line = line.replace("%AUTHOR%", author)
                        line = line.replace("%BLOCK%", self.getTitle_old(low=False))
                        file_data.append(line)
                    read_file.close()
                #write new lines
                with open(f, 'w') as write_file:
                    for line in file_data:
                        write_file.write(line)
                    write_file.close()
                pass
            pass

        #generate fresh metadata fields
        self.loadMeta() 
        self.setMeta('name', self.getName(low=False))
        self.setMeta('library', self.getLib(low=False))
        self.setMeta('version', '0.0.0')
        #log.info("Remote status: "+self.getMeta("remote"))
        self.identifyTop()
        log.debug(self.getName())
        #set the remote if not None
        if(remote != None):
            self.setRemote(remote, push=False)
        #save current progress into cfg
        self.save() 
        #add and commit to new git repository
        #self._repo.git.add('.') #self._repo.index.add(self._repo.untracked_files)
        #try:
            #self._repo.git.commit('-m','Initializes block')
        #except git.exc.GitCommandError:
            #log.warning("Nothing new to commit.")

        #set it up to track origin
        if(self.grabGitRemote() != None):
            #sync with remote repository if not forking
            if(fork == False):
                log.info('Pushing to remote repository...')
                #try:
                    #self._repo.git.push("-u","origin",str(self._repo.head.reference))
                #except git.exc.GitCommandError:
                    #log.warning("Cannot configure remote origin because it is not empty!")
                    #remove remote url from existing areas
                    #self._repo.delete_remote('origin')
                    #self.setRemote(None, push=False)
                    #self.save()
            else:
                log.info("Detaching remote from block...")
                #self._repo.delete_remote('origin')
                #self.setRemote(None, push=False)
                #self.save()
        else:
            log.info('No remote code base attached to local repository')
        pass


    @DeprecationWarning
    def init_old(self, title=None, path=None, remote=None, excludeGit=False, market=None):
        self._meta = {'block' : {}}
        #split title into library and block name
        _,self.__lib,self.__name,_ = Block.snapTitle(title, lower=False)
        if(remote != None):
            self._remote = remote
        self.__market = market

        self._path = apt.fs(path)
        if(path != None):
            if(self.isValid()):
                #if(not excludeGit):
                    #try:
                        #self._repo = git.Repo(self.getPath())
                    #make git repository if DNE
                    #except git.exc.InvalidGitRepositoryError:
                        #self._repo = git.Repo.init(self.getPath())
                self.loadMeta()
                return
        #elif(path == None):
            #self._path = apt.fs(Workspace.getActive().getPath()+"/"+self.getLib(low=False)+"/"+self.getName(low=False)+'/')

        #try to see if this directory is indeed a git repo
        #self._repo = None
        #try:
            #self._repo = git.Repo(self.getPath())
        #except:
            #pass

        #if(remote != None):
            #self.grabGitRemote(remote)

        #is this block already existing?
        #if(self.isValid()):
            #load in metadata from cfg
            #self.loadMeta()
        pass


    pass


def main():
    pass


if __name__ == "__main__":
    main()