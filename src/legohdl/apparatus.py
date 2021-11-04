# Project: legohdl
# Script: apparatus.py
# Author: Chase Ruskin
# Description:
#   This script is used to hold the legohdl settings. It includes code for 
#   safety measures to ensure the proper settings exits, as well as helper
#   functions that are used throughout other scripts.

import os,shutil,stat,glob,subprocess
import copy,platform
import logging as log
from .cfgfile import CfgFile as cfg


class Apparatus:

    #legohdl settings data structure
    SETTINGS = dict()

    #path to hidden legohdl folder
    HIDDEN = os.path.expanduser("~/.legohdl/")
    
    #temporary path for various purposes
    TMP = HIDDEN+"tmp/"

    #identify custom configuration files
    CFG_EXT = ".cfg"
    #identify a valid HDL design project folder
    BLOCK_EXT = ".cfg"

    SETTINGS_FILE = "legohdl"+CFG_EXT

    #identify a valid block project within the framework
    MARKER = "Block"+BLOCK_EXT

    #looks for this file upon a release to ask user to update changelog
    CHANGELOG = "CHANGELOG.md"

    #path to template within legohdl
    TEMPLATE = HIDDEN+"template/"
    #path to markets within legohdl
    MARKETS = HIDDEN+"markets/"
    #path to workspaces within legohdl
    WORKSPACE = HIDDEN+"workspaces/"

    #replace this name with HIDDEN path to the tool when found in paths
    ENV_NAME = "%LEGOHDL%"

    #all available options allowed to be edited within the legohdl.cfg
    #append all non-field options here (editable dictionaries)
    OPTIONS = ['label', 'script', 'workspace', 'market']

    LAYOUT = { 'general' : {
                    'active-workspace' : cfg.NULL, 
                    'author' : cfg.NULL, 
                    'editor' : cfg.NULL,
                    'template' : cfg.NULL, 
                    'profiles' : cfg.NULL, 
                    'multi-develop' : cfg.NULL, 
                    'refresh-rate' : cfg.NULL,
                    'overlap-global' : cfg.NULL},
                'label' : {
                    'local' : {}, 
                    'global' : {}},
                'script' : {},
                'workspace' : {},
                'market' : {}
            }
    
    #this is appended to the tag to make it unique for legoHDL
    TAG_ID = '-legohdl'    
    #file kept in markets to remember all valid release points
    VER_LOG = "version.log"

    #file kept in registry base folder to remember when last refresh
    #based on refresh-rate it will store that many times
    REFRESH_LOG = "refresh.log"
    #used to track which profile was last imported
    PRFL_LOG = "import.log"

    #high and low values for setting refresh-rate setting
    MAX_RATE = 1440
    MIN_RATE = -1

    #types of accepted HDL files to parse and interpret
    VHDL_CODE = ["*.vhd","*.vhdl"]
    VERILOG_CODE = ["*.v","*.sv"]

    SRC_CODE = VHDL_CODE + VERILOG_CODE

    #this character can be used on the CLI proceeding a block's title to specify
    #an entity
    ENTITY_DELIM = ':'

    DOCUMENTATION_URL = 'https://legohdl.readthedocs.io/en/latest/index.html'


    @classmethod
    def initialize(cls):
        
        cls.HIDDEN = cls.fs(cls.HIDDEN)
        ask_for_setup = (os.path.exists(cls.HIDDEN) == False)
        
        os.makedirs(cls.HIDDEN, exist_ok=True)
        os.makedirs(cls.HIDDEN+"workspaces/", exist_ok=True)
        os.makedirs(cls.HIDDEN+"scripts/", exist_ok=True)
        os.makedirs(cls.MARKETS, exist_ok=True)
        os.makedirs(cls.TEMPLATE, exist_ok=True)
        os.makedirs(cls.HIDDEN+"profiles/", exist_ok=True)

        #create bare legohdl.cfg if DNE
        if(not os.path.isfile(cls.HIDDEN+cls.SETTINGS_FILE)):
            settings_file = open(cls.HIDDEN+cls.SETTINGS_FILE, 'w')
            #save default settings layout
            cfg.save(cls.LAYOUT, settings_file)
            settings_file.close()

        #create empty import.log file for profiles if DNE
        if(os.path.isfile(cls.HIDDEN+"profiles/"+cls.PRFL_LOG) == False):
            open(cls.HIDDEN+"profiles/"+cls.PRFL_LOG, 'w').close()

        #generate list of all available fields/options
        cls.OPTIONS = cls.OPTIONS + cfg.getAllFields(cls.LAYOUT)

        #load dictionary data in variable
        with open(cls.HIDDEN+cls.SETTINGS_FILE, "r") as file:
            cls.SETTINGS = cfg.load(file)
        
        #merge bare_settings into loaded settings to ensure all keys are present
        cls.SETTINGS = cls.fullMerge(cls.SETTINGS, cls.LAYOUT)

        #ensure all pieces of settings are correct
        cls.generateDefault(dict,"local","global",header="label")
        cls.generateDefault(dict,"market","script","workspace",header=None)
        cls.generateDefault(bool,"multi-develop","overlap-global",header="general")
        cls.generateDefault(int,"refresh-rate",header="general")
        cls.generateDefault(list,"profiles",header="general")
        #return if user was missing the legohdl hidden folder
        return ask_for_setup


    @classmethod
    def generateDefault(cls, t, *args, header=None):
        '''
        Implements security check to make sure certain settings uphold a specific
        datatype.

        Parameters:
            t (type): python datatype that should be here in settings
            *args (*str): variable string (keys) requesting type t
            header (str): optional first-level section where keys are located
        Returns:
            None
        '''
        for a in args:
            if(header == None):
                sett = cls.SETTINGS
            else:
                sett = cls.SETTINGS[header]
            if(isinstance(sett[a], t) == False):
                val = sett[a]
                if(t == dict):
                    sett[a] = {}
                elif(t == bool):
                    sett[a] = cfg.castBool(val)
                elif(t == int):
                    sett[a] = cfg.castInt(val)
                elif(t == list):
                    sett[a] = []


    @classmethod
    def load(cls):
        #ensure all pieces of settings are correct
        cls.generateDefault(dict,"local","global",header="label")
        cls.generateDefault(dict,"market","script","workspace",header=None,)
        cls.generateDefault(bool,"multi-develop","overlap-global",header="general")
        cls.generateDefault(int,"refresh-rate",header="general")
        cls.generateDefault(list,"profiles",header="general")

        #constrain the refresh-rate
        cls.setRefreshRate(cls.getRefreshRate())

        if(cls.SETTINGS['general']['template'] != cfg.NULL and os.path.isdir(cls.SETTINGS['general']['template'])):
            cls.SETTINGS['general']['template'] = cls.fs(cls.SETTINGS['general']['template'])
            cls.TEMPLATE = cls.SETTINGS['template']
            pass
        
        #save all safety measures
        cls.save()
        pass


    @classmethod
    def isSubPath(cls, inner_path, path):
        '''
        Tests if one `inner_path` is encapsulated by `path`. Returns false if
        identical. If called on Linux, the paths are not evaluated as case-insensitive.

        Parameters:
            inner_path (str): path to see if within another path
            path (str): the bigger path to see if a path is within it
        Returns:
            (bool): true if path starts with inner_path 
        '''
        kernel = platform.system()
        #must be careful to exactly match paths within Linux OS
        if(kernel != "Linux"):
            inner_path = inner_path.lower()
            path = path.lower()

        return cls.fs(path).startswith(cls.fs(inner_path)) and (path != inner_path)

    
    @classmethod
    def isEqualPath(cls, path1, path2):
        '''
        Tests if one `path1` is identical to `path2`. If called on Linux, 
        the paths are not evaluated as case-insensitive.

        Parameters:
            path1 (str): the lhs path
            path2 (str): the rhs path
        Returns:
            (bool): true if path1 == path2
        '''
        kernel = platform.system()
        #must be careful to exactly match paths within Linux OS
        if(kernel != "Linux"):
            path1 = path1.lower()
            path2 = path2.lower()

        return cls.fs(path1) == cls.fs(path2)


    @classmethod
    def makeTmpDir(cls):
        '''
        Create a hidden temporary directory within legoHDL.

        Parameters:
            None
        Returns:
            (str): the path to the temporary directory
        '''
        tmp_path = cls.fs(cls.HIDDEN+"tmp/")
        #check if temporary directory already exists
        cls.cleanTmpDir()
        #create temporary directory
        os.makedirs(tmp_path)
        return tmp_path


    @classmethod
    def cleanTmpDir(cls):
        '''Remove the tmporary directory within legoHDL.'''

        tmp_path = cls.fs(cls.HIDDEN+"tmp/")
        #check if temporary directory already exists
        if(os.path.exists(tmp_path)):
            shutil.rmtree(tmp_path, onerror=cls.rmReadOnly)
        pass


    @classmethod
    def getAuthor(cls):
        '''Return the author (str) from the settings data structure.'''

        author = cls.SETTINGS['general']['author']
        if(author == None):
            author = ''
        return author


    @classmethod
    def setAuthor(cls, author):
        '''Sets the author (str) to the settings data structure.'''
        cls.SETTINGS['general']['author'] = author
        pass


    @classmethod
    def getMultiDevelop(cls):
        '''Return the multi-develop (bool) from the settings data structure.'''
        return cls.SETTINGS['general']['multi-develop']


    @classmethod
    def getTemplateFiles(cls, returnlist=False):
        '''
        Returns a list of all available files within the template, excluding the
        .git folder (if exists). Paths are relative to the template base path.

        Parameters:
            returnlist (bool): determine if to return list or print to console
        Returns:
            ([str]): list of all available files within the current template.
        '''
        #get all files
        cls.TEMPLATE = cls.fs(cls.TEMPLATE)
        files = glob.glob(cls.TEMPLATE+"/**/*", recursive=True)
        
        tmplt_files = []
        for f in files:
            f = cls.fs(f)
            #skip all hidden git files
            if(f.lower().count('/.git/')):
                continue
            #only print files
            if(os.path.isfile(f)):
                # :todo: it is an invisible file do something special?
                #if(f.startswith('/.')):
                #   pass
                f = f.replace(cls.TEMPLATE,'/')
                tmplt_files += [f]
        #print files to the console
        if(returnlist == False):
            log.info("All available files in the current template:")
            for tf in tmplt_files:
                print('\t',tf)
        #return the files as a list
        else:
            return tmplt_files


    @classmethod
    def confirmation(cls, prompt, warning=True):
        '''
        Prompt the user to verify a given action before proceeding.

        Parameters:
            prompt (str): the message to display for confirmation
            warning (bool): determine if to use log.info or log.warning
        Returns:
            (bool): true if user inputted 'y', false if 'n'
        '''
        if(warning):
            log.warning(prompt+" [y/n]")
        else:
            try:
                log.info(prompt+" [y/n]")
            except KeyboardInterrupt:
                exit("\nExited prompt.")
        verify = input().lower()
        while True:
            if(verify == 'y'):
                return True
            elif(verify == 'n'):
                return False
            try:
                verify = input("[y/n]").lower()
            except KeyboardInterrupt:
                exit("\nExited prompt.")
        pass


    @classmethod
    def strToList(self, c_str, delim=','):
        '''
        Converts a string seperated by `delim` to a list of its string values.
        Strips off whitespace for each value.

        Returns an empty list if `c_str` is None.

        Parameters:
            c_str (str): unparsed string
            delim (str): valid delimiter to parse the string
        Returns:
            [(str)]: list of words/values found in the unparsed string
        '''
        #return empty list if None is given.
        if(c_str == None):
            return []

        parsed = c_str.split(delim)
        #trim off any whitespace or \n characters
        for i in range(len(parsed)):
            parsed[i] = parsed[i].strip()

        return parsed


    @classmethod
    def listToStr(self, in_list, delim=','):
        '''
        Converts a list to a string separated by `delim`. The last delimiter
        is omitted.

        Parameters:
            in_list ([str]): list of string items to convert
            delim (str): valid delimiter to separate list items in the string
        Returns:
            str: single complete string with items separated by delimiter
        '''
        single_str = ''
        if(isinstance(in_list, str)):
            return in_list
        #concatenate all items together split by delimiter
        for w in in_list:
            single_str = single_str + w + delim
        #return with last delimiter trimmed off
        if(len(delim)):
            return single_str[:len(single_str)-len(delim)]
        else:
             return single_str
    

    @classmethod
    def save(cls):
        '''
        Saves the current multi-level dictionary cls.SETTINGS to the cfg file.

        Parameters:
            None
        Returns:
            None
        '''
        with open(cls.HIDDEN+cls.SETTINGS_FILE, "w") as file:
            cfg.save(cls.SETTINGS, file, cls.getComments())
        pass


    #return the block file metadata from a specific version tag already includes 'v'
    #if returned none then it is an invalid legohdl release point
    @classmethod
    #:todo: clean up and refactor...move elsewhere?
    def getBlockFile(cls, repo, tag, path="./", in_branch=True):
        #checkout repo to the version tag and dump cfg file
        repo.git('checkout',tag+cls.TAG_ID)
        #find Block.cfg
        if(os.path.isfile(path+cls.MARKER) == False):
            #return None if Block.cfg DNE at this tag
            log.warning("Version "+tag+" does not contain a Block.cfg file. Invalid version.")
            meta = None
        #Block.cfg exists so read its contents
        else:
            log.info("Identified valid version "+tag)
            with open(path+cls.MARKER, 'r') as f:
                meta = cfg.load(f, ignore_depth=True)
                if('block' not in meta.keys()):
                    log.error("Invalid "+cls.MARKER+" file; no 'block' section.")
                    return None

        #revert back to latest release
        if(in_branch == True):
            #in a branch so switch back
            repo.git('switch','-')
        #in a single branch (cache) so checkout back
        else:
            repo.git('checkout','-')
        #perform additional safety measure that this tag matches the 'version' found in meta
        if(meta['block']['version'] != tag[1:]):
            log.error("Block.cfg file version does not match for: "+tag+". Invalid version.")
            meta = None
        return meta
    

    @classmethod
    def execute(cls, *code, subproc=False, quiet=True, returnoutput=False):
        '''
        Execute the command and runs it through the terminal. 
        
        Immediately exits the script if return code is non-zero and 
        `returnoutput` is false.

        Parameters:
            code (*str): variable amount of arguments for execution
            subproc (bool): run in subprocess if true else use os.system()
            quiet (bool): display the command being executed
            returnoutput (bool): uses subprocess to retun stdout and stderr
        Returns:
            stdout (str): standard output if `returnoutput` is true
            stderr (str): error output if `returnoutput` is true
        '''
        #compile all variable arguments into single string separated by spaces
        code_line = ''
        for c in code:
            code_line = code_line + c + ' '
        #print to console the command to be executed
        if(quiet == False):
            log.info(code_line)
        #use subprocess to return stdout and stderr as strings
        if(returnoutput):
            proc = subprocess.Popen([*code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            out = proc.stdout.read()
            err = proc.stderr.read()
            return out.decode().strip(), err.decode().strip()
        #use subprocess
        if(subproc):
            rc = subprocess.run([*code])
            try:
                rc.check_returncode()
            except ChildProcessError:
                rc = 1
        #use os.system()
        else:
            rc = os.system(code_line)
        #immediately stop script upon a bad return code
        if(rc):
            exit(rc)


    @classmethod
    def fs(cls, path):
        '''
        Properly formats a path string by fixing all `\` to be `/`. 
        
        Also appends an extra '/' if the ending of the path is not a file, 
        indicated by having no file extension. Will not alter URLs. Expands 
        users in path.

        Parameters:
            path (str): an unformatted path
        Returns:
            path (str): the formatted path

        Similar to os.path.normcase(path).
        '''
        #do not format the path if it is a URL or path is empty
        if(path == None or path == '' or path.lower().startswith('http') or \
            path.lower().startswith('git@')):
            return path

        #replace 'environment' name with the hidden directory
        path = path.replace(cls.ENV_NAME, cls.HIDDEN)
        #expand the user variable
        path = os.path.expanduser(path)
        #replace all backward slashes
        path = path.replace('\\','/')
        #replace any double slashes
        path = path.replace('//','/')

        #append an extra '/' if not ending in one and trying to be a filepath
        dot = path.rfind('.')
        last_slash = path.rfind('/')
        if(last_slash > dot and path[-1] != '/'):
            path = path + '/'
        
        return path

    
    @classmethod
    def fullMerge(cls, dest, src):
        '''
        Recursively moves keys/vals from src dictionary into destination
        dictionary if they don't exist. Returns dest.

        Parameters:
            dest (dict): the dictionary to modify
            src (dict): the dictionary to grab keys/values from
        Returns:
            dest (dict): modified dictionary with key/values from src
        '''

        for k,v in src.items():
            #does the destination have this key?
            if(k not in dest.keys()): 
                dest[k] = v
            if(isinstance(v, dict)):
                dest[k] = cls.fullMerge(dest[k], src[k])

        return dest


    @classmethod
    def merge(cls, place1, place2):
        '''
        Perform a 2-level python dictionary object merge. Any place2 key's and
        values will be merged into place1's dictionary. Place2 has precedence
        over Place1. Returns the final merged dictionary. 
        
        Parameters
        ---
        place1 : python dictionary object
        place2 : python dictionary object
        '''
        tmp = copy.deepcopy(place1)
        for lib in place1.keys(): #go through each current lib
            if lib in place2.keys(): #is this lib already in merging lib?
                for prj in place2[lib]:
                    tmp[lib][prj] = place2[lib][prj]

        for lib in place2.keys(): #go through all libs not in current lib
            if not lib in place1.keys():
                tmp[lib] = dict()
                for prj in place2[lib]:
                    tmp[lib][prj] = place2[lib][prj]
        return tmp


    @classmethod
    def getRefreshRate(cls):
        '''Returns the refresh-rate (int) from the settings data structure.'''
        return cls.SETTINGS['general']['refresh-rate']


    @classmethod
    def setRefreshRate(cls, r):
        '''
        Sets the refresh-rate to settings data structure.

        Parameters:
            r (int): how often to refresh markets
        Returns:
            None
        '''
        #convert to integer
        cfg.castInt(r)
        #clamp upper and lower bounds
        if(r > cls.MAX_RATE):
            r = cls.MAX_RATE
        elif(r < cls.MIN_RATE):
            r = cls.MIN_RATE
        #set in settings
        cls.SETTINGS['general']['refresh-rate'] = r
        pass


    @classmethod
    def getTemplatePath(cls):
        '''
        Returns the template path (str) from the settings data structure.

        If the path DNE or is blank, returns path to built-in template.
        
        Parameters:
            None
        Returns:
            (str): path to template
        '''
        #load template path from settings
        tmp = cls.SETTINGS['general']['template']
        #return built-in template folder if invalid folder in settings
        if(tmp == '' or os.path.exists(tmp) == False):
            tmp = cls.TEMPLATE
        return tmp

    
    @classmethod
    def getProgramPath(cls):
        '''
        Returns the path to the actual legoHDL script program.

        Parameters:
            None
        Returns:
            (str): directory to the entry-point script
        '''
        file_path = os.path.realpath(__file__)
        tail,_ = os.path.split(file_path)
        return cls.fs(tail)

    
    @classmethod
    def getEditor(cls):
        '''Returns the editor to the settings data-structure.'''
        return cls.SETTINGS['general']['editor']


    @classmethod
    def setEditor(cls, editor):
        '''Sets the editor to the settings data-structure.'''
        cls.SETTINGS['general']['editor'] = editor
        pass


    @classmethod
    def rmReadOnly(cls, func, path, execinfo):
        '''
        Work-around fix to windows issues when trying to remove a file/folder
        that may be used in a process.

        To be used with shutil.rmtree() as the `onerror` argument.
        '''
        os.chmod(path, stat.S_IWRITE)
        try:
            func(path)
        except PermissionError:
            exit(log.error("Failed to remove path due to being open in another process."))
    pass

    
    @classmethod
    def getComments(cls):
        '''
        Returns a dictionary of comments to be written to the settings.cfg file.

        Parameters:
            None
        Returns:
            cls.SETTING_COMMENTS (dict): settings section information
        '''
        if(hasattr(cls, "SETTINGS_COMMENTS")):
            return cls.SETTINGS_COMMENTS

        cls.SETTINGS_COMMENTS = {
    'general' : (cfg.HEADER,\
'''; ---
; legohdl.cfg
; ---
; description:
;   A properties file to manually configure the packaging and development tool.
; help:
;   For more information, read the documentation at ___.

; --- General settings ---
; description:
;   Various assignments related to the tool in general.'''),

    'active-workspace' : (cfg.VAR,\
'''
; description:
;   What workspace listed under [workspace] currently being used.
;   If an empty assignment, a lot of functionality will be unavailable.
; value: 
;   string'''),

    'author' : (cfg.VAR,\
'''
; description:
;   Your name! (or code-name, code-names are cool too)
; value: 
;   string'''),

    'editor' : (cfg.VAR,\
'''
; description:
;   The command to call your preferred text editor.
; value: 
;   string'''),

    'template' : (cfg.VAR,\
'''
; description:
;   The path of where to copy a template folder from when making a new 
;   block. If an empty assignment, it will use the built-in template folder.
; value: 
;   string'''),

    'profiles' : (cfg.VAR,\
'''
; description:
;   A list of profiles to import settings, templates, and/or scripts.
; value: 
;   list of strings'''),

    'multi-develop' : (cfg.VAR,\
'''
; description:
;   When enabled, it will reference blocks found in the workspace path over
;   block's found in the cache. This would be beneficial for simulataneously 
;   working on multiple related blocks. When done, be sure to release the
;   block's as new versions so the modifications are in stone.
; value: 
;   boolean (true or false)'''),

    'refresh-rate' : (cfg.VAR,\
'''
; description: 
;   How often to synchronize markets with their remote every day. set to 
;   -1 to refresh on every call. Max value is 1440 (every minute). Evenly divides
;   the refresh points throughout the 24-hour day. This setting simply
;   is automation for the 'refresh' command.
; value:
;   integer (-1 to 1440)'''),

    'overlap-global' : (cfg.VAR,\
'''
; description:
;   When enabled, on export the labels to be gathered can be the same file
;   from the same project even if they are different versions (overlap).
;   If disabled, it will not write multiple labels for the same file, even
;   across different versioned blocks.
; value:
;   boolean (true or false)'''),

    'label' : (cfg.HEADER,\
'''
; --- Label settings ---
; description:
;   User-defined groupings of filetypes, to be collected and written to the
;   blueprint file on export. Labels help bridge a custom workflow with the user's
;   backend tool.'''),

    'local' : (cfg.HEADER,\
'''
; description:
;   Find these files only throughout the current block.
; value:
;   assignments of string'''),

    'global' : (cfg.HEADER,\
'''
; description:
;   Find these files throughout all blocks used in the current design.
; value:
;   assignments of string'''),

    'script' : (cfg.HEADER,\
'''
; --- Script settings ---
; description:
;   User-defined aliases to execute backend scripts/tools. Assignments can
;   be either a string or list of strings separated by commas.
; value:
;   assignments of string'''),

    'workspace' : (cfg.HEADER,\
'''
; --- Workspace settings ---
; description:
;   User-defined spaces for working with blocks. Blocks must appear in the 
;   workspace's path to be recognized as downloaded. Multiple markets can be
;   configured to one workspace and markets can be shared across workspaces.
;   Block downloads and installations in one workspace are separate from those 
;   of another workspace.
; value:
;   headers with 'path' assignment of string and 'market' assignment of list 
;   of strings'''),

    'market' : (cfg.HEADER,\
'''
; --- Market settings ---
; description:
;   The list of available markets to be connected to workspaces. A market allows
;   blocks to be visible from remote repositories and downloaded/installed 
;   across machines. If a market is not configured to a remote repository, its
;   assignment is empty.
; value:
;   assignments of string'''),
        }
        return cls.SETTINGS_COMMENTS

    pass