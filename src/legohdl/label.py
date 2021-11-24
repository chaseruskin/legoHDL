# ------------------------------------------------------------------------------
# Project: legohdl
# Script: workspace.py
# Author: Chase Ruskin
# Description:
#   The Label class. A Label object has a unique name that will be prepended
#   with '@' in the blueprint file. A label has a list of extensions to be
#   searched for within a block. A label can be global or local.
# ------------------------------------------------------------------------------

import logging as log
from .map import Map
from .apparatus import Apparatus as apt


class Label:

    #store all label objs in a class variable container
    Jar = Map()

    def __init__(self, name, exts, is_global):
        '''
        Creates Label instance. The name will be automatically converted to all
        upper-case.

        Parameters:
            name (str): label's name
            exts ([str]): list of glob-style file extensions
            is_global (bool): does the label affect all dependent blocks in a design
        Returns:
            None
        '''
        self._name = name.upper()
        self._exts = exts
        self._global = is_global

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

    
    @classmethod
    def load(cls):
        '''Load local and global labels from settings.'''

        #load local labels
        local_lbls = apt.SETTINGS['label']['local']
        for lbl,exts in local_lbls.items():
            Label(lbl, apt.strToList(exts), is_global=False)
        #load global labels
        global_lbls = apt.SETTINGS['label']['global']
        for lbl,exts in global_lbls.items():
            Label(lbl, apt.strToList(exts), is_global=True)
        pass


    @classmethod
    def save(cls):
        '''
        Serializes the Label objects and saves them to the settings dictionary.

        Parameters:
            None
        Returns:
            None
        '''
        serialized = {'global' : {}, 'local' : {}}
        #serialize the Workspace objects into dictionary format for settings
        for lbl in cls.Jar.values():
            if(lbl.isGlobal()):
                serialized['global'][lbl.getName()] = apt.listToStr(lbl.getExtensions())
            else:
                serialized['local'][lbl.getName()] = apt.listToStr(lbl.getExtensions())
        #update settings dictionary
        apt.SETTINGS['label'] = serialized
        apt.save()
        pass


    @classmethod
    def printList(cls):
        '''
        Prints formatted list for labels with global flag and file extensions.

        Parameters:
            None
        Returns:
            None
        '''
        print('{:<20}'.format("Label"),'{:<24}'.format("Extensions"),'{:<14}'.format("Global"))
        print("-"*20+" "+"-"*24+" "+"-"*14+" ")
        for lbl in cls.Jar.values():
            rec = 'yes' if(lbl.isGlobal()) else '-'
            print('{:<20}'.format(lbl.getName()),'{:<24}'.format(apt.listToStr(lbl.getExtensions())),'{:<14}'.format(rec))
        pass


    def setExtensions(self, exts):
        '''
        Modify the label's extensions.

        Parameters:
            exts ([str]): new list of extensions to use for given label
        Returns:
            (bool): true if extensions were modified
        '''
        if(isinstance(exts, list) == False):
            raise TypeError("Must be a list of extensions!")
        if(len(exts) == 0):
            log.error("Label "+self.getName()+" cannot have zero extensions.")
            return False
        #set the new extensions
        self._exts = exts
        return True

    
    def setGlobal(self, g):
        '''Sets _global (bool) attr.'''
        self._global = g


    def isGlobal(self):
        '''Returns _global (bool) attr.'''
        return self._global


    def getExtensions(self):
        '''Returns _exts ([str]) attr.'''
        #ensure the extensions are list datatype
        if(isinstance(self._exts, list) == False):
            self._exts = apt.strToList(self._exts)
        return self._exts


    def getName(self):
        '''Returns _name (str) attr.'''
        return self._name


    # uncomment to use for debugging
    # def __str__(self):
    #     return f'''
    #     ID: {hex(id(self))}
    #     Label: {self.getName()}
    #     Extensions: {self.getExtensions()}
    #     Global: {self.isGlobal()}
    #     '''


    pass