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
from .cfgfile import CfgFile as cfg
import os,shutil,copy,platform


class Apparatus:
    SETTINGS = dict()

    #path to hidden legohdl folder
    HIDDEN = os.path.expanduser("~/.legohdl/")

    #identify a valid market and its name
    MRKT_EXT = ".mrkt"
    #identify a valid profile and its name
    PRFL_EXT = ".prfl"
    #identify custom configuration files
    CFG_EXT = ".cfg"

    #identify a valid block project within the framework
    MARKER = "Block"+CFG_EXT

    #looks for this file upon a release to ask user to update changelog
    CHANGELOG = "CHANGELOG.md"

    #path to template within legohdl
    TEMPLATE = HIDDEN+"template/"
    #path to markets within legohdl
    MARKETS = HIDDEN+"markets/"

    #path to current workspace within legohdl (is updated on intialization)
    WORKSPACE = HIDDEN+"workspaces/"

    OPTIONS = ['author', 'editor', 'template', 'multi-develop', 'profiles',\
               'overlap-recursive', 'label',\
               'script',\
               'active-workspace', 'workspace',\
               'refresh-rate','market']

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

    __active_workspace = None

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

        #create bare settings.cfg if DNE
        if(not os.path.isfile(cls.HIDDEN+"settings.cfg")):
            settings_file = open(cls.HIDDEN+"settings.cfg", 'w')
            #save default settings layout
            cfg.save(cls.LAYOUT, settings_file)
            settings_file.close()
        
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
        cls.SETTINGS['author'] = cls.SETTINGS['author'] if(feedback.strip() == '') else feedback.strip()
        #ask for test-editor to store in settings
        feedback = input("Enter your text-editor: ")
        cls.SETTINGS['editor'] = cls.SETTINGS['editor'] if(feedback.strip() == '') else feedback.strip()
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
                    sett[a] = cls.castBool(val)
                elif(t == int):
                    sett[a] = cls.castInt(val)
                elif(t == list):
                    sett[a] = []

    @classmethod
    def load(cls):
        log.basicConfig(format='%(levelname)s:\t%(message)s', level=log.INFO)
        #ensure all necessary hidden folder structures exist
        ask_for_setup = cls.initialize()

        #load dictionary data in variable
        with open(cls.HIDDEN+"settings.cfg", "r") as file:
            cls.SETTINGS = cfg.load(file)
        
        #merge bare_settings into loaded settings to ensure all keys are present
        cls.SETTINGS = cls.fullMerge(cls.SETTINGS, cls.LAYOUT)

        #ensure all pieces of settings are correct
        cls.generateDefault(dict,"shallow","recursive",header="label")
        cls.generateDefault(dict,"market","script","workspace",header=None)
        cls.generateDefault(bool,"multi-develop","overlap-recursive",header="general")
        cls.generateDefault(int,"refresh-rate",header="general")
        cls.generateDefault(list,"profiles",header="general")

        #run setup here
        if(ask_for_setup):
            cls.runSetup()

        #ensure all pieces of settings are correct
        cls.generateDefault(dict,"shallow","recursive",header="label")
        cls.generateDefault(dict,"market","script","workspace",header=None,)
        cls.generateDefault(bool,"multi-develop","overlap-recursive",header="general")
        cls.generateDefault(int,"refresh-rate",header="general")
        cls.generateDefault(list,"profiles",header="general")

        if(cls.SETTINGS['general']['refresh-rate'] > cls.MAX_RATE):
            cls.SETTINGS['general']['refresh-rate'] = cls.MAX_RATE
        elif(cls.SETTINGS['general']['refresh-rate'] < cls.MIN_RATE):
            cls.SETTINGS['general']['refresh-rate'] = cls.MIN_RATE

        cls.dynamicProfiles()
        cls.dynamicWorkspace()

        #determine current workspace currently being used
        cls.__active_workspace = cls.SETTINGS['general']['active-workspace']

        if(not cls.inWorkspace()):
            log.warning("Active workspace not found!")
            return False

        if(cls.SETTINGS['general']['template'] != None and os.path.isdir(cls.SETTINGS['general']['template'])):
            cls.SETTINGS['general']['template'] = cls.fs(cls.SETTINGS['general']['template'])
            cls.TEMPLATE = cls.SETTINGS['template']
            pass
        
        if(cls.getLocal() == None):
            log.error("Please specify a workspace path for "\
                +cls.SETTINGS['general']['active-workspace']\
                +". See \'legohdl help config\' for more details.")
            cls.SETTINGS['general']['active-workspace'] = None
            return

        cls.WORKSPACE = cls.fs(cls.WORKSPACE+cls.SETTINGS['general']['active-workspace'])

        #ensure no dead scripts are populated in 'script' section of settings
        cls.dynamicScripts()
        #save all safety measures
        cls.save()
        pass

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
        kernel = platform.system()
        #must be careful to exactly match paths within Linux OS
        if(kernel != "Linux"):
            inner_path = inner_path.lower()
            path = path.lower()

        return cls.fs(path).startswith(cls.fs(inner_path)) and (path != inner_path)

    @classmethod
    def getProfileNames(cls):
        '''
        This method returns a dictionary of the lower-case names to the
        true-case names for each profile.
        '''
        if(hasattr(cls, "_prfl_map")):
            return cls._prfl_map

        cls._prfl_map = {}
        names = cls.getProfiles()
        for n in names:
            cls._prfl_map[n.lower()] = n
        return cls._prfl_map

    @classmethod
    def dynamicProfiles(cls):
        #identify valid profiles in the hidden direcotory
        found_prfls = cls.getProfiles()
        #identify potential profiles in the setting.cfg
        listed_prfls = cls.SETTINGS['general']['profiles']
        #target deletions
        for prfl in found_prfls:
            if(prfl not in listed_prfls):
                shutil.rmtree(cls.getProfiles()[prfl])
        
        #target additions
        for prfl in listed_prfls:
            if(prfl not in found_prfls):
                #check if there is a conflict with trying to make a new profile
                if(os.path.exists(cls.HIDDEN+"profiles/"+prfl)):
                    log.error("A profile already exists for "+prfl+".")
                    cls.SETTINGS['general']['profiles'].remove(prfl)
                    continue
                log.info("Creating empty profile "+prfl+"...")
                os.makedirs(cls.HIDDEN+"profiles/"+prfl, exist_ok=True)
                
                with open(cls.HIDDEN+"profiles/"+prfl+"/"+prfl+cls.PRFL_EXT, 'w'):
                    pass
        pass

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
    
    @classmethod
    def dynamicWorkspace(cls):
        '''
        This method automatically creates local paths for workspaces and 
        deletes data from stale workspaces.
        '''
        acting_ws = cls.SETTINGS['general']['active-workspace']
        coupled_ws = tuple(cls.SETTINGS['workspace'].items())
        all_mrkts = list(cls.getMarkets(workspace_level=False).keys())
        for ws,val in coupled_ws:
            #check if there is a name conflict
            if(cls.isConflict(cls.getWorkspaceNames(), ws)):
                del cls.SETTINGS['workspace'][ws]
                continue
            if(isinstance(val, dict) == False):
                val = dict()
                cls.SETTINGS['workspace'][ws] = dict()
            if('path' not in val.keys()):
                cls.SETTINGS['workspace'][ws]['path'] = cfg.NULL
            if('market' not in val.keys() or isinstance(val['market'],list) == False):
                val['market'] = list()
                cls.SETTINGS['workspace'][ws]['market'] = list()
            #automatically remove invalid market names from workspace's market list
            ws_mrkts = list(cls.SETTINGS['workspace'][ws]['market'])
            for mrkt in ws_mrkts:
                if mrkt not in all_mrkts:
                    cls.SETTINGS['workspace'][ws]['market'].remove(mrkt)
            #try to initialize workspace
            cls.initializeWorkspace(ws, cls.fs(val['path']))

        #remove any hidden workspace folders that are no longer in the settings.cfg
        for ws in cls.getWorkspaceNames().values():
            if(ws not in cls.SETTINGS['workspace'].keys()):
                #delete if found a directory type
                if(os.path.isdir(cls.HIDDEN+"workspaces/"+ws)):
                    shutil.rmtree(cls.HIDDEN+"workspaces/"+ws, onerror=cls.rmReadOnly)
                #delete if found a file type
                else:
                    os.remove(cls.HIDDEN+"workspaces/"+ws)

        if(acting_ws != cfg.NULL):
            cls.SETTINGS['general']['active-workspace'] = acting_ws
        
        pass
    
    #automatically manage if a script still exists and clean up non-existent scripts
    @classmethod
    def dynamicScripts(cls):
        #loop through all script entries
        deletions = []
        for key,val in cls.SETTINGS['script'].items():
            exists = False
            parsed = val.split()
            #try every part of the value as a path
            for pt in parsed:
                pt = pt.replace("\"","").replace("\'","")
                if(os.path.isfile(pt)):
                    exists = True
                    break
            #mark this pair for deletion from settings
            if(not exists):
                deletions.append(key)
        #clean dead script from scripts section
        for d in deletions:
            del cls.SETTINGS['script'][d]
        pass

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
        return True

    #perform backend operation to overload settings, template, and scripts
    @classmethod
    def importProfile(cls, prfl_name, explicit=False):
        with open(cls.HIDDEN+"profiles/"+cls.PRFL_LOG, 'w') as f:
            f.write(prfl_name)
        if(prfl_name not in cls.SETTINGS['general']['profiles']):
            cls.SETTINGS['general']['profiles'] += [prfl_name]
        #merge all values found in src override dest into a new dictionary
        def deepMerge(src, dest, setting="", scripts_only=False):
            for k,v in src.items():
                next_level = setting
                isHeader = isinstance(v, dict)
                if(setting == ""):
                    if(isHeader):
                        next_level = cfg.HEADER[0]+k+cfg.HEADER[1]+" "
                    else:
                        next_level = k
                else:
                    if(isHeader):
                        next_level = next_level + cfg.HEADER[0] + k + cfg.HEADER[1]+" "
                    else:
                        next_level = next_level + k
                #print(next_level)
                #only proceed when importing just scripts
                if(scripts_only and next_level.startswith(cfg.HEADER[0]+'script'+cfg.HEADER[1]) == 0):
                    continue
                #skip scripts if not explicitly set in argument
                elif(scripts_only == False and next_level.startswith(cfg.HEADER[0]+'script'+cfg.HEADER[1]) == 1):
                    continue
                #go even deeper into the dictionary tree
                if(isinstance(v, dict)):
                    if(k not in dest.keys()):
                        dest[k] = dict()
                        #log.info("Creating new dictionary "+k+" under "+next_level+"...")
                    deepMerge(v, dest[k], setting=next_level, scripts_only=scripts_only)
                #combine all settings except if profiles setting exists in src
                elif(k != 'profiles'):
                    #log.info("Overloading "+next_level+"...")
                    #append to list, don't overwrite
                    if(isinstance(v, list)):
                        #create new list if DNE
                        if(k not in dest.keys()):
                            #log.info("Creating new list "+k+" under "+next_level+"...")
                            dest[k] = []
                        if(isinstance(dest[k], list)):   
                            for i in v:
                                #find replace all parts of string with %LEGOHDL%
                                if(isinstance(v,str)):
                                    v = v.replace("%LEGOHDL%", cls.HIDDEN[:len(cls.HIDDEN)-1])
                                if(i not in dest[k]):
                                    dest[k] += [i]
                    #otherwise normal overwrite
                    else:
                        if(isinstance(v,str)):
                            v = v.replace("%LEGOHDL%", cls.HIDDEN[:len(cls.HIDDEN)-1])
                        #do not allow a null workspace path to overwrite an already established workspace path
                        if(k in dest.keys() and k == 'path' and v == cfg.NULL):
                            continue
                        dest[k] = v
                    #print to console the overloaded settings
                    log.info(next_level+" = "+str(v))
            return dest

        prfl_path = cls.getProfiles()[prfl_name]
        #overload available settings
        if(cls.isInProfile(prfl_name, 'settings.cfg')):
            act = not explicit or cls.confirmation("Import settings.cfg?", warning=False)
            if(act):
                log.info('Overloading settings.cfg...')
                with open(prfl_path+'settings.cfg', 'r') as f:
                    prfl_settings = cfg.load(f)
                    
                    dest_settings = copy.deepcopy(cls.SETTINGS)
                    dest_settings = deepMerge(prfl_settings, dest_settings)
                    cls.SETTINGS = dest_settings
            pass

        #copy in template folder
        if(cls.isInProfile(prfl_name, 'template')):
            act = not explicit or cls.confirmation("Import template?", warning=False)
            if(act):
                log.info('Importing template...')
                shutil.rmtree(cls.HIDDEN+"template/",onerror=cls.rmReadOnly)
                shutil.copytree(prfl_path+"template/", cls.HIDDEN+"template/")
            pass

        #copy in scripts
        if(cls.isInProfile(prfl_name, 'scripts')):
            act = not explicit or cls.confirmation("Import scripts?", warning=False)
            if(act):
                log.info('Importing scripts...')
                scripts = os.listdir(prfl_path+'scripts/')
                for scp in scripts:
                    log.info("Copying "+scp+" to built-in scripts folder...")
                    if(os.path.isfile(prfl_path+'scripts/'+scp)):
                        #copy contents into built-in script folder
                        prfl_script = open(prfl_path+'scripts/'+scp, 'r')
                        copied_script = open(cls.HIDDEN+'scripts/'+scp,'w')
                        script_data = prfl_script.readlines()
                        copied_script.writelines(script_data)
                        prfl_script.close()
                        copied_script.close()
                        pass
                    pass
                log.info('Overloading scripts in settings.cfg...')
                with open(prfl_path+'settings.cfg', 'r') as f:
                    prfl_settings = cfg.load(f)
                    dest_settings = copy.deepcopy(cls.SETTINGS)
                    dest_settings = deepMerge(prfl_settings, dest_settings, scripts_only=True)
                    cls.SETTINGS = dest_settings
            pass

        cls.save()
        pass

    @classmethod
    def updateProfile(cls, name):
        reload_default = (name.lower() == "default")

        if name in cls.getProfiles():
            #see if this path is a git repository
            try:
                repo = git.Repo(cls.getProfiles()[name])
                log.info("Updating repository for "+name+" profile...")
                #pull down the latest
                if(len(repo.remotes)):
                    repo.git.remote('update')
                    status = repo.git.status('-uno')
                    if(status.count('Your branch is up to date with') or status.count('Your branch is ahead of')):
                        log.info("Already up-to-date.")
                        return
                    else:
                        log.info('Pulling new updates...')
                    repo.remotes[0].pull()
                    log.info("success")
                    return
                else:  
                    if(not reload_default):
                        exit(log.error("This git repository has no remote URL."))
            except:
                if(not reload_default):
                    exit(log.error("Not a git repository."))
        else:
            #must add to setting if default not found
            if(reload_default):
                cls.SETTINGS['general']['profiles'].append('default')
                cls.save()
            else:
                log.error("Profile "+name+" does not exist.")
            pass

        if(reload_default):
            log.info("Reloading default profile...")
            cls.loadDefaultProfile(importing=False)
        pass
    
    @classmethod
    def isInProfile(cls, name, loc):
        if(name in cls.getProfiles()):
            if(loc == 'settings.cfg'):
                return os.path.isfile(cls.getProfiles()[name]+loc)
            else:
                return os.path.isdir(cls.getProfiles()[name]+loc+"/")

    #looks within profiles directory and returns dict of all valid profiles
    @classmethod
    def getProfiles(cls):
        places = os.listdir(cls.HIDDEN+"profiles/")
        profiles = dict()
        for plc in places:
            path = cls.fs(cls.HIDDEN+"profiles/"+plc+"/")
            if(os.path.isfile(path+plc+cls.PRFL_EXT)):
                profiles[plc] = path

        return profiles

    @classmethod
    def initializeWorkspace(cls, name, local_path=None):
        workspace_dir = cls.HIDDEN+"workspaces/"+name+"/"
        if(os.path.isdir(workspace_dir) == False):
            log.info("Creating workspace directories for "+name+"...")
            os.makedirs(workspace_dir, exist_ok=True)
        #store the code's state of each version for each block
        os.makedirs(workspace_dir+"cache", exist_ok=True)
        #create the refresh log
        if(os.path.isfile(workspace_dir+cls.REFRESH_LOG) == False):
            open(workspace_dir+cls.REFRESH_LOG, 'w').close()
        
        #ask to create paths for workspace's with invalid paths
        ws_path = local_path
        if(ws_path == cfg.NULL):
            ws_path = input("Enter workspace "+name+"'s path: ")
            while(len(ws_path) <= 0):
                ws_path = input()

        cls.SETTINGS['workspace'][name]['path'] = cls.fs(ws_path)
        local_path = cls.SETTINGS['workspace'][name]['path']
        
        if(os.path.exists(local_path) == False):
            log.info("Creating new path... "+local_path)
            os.makedirs(local_path)

        #create cfg structure for workspace settings 'local' and 'market'
        if(name not in cls.SETTINGS['workspace'].keys()):
            cls.SETTINGS['workspace'][name] = {'path' : local_path, 'market' : None}
        #make sure market is a list
        if(isinstance(cls.SETTINGS['workspace'][name]['market'],list) == False):
            cls.SETTINGS['workspace'][name]['market'] = []

        #cannot be active workspace if a workspace path is null
        if(cls.SETTINGS['workspace'][name]['path'] == None and cls.__active_workspace == name):
            cls.__active_workspace = None
            return

        #if no active-workspace then set it as active
        if(not cls.inWorkspace()):
            cls.SETTINGS['general']['active-workspace'] = name
            cls.__active_workspace = name
        pass

    @classmethod
    def confirmation(cls, prompt, warning=True):
        if(warning):
            log.warning(prompt+" [y/n]")
        else:
            log.info(prompt+" [y/n]")
        verify = input().lower()
        while True:
            if(verify == 'y'):
                return True
            elif(verify == 'n'):
                return False
            verify = input("[y/n]").lower()

    @classmethod
    def readyForRefresh(cls):
        #helper method to convert a datetime time word to a decimal floating type number
        def timeToFloat(prt):
            time_stamp = str(prt).split(' ')[1]
            time_sects = time_stamp.split(':')
            hrs = int(time_sects[0])
            #convert to 'hours'.'minutes'
            time_fmt = (float(hrs)+(float(float(time_sects[1])/60)))
            return time_fmt
            
        rf_log_path = cls.WORKSPACE+cls.REFRESH_LOG
        rate = cls.SETTINGS['general']['refresh-rate']
        
        #never perform an automatic refresh
        if(rate == 0):
            return False
        #always perform an automatic refresh
        elif(rate <= cls.MIN_RATE):
            log.info("Automatically refreshing markets...")
            return True
    
        refresh = False
        latest_punch = None
        stage = 1
        cur_time = datetime.now()

        #divide the 24 hour period into even checkpoints
        max_hours = float(24)
        spacing = float(max_hours / rate)
        intervals = []
        for i in range(rate):
            intervals += [spacing*i]

        #read when the last refresh time occurred
        with open(rf_log_path, 'r') as rf_log:
            #read the latest date
            file_data = rf_log.readlines()
            #no refreshes have occurred so automatically need a refresh
            if(len(file_data) == 0):
                latest_punch = cur_time
                refresh = True
            else:
                latest_punch = datetime.fromisoformat(file_data[0])
                #print(latest_punch)
                #get latest time that was punched
                last_time_fmt = timeToFloat(latest_punch)
                #determine the next checkpoint available for today
                next_checkpoint = max_hours
                for i in range(len(intervals)):
                    if(last_time_fmt < intervals[i]):
                        next_checkpoint = intervals[i]
                        stage = i + 1
                        break
                #print('next checkpoint',next_checkpoint)
                cur_time_fmt = timeToFloat(cur_time)
                #check if the time has occurred on a previous day, (automatically update because its a new day)
                next_day = cur_time.year > latest_punch.year or cur_time.month > latest_punch.month or cur_time.day > latest_punch.day
                #print(next_day)
                #print("currently",cur_time_fmt)
                #determine if the current time has passed the next checkpoint or if its a new day
                if(next_day or cur_time_fmt >= next_checkpoint):
                    latest_punch = cur_time
                    refresh = True

        #write back the latest punch
        with open(rf_log_path, 'w') as rf_log:
            rf_log.write(str(latest_punch))

        if(refresh):
            log.info("Automatically refreshing markets... ("+str(stage)+"/"+str(rate)+")")

        return refresh
    
    @classmethod
    def save(cls):
        with open(cls.HIDDEN+"settings.cfg", "w") as file:
            cfg.save(cls.SETTINGS, file)
            # for key in cls.OPTIONS:
            #     #pop off front key/val pair of cfg data
            #     single_dict = {}
            #     single_dict[key] = cls.SETTINGS[key]

            #     if(key == 'author'):
            #         file.write("#general configurations\n")
            #     elif(key == 'overlap-recursive'):
            #         file.write("#label configurations\n")
            #     elif(key == 'script'):
            #         file.write("#script configurations\n")
            #     elif(key == 'active-workspace'):
            #         file.write("#workspace configurations\n")
            #     elif(key == 'refresh-rate'):
            #         file.write("#market configurations\n")

                # cfg.save(single_dict, file)
            pass
        pass

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
                meta = cfg.load(f)
                if('block' not in meta.keys()):
                    log.error("Invalid Block.cfg file; no 'block' section")
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

    @classmethod
    def linkedMarket(cls):
        '''
        Returns true if the current workspace has some markets listed.
        '''
        rem = cls.SETTINGS['workspace'][cls.__active_workspace]['market']
        return (rem != None and len(rem))

    @classmethod
    def fs(cls, path):
        '''
        Fixes all \ slashes to become / slashes in path strings. Will also
        append an extra '/' if the ending of the path is not a file (has no
        file extension).
        '''
        if(path == None or path.lower().startswith('http') or path.lower().startswith('git@')):
            return path

        path = path.replace("%LEGOHDL%", cls.HIDDEN[:len(cls.HIDDEN)-1])

        path = os.path.expanduser(path)
        path = path.replace('\\','/')
        path = path.replace('//','/')

        dot = path.rfind('.')
        last_slash = path.rfind('/')

        if(last_slash > dot and path[len(path)-1] != '/'):
            path = path + '/'
        
        return path

    @classmethod
    def castBool(cls, str_val):
        if(isinstance(str_val, bool)):
            return str_val
        str_val = str_val.lower()
        return (str_val == 'true' or str_val == 't' or str_val == '1' or str_val == 'yes' or str_val == 'on')
    
    @classmethod
    def castNone(cls, str_blank):
        if(str_blank == cfg.NULL):
            return None
        else:
            return str_blank
            
    @classmethod
    def castInt(cls, str_int):
        if(isinstance(str_int, int)):
            return str_int
        if(str_int.isdigit()):
            return int(str_int)
        else:
            return 0

    @classmethod
    def fullMerge(cls, dest, src):
        '''
        Recursively moves keys/vals from src dictionary into destination
        dictionary if they don't exist. Returns dest.
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
    def rmReadOnly(cls, func, path, execinfo):
        os.chmod(path, stat.S_IWRITE)
        try:
            func(path)
        except PermissionError:
            exit("Failed to remove path due to being open in another process.")
    pass

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
    def loadDefaultProfile(cls, importing=True):
        prfl_dir = cls.HIDDEN+"profiles/"
        prfl_name = "default"
        prfl_path = prfl_dir+prfl_name+"/"

        #remove default if previously existed
        if(os.path.isdir(prfl_path)):
            shutil.rmtree(prfl_path, onerror=cls.rmReadOnly)
        
        #create default
        os.makedirs(prfl_path)
        #create profile marker file
        open(prfl_path+prfl_name+cls.PRFL_EXT, 'w').close()

        def_settings = dict()
        def_settings['script'] = \
        {
            'hello'  : 'python %LEGOHDL%/scripts/hello_world.py',
        }
        def_settings['workspace'] = dict()
        def_settings['workspace']['primary'] = {'path' : None, 'market' : None}
        #create default settings.cfg
        with open(prfl_path+"settings.cfg", 'w') as f:
            cfg.save(def_settings, f)
            pass

        #create default template
        os.makedirs(prfl_path+"template/")
        os.makedirs(prfl_path+"template/src")
        os.makedirs(prfl_path+"template/test")
        os.makedirs(prfl_path+"template/constr")
        #create readme
        with open(prfl_path+'template/README.md', 'w') as f:
            f.write("# %BLOCK%")
            pass
        #create .gitignore
        with open(prfl_path+'template/.gitignore', 'w') as f:
            f.write("build/")
            pass

        comment_section = """--------------------------------------------------------------------------------
-- Block: %BLOCK%
-- Author: %AUTHOR%
-- Creation Date: %DATE%
-- Entity: template
-- Description:
--      This is a sample template VHDL source file to help automate boilerplate 
--  code.
--------------------------------------------------------------------------------"""
        vhdl_code = """
  
library ieee;
use ieee.std_logic_1164.all;


entity template is
    port(

    );
end entity;


architecture rtl of template is
begin

end architecture;      
"""
        #create template design
        with open(prfl_path+'template/src/template.vhd', 'w') as f:
            f.write(comment_section)
            f.write(vhdl_code)
            pass

        #create template testbench
        with open(prfl_path+'template/test/template_tb.vhd', 'w') as f:
            f.write(comment_section.replace("template", "template_tb"))
            f.write(vhdl_code.replace("template", "template_tb").replace("""\n    port(

    );""", '\b'))
            pass

        #create default scripts
        os.makedirs(prfl_path+"scripts/")

        # with open(prfl_path+"scripts/xsim_default.py", 'w') as f:
            
        #     pass

        # with open(prfl_path+"scripts/modelsim_default.py", 'w') as f:

        #     pass
        with open(prfl_path+"scripts/hello_world.py", 'w') as f:
            f.write("""# Script: hello_world.py
# Author: Chase Ruskin
# Creation Date: 09.19.2021
# Description:
#   Backend script that uses no EDA tool but provides an outline for one way
#   how to structure a script. A workflow is ran here by only printing related
#   information to the console.
# Default:
#   Do nothing.
# Options:
#   -lint        : lint the design
#   -synth       : synthesis the design
#   -route       : route/implement/fit the design (assign pins)
#   -sim         : simulate the design
#   -gen         : any arguments after this one are VHDL generics or verilog 
#                  parameters and will be passed to the top-level design and to 
#                  the test vector script, if available. An example of setting 
#                  generics: -gen width=10 addr=32 trunc=2
#   
# To learn more about writing your own backend scripts for legohdl, visit:
# https://hdl.notion.site/Writing-Scripts-f7fc7f75be104c4fa1640d2316f5d6ef

import sys,os

# === Define constants, important variables, helper methods ====================
#   Identify any variables necessary for this script to work. Some examples
#   include tool path, device name, project name, device family name. 
# ==============================================================================

def execute(*code):
    '''
    This method prints out the inputted command before executing it. The
    parameter is a variable list of strings that will be separated by spaces
    within the method. If a bad return code is seen on execution, this entire
    script will exit with that error code.
    '''
    #format the command with spaces between each passed-in string
    code_line = ''
    for c in code:
        code_line = code_line + c + ' '
    #print command to console
    print(code_line)
    #execute the command
    rc = os.system(code_line)
    #immediately stop script upon a bad return code
    if(rc):
        exit(rc)

#path to the tool's executable (can be blank if the tool is already in the PATH)
TOOL_PATH = ""

#fake device name, but can be useful to be defined or to be set in command-line
DEVICE = "A2CG1099-1"

#the project will reside in a folder the same name as this block's folder
PROJECT = os.path.basename(os.getcwd())

# === Handle command-line arguments ============================================
#   Create custom command-line arguments to handle specific workflows and common
#   usage cases.
# ==============================================================================

#keep all arguments except the first one (the filepath is not needed)
args = sys.argv[1:]

#detect what workflow to perform
lint = args.count('-lint')
synthesize = args.count('-synth')
simulate = args.count('-sim')
route = args.count('-route')

#identify if there are any generics set on command-line
generics = {}
if(args.count('-gen')):
    start_i = args.index('-gen')
    #iterate through remaining arguments to capture generic value sets
    for i in range(start_i+1, len(args)):
        #split by '=' sign
        if(args[i].count('=') == 1):
            name,value = args[i].split('=')
            generics[name] = value

# === Collect data from the recipe file ========================================
#   This part will gather the necessary data we want for our workflow so that
#   we can act accordingly on that data to get the ouptut we want.
# ==============================================================================

#enter the 'build' directory for this is where the recipe file is located
os.chdir('build')

src_files = {'VHDL' : [], 'VLOG' : []}
sim_files = {'VHDL' : [], 'VLOG' : []}
lib_files = {'VHDL' : {}, 'VLOG' : {}}
top_design = top_testbench = None
python_vector_script = None
pin_assignments = {}

#read the contents of the recipe file
with open('recipe', 'r') as recipe:
    lines = recipe.readlines()
    for rule in lines:
        parsed = rule.split()
        #label is always first item
        label = parsed[0]
        #filepath is always last item
        filepath = parsed[-1]

        #add VHDL source files
        if(label == "@VHDL-SRC"):
            src_files['VHDL'].append(filepath)

        #add VHDL simulation files
        elif(label == "@VHDL-SIM"):
            sim_files['VHDL'].append(filepath)

        #add VHDL files from libraries
        elif(label == "@VHDL-LIB"):
            lib = parsed[1]
            #create new list to track all files belonging to this library
            if(lib not in lib_files['VHDL'].keys()):
                lib_files['VHDL'][lib] = []

            lib_files['VHDL'][lib].append(filepath)

        #capture the top-level design unit
        elif(label == "@VHDL-SRC-TOP" or label == "@VLOG-SRC-TOP"):
            top_design = parsed[1]

        #capture the top-level testbench unit
        elif(label == "@VHDL-SIM-TOP" or label == "@VLOG-SIM-TOP"):
            top_testbench = parsed[1]

        #add Verilog source files
        elif(label == "@VLOG-SRC"):
            src_files['VLOG'].append(filepath)

        #add Verilog library files
        elif(label == "@VLOG-LIB"):
            lib = parsed[1]
            #create new list to track all files belonging to this library
            if(lib not in lib_files['VLOG'].keys()):
                lib_files['VLOG'][lib] = []

            lib_files['VLOG'][lib].append(filepath)

        #add Verilog simulation files
        elif(label == "@VLOG-SIM"):
            sim_files['VLOG'].append(filepath)

        #custom label: capture information regarding pin assignments
        elif(label == "@PIN-PLAN"):
            #write a custom file parser for these special files we designed to
            # extract pin information
            with open(filepath) as pin_file:
                locations = pin_file.readlines()
                for spot in locations:
                    #skip any comment lines indicated by '#'
                    comment_index = spot.find('#')
                    if(comment_index > -1):
                        spot = spot[:comment_index]
                    #separate by the comma
                    if(spot.count(',') != 1):
                        continue
                    #organize into fpga pin and port name
                    pin,name = spot.split(',')
                    pin_assignments[pin.strip()] = name.strip()

        #custom label: capture the python test vector script if avaialable
        elif(label == "@PY-MODEL"):
            python_vector_script = filepath.strip()

    #done collecting data for our workflow
    recipe.close()

# === Act on the collected data ================================================
#   Now that we have the 'ingredients', write some logic to call your tool
#   based on the data we collected. One example could be to use the collected
#   data to write a TCL script, and then call your EDA tool to use that TCL
#   script.
# ==============================================================================

#simulation
if(simulate):    
    if(top_testbench == None):
        exit("Error: No top level testbench found.")
    #format generics for as a command-line argument for test vector script
    generics_command = ''
    for g,v in generics.items():
        generics_command += '-'+g+'='+v+' '
    #call test vector generator first with passing generics into script
    if(python_vector_script):
        execute('python',python_vector_script,generics_command)

    execute(TOOL_PATH+"echo","Simulating design with tesbench...")
    print('---RUNNING SIMULATION---')
    print('TOP:',top_testbench)
    #print out any generics we set on command-line
    if(len(generics)):
        print('GENERICS SET:',)
        for g,v in generics.items():
            print(g,'=',v)
    pass
#routing/fit/implementation
elif(route):
    execute(TOOL_PATH+"echo","Routing design to pins...")
    print("----PINS ALLOCATED-----")
    for pin,port in pin_assignments.items():
        print(pin,'-->',port)
    pass
#synthesis
elif(synthesize):
    if(top_design == None):
        exit("Error: No top level design found.")
    execute(TOOL_PATH+"echo","Synthesizing design...")
    print('---FILES SYNTHESIZED---')
    print("TOP:",top_design)
    #print out any generics we set on command-line
    if(len(generics)):
        print('GENERICS SET:',)
        for g,v in generics.items():
            print(g,'=',v)
    #print all files being synthesized
    for l in src_files.keys():
        for f in src_files[l]:
            print(l,f)
    #print all files from libraries (external from project)
    for f_type in lib_files.keys():
        for lib in lib_files[f_type].keys():
            for f in lib_files[f_type][lib]:
                print(f_type,lib,f)
    pass
#syntax checking
elif(lint):
    execute(TOOL_PATH+"echo","Checking design syntax...")
    print("---FILES ANALYZED----")
    #print souce files being analyzed
    for l in src_files.keys():
        for f in src_files[l]:
            print(l,f)
    #print simulation fies being analyzed
    for l in sim_files.keys():
        for f in sim_files[l]:
            print(l,f)
    pass
#no action
else:
    exit("Error: No flow was recognized! Try one of the following: -lint, \
-synth, -route, -sim.")
""")
            pass

        if(importing):
            cls.importProfile("default")
        pass