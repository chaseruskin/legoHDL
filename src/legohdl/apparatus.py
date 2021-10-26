################################################################################
#   Project: legohdl
#   Script: apparatus.py
#   Author: Chase Ruskin
#   Description:
#       This script is used to hold the legohdl settings. It includes code for 
#   safety measures to ensure the proper settings exits, as well as helper
#   functions that are used throughout other scripts.
################################################################################

import stat,glob,git
from datetime import datetime
import logging as log
from subprocess import check_output
import subprocess
from .cfgfile import CfgFile as cfg
import os,shutil,copy,platform


class Apparatus:
    SETTINGS = dict()

    #path to hidden legohdl folder
    HIDDEN = os.path.expanduser("~/.legohdl/")
    
    #temporary path for various purposes
    TMP = HIDDEN+"tmp/"

    #identify a valid market and its name
    MRKT_EXT = ".mrkt"
    #identify a valid profile and its name
    PRFL_EXT = ".prfl"
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

    #replace this name with HIDDEN path to the tool when found in paths
    ENV_NAME = "%LEGOHDL%"

    #path to current workspace within legohdl (is updated on intialization)
    WORKSPACE = HIDDEN+"workspaces/"

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
                    'overlap-recursive' : cfg.NULL},
                'label' : {
                    'shallow' : {}, 
                    'recursive' : {}},
                'script' : {},
                'workspace' : {},
                'market' : {}
            }   

    META = ['name', 'library', 'version', 'summary', 'toplevel', 'bench', \
            'remote', 'market', 'derives']
    
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

    __active_workspace = None

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
        cls.generateDefault(dict,"shallow","recursive",header="label")
        cls.generateDefault(dict,"market","script","workspace",header=None)
        cls.generateDefault(bool,"multi-develop","overlap-recursive",header="general")
        cls.generateDefault(int,"refresh-rate",header="general")
        cls.generateDefault(list,"profiles",header="general")
            
        return ask_for_setup

    @classmethod
    def runSetup(cls):
        is_select = cls.confirmation("This looks like your first time running \
legoHDL! Would you like to use a profile (import settings, template, and \
scripts)?", warning=False)
        if(is_select):
            #give user options to proceeding to load a profile
            resp = input("""Enter:
1) nothing for default profile
2) a path or git repository to a new profile
3) 'exit' to cancel
""")
            #continually prompt until get a valid response to move forward
            while True:
                if(resp.lower() == 'exit'):
                    log.info('Profile configuration skipped.')
                    break
                elif(resp == ''):
                    log.info("Setting up default profile...")
                    cls.loadDefaultProfile()
                    break
                elif(cls.loadProfile(resp.lower())):
                    break
                resp = input()
                pass
        
        if(not is_select or len(cls.SETTINGS['workspace'].keys()) == 0):
            #ask to create workspace
            ws_name = input("Enter a workspace name: ")
            while(len(ws_name) == 0 or ws_name.isalnum() == False):
                ws_name = input()
            cls.SETTINGS['workspace'][ws_name] = dict()


        #ask for name to store in settings
        feedback = input("Enter your name: ")
        cls.SETTINGS['general']['author'] = cls.SETTINGS['general']['author'] if(feedback.strip() == cfg.NULL) else feedback.strip()
        #ask for test-editor to store in settings
        feedback = input("Enter your text-editor: ")
        cls.SETTINGS['general']['editor'] = cls.SETTINGS['general']['editor'] if(feedback.strip() == cfg.NULL) else feedback.strip()
        pass

    @classmethod
    def generateDefault(cls, t, *args, header=None):
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
        cls.generateDefault(dict,"shallow","recursive",header="label")
        cls.generateDefault(dict,"market","script","workspace",header=None,)
        cls.generateDefault(bool,"multi-develop","overlap-recursive",header="general")
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

    #[!] PREPARING FOR REMOVAL $
    @classmethod
    def getWorkspace(cls, key, modify=False, value=None):
        '''
        This method directly accesses the settings for the active workspace as a
        dictionary. It allows for modification and accessing. Set modify=True to
        write the value parameter to the key within the current workspace's
        settings. Key can be 'path' or 'market'.
        '''
        if(not modify):
            return cls.SETTINGS['workspace'][cls.SETTINGS['general']['active-workspace']][key]
        else:
            cls.SETTINGS['workspace'][cls.SETTINGS['general']['active-workspace']][key] = value
            return True


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


    #[!] PREPARING FOR REMOVAL $
    @classmethod
    def getWorkspaceNames(cls):
        '''
        This method returns a dictionary of lower-case workspace names mapped 
        with their case-sensitive folder names found within legohdl's workspace 
        folder.
        '''
        if(hasattr(cls, '_ws_map')):
            return cls._ws_map
        cls._ws_map = {}
        ws_names = os.listdir(cls.HIDDEN+"workspaces/")
        for n in ws_names:
            cls._ws_map[n.lower()] = n
        return cls._ws_map


    #[!] PREPARING FOR REMOVAL $
    @classmethod
    def inWorkspace(cls):
        #determine current workspace currently being used
        cls.__active_workspace = cls.SETTINGS['general']['active-workspace']
        if(cls.__active_workspace == cfg.NULL or cls.__active_workspace not in cls.SETTINGS['workspace'].keys() or \
           os.path.isdir(cls.HIDDEN+"workspaces/"+cls.__active_workspace) == False):
            return False
        else:
            return True


    @classmethod
    def getAuthor(cls):
        'Return the author string from the settings.'
        author = cls.SETTINGS['general']['author']
        if(author == None):
            author = ''
        return author


    #[!] TO MOVE TO MARKET CLASS
    @classmethod
    def loadMarket(cls, value):
        '''
        This method determines if the value is a valid remote url wired to a
        valid market (indicated by having a .mrkt file). Returns the market name
        if successfully imported it, returns false otherwise. It will attempt to
        add it in if the name is not already taken.
        '''
        tmp_dir = cls.HIDDEN+"tmp/"
        mrkt_names = cls.getMarketNames()
        value = cls.fs(value)
        if(cls.isValidURL(value)):
            #clone the repository and see if it is a valid profile
            log.info("Grabbing market from... "+value)
            os.makedirs(tmp_dir)
            git.Git(tmp_dir).clone(value)
            url_name = value[value.rfind('/')+1:value.rfind('.git')]
            path_to_check = cls.fs(tmp_dir+url_name)
        else:
            log.error("Invalid remote repository URL.")
            return False

        #check if a .prfl file exists for this folder (validates profile)
        log.info("Locating .mrkt file... ")
        mrkt_file = glob.glob(path_to_check+"*"+cls.MRKT_EXT)
        if(len(mrkt_file)):
            sel_mrkt = os.path.basename(mrkt_file[0].replace('.mrkt',''))
            pass
        else:
            log.error("Invalid market; no .mrkt file found.")
            #delete if it was cloned for evaluation
            if(os.path.exists(tmp_dir)):   
                shutil.rmtree(tmp_dir, onerror=cls.rmReadOnly)
            return False

        success = (cls.isConflict(mrkt_names,sel_mrkt) == False)
        if(success):
            #insert market into markets directory
            log.info("Importing new market "+sel_mrkt+"...")
            if(os.path.exists(cls.MARKETS+sel_mrkt) == False):
                shutil.copytree(path_to_check, cls.MARKETS+sel_mrkt)
            else:
                shutil.rmtree(cls.MARKETS+sel_mrkt, onerror=cls.rmReadOnly)
                shutil.copytree(path_to_check, cls.MARKETS+sel_mrkt)
            
            cls.SETTINGS['market'][sel_mrkt] = value  
        #remove temp directory
        if(os.path.exists(tmp_dir)):  
            shutil.rmtree(tmp_dir, onerror=cls.rmReadOnly)
        
        if(success):
            return sel_mrkt
        else:
            return success


    #[!] TO MOVE TO PROFILE CLASS
    @classmethod
    def loadProfile(cls, value, explicit=False, append=False):
        '''
        This method determines if the value is an existing profile name or a git
        repository/path to a valid profile. It will stage the profile into the 
        correct place.
        '''
        prfl_dir = cls.HIDDEN+"profiles/"
        tmp_dir = cls.HIDDEN+"tmp/"
        #get all available profiles
        prfl_names = cls.getProfileNames()
        sel_prfl = None
        #see if this is a profile that already exists
        if(value.lower() in prfl_names.keys()):
            sel_prfl = prfl_names[value.lower()]
            log.info("Loading existing profile "+sel_prfl+"...")
        else:
            value = cls.fs(value)
            if(cls.isValidURL(value)):
                #clone the repository and see if it is a valid profile
                log.info("Grabbing profile from... "+value)
                os.makedirs(tmp_dir)
                git.Git(tmp_dir).clone(value)
                url_name = value[value.rfind('/')+1:value.rfind('.git')]
                path_to_check = cls.fs(tmp_dir+url_name)
            #check if the path is a local directory
            elif(os.path.isdir(value)):
                log.info("Grabbing profile from... "+value)
                path_prts = value.strip('/').split('/')
                url_name = path_prts[len(path_prts)-1]
                path_to_check = value
                pass
            elif(append):
                #add to settings
                cls.SETTINGS['general']['profiles'].append(value)
                #create new directories if applicable
                cls.dynamicProfiles()
                return True
            else:
                log.error("This is not an existing profile name, path, or repository")
                return False
            
            #check if a .prfl file exists for this folder (validates profile)
            log.info("Locating .prfl file... ")
            prfl_file = glob.glob(path_to_check+"*"+cls.PRFL_EXT)
            if(len(prfl_file)):
                sel_prfl = os.path.basename(prfl_file[0].replace('.prfl',''))
                pass
            else:
                log.error("Invalid profile; no .prfl file found.")
                #delete if it was cloned for evaluation
                if(os.path.exists(tmp_dir)):   
                    shutil.rmtree(tmp_dir, onerror=cls.rmReadOnly)
                
                return False

            #insert profile into profiles directory
            log.info("Importing new profile "+sel_prfl+"...")
            if(os.path.exists(prfl_dir+sel_prfl) == False):
                shutil.copytree(path_to_check, prfl_dir+sel_prfl)
            else:
                shutil.rmtree(prfl_dir+sel_prfl, onerror=cls.rmReadOnly)
                shutil.copytree(path_to_check, prfl_dir+sel_prfl)
                
            #remove temp directory
            if(os.path.exists(tmp_dir)):  
                shutil.rmtree(tmp_dir, onerror=cls.rmReadOnly)
            pass

        #perform backend operation to overload settings, template, and scripts
        if(append == False):
            cls.importProfile(sel_prfl, explicit=explicit)

        # add to settings if not already existing
        if(sel_prfl not in cls.SETTINGS['general']['profiles']):
            cls.SETTINGS['general']['profiles'].append(sel_prfl)
        return True


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


    @classmethod
    def strToList(self, c_str, delim=','):
        '''
        Converts a string seperated by `delim` to a list of its string values.
        Strips off whitespace for each value.

        Parameters:
            c_str (str): unparsed string
            delim (str): valid delimiter to parse the string
        Returns:
            [(str)]: list of words/values found in the unparsed string
        '''
        parsed = c_str.split(delim)
        #trim off any whitespace or \n characters
        for i in range(len(parsed)):
            parsed[i] = parsed[i].strip()

        return parsed


    @classmethod
    def listToStr(self, in_list, delim=','):
        '''
        Converts a list to a string separated by `delim`.

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
        return single_str[0:-1]


    @classmethod
    def getRefreshRate(cls):
        return cls.SETTINGS['general']['refresh-rate']


    @classmethod
    def setRefreshRate(cls, r):
        #convert to integer
        cfg.castInt(r)
        #clamp upper and lower bounds
        if(r > cls.MAX_RATE):
            r = cls.MAX_RATE
        elif(r < cls.MIN_RATE):
            r = cls.MIN_RATE
        #set in settings
        cls.SETTINGS['general']['refresh-rate'] = r


    @classmethod
    def getTemplatePath(cls):
        #load template path from settings
        tmp = cls.SETTINGS['general']['template']
        #return built-in template folder if invalid folder in settings
        if(tmp == '' or os.path.exists(tmp) == False):
            tmp = cls.TEMPLATE
        return tmp
    

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

    #[!] PREPARING FOR REMOVAL $
    @classmethod
    def getLocal(cls):
        if(cls.inWorkspace()):
            return cls.fs(cls.SETTINGS['workspace'][cls.__active_workspace]['path'])
        else:
            return ''

    #return the block file metadata from a specific version tag already includes 'v'
    #if returned none then it is an invalid legohdl release point
    @classmethod
    def getBlockFile(cls, repo, tag, path="./", in_branch=True):
        #checkout repo to the version tag and dump cfg file
        repo.git.checkout(tag+cls.TAG_ID)
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
            repo.git.switch('-')
        #in a single branch (cache) so checkout back
        else:
            repo.git.checkout('-')
        #perform additional safety measure that this tag matches the 'version' found in meta
        if(meta['block']['version'] != tag[1:]):
            log.error("Block.cfg file version does not match for: "+tag+". Invalid version.")
            meta = None
        return meta

    #[!] PREPARING FOR REMOVAL
    @classmethod
    def isConflict(cls, mapping, name):
        '''
        This method returns true if a naming conflict exists between the name
        in question with a dictionary of the true names mapped by lower names.
        '''
        c = (name.lower() in mapping.keys() and mapping[name.lower()] != name)
        if(c):
            log.warning("Could not keep "+name+" due to name conlict with "+\
                mapping[name.lower()]+".")
        return c

    #[!] PREPARING FOR REMOVAL
    @classmethod
    def getMarkets(cls, workspace_level=True):
        '''
        This method returns a dictionary consisting of the key as the market's 
        eval name and the value as its root status (local or a valid git url).
        Can be used to only gather info on current workspace markets or all
        markets available.
        '''
        mrkt_roots = dict()
        #key: name (lower-case), val: url
        if(cls.inWorkspace() and workspace_level):
            name_list = list(cls.getWorkspace('market'))
            for name in name_list:
                #see if there is conflict
                if(cls.isConflict(cls.getMarketNames(), name)):
                    #this means this name does have a folder in the markets/ 
                    cls.getWorkspace('market').remove(name)
                    del cls.SETTINGS['market'][name]
                    continue
                #must be case-matching between workspace market list and entire market list
                if(name in cls.SETTINGS['market'].keys()):
                    #store its root (location/path, aka is it remote or only local)
                    mrkt_roots[name.lower()] = cls.SETTINGS['market'][name]
                #this market DNE as any market!
                else:
                    cls.getWorkspace('market').remove(name)
                pass
        else:
            name_list = list(cls.SETTINGS['market'].keys())
            for name in name_list:
                if(cls.isConflict(cls.getMarketNames(), name)):                
                    #this means this name does have a folder in the markets/ 
                    del cls.SETTINGS['market'][name]
                    continue
                #store its root (location/path, aka is it remote or only local)
                mrkt_roots[name] = cls.SETTINGS['market'][name]

        cls.save()
        return mrkt_roots

    #[!] PREPARING FOR REMOVAL
    def resolveMarketConflict(cls, first_mrkt, second_mrkt):
        '''
        This method resolves naming conflicts between two markets that share
        the same eval name (not necessarily the same true name). Returns true if
        the second market (the market )
        '''
        log.warning("Duplicate market names have been detected; which one do you want to keep?")
        print('1)',first_mrkt,':',cls.SETTINGS['market'][first_mrkt])
        print('2)',second_mrkt,':',cls.SETTINGS['market'][second_mrkt])
        resp = None
        while True:
            resp = input()
            opt_1 = resp == '1' or resp == first_mrkt
            opt_2 = resp == '2' or resp == second_mrkt
            #keep second market
            if(opt_2):
                #remove first market from settings
                del cls.SETTINGS['market'][first_mrkt]
                if(os.path.exists(cls.MARKETS+first_mrkt)):
                    shutil.rmtree(cls.MARKETS+first_mrkt,onerror=cls.rmReadOnly)
                return True
            #keep first market
            elif(opt_1):
                #remove second market from market settings
                del cls.SETTINGS['market'][second_mrkt]
                return False
        pass
    

    @classmethod
    def execute(cls, *code, subproc=False, quiet=True, returnoutput=False):
        '''
        Execute the command and runs it through the terminal. Immediately exits
        the script if return code is non-zero and `returnoutput` is false.

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
        Properly formats a path string by fixing all `\` to be `/`. Will also
        append an extra '/' if the ending of the path is not a file, indicated by having
        no file extension. Will not alter URLs. Expands users in path.

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


    #[!] PREPARING FOR REMOVAL $
    @classmethod
    def getMarketNames(cls):
        '''
        Return a dictionary mapping a market's lower-case name (key) to its
        real-case name (value). No market can share the same case-insensitive
        name. This are the .mrkt files found in the market folder.
        '''
        if(hasattr(cls,"_mrkt_map")):
            return cls._mrkt_map

        cls._mrkt_map = {}
        #find all markets
        mrkt_files = glob.glob(cls.MARKETS+"**/*"+cls.MRKT_EXT, recursive=True)
        for m in mrkt_files:
            #get file name and exlude extension
            name = os.path.basename(m).replace(cls.MRKT_EXT,'')
            #ask user to resolve issue of multiple eval names
            #if(name.lower() in cls._mrkt_map.keys()):
                #cls.resolveMarketConflict(cls._mrkt_map[name.lower()], name)
            #store the true-case name as value behind the lower-case name key
            cls._mrkt_map[name.lower()] = name
        
        return cls._mrkt_map


    #[!] PREPARING FOR REMOVAL $
    @classmethod
    def isValidURL(cls, url):
        '''
        This method takes a URL and tests it to see if it is a valid remote git
        repository. Returns true if its valid else false.
        '''
        #first perform quick test to pass before actually verifying url
        log.info("Checking ability to link to url...")
        if(url == None or url.count(".git") == 0):
            return False
        try:
            check_output(["git","ls-remote",url])
        except:
            return False
        return True


    #[!] PREPARING FOR REMOVAL $
    @classmethod
    def linkedMarket(cls):
        '''
        Returns true if the current workspace has some markets listed.
        '''
        rem = cls.SETTINGS['workspace'][cls.__active_workspace]['market']
        return (rem != None and len(rem))

    
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
        return cls.SETTINGS['general']['editor']


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


    #[!] PREPARED FOR REMOVAL $
    @classmethod
    def isRemoteBare(cls, git_url):
        tmp_dir = cls.HIDDEN+"tmp/"
        #print(repo.git.rev_parse('--is-bare-repository '))
        os.makedirs(tmp_dir, exist_ok=True)
        repo = git.Git(tmp_dir).clone(git_url)
        name = os.listdir(tmp_dir)[0]
        repo = git.Repo(tmp_dir+name)
        isBare = repo.git.status('-uno').count('No commits yet\n') > 0
        shutil.rmtree(tmp_dir, onerror=cls.rmReadOnly)
        return isBare

    
    @classmethod
    def getComments(cls):
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

    'overlap-recursive' : (cfg.VAR,\
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

    'shallow' : (cfg.HEADER,\
'''
; description:
;   Find these files only throughout the current block.
; value:
;   assignments of string'''),

    'recursive' : (cfg.HEADER,\
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