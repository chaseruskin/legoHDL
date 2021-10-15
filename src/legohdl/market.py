# Project: legohdl
# Script: market.py
# Author: Chase Ruskin
# Description:
#   This script describes the attributes and behaviors of legohdl markets.
#   A market holds 'pointer' files to legohdl blocks available on the internet
#   as git repositories.

import os,shutil,git
import logging as log
from .apparatus import Apparatus as apt
from .cfgfile import CfgFile as cfg
from .map import Map

class Market:
    #store all markets in a class dictionary
    Jar = Map()

    def __init__(self, name, url):
        self._name = name
        self.url = url
        self._local_path = apt.fs(apt.MARKETS+self.getName(low=False))
        valid_remote = False
        #is there not a git repository here? if so, need to init
        if(not os.path.isdir(self.getPath()+"/.git")):
            #validate if the url is good to connect
            if(url != None):
                valid_remote = apt.isValidURL(url)
                url_name = url[url.rfind('/')+1:url.rfind('.git')]

            if(valid_remote):
                tmp_dir = apt.HIDDEN+"tmp/"
                #create temp directory to clone market into
                os.makedirs(tmp_dir, exist_ok=True)
                git.Git(tmp_dir).clone(url)

                log.info("Found and linked remote repository to "+self.getName(low=False))
                #transfer from temp directory into market directory
                shutil.copytree(tmp_dir+url_name, self.getPath())
                shutil.rmtree(tmp_dir, onerror=apt.rmReadOnly)
                # write mrkt file and push to remote repository if it is bare
                if(apt.isRemoteBare(url)):
                    open(self.getPath()+self.getName(low=False)+apt.MRKT_EXT, 'w').close()
                    self._repo = git.Repo(self.getPath())
                    self._repo.git.add(update=True)
                    self._repo.index.add(self._repo.untracked_files)
                    self._repo.git.commit('-m',"Initializes legohdl market")
                    self._repo.git.push("-u","origin",str(self._repo.head.reference))
            else:
                self.url = None
                apt.SETTINGS['market'][self.getName(low=False)] = None
                git.Repo.init(self.getPath())
                log.warning("No remote repository configured for "+self.getName(low=False))
                #create blank market marker file
                open(self.getPath()+self.getName(low=False)+apt.MRKT_EXT, 'w').close()
                #add and commit the market .mrkt file
                apt.execute('git','-C',self.getPath(),'add','.')
                apt.execute('git','-C',self.getPath(),'commit','-m','"Initializes legohdl market"','-q')
                pass

        self.Jar[self.getName(low=False)] = self
        self._repo = git.Repo(self.getPath())
        pass

    def getName(self, low=True):
        if(low):
            return self._name.lower()
        else:
            return self._name

    def delete(self):
        if(os.path.exists(self._local_path)):
            shutil.rmtree(self._local_path, onerror=apt.rmReadOnly)

    def setRemote(self, url):
        if((self.isRemote() and self._repo.remotes.origin.url != self.url) or (not self.isRemote())):
            if(url == None):
                return None
            valid_remote = apt.isValidURL(url)
            #is this a valid remote path? if it is and we have no origin, make it linked!
            if(not self.isRemote() and valid_remote):
                self._repo.create_remote('origin', self.url)
                log.info("Creating link for "+self.getName(low=False)+" to "+self.url+"...")
            elif(self.isRemote() and valid_remote):
            #is this a valid remote path? do we already have one? if we already have a remote path, delete folder
                log.info("Swapping link for "+self.getName(low=False)+" to "+self.url+"...")
                if(os.path.exists(self._local_path)):
                    shutil.rmtree(self._local_path, onerror=apt.rmReadOnly)
                git.Git(apt.MARKETS).clone(url) #and clone from new valid remote path
                url_name = url[url.rfind('/')+1:url.rfind('.git')]
                os.rename(apt.MARKETS+url_name, self._local_path)
            else:
                log.error("Invalid link- setting could not be changed")
                if(self.isRemote() and url != None):
                    self.url = self._repo.remotes.origin.url
        return self.url

    #release a block to this market
    def publish(self, meta, options=[], all_vers=[], changelog=None):
        if(self.url != None):
            #refresh remote
            if(len(self._repo.remotes)):
                log.info("Refreshing "+self.getName(low=False)+"... "+self.url)
                if(apt.isRemoteBare(self.url) == False):
                    self._repo.git.pull()
            #create remote origin
            else:
                if(apt.isValidURL(self.url)):
                    self._repo.git.remote("add","origin",self.url)
                else:
                    log.warning("Remote does not exist for market "+self.getName())
                    self.url = None

        block_meta = meta['block']

        active_branch = self._repo.active_branch
        #switch to side branch if '-soft' flag raised
        tmp_branch = block_meta['library']+"."+block_meta['name']+"-"+block_meta['version']
        #try to publish on a side branch (possibly for team reviewing)
        if(options.count("soft")):
            if(self.url != None):
                log.info("Checking out new branch '"+tmp_branch+"' to release block to "+self.getName(low=False)+"...")
                self._repo.git.checkout("-b",tmp_branch)
            else:
                log.warning("Cannot perform soft release because this market has no remote.")

        #locate block's directory within market
        block_dir = apt.fs(self._local_path+"/"+block_meta['library']+"/"+block_meta['name']+"/")
        os.makedirs(block_dir,exist_ok=True)

        #read in all logging info about valid release points
        file_data = []
        #insert any versions found as valid release points to version.log
        for v in all_vers:
            file_data = file_data + [v+"\n"]
        #rewrite version.log file to track all valid versions
        with open(block_dir+apt.VER_LOG,'w') as f:
                f.writelines(file_data)
                pass

        #save changelog 
        if(changelog != None):
            with open(block_dir+apt.CHANGELOG,'w') as f:
                for line in changelog:
                    f.write(line)
                f.close()
                pass

        #save cfg file
        with open(block_dir+apt.MARKER, 'w') as file:
            cfg.save(meta, file, ignore_depth=True, space_headers=True)
            file.close()
            
        #save changes to repository (only add and stage the file that was made)
        rel_git_path = block_meta['library']+'/'+block_meta['name']+'/'
        self._repo.index.add(rel_git_path+apt.MARKER)
        self._repo.index.add(rel_git_path+apt.VER_LOG)
        if(changelog != None):
            self._repo.index.add(rel_git_path+apt.CHANGELOG)
        pass
        
        #commit all releases
        self._repo.git.commit('-m',"Adds "+block_meta['library']+'.'+block_meta['name']+"-v"+block_meta['version'])
        #push to remote market repository
        if(self.url != None):
            self._repo.git.push("-u","origin",str(self._repo.head.reference))
            self._repo.git.checkout(active_branch)
            # delete soft/tmp branch that was created for release
            if(options.count("soft")):
                self._repo.git.branch("-d",tmp_branch)
        pass

    #return true is configured to a remote repository
    def isRemote(self):
        return len(self._repo.remotes)

    def getPath(self):
        return self._local_path

    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        Name: {self.getName()}
        URL: {self.url}
        '''
    pass