################################################################################
#   Project: legohdl
#   Script: apparatus.py
#   Author: Chase Ruskin
#   Description:
#       This script is used to hold the legohdl settings. It includes code for 
#   safety measures to ensure the proper settings exits, as well as helper
#   functions that are used throughout other scripts.
################################################################################

from posixpath import basename
import yaml,stat,glob,git
from datetime import datetime
import logging as log
from subprocess import check_output
import os,shutil,copy,platform


class Apparatus:
    SETTINGS = dict()

    #path to hidden legohdl folder
    HIDDEN = os.path.expanduser("~/.legohdl/")

    #identify a valid block project within the framework
    MARKER = "Block.lock"

    #identify a valid market and its name
    MRKT_EXT = ".mrkt"
    #identify a valid profile and its name
    PRFL_EXT = ".prfl"

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

        #create bare settings.yml if DNE
        if(not os.path.isfile(cls.HIDDEN+"settings.yml")):
            settings_file = open(cls.HIDDEN+"settings.yml", 'w')
            structure = ''
            for opt in cls.OPTIONS:
                structure = structure + opt
                if(opt == 'label'):
                    structure = structure + ":\n  recursive: {}\n"
                    structure = structure + "  shallow: {}\n"
                else:
                    structure = structure + ": null\n"

            settings_file.write(structure)
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
    def generateDefault(cls, t, *args):
        for a in args:
            if(isinstance(cls.SETTINGS[a], t) == False):
                if(t == dict):
                    cls.SETTINGS[a] = {}
                elif(t == bool):
                    cls.SETTINGS[a] = False
                elif(t == int):
                    cls.SETTINGS[a] = 0
                elif(t == list):
                    cls.SETTINGS[a] = []

    @classmethod
    def load(cls):
        log.basicConfig(format='%(levelname)s:\t%(message)s', level=log.INFO)
        #ensure all necessary hidden folder structures exist
        ask_for_setup = cls.initialize()

        #load dictionary data in variable
        with open(cls.HIDDEN+"settings.yml", "r") as file:
            cls.SETTINGS = yaml.load(file, Loader=yaml.FullLoader)
        #create any missing options
        for opt in cls.OPTIONS:
            if(opt not in cls.SETTINGS.keys()):
                cls.SETTINGS[opt] = None
            #make sure label section is set up correctly
            if(opt == 'label'):
                if(cls.SETTINGS[opt] == None):
                    cls.SETTINGS[opt] = dict()
                if('recursive' not in cls.SETTINGS[opt].keys() or \
                    isinstance(cls.SETTINGS[opt]['recursive'], dict) == False):
                    cls.SETTINGS[opt]['recursive'] = {}
                if('shallow' not in cls.SETTINGS[opt].keys() or \
                    isinstance(cls.SETTINGS[opt]['shallow'], dict) == False):
                    cls.SETTINGS[opt]['shallow'] = {}

        #ensure all pieces of settings are correct
        cls.generateDefault(dict,"market","script","workspace")
        cls.generateDefault(bool,"multi-develop","overlap-recursive")
        cls.generateDefault(int,"refresh-rate")
        cls.generateDefault(list,"profiles")

        #run setup here
        if(ask_for_setup):
            cls.runSetup()

        #ensure all pieces of settings are correct
        cls.generateDefault(dict,"market","script","workspace")
        cls.generateDefault(bool,"multi-develop","overlap-recursive")
        cls.generateDefault(int,"refresh-rate")
        cls.generateDefault(list,"profiles")

        if(cls.SETTINGS['refresh-rate'] > cls.MAX_RATE):
            cls.SETTINGS['refresh-rate'] = cls.MAX_RATE
        elif(cls.SETTINGS['refresh-rate'] < cls.MIN_RATE):
            cls.SETTINGS['refresh-rate'] = cls.MIN_RATE

        cls.dynamicProfiles()
        cls.dynamicWorkspace()
        cls.dynamicMarkets()

        #determine current workspace currently being used
        cls.__active_workspace = cls.SETTINGS['active-workspace']

        if(not cls.inWorkspace()):
            log.warning("Active workspace not found!")
            return

        if(cls.SETTINGS['template'] != None and os.path.isdir(cls.SETTINGS['template'])):
            cls.SETTINGS['template'] = cls.fs(cls.SETTINGS['template'])
            cls.TEMPLATE = cls.SETTINGS['template']
            pass
        
        if(cls.getLocal() == None):
            log.error("Please specify a workspace path for "\
                +cls.SETTINGS['active-workspace']\
                +". See \'legohdl help config\' for more details.")
            cls.SETTINGS['active-workspace'] = None
            return

        cls.WORKSPACE = cls.WORKSPACE+cls.SETTINGS['active-workspace']+"/"

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
        settings. Key can be 'local' or 'market'.
        '''
        if(not modify):
            return cls.SETTINGS['workspace'][cls.SETTINGS['active-workspace']][key]
        else:
            cls.SETTINGS['workspace'][cls.SETTINGS['active-workspace']][key] = value
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
    def dynamicProfiles(cls):
        #identify valid profiles in the hidden direcotory
        found_prfls = cls.getProfiles()
        #identify potential profiles in the setting.yml
        listed_prfls = cls.SETTINGS['profiles']
        #target deletions
        for prfl in found_prfls:
            if(prfl not in listed_prfls):
                shutil.rmtree(cls.getProfiles()[prfl])
        
        #target additions
        for prfl in listed_prfls:
            if(prfl not in found_prfls):
                log.info("Creating empty profile "+prfl+"...")
                os.makedirs(cls.HIDDEN+"profiles/"+prfl, exist_ok=True)
                with open(cls.HIDDEN+"profiles/"+prfl+"/"+prfl+cls.PRFL_EXT, 'w'):
                    pass
        pass

    #automatically set market names to lower-case, and prompt user to settle duplicate keys
    @classmethod
    def dynamicMarkets(cls):
        true_case = {}
        tmp_dict = {}
        for mrkt in cls.SETTINGS['market'].keys():
            lower_mrkt = mrkt.lower()
            replace = True
            if(lower_mrkt in tmp_dict.keys()):
                log.warning("Duplicate market names have been detected; which one do you want to keep?")
                print('1)',true_case[lower_mrkt],':',tmp_dict[lower_mrkt])
                print('2)',mrkt,':',cls.SETTINGS['market'][mrkt])
                resp = None

                while True:
                    resp = input()
                    opt_1 = resp == '1' or resp == true_case[lower_mrkt]
                    opt_2 = resp == '2' or resp == mrkt
                    if(opt_2):
                        tmp_dict[lower_mrkt] = cls.SETTINGS['market'][mrkt]
                        if(os.path.exists(cls.MARKETS+true_case[lower_mrkt])):
                            shutil.rmtree(cls.MARKETS+true_case[lower_mrkt],onerror=cls.rmReadOnly)
                    else:
                        if(os.path.exists(cls.MARKETS+mrkt)):
                            shutil.rmtree(cls.MARKETS+mrkt,onerror=cls.rmReadOnly)
                        replace = False
                    if(opt_1 or opt_2):
                        break
            else:   
                tmp_dict[lower_mrkt] = cls.SETTINGS['market'][mrkt]
            
            if(replace):
                true_case[lower_mrkt] = mrkt

        for mrkt_low in true_case.keys():
            if(mrkt_low in tmp_dict.keys()):
                cls.SETTINGS['market'][true_case[mrkt_low]] = tmp_dict[mrkt_low]
        
        #cls.SETTINGS['market'] = tmp_dict
    
    #automatically create local paths for workspaces or delete hidden folders
    @classmethod
    def dynamicWorkspace(cls):
        acting_ws = cls.SETTINGS['active-workspace']
        for ws,val in cls.SETTINGS['workspace'].items():
            if(isinstance(val, dict) == False):
                val = dict()
                cls.SETTINGS['workspace'][ws] = dict()
            if('local' not in val.keys() or isinstance(val['local'],str) == False):
                val['local'] = None
                cls.SETTINGS['workspace'][ws]['local'] = None
            if('market' not in val.keys() or isinstance(val['market'],list) == False):
                val['market'] = list()
                cls.SETTINGS['workspace'][ws]['market'] = list()
            cls.initializeWorkspace(ws, cls.fs(val['local']))

        ws_dirs = os.listdir(cls.HIDDEN+"workspaces/")
        #remove any hidden workspace folders that are no longer in the settings.yml
        for ws in ws_dirs:
            if(ws not in cls.SETTINGS['workspace'].keys()):
                #delete if found a directory type
                if(os.path.isdir(cls.HIDDEN+"workspaces/"+ws)):
                    shutil.rmtree(cls.HIDDEN+"workspaces/"+ws, onerror=cls.rmReadOnly)
                #delete if found a file type
                else:
                    os.remove(cls.HIDDEN+"workspaces/"+ws)

        if(acting_ws != None):
            cls.SETTINGS['active-workspace'] = acting_ws
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
        cls.__active_workspace = cls.SETTINGS['active-workspace']
        if(cls.__active_workspace == None or cls.__active_workspace not in cls.SETTINGS['workspace'].keys() or \
           os.path.isdir(cls.HIDDEN+"workspaces/"+cls.__active_workspace) == False):
            return False
        else:
            return True

    #determines if value is an existing profile or a path to a new profile to be copied in
    #will stage the profile into the correct place
    @classmethod
    def loadProfile(cls, value, explicit=False):
        prfl_dir = cls.HIDDEN+"profiles/"
        tmp_dir = cls.HIDDEN+"tmp/"
        #get all available profiles
        profiles = cls.getProfiles()
        sel_prfl = None
        #see if this is a profile that already exists
        if(value in profiles):
            sel_prfl = value
            log.info("Loading existing profile "+sel_prfl+"...")
        else:
            value = cls.fs(value)
            #clone the repository and see if it is a valid profile
            log.info("Grabbing profile from... "+value)
            if(cls.isValidURL(value)):
                os.makedirs(tmp_dir)
                git.Git(tmp_dir).clone(value)
                url_name = value[value.rfind('/')+1:value.rfind('.git')]
                path_to_check = cls.fs(tmp_dir+url_name)
            #check if the path is a local directory
            elif(os.path.isdir(value)):
                path_prts = value.strip('/').split('/')
                url_name = path_prts[len(path_prts)-1]
                path_to_check = value
                pass
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
                log.error("Invalid profile; no .prfl file found")
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
        cls.importProfile(sel_prfl, explicit=explicit)
        return True

    #perform backend operation to overload settings, template, and scripts
    @classmethod
    def importProfile(cls, prfl_name, explicit=False):
        with open(cls.HIDDEN+"profiles/"+cls.PRFL_LOG, 'w') as f:
            f.write(prfl_name)
        if(prfl_name not in cls.SETTINGS['profiles']):
            cls.SETTINGS['profiles'] += [prfl_name]
        #merge all values found in src override dest into a new dictionary
        def deepMerge(src, dest, setting=""):
            for k,v in src.items():
                next_level = setting
                if(setting == ""):
                    next_level = k
                else:
                    next_level = next_level + ":" + k

                #go even deeper into the dictionary tree
                if(isinstance(v, dict)):
                    if(k not in dest.keys()):
                        dest[k] = dict()
                        #log.info("Creating new dictionary "+k+" under "+next_level+"...")
                    deepMerge(v, dest[k], setting=next_level)
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
                                dest[k] += [i]
                    #otherwise normal overwrite
                    else:
                        if(isinstance(v,str)):
                            v = v.replace("%LEGOHDL%", cls.HIDDEN[:len(cls.HIDDEN)-1])
                        #do not allow a null workspace path to overwrite an already established workspace path
                        if(k in dest.keys() and k == 'local' and v == None):
                            continue
                        dest[k] = v
                    log.info(next_level+" = "+str(v))
            return dest

        prfl_path = cls.getProfiles()[prfl_name]
        #overload available settings
        if(cls.isInProfile(prfl_name, 'settings.yml')):
            act = not explicit or cls.confirmation("Import settings.yml?", warning=False)
            if(act):
                log.info('Overloading settings.yml...')
                with open(prfl_path+'settings.yml', 'r') as f:
                    prfl_settings = yaml.load(f, Loader=yaml.FullLoader)
                    
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
            log.error("Profile "+name+" does not exist.")
            pass

        if(reload_default):
            log.info("Reloading default profile...")
            cls.loadDefaultProfile(importing=False)
        pass
    
    @classmethod
    def isInProfile(cls, name, loc):
        if(name in cls.getProfiles()):
            if(loc == 'settings.yml'):
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
        if(ws_path == None):
            ws_path = input("Enter workspace "+name+"'s path: ")
            while(len(ws_path) <= 0):
                ws_path = input()

        cls.SETTINGS['workspace'][name]['local'] = cls.fs(ws_path)
        local_path = cls.SETTINGS['workspace'][name]['local']
        
        if(os.path.exists(local_path) == False):
            log.info("Creating new path... "+local_path)
            os.makedirs(local_path)

        #create YAML structure for workspace settings 'local' and 'market'
        if(name not in cls.SETTINGS['workspace'].keys()):
            cls.SETTINGS['workspace'][name] = {'local' : local_path, 'market' : None}
        #make sure market is a list
        if(isinstance(cls.SETTINGS['workspace'][name]['market'],list) == False):
            cls.SETTINGS['workspace'][name]['market'] = []
        #make sure local is a string 
        if(isinstance(cls.SETTINGS['workspace'][name]['local'],str) == False):
            cls.SETTINGS['workspace'][name]['local'] = None

        #cannot be active workspace if a workspace path is null
        if(cls.SETTINGS['workspace'][name]['local'] == None and cls.__active_workspace == name):
            cls.__active_workspace = None
            return

        #if no active-workspace then set it as active
        if(not cls.inWorkspace()):
            cls.SETTINGS['active-workspace'] = name
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
        rate = cls.SETTINGS['refresh-rate']
        
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
        with open(cls.HIDDEN+"settings.yml", "w") as file:
            for key in cls.OPTIONS:
                #pop off front key/val pair of yaml data
                single_dict = {}
                single_dict[key] = cls.SETTINGS[key]

                if(key == 'author'):
                    file.write("#general configurations\n")
                elif(key == 'overlap-recursive'):
                    file.write("#label configurations\n")
                elif(key == 'script'):
                    file.write("#script configurations\n")
                elif(key == 'active-workspace'):
                    file.write("#workspace configurations\n")
                elif(key == 'refresh-rate'):
                    file.write("#market configurations\n")

                yaml.dump(single_dict, file)
                pass
            pass
        pass

    @classmethod
    def getLocal(cls):
        if(cls.inWorkspace()):
            return cls.fs(cls.SETTINGS['workspace'][cls.__active_workspace]['local'])
        else:
            return ''

    #return the block file metadata from a specific version tag already includes 'v'
    #if returned none then it is an invalid legohdl release point
    @classmethod
    def getBlockFile(cls, repo, tag, path="./", in_branch=True):
        #checkout repo to the version tag and dump yaml file
        repo.git.checkout(tag+cls.TAG_ID)
        #find Block.lock
        if(os.path.isfile(path+cls.MARKER) == False):
            #return None if Block.lock DNE at this tag
            log.warning("Version "+tag+" does not contain a Block.lock file. Invalid version.")
            meta = None
        #Block.lock exists so read its contents
        else:
            log.info("Identified valid version "+tag)
            with open(path+cls.MARKER, 'r') as f:
                meta = yaml.load(f, Loader=yaml.FullLoader)

        #revert back to latest release
        if(in_branch == True):
            #in a branch so switch back
            repo.git.switch('-')
        #in a single branch (cache) so checkout back
        else:
            repo.git.checkout('-')
        #perform additional safety measure that this tag matches the 'version' found in meta
        if(meta['version'] != tag[1:]):
            log.error("Block.lock file version does not match for: "+tag+". Invalid version.")
            meta = None
        return meta

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
            for name in cls.getWorkspace('market'):
                #must be case-matching between workspace market list and entire market list
                if(name in cls.SETTINGS['market'].keys()):
                    #store its root (location/path, aka is it remote or only local)
                    mrkt_roots[name.lower()] = cls.SETTINGS['market'][name]
                #this market DNE as any market!
                else:
                    cls.getWorkspace('market').remove(name)
                cls.save()
        elif(cls.inWorkspace()):
            for name in cls.SETTINGS['market'].keys():
                #store its root (location/path, aka is it remote or only local)
                mrkt_roots[name] = cls.SETTINGS['market'][name]

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
            if(name.lower() in cls._mrkt_map.keys()):
                cls.resolveMarketConflict(cls._mrkt_map[name.lower()], name)
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

    #returns true if the current workspace has some markets listed
    @classmethod
    def linkedMarket(cls):
        rem = cls.SETTINGS['workspace'][cls.__active_workspace]['market']
        return (rem != None and len(rem))

    #forward-slash fixer
    @classmethod
    def fs(cls, path):
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

    #merge: place1 <- place2 (place2 has precedence)
    @classmethod
    def merge(cls, place1, place2):
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
        func(path)
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
        def_settings['workspace']['primary'] = {'local' : None, 'market' : None}
        #create default settings.yml
        with open(prfl_path+"settings.yml", 'w') as f:
            yaml.dump(def_settings, f)
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
            f.write("""import sys
if(sys.argv.count('uf')):
    print('go gators!')
else:
    print('hello world!')
""")
            pass

        if(importing):
            cls.importProfile("default")
        pass