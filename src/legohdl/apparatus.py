# ------------------------------------------------------------------------------
# Project: legohdl
# Script: apparatus.py
# Author: Chase Ruskin
# Description:
#   This script is used to hold the legohdl settings. It includes code for 
#   safety measures to ensure the proper settings exits, as well as helper
#   functions that are used throughout other scripts.
# ------------------------------------------------------------------------------

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
    #path to vendors within legohdl
    MARKETS = HIDDEN+"vendors/"
    #path to workspaces within legohdl
    WORKSPACE = HIDDEN+"workspaces/"

    #replace this name with HIDDEN path to the tool when found in paths
    ENV_NAME = "%LEGOHDL%"

    #all available options allowed to be edited within the legohdl.cfg
    #append all non-field options here (editable dictionaries)
    OPTIONS = ['label', 'script', 'workspace', 'vendor', 'placeholders', 'metadata']

    LAYOUT = { 'general' : {
                    'active-workspace' : cfg.NULL, 
                    'author' : cfg.NULL, 
                    'editor' : cfg.NULL,
                    'template' : cfg.NULL, 
                    'profiles' : cfg.NULL,
                    'mixed-language' : cfg.NULL, 
                    'multi-develop' : cfg.NULL, 
                    'refresh-rate' : cfg.NULL,
                    'overlap-global' : cfg.NULL},
                'label' : {
                    'local' : {}, 
                    'global' : {}},
                'script' : {},
                'workspace' : {},
                'vendor' : {},
                'placeholders' : {},
                'HDL-styling' : {
                    'hanging-end' : cfg.NULL,
                    'auto-fit' : cfg.NULL,
                    'alignment' : cfg.NULL,
                    'newline-maps' : cfg.NULL,
                    'default-language' : cfg.NULL,
                    'instance-name' : cfg.NULL,
                    'port-modifier' : cfg.NULL,
                    'generic-modifier' : cfg.NULL
                },
                'metadata' : {}
            }
    
    #this is appended to the tag to make it unique for legoHDL
    TAG_ID = '-legohdl'    
    #file kept in vendors to remember all valid release points
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
    VHDL_CODE = ["*.vhd", "*.vhdl", "*.VHD", "*.VHDL"]
    VERILOG_CODE = ["*.v", "*.sv", "*.V", "*.SV"]

    SRC_CODE = VHDL_CODE + VERILOG_CODE

    #this character can be used on the CLI proceeding a block's title to specify
    #an entity
    ENTITY_DELIM = ':'

    DOCUMENTATION_URL = 'https://c-rus.github.io/legoHDL/'


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
        cls.secureSettings()

        #return if user was missing the legohdl hidden folder
        return ask_for_setup


    @classmethod
    def secureSettings(cls):
        '''
        Ensure proper values are given to various settings.
        
        Parameters:
            None
        Returns:
            None
        '''
        cls.generateDefault(dict,"local","global",header="label")

        cls.generateDefault(dict,"vendor","script","workspace","metadata","placeholders",header=None)

        cls.generateDefault(bool,"multi-develop","overlap-global","mixed-language",header="general")
        cls.generateDefault(int,"refresh-rate",header="general")
        cls.generateDefault(list,"profiles",header="general")

        cls.generateDefault(bool,"hanging-end","newline-maps","auto-fit",header="HDL-styling")
        cls.generateDefault(int,"alignment",header="HDL-styling")

        #validate that default-language is one of 3 options
        def_lang = cls.getField(['HDL-styling', 'default-language']).lower()
        if(def_lang != 'vhdl' and def_lang != 'verilog'):
            cls.setField('auto', ['HDL-styling', 'default-language'])
            pass

        #validate an instance name exists
        if(cls.getField(['HDL-styling', 'instance-name'], None) == None):
            cls.setField('uX', ['HDL-styling', 'instance-name'])
            pass

        #ensure the alignment setting is constrained between 0 and 80
        align = cls.getField(['HDL-styling', 'alignment'], int)
        if(align < 0):
            align = 0
        elif(align > 80):
            align = 80
        cls.setField(align, ['HDL-styling', 'alignment'])

        #ensure the modifiers have a default value (wildcard)
        if(cls.getField(['HDL-styling', 'generic-modifier']) == ''):
            cls.setField('*', ['HDL-styling', 'generic-modifier'])

        if(cls.getField(['HDL-styling', 'port-modifier']) == ''):
            cls.setField('*', ['HDL-styling', 'port-modifier'])

        pass


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
        cls.secureSettings()

        #constrain the refresh-rate
        cls.setRefreshRate(cls.getRefreshRate())

        if(cls.SETTINGS['general']['template'] != cfg.NULL and os.path.isdir(cls.SETTINGS['general']['template'])):
            cls.SETTINGS['general']['template'] = cls.fs(cls.SETTINGS['general']['template'])
            cls.TEMPLATE = cls.SETTINGS['general']['template']
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
    def getTemplateFiles(cls, tmplt_path, inc_hidden=False, is_hidden=False, returnnames=False):
        '''
        Returns a list of all available files within the template, excluding the
        .git/ folder (if exists). Paths are relative to the template base path.
        Recursive method.

        Parameters:
            tmplt_path (str): path to search for files/directories
            inc_hidden (bool): determine if to add hidden files in the directory
            is_hidden (bool): remember if the current path is hidden or not
            returnnames (bool): determine if to only return the relative filepaths
        Returns:
            ([(str, bool)]): list of all available files within the current template
            or
            ([str]): list of all available files without status of hidden or not
        '''
        #check what files/folders exist at under this path
        branches = os.listdir(tmplt_path)

        files = []

        for f in branches:
            next_hidden = False
            #skip all hidden git files
            if(f.lower() == '.git'):
                continue
            #this file/directory is hidden if the previous was hidden
            next_hidden = (f[0] == '.' or is_hidden)

            next_path = cls.fs(tmplt_path+f)
            #print(next_path)
            #recursively search this directory
            if(os.path.isdir(next_path+'/'*(f[0] == '.'))):
                next_path = next_path+'/'*(f[0] == '.')
                files += cls.getTemplateFiles(next_path, inc_hidden, is_hidden=next_hidden, returnnames=returnnames)

            #add files to the list
            elif(os.path.isfile(next_path)):
                #shorten the template path to exluse the common template base path
                rel_path = next_path[len(cls.getTemplatePath())-1:]
                #determine how to store template file item in the list (attach hidden status?)
                item = rel_path if(returnnames == True) else (rel_path, is_hidden)
                #print(item)
                #add all files or must make sure the file is not hidden
                if(inc_hidden == True or is_hidden == False):
                    files += [item]
            pass
        #return the files as a list
        return files


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
        return cfg.castInt(cls.getField(['general', 'refresh-rate']))


    @classmethod
    def setRefreshRate(cls, r):
        '''
        Sets the refresh-rate to settings data structure.

        Parameters:
            r (int): how often to refresh vendors
        Returns:
            None
        '''
        #convert to integer
        r = cfg.castInt(r)
        #clamp upper and lower bounds
        if(r > cls.MAX_RATE):
            r = cls.MAX_RATE
        elif(r < cls.MIN_RATE):
            r = cls.MIN_RATE
        #set in settings
        cls.setField(r, ['general', 'refresh-rate'])
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
        return cls.fs(tmp)

    
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
    def autoFillUnitFields(cls):
        '''
        Determines if to auto-set unit fields from export command.

        Parameters:
            None
        Returns:
            (bool): determine if to auto-fill "toplevel" and "bench" in
                metadata, if exists.
        '''
        return False

    
    @classmethod
    def getDisabledBlockFields(cls):
        '''
        Returns a list of optionally disabled metadata fields for newly created
        blocks.

        Parameters:
            None
        Returns:
            ([str]): list of metadata fields to remove from block initialization
        '''
        all_fields = ['toplevel', 'bench', 'summary']
        return []

    
    @classmethod
    def getEditor(cls):
        '''Returns the editor to the settings data-structure.'''
        return cls.SETTINGS['general']['editor']


    @classmethod
    def getField(cls, scope, dtype=str):
        '''
        Returns the value from the settings data structure passed in from
        the scope ([str]) headers/fields (case-sensitive).

        Parameters:
            scope ([str]): list of keys to traverse
            dtype (type): what datatype to cast from str to
        Returns:
            (bool | int | str | None): the value at the scoped field
        
        '''
        #traverse down the dictionary
        field = cls.SETTINGS
        for i in scope:
            field = field[i]
        #case to specified datatype
        if(dtype == bool):
            return cfg.castBool(field)
        elif(dtype == int):
            return cfg.castInt(field)
        elif(dtype == None):
            return cfg.castNone(field)
        return field


    @classmethod
    def setField(cls, val, scope, data=None):
        '''
        Sets the value for a generic field in the settings dictionary.
        
        Parameters:
            val (str): the value to store
            scope ([str]): the list of keys to traverse
            data (None): leave None so for recursion to use cls.SETTINGS
        Returns:
            None
        '''
        #before entering recursion set the data to traverse
        if(data == None):
            data = cls.SETTINGS
        
        #traverse down the dictionary
        if(len(scope) > 1):
            cls.setField(val, scope[1:], data[scope[0]])
        else:
            #ensure the value is type string
            val = '' if(val == None) else str(val)
            #set the value here
            data[scope[0]] = val
        pass


    @classmethod
    def getBuildDirectory(cls):
        '''Returns the build directory (str) relative to a block's cfg file.'''
        return 'build/'

    
    @classmethod
    def getMixedLanguage(cls):
        '''Returns (bool) if all units from cross-languages should be included.'''
        return cls.SETTINGS['general']['mixed-language']


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
    def listToGrid(cls, items, cols=-1, limit=80, min_space=1, offset=''):
        '''
        Iterate over a list to generate a string of evenly spaced items in
        grid-like format.

        If cols is -1, then the algorithm will auto-fit the grid to ensure at
        least 1 space exists between each item.

        'offset' is taken into account when computing the spacing.

        Parameters:
            items ([str]): list of string values to format
            cols (int): number of columns
            limit (int): max number of characters to evenly divide columns into.
            min_space (int): minimum space allowed between items in a row
            offset (str): how to start each row
        Returns:
            grid (str): a grid-like multi-line string to be printed
        '''
        #replace all tabs with 4 spaces
        offset = offset.replace('\t',' '*4)
        
        grid = offset
        if(cols == -1):
            longest = cls.computeLongestWord(items) 
            spacer = longest+min_space
            cols = int((limit-len(offset))/(spacer))
        else:
            #compute the markers
            spacer = int((limit-len(offset))/cols)
        #print(spacer)

        count = 0
        for it in items:
            diff = spacer - len(it)
            grid = grid + it + diff*' '
            count += 1
            if(count % cols == 0 and it != items[-1]):
                grid = grid + '\n' + offset
        return grid


    @classmethod
    def getPathSize(cls, path):
        '''
        Recursively sums the file sizes within the 'path' parameter to get
        the total size in bytes.
        
        Parameters:
            path (str): the path to begin getting total size
        Returns:
            total (int): number of bytes within the 'path'
        '''
        #return 0 if path DNE
        if(os.path.exists(path) == False):
            return 0
        #base case: return the file's size in bytes
        elif(os.path.isfile(path) == True):
            return os.path.getsize(path)
        #standardize the path's format
        path = cls.fs(path)
        #ensure the last character in path is '/' for concatenation purposes
        if(path[-1] != '/'):
            path = path + '/'
        #recursively add each sub directory/file
        dirs = os.listdir(path)
        total = 0
        #iterate through all sub-paths
        for d in dirs:
            total += cls.getPathSize(path+d)

        return total


    @classmethod
    def computeLongestWord(cls, words):
        '''
        Computes the longest word length from a list of words. Returns -1 if
        no words are in the list.

        Parameters:
            words ([str]): list of words to compare
        Returns:
            farthest (int): length of longest word in the list
        '''
        farthest = -1
        for s in words:
            if(len(s) > farthest):
                farthest = len(s)
        return farthest

    
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

    'general|active-workspace' : (cfg.VAR,\
'''
; description:
;   What workspace listed under [workspace] currently being used.
;   If an empty assignment, a lot of functionality will be unavailable.
; value: 
;   string'''),

    'general|author' : (cfg.VAR,\
'''
; description:
;   Your name! (or code-name, code-names are cool too)
; value: 
;   string'''),

    'general|editor' : (cfg.VAR,\
'''
; description:
;   The command to call your preferred text editor.
; value: 
;   string'''),

    'general|template' : (cfg.VAR,\
'''
; description:
;   The path of where to copy a template folder from when making a new 
;   block. If an empty assignment, it will use the built-in template folder.
; value: 
;   string'''),

    'general|profiles' : (cfg.VAR,\
'''
; description:
;   A list of profiles to import settings, templates, and/or scripts.
; value: 
;   list of strings'''),

    'general|mixed-language' : (cfg.VAR,\
'''
; description:
;   When enabled, units will be able to be identified as instantiated regardless
;   what language it was written in (VHDL or Verilog). When disabled,
;   determining what component is instantiated is filtered to only search
;   through units written in the original language.
; value: 
;   boolean (true or false)'''),

    'general|multi-develop' : (cfg.VAR,\
'''
; description:
;   When enabled, it will reference blocks found in the workspace path over
;   block's found in the cache. This would be beneficial for simulataneously 
;   working on multiple related blocks. When done, be sure to release the
;   block's as new versions so the modifications are in stone.
; value: 
;   boolean (true or false)'''),

    'general|refresh-rate' : (cfg.VAR,\
'''
; description: 
;   How often to synchronize vendors with their remote every day. set to 
;   -1 to refresh on every call. Max value is 1440 (every minute). Evenly divides
;   the refresh points throughout the 24-hour day. This setting simply
;   is automation for the 'refresh' command.
; value:
;   integer (-1 to 1440)'''),

    'general|overlap-global' : (cfg.VAR,\
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

    'label|local' : (cfg.HEADER,\
'''
; description:
;   Find these files only throughout the current block.
; value:
;   assignments of string'''),

    'label|global' : (cfg.HEADER,\
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
;   workspace's path to be recognized as downloaded. Multiple vendors can be
;   configured to one workspace and vendors can be shared across workspaces.
;   Block downloads and installations in one workspace are separate from those 
;   of another workspace.
; value:
;   headers with 'path' assignment of string and 'vendor' assignment of list 
;   of strings'''),

    'placeholders' : (cfg.HEADER,\
'''
; --- Placeholder settings ---
; description:
;   User-defined values to be replaced when referenced within '%' symbols for
;   files created through legoHDL.
; value:
;   assignments of string'''),

    'metadata' : (cfg.HEADER,\
'''
; --- Metadata settings ---
; description:
;   User-defined fields for Block.cfg files. These fields will be automatically
;   copied into new Block.cfg files. Supports using placeholders for field values.
; value:
;   headers with variable amount of assignments of string'''),

    'hdl-styling' : (cfg.HEADER,\
'''
; --- HDL-styling settings ---
; description:
;   Configure how to print compatible HDL instantiation code.'''),

    'hdl-styling|hanging-end' : (cfg.VAR,\
'''
; description:
;   Determine if the last ')' in instantiation code should deserve its own line.
; value:
;   boolean (true or false)'''),

    'hdl-styling|auto-fit' : (cfg.VAR,\
'''
; description:
;   Determine if the proceeding character/symbol after identifiers should all
;   align together based on the longest identifier name. Used in conjunction with
;   the 'aligment' setting.
; value:
;   boolean (true or false)'''),

    'hdl-styling|alignment' : (cfg.VAR,\
'''
; description:
;   Determine the number of spaces to proceed an identifier. Used in conjunction
;   with the 'auto-fit' setting.
; value:
;   int (0 to 80)'''),

    'hdl-styling|newline-maps' : (cfg.VAR,\
'''
; description:
;   Determine if the indication code for a 'map' begins on a newline.
; value:
;   bool (true or false)'''),

    'hdl-styling|default-language' : (cfg.VAR,\
'''
; description:
;   Determine which HDL language to by default print compatible instantiation
;   code. If auto, then the language the unit was originally written in is used
;   by default.
; value:
;   vhdl, verilog, or auto'''),

    'hdl-styling|instance-name' : (cfg.VAR,\
'''
; description:
;   Determine the default instantiation name given to a unit being used.
;   Placeholders are supported.
; value:
;   assignment of string'''),

    'hdl-styling|generic-modifier' : (cfg.VAR,\
'''
; description:
;   Determine the constant/parameter identifier name to connect to 
;   instantiation generics/parameters. Wildcard '*' will be replaced with 
;   the generics' original identifiers.
; value:
;   assignment of string'''),

    'hdl-styling|port-modifier' : (cfg.VAR,\
'''
; description:
;   Determine the signal/wire identifier name to connect to instantiation ports.
;   Wildcard '*' will be replaced with the ports' original identifiers.
; value:
;   assignment of string'''),

    'vendor' : (cfg.HEADER,\
'''
; --- Vendor settings ---
; description:
;   The list of available vendors to be connected to workspaces. A vendor allows
;   blocks to be visible from remote repositories and downloaded/installed 
;   across machines. If a vendor is not configured to a remote repository, its
;   assignment is empty.
; value:
;   assignments of string'''),
        }
        return cls.SETTINGS_COMMENTS

    pass