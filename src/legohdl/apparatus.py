# ------------------------------------------------------------------------------
# Project: legohdl
# Script: apparatus.py
# Author: Chase Ruskin
# Description:
#   This script is used to hold the legohdl settings. 
# 
#   It includes code for safety measures to ensure the proper settings exits, 
#   as well as helper functions that are used throughout other scripts.
# ------------------------------------------------------------------------------

import os,shutil,stat,subprocess
import platform
import logging as log

from .cfg import Cfg, Section, Key


class Apparatus:

    #legohdl settings data structure
    SETTINGS = dict()
    CFG = Section()

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
    VENDORS = HIDDEN+"vendors/"
    #path to workspaces within legohdl
    WORKSPACE = HIDDEN+"workspaces/"

    #all available options allowed to be edited within the legohdl.cfg
    #append all non-field options here (editable dictionaries)
    OPTIONS = ['label', 'plugin', 'workspace', 'vendor', 'placeholders', 'metadata']

    LAYOUT = { 'general' : {
                    'active-workspace' : Cfg.NULL, 
                    'author' : Cfg.NULL, 
                    'editor' : Cfg.NULL,
                    'template' : Cfg.NULL, 
                    'profiles' : '()',
                    'mixed-language' : 'off', 
                    'multi-develop' : 'off', 
                    'refresh-rate' : '0',
                    'overlap-global' : 'off'},
                'label' : {
                    'local' : {}, 
                    'global' : {}},
                'plugin' : {},
                'workspace' : {},
                'vendor' : {},
                'placeholders' : {},
                'HDL-styling' : {
                    'hanging-end' : 'off',
                    'auto-fit' : 'on',
                    'alignment' : '1',
                    'newline-maps' : 'off',
                    'default-language' : 'auto',
                    'instance-name' : 'uX',
                    'port-modifier' : '*',
                    'generic-modifier' : '*'
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
    VHDL_CODE = ["*.vhd", "*.vhdl"]
    VERILOG_CODE = ["*.v", "*.sv"]

    SRC_CODE = VHDL_CODE + VERILOG_CODE

    #this character can be used on the CLI proceeding a block's title to specify
    #an entity
    ENTITY_DELIM = ':'

    DOCUMENTATION_URL = 'https://c-rus.github.io/legoHDL/'


    @classmethod
    def initialize(cls):
        '''
        Ensure all usable directories and files exist.
        '''
        
        cls.HIDDEN = cls.fs(cls.HIDDEN)
        #ask for 1st time user setup if the base directory does not exist
        ask_for_setup = (os.path.exists(cls.HIDDEN) == False)
        
        #make sure directories exist
        os.makedirs(cls.HIDDEN, exist_ok=True)
        os.makedirs(cls.HIDDEN+"workspaces/", exist_ok=True)
        os.makedirs(cls.HIDDEN+"plugins/", exist_ok=True)
        os.makedirs(cls.VENDORS, exist_ok=True)
        os.makedirs(cls.TEMPLATE, exist_ok=True)
        os.makedirs(cls.HIDDEN+"profiles/", exist_ok=True)

        #read legohd.cfg file
    
        #create empty legohdl.cfg file if DNE
        if(os.path.isfile(cls.HIDDEN+cls.SETTINGS_FILE) == False):
            open(cls.HIDDEN+cls.SETTINGS_FILE, 'w').close()
        
        cls.CFG = Cfg(cls.HIDDEN+cls.SETTINGS_FILE, data=Section(), comments=cls.getComments())

        #load in contents
        cls.CFG.read()

        #ensure all sections/keys are present
        cls.CFG.set('', Section(cls.LAYOUT), override=False)

        #create empty import.log file for profiles if DNE
        if(os.path.isfile(cls.HIDDEN+"profiles/"+cls.PRFL_LOG) == False):
            open(cls.HIDDEN+"profiles/"+cls.PRFL_LOG, 'w').close()

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
        #validate that default-language is one of 3 options
        dl = cls.CFG.get('hdl-styling.default-language')
        if(dl.lower() not in ['vhdl', 'verilog', 'auto']):
            dl = cls.CFG.set('hdl-styling.default-language', 'auto')

        #ensure the alignment setting is constrained between 0 and 80
        align = cls.CFG.get('hdl-styling.alignment', dtype=int)
        if(align < 0):
            align = 0
        elif(align > 80):
            align = 80
        cls.CFG.set('hdl-styling.alignment', align)
        pass



    @classmethod
    def load(cls):
        #ensure all pieces of settings are correct
        cls.secureSettings()

        #constrain the refresh-rate
        cls.setRefreshRate(cls.getRefreshRate())

        tmplt_path = cls.CFG.get('general.template')

        if(tmplt_path != Cfg.NULL and os.path.isdir(os.path.expandvars(tmplt_path))):
            cls.CFG.set('general.template', cls.fs(tmplt_path))
            cls.TEMPLATE = tmplt_path
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
        return cls.CFG.get('general.author')


    @classmethod
    def setAuthor(cls, author):
        '''Sets the author (str) to the settings data structure.'''
        cls.CFG.set('general.author', author, verbose=True)
        pass


    @classmethod
    def getMultiDevelop(cls):
        '''Return the multi-develop (bool) from the settings data structure.'''
        return cls.CFG.get('general.multi-develop', dtype=bool)


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
        Saves the current multi-level Section CFG object its legohdl.cfg file.

        Parameters:
            None
        Returns:
            None
        '''
        cls.CFG.write()
        pass
    

    @classmethod
    def execute(cls, *code, subproc=False, quiet=True, returnoutput=False):
        '''
        Execute the command and runs it through the terminal. 
        
        Immediately exits the command if return code is non-zero and 
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
        #immediately stop command upon a bad return code
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

        #expand the env variables
        #path = os.path.expandvars(path)

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
    def getRefreshRate(cls):
        '''Returns the refresh-rate (int) from the settings data structure.'''
        return cls.CFG.get('general.refresh-rate', dtype=int)


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
        r = Cfg.castInt(r)
        #clamp upper and lower bounds
        if(r > cls.MAX_RATE):
            r = cls.MAX_RATE
        elif(r < cls.MIN_RATE):
            r = cls.MIN_RATE
        #set in settings
        cls.CFG.set('general.refresh-rate', r)
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
        tmp = cls.CFG.get('general.template')
        #return built-in template folder if invalid folder in settings
        if(tmp == '' or os.path.exists(tmp) == False):
            tmp = cls.TEMPLATE
        return cls.fs(os.path.expandvars(tmp))

    
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
        return os.path.expandvars(cls.CFG.get('general.editor'))


    @classmethod
    def getBuildDirectory(cls):
        '''Returns the build directory (str) relative to a block's cfg file.'''
        return 'build/'

    
    @classmethod
    def getMixedLanguage(cls):
        '''Returns (bool) if all units from cross-languages should be included.'''
        return cls.CFG.get('general.mixed-language', dtype=bool)


    @classmethod
    def setEditor(cls, editor):
        '''Sets the editor to the settings data-structure.'''
        cls.CFG.set('general.editor', editor, verbose=True)
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

        cls.SETTINGS_COMMENTS = {}

        #open the info.txt
        with open(cls.getProgramPath()+'data/info.txt', 'r') as info:
            txt = info.readlines()
            disp = False
            key = ''
            for line in txt:
                sep = line.split()
                #skip comments and empty lines
                if(len(sep) and sep[0].startswith(';')):
                    continue
                if(len(sep) == 0):
                    if(disp == True):
                        cls.SETTINGS_COMMENTS[key] = cls.SETTINGS_COMMENTS[key] + '\n'
                    continue
                #find where to start
                if(len(sep) > 1 and sep[0] == '*'):
                    key = sep[1].lower()
                    if(key == 'settings-header'):
                        key = ''
                    cls.SETTINGS_COMMENTS[key] = ''
                    disp = True
                elif(disp == True):
                    if(sep[0] == '*'):
                        break
                    else:
                        end = line.rfind('\\')
                        if(end > -1):
                            line = line[:end]
                        cls.SETTINGS_COMMENTS[key] = cls.SETTINGS_COMMENTS[key] + line
            pass
        return cls.SETTINGS_COMMENTS


    pass