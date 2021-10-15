# Project: legohdl
# Script: profile.py
# Author: Chase Ruskin
# Description:
#   The Profile class. A Profile object can have legohdl settings, template,
#   and/or scripts that can be maintained and imported. They are mainly used
#   to save certain setting configurations (loadouts) and share settings across
#   users.

import os,shutil
import logging as log
from .map import Map
from .apparatus import Apparatus as apt


class Profile:

    #store dictionary of all Profile objs
    Jar = Map()

    LastImport = None

    def __init__(self, name):
        '''
        Creates a Profile instance.
        '''
        #set profile's name
        self._name = name
        #set profile's directory
        self._prfl_dir = apt.fs(apt.HIDDEN+"profiles/"+self.getName())

        #create profile directory if DNE
        os.makedirs(self.getProfileDir(), exist_ok=True)
        #create profile market file if DNE
        if(os.path.exists(self.getProfileDir()+self.getName()+apt.PRFL_EXT) == False):
            open(self.getProfileDir()+self.getName()+apt.PRFL_EXT, 'w').close()
        
        #add to the catalog
        self.Jar[self.getName()] = self
        pass


    def remove(self):
        '''
        Deletes the profile from the Jar and its directory.

        Parameters:
            None
        Returns:
            None
        '''
        log.info("Deleting profile "+self.getName()+"...")
        #remove profile dir
        shutil.rmtree(self.getProfileDir(), onerror=apt.rmReadOnly)
        #remove from Jar
        del self.Jar[self.getName()]
        pass


    def setName(self, n):
        '''
        Change the profile's name if the name is not already taken.

        Parameters:
            n (str): new name for profile
        Returns:
            (bool): true if name successfully altered and updated in Jar
        '''
        if(n == '' or n == None):
            log.error("Profile name cannot be empty.")
            return False

        #cannot name change if the name already exists
        if(n.lower() in self.Jar.keys()):
            log.error("Cannot change profile name to "+n+" due to name conflict.")
            return False
        #change is okay to occur
        else:
            log.info("Renaming profile "+self.getName()+" to "+n+"...")
            #delete the old value in Jar
            if(self.getName().lower() in self.Jar.keys()):
                del self.Jar[self.getName()]

            #rename the prfl file
            os.rename(self.getProfileDir()+self.getName()+apt.PRFL_EXT, self.getProfileDir()+n+apt.PRFL_EXT)
            new_prfl_dir = apt.fs(apt.HIDDEN+"profiles/"+n)
            #rename the profile directory
            os.rename(self.getProfileDir(), new_prfl_dir)

            #update the import log if the name was the previous name
            if(self.LoadLastImport() == self):
                 with open(apt.HIDDEN+"profiles/"+apt.PRFL_LOG, 'w') as f:
                     f.write(n)

            #update attibutes
            self._name = n
            self._prfl_dir = new_prfl_dir
            #update the Jar
            self.Jar[self.getName()] = self
            
        pass


    @classmethod
    def LoadLastImport(cls):
        '''
        Read from import.log the name of the last used profile is, if exists.
        Sets the class atribute LastImport Profile obj.

        Parameters:
            None
        Returns:
            cls.LastImport (Profile): the profile obj last used to import
        '''
        #open the import.log
        with open(apt.HIDDEN+"profiles/"+apt.PRFL_LOG, 'r') as f:
            #read the profile's name
            prfl_name = f.readline().strip()
            #return that profile obj if the name is found in the Jar
            if(prfl_name.lower() in cls.Jar.keys()):
                #set the found profile obj as last import
                cls.LastImport = cls.Jar[prfl_name]

        return cls.LastImport


    def getName(self):
        return self._name


    def getProfileDir(self):
        return self._prfl_dir


    def hasTemplate(self):
        return os.path.exists(self.getProfileDir()+"template/")


    def hasScripts(self):
        return os.path.exists(self.getProfileDir()+"scripts/")


    def hasSettings(self):
        return os.path.exists(self.getProfileDir()+apt.SETTINGS_FILE)

    
    def isLastImport(self):
        return self == self.LastImport


    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        Name: {self.getName()}
        Imported Last: {self.isLastImport()}
        settings: {self.hasSettings()}
        template: {self.hasTemplate()}
        scripts: {self.hasScripts()}
        '''

    pass