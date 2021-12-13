# ------------------------------------------------------------------------------
# Project: legohdl
# Script: plugin.py
# Author: Chase Ruskin
# Description:
#   The Plugin class. A Plugin object can be used to execute a command through
#   legohdl, very similiar to how aliases function within the command-line.
# ------------------------------------------------------------------------------

import os
import logging as log
from .apparatus import Apparatus as apt
from .map import Map
from .cfgfile2 import Cfg, Section, Key


class Plugin:

    #store all plugins in class variable
    Jar = Map()
    

    def __init__(self, alias, cmd_call):
        '''
        Create a plugin object from its string. The string may contain a
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
        Returns true if the plugin object does have a path within its command.
        Also is used to determine if the plugin is 'openable'.
        
        Parameters:
            None
        Returns:
            (bool): if a path variable exists for the given object
        '''
        return hasattr(self, "_path")


    def setAlias(self, a):
        '''
        Set the Plugin's alias name. Removes old key pair in dictionary
        if one existed. Adds self as value to new key name in dictionary.
        
        Parameters:
            a (str): alias name
        Returns:
            (bool): if successfully added to Jar (key name not taken)
        '''
        if(a == '' or a == None):
            log.error("Plugin alias cannot be empty.")
            return False
        if(a.lower() in self.Jar.keys()):
            log.error('Could not set plugin alias to '+a+' due to name conflict.')
            return False

        #remove old key if it exists
        if(hasattr(self, '_alias') and self.getAlias().lower() in self.Jar.keys()):
            del self.Jar[self.getAlias()]
        #set the alias name and add it to the jar
        self._alias = a
        #add this plugin to the dictionary
        self.Jar[self.getAlias()] = self
        return True


    def setCommand(self, c):
        '''
        Change the command. Appropriately update the path to plugin if exists.
        
        Parameters:
            c (str): command call
        Returns:
            (bool): if command was successfully set (not empty string)
        '''
        #do not change command if it is blank
        if(len(c.strip()) == 0):
            log.error("Plugin "+self.getAlias()+" cannot have an empty command.")
            return False

        self._cmd = c
        #chop up the string into words
        cmd_parts = c.split()
        #the program to execute the plugin is always first
        self._prog = cmd_parts[0]

        #from the remaining words try to guess which is plugin path (if exists)
        for word in cmd_parts[1:]:
            if(os.path.exists(os.path.expandvars(word))):
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
        Prints formatted list for plugins with alias and the commands.

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
        Returns the plugin's name.
        
        Parameters:
            None
        Returns:
            self._alias (str): the name for this command call   
        '''
        return self._alias


    def execute(self, args=[]):
        '''
        Execute the plugin's command.

        Parameters:
            args ([str]): list of additional arguments to go along with the command
        Returns:
            None
        '''
        cmd = [self.getCommand()] + args
        apt.execute(*cmd,quiet=False)
        pass


    def getExe(self):
        '''Returns the _prog (str) that is used to run the command.'''
        return self._prog


    def getPath(self):
        '''Returns the _path (str) that is in the command, or None if DNE.'''
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
            self._cmd (str): the entire command for this plugin
        '''
        return self._cmd


    @classmethod
    def load(cls):
        '''Load plugins from settings.'''
        
        plgns = apt.CFG.get('plugin', dtype=Section, returnkey=True)
        for plgn in plgns.values():
            Plugin(plgn._name, plgn._val)
        pass


    @classmethod
    def save(cls):
        '''
        Serializes the Plugin objects and saves them to the settings dictionary.

        Parameters:
            None
        Returns:
            None
        '''
        serialized = {}
        #serialize the Workspace objects into dictionary format for settings
        for scpt in cls.Jar.values():
            serialized[scpt.getAlias()] = scpt.getCommand()
        #update settings dictionary
        apt.CFG.set('plugin', Section(serialized))
        apt.save()
        pass


    # uncomment to use for debugging
    # def __str__(self):
    #     return f'''
    #     ID: {hex(id(self))}
    #     alias: {self.getAlias()}
    #     cmd: {self.getCommand()}
    #     program: {self.getExe()}
    #     path: {self.getPath()}
    #     '''


    pass