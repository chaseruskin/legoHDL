# Project: legohdl
# Script: script.py
# Author: Chase Ruskin
# Description:
#   The Script class. A Script object can be used to execute a command through
#   legohdl, very similiar to how aliases function within the command-line.

import os
import logging as log
from .apparatus import Apparatus as apt
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
        if(a == '' or a == None):
            log.error("Script alias cannot be empty.")
            return False
        if(a.lower() in self.Jar.keys()):
            log.error('Could not set script alias to '+a+' due to name conflict.')
            return False

        #remove old key if it exists
        if(hasattr(self, '_alias') and self.getAlias().lower() in self.Jar.keys()):
            del self.Jar[self.getAlias()]
        #set the alias name and add it to the jar
        self._alias = a
        #add this script to the dictionary
        self.Jar[self.getAlias()] = self
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
            log.error("Script "+self.getAlias()+" cannot have an empty command.")
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


    @classmethod
    def printList(cls):
        '''
        Prints formatted list for scripts with alias and the commands.

        Parameters:
            None
        Returns:
            None
        '''
        print('{:<15}'.format("Alias"),'{:<12}'.format("Command"))
        print("-"*15+" "+"-"*64)
        for scpt in cls.Jar.values():
            print('{:<15}'.format(scpt.getAlias()),'{:<12}'.format(scpt.getCommand()))
            pass
        pass


    def getAlias(self):
        '''
        Returns the script's name.
        
        Parameters:
            None
        Returns:
            self._alias (str): the name for this command call   
        '''
        return self._alias


    def getExe(self):
        return self._prog


    def getPath(self):
        if(self.hasPath()):
            return self._path
        else:
            return None


    def getCommand(self):
        '''
        Retrieve the command string.
        
        Parameters:
            None
        Returns:
            self._cmd (str): the entire command for this script
        '''
        return self._cmd


    @classmethod
    def load(cls):
        '''
        Load scripts from settings.

        '''
        scpts = apt.SETTINGS['script']
        for alias,cmd in scpts.items():
            Script(alias, cmd)
        pass


    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        alias: {self.getAlias()}
        cmd: {self.getCommand()}
        program: {self.getExe()}
        path: {self.getPath()}
        '''

    pass