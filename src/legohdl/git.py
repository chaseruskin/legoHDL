# Project: legohdl
# Script: git.py
# Author: Chase Ruskin
# Description:
#   The Git class. A git object has handy commands available for Git 
#   repositories.

import os, shutil
import logging as log
from .apparatus import Apparatus as apt


class Git:

    #track all valid and invalid urls for faster performance
    _URLstatus = {}


    def __init__(self, path, clone=None):
        '''
        Create a Git instance. This is a repository-like object. Will `init`
        if one DNE at local path, or try to `clone` to `path` name if `clone` is
        not None.

        Parameters:
            path (str): path to initialize git to
            clone (str): path/remote url to clone from
        Returns:
            None
        '''
        self._path = apt.fs(path)
        #create directory if DNE
        os.makedirs(self.getPath(), exist_ok=True)

        #are we trying to clone?
        if(clone != None):
            #verify its a valid URL
            if(self.isValidRepo(clone, remote=True)):
                #use init and then add remote
                if(self.isBlankRepo(clone, remote=True)):
                    self.git('init')
                    self.setRemoteURL(clone)
                elif(self.isValidRepo(self.getPath(), remote=False) == False):
                    #clone from remote url
                    _,err = apt.execute('git', 'clone', clone, self.getPath(), quiet=False, returnoutput=True)
                    #if(len(err)):
                        #log.error(err)
                else:
                    log.error("Cannot clone to an already initialized git repository.")
            #verify its a valid local repository and clone from local repository
            elif(self.isValidRepo(clone, remote=False) == True and self.isBlankRepo(clone, remote=False) == False):
                _,err = apt.execute('git', 'clone', clone, self.getPath(), quiet=False, returnoutput=True)
                #if(len(err)):
                    #log.error(err)
        #check if git exists here for local repository
        elif(self.isValidRepo(self.getPath(), remote=False) == False):
            #initialize a new repository if DNE
            self.git('init')
        pass


    def git(self, *args):
        '''
        Use git executable with specified repository path.

        Parameters:
            *args (*str): arguments to be passed to git
        Returns:
            output (str): stdout from the subprocess
            error (str): stderr from the subprocess
        '''
        resp,err = apt.execute('git', '-C', self.getPath(), *args, quiet=False, returnoutput=True)
        return resp,err


    def commit(self, msg):
        '''
        Commits files from staging level to a commit in the tree/log.

        Parameters:
            msg (str): message for the git commit
        Returns:
            None
        '''
        self.git('commit','-m',msg)
        pass


    def add(self, *args):
        '''
        Adds files from working level to staging level.

        Parameters:
            files ([str]): list of files to add
        Returns:
            None
        '''
        self.git('add',*args)
        pass


    def push(self):
        '''
        Push to remote repository, if exists.
        
        Parameters:
            None
        Returns:
            None
        '''
        if(self.remoteExists()):
            self.git('push','--set-upstream',self.getRemoteName(),self.getBranch(),'--tags')
        pass
        

    def pull(self):
        '''
        Pull from remote repository if exists.

        Parameters:
            None
        Returns:
            None
        '''
        if(self.remoteExists()):
            self.git('pull')
        pass


    def delete(self, path=None):
        '''
        Delete's the .git/ folder at the specified directory. If path is None
        then it uses the Git object's path to remove directory.
        
        Parameters:
            path (str): optionally specify the path to remove .git/ folder from
        Returns:
            None
        '''
        path_to_del = apt.fs(path) if(path != None) else self.getPath()
        shutil.rmtree(path_to_del+".git/", onerror=apt.rmReadOnly)
        pass


    def setRemoteURL(self, url, force=False):
        '''
        Attempts to set the remote's url. If no remote is configured it will
        create a new one with name 'origin'. Verifies the url is valid before
        trying to overwrite.

        Parameters:
            url (str): the git remote repository to connect to
            force (bool): overwrite remote url (remove it) even if its invalid
        Returns:
            None
        '''
        r = self.getRemoteName()
        #force will be used if wanting to force override even if invalid url
        #else if its an invalid url then no change will occur
        valid_url = self.isValidRepo(url, remote=True)
        #add new remote connection
        if(r == '' and valid_url):
            r = 'origin'
            self.git('remote', 'add', r, url)
            #update remote's name because it is being added
            self._remote_name = r
            self._remote_url = url
        #remove remote connection
        elif(r != '' and (not valid_url and force)):
            self.git('remote', 'remove', r)
            #update remote's name to reflect nothing because its being deleted
            self._remote_name = ''
            self._remote_url = ''
        #modify existing remote connection
        elif(r != '' and valid_url):
            self.git('remote', 'set-url', r, url)
            self._remote_url = url
        pass


    def isLatest(self):
        '''
        Fetches any changes from remote and determines if behind the remote.

        Parameters:
            None
        Returns:
            (bool): true if current branch is up-to-date or ahead of remote
        '''
        #sync with remote repository for any branch changes
        if(self.remoteExists()):
            self.git('remote','update')
            st,_ = self.git('status')
            return (st.count('Your branch is up to date with') or st.count('Your branch is ahead of'))
        #always is latest if no remote to sync with
        else:
            return True
        

    @classmethod
    def isValidRepo(cls, path, remote=False):
        '''
        Checks if a path has a .git/ folder at the root. Also can verify if a
        remote repository is valid url.

        Parameters:
            path (str): local repository or remote url
            remote (bool): is the path a remote url to verify
        Returns:
            (bool): true if .git/ folder exists at path or connection is established for remote url
        '''
        #check local path
        if(remote == False):
            return os.path.isdir(apt.fs(path)+'.git/')
        #has it aleady been checked?
        if(path in cls._URLstatus.keys()):
            return cls._URLstatus[path]
        #actually check the remote connection
        log.info("Checking ability to link to remote url...")
        if(path == None or path.count(".git") == 0):
            #update dictionary to log this url
            cls._URLstatus[path] = False
            return False

        _,err = apt.execute('git', 'ls-remote', path, quiet=False, returnoutput=True)
        is_valid = (len(err) == 0)
        #update dictionary to log this url
        cls._URLstatus[path] = is_valid
        #verify no errors on output
        return is_valid


    @classmethod
    def isBlankRepo(cls, path, remote=False):
        '''
        Tests if the path/url is an empty git repository. As a byproduct it
        will also test if the remote is valid (needed in order to be blank).

        Parameters:
            path (str): local repository or remote url
            remote (bool): is the path a remote url to verify
        Returns:
            (bool): true if no commits are made to the repository
        '''
        #check local path
        if(remote == False):
            #check output from running log and seeing if error pops up
            _,err = apt.execute('git','-C',path,'log', quiet=False, returnoutput=True)
            return (len(err) > 0)
        
        #actually check the remote connection
        log.info("Checking ability to link to remote url...")
        if(path == None or path.count(".git") == 0):
            return False

        out,err = apt.execute('git', 'ls-remote', path, quiet=False, returnoutput=True)
        is_valid = (len(err) == 0)
        #update dictionary to log this url
        cls._URLstatus[path] = is_valid
        #verify no output and no errors (it is blank)
        return (len(out) == 0 and len(err) == 0)


    def getBranch(self, force=False):
        '''
        Identify the current branch for the git repository. 

        Parameters:
            force (bool): resuses previously determined branch name unless true
        Returns:
            self._branch (str): branch name
        '''
        if(hasattr(self, '_branch') and force == False):
            return self._branch
        out,_ = self.git('status')
        txt = out.split()
        #create variable to know when to be ready for branch name
        next_is_name = False
        for word in txt:
            if(next_is_name):
                self._branch = word
                #stop reading words upon identifying the branch name
                break
            #branch name will come next in the list of words
            next_is_name = (word == 'branch')

        return self._branch


    def getRemoteName(self):
        '''
        Reads output from `git remote` to find what the remote name is called.
        Dynamically creates attribute for quick access the next time needed.

        Parameters:
            None
        Returns:
            self._remote_name (str): git remote name for the repository
        '''
        if(hasattr(self, "_remote_name")):
            return self._remote_name
        
        out,_ = self.git('remote')
        if(len(out)):
            self._remote_name = out.split()[0]
        else:
            self._remote_name = ''
        return self._remote_name


    def getRemoteURL(self):
        '''
        Identify the remote's url, if a remote exists. Dynamically creates attribute
        for quicker use on next call.

        Parameters:
            None
        Returns:
            self._remote_url (str): url for remote or '' if no remote configured
        '''
        if(hasattr(self, "_remote_url")):
            return self._remote_url

        self._remote_url = ''
        if(self.getRemoteName() != ''):
            self._remote_url,_ = self.git('remote','get-url',self.getRemoteName())
        
        return self._remote_url
        

    def getPath(self):
        return self._path


    def remoteExists(self):
        return self.getRemoteURL() != ''


    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        path: {self.getPath()}
        branch: {self.getBranch()}
        remote: {self.getRemoteName()} {self.getRemoteURL()}
        '''

    pass