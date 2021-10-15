# Project: legohdl
# Script: workspace.py
# Author: Chase Ruskin
# Description:
#   The Label class. A Label object has a unique name that will be prepended
#   with '@' in the blueprint file. A label has a list of extensions to be
#   searched for within a block. A label can be recursive or shallow.

from .apparatus import Apparatus as apt
from .map import Map
import logging as log


class Label:

    #store all label objs in a class variable container
    Jar = Map()

    def __init__(self, name, exts, is_recur):
        '''
        Creates Label instance.

        Parameters:
            name (str): label's name
            exts ([str]): list of glob-style file extensions
            is_recur (bool): does the label affect all dependent blocks in a design
        Returns:
            None
        '''
        self._name = name
        self._exts = exts
        self._is_recur = is_recur

        #add to class container
        self.Jar[self.getName()] = self
        pass


    def setName(self, n):
        '''
        Modifies the label's name if not already taken.

        Parameters:
            n (str): label's name
        Returns:
            (bool): true if name was modified
        '''
        #cannot change to a blank name
        if(n == '' or n == None):
            log.error("Label name cannot be empty.")
            return False
        #cannot change to a name already being used
        if(n.lower() in self.Jar.keys()):
            log.error("Cannot rename label to "+n+" due to name conflict.")
            return False
        #okay to proceed with modification
        #remove key from Jar
        if(self.getName().lower() in self.Jar.keys()):
            del self.Jar[self.getName()]
        
        #set new name
        self._name = n
        #update Jar
        self.Jar[self.getName()] = self
        return True


    def setExtensions(self, exts):
        '''
        Modify the label's extensions.

        Parameters:
            exts ([str]): new list of extensions to use for given label
        Returns:
            (bool): true if extensions were modified
        '''
        if(len(exts) == 0):
            log.error("Label "+self.getName()+" cannot have zero extensions.")
            return False
        #set the new extensions
        self._exts = exts
        return True


    def isRecursive(self):
        return self._is_recur


    def getExtensions(self):
        return self._exts


    def getName(self):
        return self._name


    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        Label: {self.getName()}
        Extensions: {self.getExtensions()}
        Recursive: {self.isRecursive()}
        '''

    pass