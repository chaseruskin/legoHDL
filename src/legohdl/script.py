# Project: legohdl
# Script: script.py
# Author: Chase Ruskin
# Description:
#   The Script class. A script object can be used to execute a command through
#   legohdl, very similiar to how aliases function within the command-line.

import os
from .map import Map

class Script:

    #store all scripts in class variable
    Jar = Map()

    def __init__(self, alias, cmd_call):
        '''
        Create a script object from its string. The string may contain a
        valid path to a file to be executed by some program.
        
        Parameters:
            alias (str): the name for this command call
            cmd_call (str): the line to be executed through the command-line
        Returns:
            None
        '''
        self._alias = alias
        self.setCommand(cmd_call)

        #add this script to the map
        self.Jar[self.getName()] = self
        pass
    
    def hasPath(self):
        '''
        Returns true if the script object does have a path within its command.
        
        Parameters:
            None
        Returns:
            (bool): if a path variable exists for the given object
        '''
        return hasattr(self, "_path")

    def setAlias(self, a):
        if(a.lower() in self.Jar.keys()):
            print('Could not set name (already exists).')
            return False
        
        del self.Jar[self.getName()]
        self._alias = a
        self.Jar[self.getName()] = self
        return True

    def setCommand(self, c):
        '''
        Change the command. Appropiately update the path to script if exists.
        
        Parameters:
            c (str): command call
        Returns:
            (bool): if a path variable exists for the given object
        '''
        self._cmd = c
        #chop up the string into words
        cmd_parts = c.split()
        #the program to execute the script is always first
        self._prog = cmd_parts[0]

        #from the remaining words try to guess which is script path (if exists)
        for word in cmd_parts[1:]:
            if(os.path.exists(word)):
                self._path = word
                break
        else:
            if(self.hasPath()):
                #remove path attribute
                delattr(self._path)

        pass

    def getName(self):
        '''
        Returns the script's name.
        
        Parameters:
            None
        Returns:
            self._alias (str): the name for this command call   
        '''
        return self._alias

    def getCommand(self):
        '''
        Retrieve the command string.
        
        Parameters:
            None
        Returns:
            self._cmd (str): the entire command for this script
        '''
        return self._cmd

    def __str__(self):
        '''
        Represent the object and its variables as a string.

        Parameters:
            None
        Returns:
            self._cmd (str): the entire command for this script
        '''
        path = ''
        if(self.hasPath()):
            path = self._path
        txt = f'''
        hash: {self.__hash__}
        cmd: {self._cmd}
        program: {self._prog}
        path: {path}
        '''
        return txt

    pass