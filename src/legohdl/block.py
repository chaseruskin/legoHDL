################################################################################
#   Project: legohdl
#   Script: block.py
#   Author: Chase Ruskin
#   Description:
#       This script describes the attributes and behaviors for a "block" within
#   the legohdl framework. A block is a HDL project with a marker file at the 
#   root folder.
################################################################################

import os, shutil
from datetime import date
import glob, git
import logging as log
from .market import Market
from .cfgfile import CfgFile as cfg
from .apparatus import Apparatus as apt
from .graph import Graph 
from .unit import Unit


#a Block is a package/module that is signified by having the marker file
class Block:

    def __init__(self, title=None, path=None, remote=None, new=False, excludeGit=False, market=None):
        self.__metadata = dict()
        #split title into library and block name
        self.__lib,self.__name = Block.split(title, lower=False)

        self._remote = remote
        self.__market = market

        self.__local_path = apt.fs(path)
        if(path != None):
            if(self.isValid()):
                if(not excludeGit):
                    try:
                        self._repo = git.Repo(self.getPath())
                    #make git repository if DNE
                    except git.exc.InvalidGitRepositoryError:
                        self._repo = git.Repo.init(self.getPath())
                self.loadMeta()
                return
        elif(path == None):
            self.__local_path = apt.fs(apt.getLocal()+"/"+self.getLib(low=False)+"/"+self.getName(low=False)+'/')

        #try to see if this directory is indeed a git repo
        self._repo = None
        try:
            self._repo = git.Repo(self.getPath())
        except:
            pass

        if(remote != None):
            self.grabGitRemote(remote)

        #is this block already existing?
        if(self.isValid()):
            #load in metadata from cfg
            self.loadMeta()
        #create a new block
        elif(new):
            #create the repo and directory structure
            self.create(remote=remote) 
        pass

    #return the block's root path
    def getPath(self, low=False):
        if(low):
            return self.__local_path.lower()
        else:
            return self.__local_path

    #download block from a url (can be from cache or remote)
    def downloadFromURL(self, rem, in_place=False):
        tmp_dir = apt.HIDDEN+"tmp/"
        if(in_place):
            self._repo = git.Repo(self.getPath())
            self.pull()
            return

        rem = apt.fs(rem)
        #new path is default to local/library/
        new_path = apt.fs(apt.getLocal()+"/"+self.getLib(low=False)+"/")
        os.makedirs(new_path, exist_ok=True)
        #create temp directory to clone project into
        os.makedirs(tmp_dir, exist_ok=True)
        #clone project
        git.Git(tmp_dir).clone(rem)

        self.__local_path = new_path+self.getName(low=False)

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
            shutil.rmtree(self.getPath(), onerror=apt.rmReadOnly)
            shutil.copytree(tmp_dir+url_name, self.getPath())

        #assign the repo of the newly downloaded block
        self._repo = git.Repo(self.getPath())
        #remove temp directory
        shutil.rmtree(tmp_dir, onerror=apt.rmReadOnly)
        
        #if downloaded from cache, make a master branch if no remote  
        if(len(self._repo.heads) == 0):
            self._repo.git.checkout("-b","master")

    #return the full block name (library.name)
    def getTitle(self, low=True, mrkt=False):
        '''
        Returns the L.N of block.
        
        Parameters:
        ---
        low (bool) : enable case-sensitivity
        mrkt (bool) : prepend market name, if available
        '''
        m = ''
        if(mrkt and self.getMeta('market') != None):
            m = self.getMeta('market')+'.'
            
        return m+self.getLib(low=low)+'.'+self.getName(low=low)

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
            print(change_file)
            os.system(apt.SETTINGS['general']['editor']+" "+change_file)
            resp = input("Enter 'k' when done writing CHANGELOG.md to proceed...")
            while resp.lower() != 'k':
                resp = input()
        return

    #release the block as a new version
    def release(self, msg=None, ver=None, options=[]):
        #dynamically link on release
        if(self.grabGitRemote() != None and hasattr(self,"_repo")):
            if(apt.isValidURL(self.grabGitRemote())):
                self.setRemote(self.grabGitRemote(), push=False)
            else:
                log.warning("Invalid remote "+self.grabGitRemote()+" will be removed from Block.cfg")
                self.setMeta('remote', None)
                self._remote = None
        if(self._remote != None):
            log.info("Verifying remote origin is up to date...")
            self._repo.git.remote('update')
            resp = self._repo.git.status('-uno')
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
                exit(log.error("No correct flag was identified."))
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
        url = self.grabGitRemote()
        if(url == None):
            if(self.__market != None):
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
            self._repo.index.add(apt.MARKER)
            if(os.path.exists(self.getPath()+apt.CHANGELOG)):
                self._repo.index.add(apt.CHANGELOG)
        #add all untracked changes to be included in the release commit
        else:   
            self._repo.git.add(update=True)
            self._repo.index.add(self._repo.untracked_files)
        #default message
        if(msg == None):
            msg = "Releases version "+self.getVersion()
        #commit new changes with message
        self._repo.git.commit('-m',msg)
        #create a tag with this version
        self._repo.create_tag(ver+apt.TAG_ID)

        sorted_versions = self.sortVersions(self.getTaggedVersions())

        #push to remote codebase!! (we have a valid remote url to use)
        if(url != None):
            self.pushRemote()
        #no other actions should happen when no url is exists
        else:
            return
        #publish on market/bazaar! (also publish all versions not found)
        if(self.__market != None):
            changelog_txt = self.getChangeLog(self.getPath())
            self.__market.publish(self.getMeta(every=True), options, sorted_versions, changelog_txt)
        elif(self.getMeta("market") != None):
            log.warning("Market "+self.getMeta("market")+" is not attached to this workspace.")
        pass
    
    #merge sort (1/2) - returns a list highest -> lowest
    def sortVersions(self, unsorted_vers):
        #split list
        midpoint = int(len(unsorted_vers)/2)
        l1 = unsorted_vers[:midpoint]
        r1 = unsorted_vers[midpoint:]
        #recursive call to continually split list
        if(len(unsorted_vers) > 1):
            return self.mergeSort(self.sortVersions(l1), self.sortVersions(r1))
        else:
            return unsorted_vers
        pass

    #merge sort (2/2) - begin merging lists
    def mergeSort(self, l1, r1):
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

    def getTaggedVersions(self):
        all_tags = self._repo.git.tag(l=True)
        #split into list
        all_tags = all_tags.split("\n")
        tags = []
        
        #only add any tags identified by legohdl
        for t in all_tags:
            if(t.endswith(apt.TAG_ID)):
                #trim off identifier
                t = t[:t.find(apt.TAG_ID)]
                #ensure it is valid version format
                if(self.validVer(t)):
                    tags.append(t)
        #print(tags)
        #return all tags
        return tags

    @classmethod
    def stdVer(cls, ver):
        return ver.replace("_",".")

    #returns rhs if equal
    @classmethod
    def biggerVer(cls, lver, rver):
        l1,l2,l3 = cls.sepVer(lver)
        r1,r2,r3 = cls.sepVer(rver)
        if(l1 < r1):
            return rver
        elif(l1 == r1 and l2 < r2):
            return rver
        elif(l1 == r1 and l2 == r2 and l3 <= r3):
            return rver
        return lver

    #return true if can be separated into 3 numeric values and starts with 'v'
    @classmethod
    def validVer(cls, ver, maj_place=False):
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
    
    #separate the version into 3 numeric values
    @classmethod
    def sepVer(cls, ver):
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

    def blockFile(self):
        '''
        Returns exact standard string for writing an empty block file.
        '''
        body = """
block:
  name:
  library:
  version:
  summary:
  toplevel:
  bench:
  remote:
  market:
  derives: []
        """
        return body

    def isMarket(self):
        return apt.isSubPath(apt.MARKETS, self.getPath())

    def isLocal(self):
        return apt.isSubPath(apt.getLocal(), self.getPath())

    def bindMarket(self, mkt):
        if(mkt != None):
            log.info("Tying "+mkt+" as the market for "+self.getTitle(low=False))
        self.setMeta('market', mkt)
        self.save()
        pass

    def setRemote(self, rem, push=True):
        if(rem != None):
            self.grabGitRemote(rem)
        elif(len(self._repo.remotes)):
            self._repo.git.remote("remove","origin")
        self.setMeta('remote', rem)
        self._remote = rem
        self.genRemote(push)
        self.save()
        pass

    def getAvailableVers(self):
        return ['v'+self.getHighestTaggedVersion()]
    
    #load the metadata from the Block.cfg file
    def loadMeta(self):
        with open(self.metadataPath(), "r") as file:
            self.__metadata = cfg.load(file)
            file.close()

        self._initial_metadata = self.getMeta().copy()

        #ensure all pieces are there
        for key in apt.META:
            if(key not in self.getMeta().keys()):
                self.setMeta(key, None)

        if(self.getMeta("remote") == cfg.NULL):
            self.setMeta("remote", None) 

        if(self.getMeta("market") == cfg.NULL):
             self.setMeta("market", None) 

        #check if this block is a local block
        if(self.isLocal()):
            #grab list of available versions
            avail_vers = self.getAvailableVers()       
            #dynamically determine the latest valid release point
            self.setMeta('version', avail_vers[0][1:])


        if(self.getMeta('derives') == cfg.NULL):
            self.setMeta('derives',list())

        if('remote' in self.getMeta().keys()):
            #upon every boot up, try to grab the remote from this git repo if it exists
            self.grabGitRemote()
            #set it if it was set by constructor
            if(self._remote != None):
                self.setMeta('remote', self._remote)
            #else set it based on the read-in value
            else:
                self._remote = self.getMeta('remote')
            
        if('market' in self.getMeta().keys()):
            #did an actual market object already get passed in?
            if(self.__market != None):
                self.setMeta('market', self.__market.getName())
            #see if the market is bound to your workspace
            elif(self.getMeta("market") != None):
                if self.getMeta("market") in apt.getMarkets().keys():
                    self.__market = Market(self.getMeta('market'), apt.SETTINGS['market'][self.getMeta('market')])
                else:
                    log.warning("Market "+self.getMeta('market')+" is removed from "+self.getTitle()+" because the market is not available in this workspace.")
                    self.setMeta('market', None)
                    self.__market = self.getMeta('market')
        self.save()
        pass

    #create a new file from a template file to an already existing block
    def fillTemplateFile(self, newfile, templateFile):
        #grab name of file
        filename = os.path.basename(newfile)
        file,_ = os.path.splitext(filename)
        
        #ensure this file doesn't already exist
        if(os.path.isfile(newfile)):
            log.info("File already exists")
            return
        log.info("Creating new file...")

        replacements = glob.glob(apt.TEMPLATE+"**/"+templateFile, recursive=True)
        #copy the template file into the proper location
        if(len(replacements) < 1):
            exit(log.error("Could not find "+templateFile+" file in template project"))
        else:
            templateFile = replacements[0]
        #make any necessary directories
        newdirs = newfile.replace(filename,"")
        if(len(newdirs)):
            os.makedirs(newdirs, exist_ok=True)
        #copy file to the new location
        shutil.copyfile(templateFile, self.getPath()+newfile)
        #reassign file to be the whole path
        newfile = self.getPath()+newfile
        #generate today's date
        today = date.today().strftime("%B %d, %Y")
        #write blank if no author configured
        author = apt.SETTINGS['general']["author"]
        if(author == None):
            author = ''

        
        #grab name of template file
        template_name = os.path.basename(templateFile)
        template_name,_ = os.path.splitext(template_name)
        template_name = template_name.lower()
        
        replace_name = template_name.count("template")

        #store the file data to be transformed and rewritten
        lines = []
        #find and replace all proper items
        with open(newfile, 'r') as file_in:
            for line in file_in.readlines():
                if(replace_name):
                    line = line.replace(template_name, file)
                line = line.replace("%DATE%", today)
                line = line.replace("%AUTHOR%", author)
                line = line.replace("%BLOCK%", self.getTitle(low=False))
                lines.append(line)
            file_in.close()
        #rewrite file to have new lines
        with open(newfile, 'w') as file_out:
            for line in lines:
                file_out.write(line)
            file_out.close()
        pass

    #create new block using template and try to set up a remote
    def create(self, fresh=True, git_exists=False, remote=None):
        log.info('Initializing new block...')
        if(fresh):
            if(os.path.isdir(apt.TEMPLATE)):
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
                os.makedirs(self.getPath(), exist_ok=True)

        #clone from existing remote repo
        if(not fresh and self.grabGitRemote() != None and ((self._repo != None and not apt.isRemoteBare(self.grabGitRemote()))  or self._repo == None)):
            log.info("Cloning project from remote url...")
            self.downloadFromURL(self.grabGitRemote(), in_place=True)
        #make a new repo
        elif(not git_exists):
            self._repo = git.Repo.init(self.getPath())
        #there is already a repo here
        elif(fresh):
            self._repo = git.Repo(self.getPath())
            #does a remote exist?
            if(self.grabGitRemote(override=True) != None):
                #ensure we have the latest version before creating marker file
                self._repo.git.pull()

        #create the marker file
        open(self.getPath()+apt.MARKER, 'w').write(self.blockFile())

        #run the commands to generate new project from template
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
            #determie the data
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
                        line = line.replace("%BLOCK%", self.getTitle(low=False))
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
        self._repo.index.add(self._repo.untracked_files)
        self._repo.git.commit('-m','Initializes block')

        #set it up to track origin
        if(self.grabGitRemote() != None):
            log.info('Generating new remote repository...')
            try:
                self._repo.git.push("-u","origin",str(self._repo.head.reference))
            except git.exc.GitCommandError:
                log.warning("Cannot configure remote origin because it is not empty!")
                #remove remote url from existing areas
                self._repo.delete_remote('origin')
                self.setRemote(None, push=False)
                self.save()
        else:
            log.info('No remote code base attached to local repository')
        pass

    #dynamically grab the origin url if it has been changed/added by user using git
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
                self._repo.git.push("-u","origin",str(self._repo.head.reference))
        pass

    #push to remote repository
    def pushRemote(self):
        self._repo.remotes.origin.push(refspec='{}:{}'.format(self._repo.head.reference, self._repo.head.reference))
        self._repo.remotes.origin.push("--tags")

    #push to remote repository if exists
    def pull(self):
        if(self.grabGitRemote() != None):
            log.info(self.getTitle()+" already exists in local path; pulling from remote...")
            self._repo.remotes.origin.pull()
        else:
            log.info(self.getTitle()+" already exists in local path")

    #has ability to return as lower case for comparison within legoHDL
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

    #return the value stored in metadata, else return None if DNE
    def getMeta(self, key=None, every=False):
        '''
        Returns the value stored in the block metadata, else retuns None if
        DNE.

        Parameters:
        ---
        key (str)  : the case-sensitive key to the cfg dictionary
        all (bool) : return entire dictionary
        '''
        #return everything, even things outside the block: scope
        if(every):
            return self.__metadata

        if(key == None):
            return self.__metadata['block']
        #check if the key is valid
        elif('block' in self.__metadata.keys() and key in self.__metadata['block'].keys()):
            return self.__metadata['block'][key]
        else:
            return None

    def setMeta(self, key, value):
        '''
        Updates the block metatdata dictionary.
        '''
        self.__metadata['block'][key] = value
        pass

    #return true if the requested project folder is a valid block
    def isValid(self):
        return os.path.isfile(self.metadataPath())

    #return path to marker file
    def metadataPath(self):
        return self.getPath()+apt.MARKER

    def getChangeLog(self, path):
        path = path+"/"+apt.CHANGELOG
        if(os.path.isfile(path)):
                with open(path,'r') as f:
                    return f.readlines()
        else:
            return None

    #print out the metadata for this block
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

                exit(log.error("No CHANGELOG.md file exists for "+self.getTitle()+". Add one in the next release."))
            return
        #grab all installed versions in the cache
        if(os.path.isdir(cache_path)):
            install_vers = os.listdir(cache_path)

        #print out the block's current metadata (found in local path)
        if(listVers == False and ver == None):
            with open(self.metadataPath(), 'r') as file:
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
    
    def load(self):
        '''
        Opens this block with the configured text-editor.
        '''
        log.info("Opening "+self.getTitle()+" at... "+self.getPath())
        cmd = apt.SETTINGS['general']['editor']+" "+self.getPath()
        os.system(cmd)
        pass
    
    def save(self, meta=None):
        '''
        Write the metadata back to the marker file only if the data has changed
        since initializing this block as an object in python.
        '''
        #do no rewrite meta data if nothing has changed
        if(self._initial_metadata == self.getMeta() and meta == None):
            return
        #default is to load the block's metadata
        if(meta == None):
            meta = self.getMeta(every=True)

        #write back cfg values with respect to order
        with open(self.metadataPath(), 'w') as file:
            cfg.save(meta, file)
            file.close()
        pass

    def isLinked(self):
        '''
        Returns true if a remote repository is linked/attached to this block.
        '''
        return self.grabGitRemote() != None

    def copyVersionCache(self, ver, folder):
        '''
        Copies new folder to cache from base installation path and updates
        entity names within the block to have the correct appened "_v". Assumes
        to be a valid release point before entering this method.
        '''
        #checkout version
        self._repo.git.checkout(ver+apt.TAG_ID)  
        #copy files
        version_path = self.getPath()+"../"+folder+"/"
        base_path = self.getPath()
        shutil.copytree(self.getPath(), version_path)
        #log.info(version_path)
        #delete the git repository for saving space and is not needed
        shutil.rmtree(version_path+"/.git/", onerror=apt.rmReadOnly)
        #temp set local path to be inside version
        self.__local_path = version_path
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
            ver_meta = cfg.load(f)
        if(ver_meta['block']['toplevel'] != None):
            ver_meta['block']['toplevel'] = ver_meta['block']['toplevel']+str_ver
        if(ver_meta['block']['bench'] != None):
            ver_meta['block']['bench'] = ver_meta['block']['bench']+str_ver

        #save metadata adjustments
        self.save(meta=ver_meta)

        #change local path back to base install
        self.__local_path = base_path

        #switch back to latest version in cache
        if(ver[1:] != self.getMeta("version")):
            self._repo.git.checkout('-')
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

        log.info("Installing block "+self.getTitle(low=False)+" version "+ver+"...")
        # 1. first download from remote if the base installation DNE or tag DNE
        if(not base_installed):
            #print("cache dir",cache_dir)
            #print(src)
            #remove old branch folder if exists
            if(os.path.exists(specific_cache_dir)):
                shutil.rmtree(specific_cache_dir, onerror=apt.rmReadOnly)
            #clone and checkout specific version tag
            git.Git(cache_dir).clone(src,"--branch",ver+apt.TAG_ID,"--single-branch")
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
            self.__local_path = specific_cache_dir+"/"
            base_installed = True

        self._repo = git.Repo(self.getPath())
        self.loadMeta()

        #2. now perform install from cache
        instl_vers = os.listdir(base_cache_dir)       
        if(self.validVer(ver)):
            #ensure this version is actually tagged
            if(ver in self.getTaggedVersions()):
                self._repo.git.checkout(ver+apt.TAG_ID)
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
                    log.info("Installing block "+self.getTitle(low=False)+" version "+maj+"...")
                    self.copyVersionCache(ver=ver, folder=maj)
                #check the version that is living in this folder
                else:
                    with open(maj_path+apt.MARKER,'r') as f:
                        maj_meta = cfg.load(f)
                        f.close()
                        pass
                    if(self.biggerVer(maj_meta['block']['version'],meta['block']['version']) == meta['block']['version']):
                        log.info("Updating block "+self.getTitle(low=False)+" version "+maj+"...")
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
        '''
        #print("Derives:",block_list)
        update = False
        #remove itself from the block list dependencies
        if(self.getTitle(mrkt=True) in block_list):
            block_list.remove(self.getTitle(mrkt=True))
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
        srcs = []
        if(path == None):
            path = self.getPath()
        for e in ext:
            srcs = srcs + glob.glob(path+"/**/"+e, recursive=True)
        #print(srcs)
        return srcs

    @classmethod
    def splitDetachVer(cls, dep):
        '''
        Splits dep string into market,library,name,version. Returns M,L,N,V. M
        is '' if not found/null.
        '''
        #split prereq into library, name, and version
        v_index = dep.find("(v")
        V = None
        if(v_index > -1):
            V = cls.stdVer(dep[v_index+1:len(dep)-1])
            dep = dep[:v_index]
        M = ''
        #is a market inluded in the title?
        if(dep.count('.') == 2):
            M = dep[:dep.find('.')]
            dep = dep[dep.find('.')+1:]

        L,N = cls.split(dep, vhdl=False)
        return M,L,N,V
    
    @classmethod
    def split(cls, dep, lower=True, vhdl=True):
        '''
        Splits dep string by '.' delimiters. Returns two strings: lib,name.
        '''
        if(dep == None):
            return '',''
        dot = dep.find('.')
        lib = dep[:dot]
        if(dot == -1):
            lib = ''
        dot2 = dep[dot+1:].find('.')
        if(dot2 == -1):
            #use semi-colon if only 1 dot is marked
            dot2 = dep[dot+1:].find(';')
        if(dot2 == -1):
            dot2 = len(dep)
        #return in vhdl-style way if in VHDL
        if(vhdl):
            name = dep[dot+1:dot+1+dot2]
        #return if trying to separate a block title
        else:
            name = dep[dot+1:]
        #necessary for title comparison
        if(lower):
            return lib.lower(),name.lower()
        #nice for user-end naming conventions
        else:
            return lib,name

    def identifyTop(self):
        '''
        Auto-detects the top-level design entity. Returns None if not found.
        '''
        if(hasattr(self, "_top")):
            return self._top
        units = self.grabUnits()
        top_contenders = list(units[self.getLib()].keys())

        self._top = None
        for name,unit in list(units[self.getLib()].items()):
            #if the entity is value under this key, it is lower-level
            if(unit.isTB() or unit.isPKG()): 
                if(name in top_contenders):
                    top_contenders.remove(name)
                continue
                
            for dep in unit.getRequirements():
                if(dep.getName() in top_contenders):
                    top_contenders.remove(dep.getName())

        if(len(top_contenders) == 0):
            log.warning("No top level detected.")
        elif(len(top_contenders) > 1):
            log.warning("Multiple top levels detected. "+str(top_contenders))
            validTop = input("Enter a valid toplevel entity: ").lower()
            while validTop not in top_contenders:
                validTop = input("Enter a valid toplevel entity: ").lower()
            
            top_contenders = [validTop]
        if(len(top_contenders) == 1):
            self._top = units[self.getLib()][top_contenders[0]]

            log.info("DETECTED TOP-LEVEL ENTITY: "+self._top.getName(low=False))
            self.identifyBench(self._top.getName(), save=True)
            #break up into src_dir and file name
            #add to metadata, ensure to push meta data if results differ from previously loaded
            if(self._top.getName(low=False) != self.getMeta("toplevel")):
                self.setMeta('toplevel', self._top.getName(low=False))
                self.save()

        return self._top

    def identifyBench(self, entity_name, save=False):
        '''
        Determine what testbench is used for the top-level design entity (if 
        found). Returns None if not found.
        '''
        if(hasattr(self, "_bench")):
            return self._bench
        units = self.grabUnits()
        benches = []
        for unit in units[self.getLib()].values():
            #print(unit)
            for dep in unit.getRequirements():
                if(dep.getLib() == self.getLib() and dep.getName() == entity_name and unit.isTB()):
                    benches.append(unit)
        self._bench = None    
        if(len(benches) == 1):
            self._bench = benches[0]
        elif(len(benches) > 1):
            top_contenders = []
            for b in benches:
                top_contenders.append(b.getName())
            log.warning("Multiple top level testbenches detected. "+str(top_contenders))
            validTop = input("Enter a valid toplevel testbench: ").lower()
            #force ask for the required testbench choice
            while validTop not in top_contenders:
                validTop = input("Enter a valid toplevel testbench: ").lower()
            #assign the testbench entered by the user
            self._bench = units[self.getLib()][validTop]
        #print what the detected testbench is
        if(self._bench != None):
            log.info("DETECTED TOP-LEVEL BENCH: "+self._bench.getName())
        else:
            log.warning("No testbench detected.")
        #update the metadata is saving
        if(save):
            if(self._bench == None):
                self.setMeta('bench', None)
            else:
                self.setMeta('bench', self._bench.getName(low=False))
            self.save()
        #return the entity
        return self._bench

    def identifyTopDog(self, top, tb):
        '''
        Determine what unit is utmost highest, whether it be a testbench
        (if applicable) or entity.
        '''
        #override auto detection
        if(top == None):
            top_ent = self.identifyTop()
            if(top_ent != None):
                top = top_ent.getName()
        top_dog = top
        #find the top's testbench
        bench_ent = self.identifyBench(top)
        #override auto detection if manually set testbench
        if(tb != None):
            top_dog = tb
        #set auto detected testbench
        elif(bench_ent != None):
            #print(bench_ent)
            tb = bench_ent.getName()
            top_dog = tb
        return top_dog,top,tb

    def printUnits(self):
        '''
        Helpful method for readable design book debugging.
        '''
        print("===UNIT BOOK===")
        for L in self.grabUnits().keys():
            print("===LIBRARY===",L)
            for U in self.grabUnits()[L]:
                print(self.grabUnits()[L][U])
        print("===END UNIT BOOK===")
        pass

    def grabUnits(self, toplevel=None, override=False):
        '''
        Color in (fill/complete) all units found in the design book.
        '''
        if(hasattr(self, "_unit_bank") and not override):
            return self._unit_bank
        elif(override):
            #reset graph
            Unit.Hierarchy = Graph()
            
        #get all possible units (units are incomplete (this is intended))
        self._unit_bank = self.grabDesigns(override, "cache","current")
        #self.printUnits()
        # :todo: only start from top-level unit if it exists
        #gather all project-level units
        project_level_units = self.grabDesigns(False, "current")[self.getLib()]
        for unit in project_level_units.values():
            #start with top-level unit and complete all required units in unit bank
            if(unit.getName() == toplevel or toplevel == None):
                self._unit_bank = unit.getLang().decipher(self._unit_bank, self.getLib(), override)
        #self.printUnits()
        return self._unit_bank

    def grabDesigns(self, override, *args):
        '''
        Return incomplete (blank) unit objects from current project or cache
        (not mutually exclusive). Override is passed to the grabCurrent and
        grabCache methods.
        '''
        design_book = dict()
        if("current" in args):
            design_book = self.grabCurrentDesigns(override).copy()
            pass
        if("cache" in args):
            design_book = apt.merge(self.grabCacheDesigns(override),design_book)
            pass
        return design_book

    # :todo: use generateCodeStream
    def skimVHDL(self, designs, filepath, L, N, M):
        '''
        Return an updated dictionary object with any blank units found in the
        file (VHDL syntax).
        '''
        with open(filepath, 'r') as file:
            for line in file.readlines():
                words = line.split()
                #skip if its a blank line
                if(len(words) == 0): 
                    continue
                #create new library dictionary if DNE
                if(L not in designs.keys()):
                    designs[L] = dict()
                #add entity units
                if(words[0].lower() == "entity"):
                    designs[L][words[1].lower()] = Unit(filepath, Unit.Type.ENTITY, L, N, words[1].lower(), M)
                #add package units
                elif((words[0].lower() == "package" and words[1].lower() != 'body')):
                    designs[L][words[1].lower()] = Unit(filepath, Unit.Type.PACKAGE, L, N, words[1].lower(), M)
        file.close()
        return designs

    # :todo: use generateCodeStream
    def skimVerilog(self, designs, filepath, L, N, M):
        '''
        Return an updated dictionary object with any blank units found in the 
        file (verilog syntax).
        '''
        with open(filepath, 'r') as file:
            for line in file.readlines():
                words = line.split()
                #skip if its a blank line
                if(len(words) == 0): 
                    continue
                #create new library dictionary if DNE
                if(L not in designs.keys()):
                    designs[L] = dict()
                #add entity units
                for i in range(len(words)):
                    #find the module keyword, the next name
                    if(words[i].lower() == "module"):
                        ports_start = words[i+1].find("(")
                        params_start = words[i+1].find("#")
                        if(params_start > -1 and params_start < ports_start):
                            ports_start = params_start
                        #cut off at the beginning of a ports list
                        if(ports_start > -1):
                            mod_name = words[i+1][:ports_start]
                        else:
                            mod_name = words[i+1]
                        mod_name = mod_name.replace(";","")
                        #keep case sensitivity in unit constructor
                        designs[L][mod_name.lower()] = Unit(filepath, Unit.Type.ENTITY, L, N, mod_name, M)
        file.close()
        return designs

    #return dictionary of entities with their respective files as values
    #all possible entities or packages to be used in current project
    def grabCacheDesigns(self, override=False):
        '''
        Gathers all VHDL and verilog source files found at cache
        level and skims through them to identify design units. Skips the cache
        location if it is for the current project.
        '''
        if(hasattr(self, "_cache_designs") and not override):
            return self._cache_designs

        self._cache_designs = dict()
        #locate VHDL cache files
        files = self.gatherSources(apt.VHDL_CODE, apt.WORKSPACE+"cache/")
        for f in files:
            M,L,N = self.grabExternalProject(f)
            #do not add the cache files of the current level project
            if(L == self.getLib() and N == self.getName()):
                continue
            #print(f)
            self._cache_designs = self.skimVHDL(self._cache_designs, f, L, N, M)
        
        #locate verilog cache files
        files = self.gatherSources(apt.VERILOG_CODE, apt.WORKSPACE+"cache/")
        for f in files:
            M,L,N = self.grabExternalProject(f)
            #do not add the cache files of the current level project
            if(L == self.getLib() and N == self.getName()):
                continue
            #print(f)
            self._cache_designs = self.skimVerilog(self._cache_designs, f, L, N, M)

        #print("Cache-Level designs: "+str(self._cache_designs))

        #if multi-develop is enabled, overwrite the units with those found in the local path
        #also allow to work with unreleased blocks? -> yes
        if(apt.SETTINGS['general']['multi-develop'] == True):
            log.info("Multi-develop is enabled")
            #1. first find all Block.cfg files (roots of blocks)
            files = glob.glob(apt.getLocal()+"**/"+apt.MARKER, recursive=True)
            #print(files)
            #2. go through each recursive search within these roots for vhd files (skip self block root)
            for f in files:
                f_dir = f.replace(apt.MARKER,"")
                with open(f, 'r') as file:
                    cfg_data = cfg.load(file)
                M = cfg_data['block']['market']
                L = cfg_data['block']['library'].lower()
                N = cfg_data['block']['name'].lower()
                #skip self block
                if(L == self.getLib() and N == self.getName()):
                    continue
                #3. open each found source file and insert units into cache design
                vhd_files = self.gatherSources(apt.VHDL_CODE, path=f_dir)
                for v in vhd_files:
                    self._cache_designs = self.skimVHDL(self._cache_designs, v, L, N, M)
                
                verilog_files = self.gatherSources(apt.VERILOG_CODE, path=f_dir)
                for v in verilog_files:
                    self._cache_designs = self.skimVerilog(self._cache_designs, v, L, N, M)
        #print("Cache-Level designs: "+str(self._cache_designs))
        return self._cache_designs

    def grabCurrentDesigns(self, override=False):
        '''
        Gathers all VHDL and verilog source files found at current
        project level and skims through them to identify design units.
        '''
        if(hasattr(self, "_cur_designs") and not override):
            return self._cur_designs

        self._cur_designs = dict()

        L,N = self.split(self.getTitle(low=True))
        M = self.getMeta('market')
        #create new library dictionary if DNE
        if(L not in self._cur_designs.keys()):
            self._cur_designs[L] = dict()
        #locate vhdl sources
        files = self.gatherSources(apt.VHDL_CODE)
        for f in files:
            self._cur_designs = self.skimVHDL(self._cur_designs, f, L, N, M)
        #locate verilog sources
        files = self.gatherSources(apt.VERILOG_CODE)
        for f in files:
            self._cur_designs = self.skimVerilog(self._cur_designs, f, L, N, M)

        #print("Project-Level Designs: "+str(self._cur_designs))
        return self._cur_designs
    
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
            meta = cfg.load(f)
            N = N+"(v"+meta['block']['version']+")"
            cur_M = meta['block']['market']
            if(cur_M != None and cur_M.lower() in apt.getMarketNames().keys()):
                M = cur_M

        #determine what the latest market being used is for this block
        with open(latest_block_path+apt.MARKER, 'r') as f:
            meta = cfg.load(f)
            latest_M = meta['block']['market']
            if(latest_M != None and latest_M.lower() in apt.getMarketNames().keys()):
                M = latest_M
 
        return M,L,N
        
    def ports(self, mapp, lib, pure_entity, entity=None, ver=None):
        '''
        Print helpful port mappings/declarations of a desired entity.
        '''
        units = self.grabUnits()
        info = ''
        if(entity == None):
            entity = self.getMeta("toplevel")
        if(entity == None):
            return info
        #tack on version number if given as arg
        if(ver != None):
            entity = entity+"_"+ver.replace(".","_")
            
        if(entity.lower() in units[self.getLib()].keys()):
            info = units[self.getLib()][entity.lower()].writePortMap(mapp, lib, pure_entity)
        else:
            exit(log.error("Cannot locate "+entity+" (version may not exist or may not be installed)."))
        return info

    pass


def main():
    pass


if __name__ == "__main__":
    main()