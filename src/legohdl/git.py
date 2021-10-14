# Project: legohdl
# Script: git.py
# Author: Chase Ruskin
# Description:
#   The Git class. A git object has handy commands availabel for Git 
#   repositories.

import os
from .apparatus import Apparatus as apt

class Git:

    def __init__(self, path):
        self._path = apt.fs(path)
        pass
    
    def getPath(self):
        return self._path

    def call(self, *args):
        return apt.execute('git','-C',self.getPath(),*args,quiet=False,returnoutput=True)

    def commit(self, msg):
        #first identify if has commits available
        status = self.getStatus()
        print(status)

        self.call('commit','-m',msg)

    def getStatus(self):
        return self.call('status')

    def add(self, *args):
        '''

        Parameters:
            files (list): list of files to add
        '''
        print(args)
        st = self.call('add',*args)
        print(st)

    def getBranch(self):
        '''
        Returns current branch name.
        '''
        keyword = 'branch'
        st = self.getStatus()
        st = st.split()
        next_is_name = False
        for word in st:
            if(word == 'branch'):
                next_is_name = True
            elif(next_is_name):
                return word

    def setRemote(self, url, force=False):
        r = self.getRemote()
        #force will be used if wanting to force override even if invalid url
        #else if its an invalid url then no change will occur
        valid_url = apt.isValidURL(url)
        #add new remote connection
        if(r == '' and valid_url):
            r = 'origin'
            self.call('remote','add','origin',url)
        #remove remote connection
        elif(r != '' and (not valid_url and force)):
            self.call('remote','remove',r)
        #modify existing remote connection
        elif(r != '' and valid_url):
            self.call('remote','set-url',r,url)
        pass
        

    @classmethod
    def isValid(cls, path):
        '''
        Checks if a path has a .git/ folder at the root

        Parameters:
            None
        Returns:
            (bool): true if .git/ folder exists at path
        '''
        return os.path.isdir(apt.fs(path)+'.git/')

    def __str__(self):
        return f'''
        hash: {self.__hash__}
        path: {self._path}
        branch: {self.getBranch()}
        remote: {self.getRemote()}
        '''

    def getRemote(self):
        st = self.call('remote')
        print(st)
        if(len(st)):
            return st.split()[0]
        else:
            return ''
    pass