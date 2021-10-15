# Project: legohdl
# Script: script.py
# Author: Chase Ruskin
# Description:
#   The Script class. A Script object can be used to execute a command through
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
        valid_cmd = self.setCommand(cmd_call)
        #only adds to Jar if a valid command is given (not empty)
        if(valid_cmd):
            self.setAlias(alias)
        pass
    

    def hasPath(self):
        '''
        Returns true if the script object does have a path within its command.
        Also is used to determine if the script is 'openable'.
        
        Parameters:
            None
        Returns:
            (bool): if a path variable exists for the given object
        '''
        return hasattr(self, "_path")


    def setAlias(self, a):
        '''
        Set the Script's alias name. Removes old key pair in dictionary
        if one existed. Adds self as value to new key name in dictionary.
        
        Parameters:
            a (str): alias name
        Returns:
            (bool): if successfully added to Jar (key name not taken)
        '''
        if(a.lower() in self.Jar.keys()):
            print('Could not set name (already exists).')
            return False
        #remove old key if it exists
        if(hasattr(self, '_alias')):
            del self.Jar[self.getName()]
        #set the alias name and add it to the jar
        self._alias = a
        #add this script to the dictionary
        self.Jar[self.getName()] = self
        return True


    def setCommand(self, c):
        '''
        Change the command. Appropriately update the path to script if exists.
        
        Parameters:
            c (str): command call
        Returns:
            (bool): if command was successfully set (not empty string)
        '''
        #do not change command if it is blank
        if(len(c.strip()) == 0):
            return False

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
                delattr(self, "_path")
        return True


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
        p = '' if(self.hasPath()) else self._path
        return f'''
        ID: {hex(id(self))}
        alias: {self._alias}
        cmd: {self._cmd}
        program: {self._prog}
        path: {p}
        '''

    pass