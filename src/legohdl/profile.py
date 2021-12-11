# ------------------------------------------------------------------------------
# Project: legohdl
# Script: profile.py
# Author: Chase Ruskin
# Description:
#   The Profile class. A Profile object can have legohdl settings, template,
#   and/or plugins that can be maintained and imported. They are mainly used
#   to save certain setting configurations (loadouts) and share settings across
#   users.
# ------------------------------------------------------------------------------

import os,shutil,copy,glob
import logging as log
from .git import Git
from .map import Map
from .apparatus import Apparatus as apt
from .cfgfile import CfgFile as cfg


class Profile:

    #store dictionary of all Profile objs
    Jar = Map()

    LastImport = None

    DIR = apt.fs(apt.HIDDEN+"profiles/")
    EXT = ".prfl"
    LOG_FILE = "import.log"


    def __init__(self, name, url=None):
        '''
        Creates a Profile instance. If creating from a url, the `name` parameter
        will be ignored and the `name` will equal the filename of the .prfl.

        Parameters:
            name (str): profile's name
            url (str): optionally a profile url to create a profile from
        Returns:
            None
        '''
        self._success = True
        if(url != None):
            self._success = self.loadFromURL(url)
        else:
            #set profile's name
            self._name = name

            #create profile directory if DNE
            os.makedirs(self.getProfileDir(), exist_ok=True)
            #create profile marker file if DNE
            if(os.path.exists(self.getProfileDir()+self.getName()+self.EXT) == False):
                open(self.getProfileDir()+self.getName()+self.EXT, 'w').close()
            
            #create git repository
            self._repo = Git(self.getProfileDir())
        
        #add to the catalog
        if(self._success):
            self.Jar[self.getName()] = self
        pass


    def successful(self):
        '''Returns True if a profile was successfully initialized.'''
        return self._success

    
    def loadFromURL(self, url):
        '''
        Attempts to load/add a profile from an external path/url. Will not add
        if the path is not a non-empty git repository, does not have .prfl, or
        the profile name is already taken.

        Parameters:
            url (str): the external path/url that is a profile to be added
        Returns:
            success (bool): if the profile was successfully add to profiles/ dir
        '''
        success = True

        if(Git.isValidRepo(url, True) == False and Git.isValidRepo(url, False) == False):
            log.error("Invalid repository "+url+".")
            return False

        #create temp dir
        os.makedirs(apt.TMP)

        #clone from repository
        if(Git.isBlankRepo(url) == False):
            tmp_repo = Git(apt.TMP, clone=url)

            #determine if a .prfl file exists
            log.info("Locating .prfl file... ")
            files = os.listdir(apt.TMP)
            for f in files:
                prfl_i = f.find(self.EXT)
                if(prfl_i > -1):
                    #remove extension to get the profile's name
                    self._name = f[:prfl_i]
                    log.info("Identified profile "+self.getName())
                    break
            else:
                log.error("Invalid profile; could not locate .prfl file.")
                success = False

            #try to add profile if found a name (.prfl file)
            if(hasattr(self, '_name')):
                #do not add to profiles if name is already in use
                if(self.getName().lower() in self.Jar.keys()):
                    log.error("Cannot add profile "+self.getName()+" due to name conflict.")
                    success = False
                #add to profiles folder
                else:
                    log.info("Adding profile "+self.getName()+"...")
                    self._repo = Git(self.getProfileDir(), clone=apt.TMP)
                    #assign the correct remote url to the profile
                    self._repo.setRemoteURL(tmp_repo.getRemoteURL())
        else:
            log.error("Cannot load profile from empty repository.")
            success = False

        #clean up temp dir
        shutil.rmtree(apt.TMP, onerror=apt.rmReadOnly)
        return success


    def importLoadout(self, ask=False):
        '''
        Load settings, template and/or plugins into legohdl from the profile.

        Parameters:
            ask (bool): explicitly prompt user at each stage in the process
        Returns:
            None
        '''


        def deepMerge(src, dest, setting="", plugins_only=False):
            '''
            Merge all values found in src to override destination into a modified
            dictionary.

            Parameters:
                src (dict): multi-level dictionary to grab values from
                dest (dict): multi-level dictionary to append values in
                plugins_only (bool): only add in plugin settings
            Returns:
                dest (dict): the modified dictionary with new overridden values
            '''
            for k,v in src.items():
                next_level = setting
                isHeader = isinstance(v, dict)
                if(setting == ""):
                    next_level = cfg.HEADER[0]+k+cfg.HEADER[1]+" " if(isHeader) else k
                else:
                    if(isHeader):
                        next_level = next_level + cfg.HEADER[0] + k + cfg.HEADER[1]+" "
                    else:
                        next_level = next_level + k
                #print(next_level)
                #only proceed when importing just plugins
                if(plugins_only and next_level.startswith(cfg.HEADER[0]+'plugin'+cfg.HEADER[1]) == 0):
                    continue
                #skip plugins if not explicitly set in argument
                elif(plugins_only == False and next_level.startswith(cfg.HEADER[0]+'plugin'+cfg.HEADER[1]) == 1):
                    continue
                #go even deeper into the dictionary tree
                if(isinstance(v, dict)):
                    if(k not in dest.keys()):
                        dest[k] = dict()
                        #log.info("Creating new dictionary "+k+" under "+next_level+"...")
                    deepMerge(v, dest[k], setting=next_level, plugins_only=plugins_only)
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
                                #find replace all parts of string with ENV_NAME
                                if(isinstance(v,str)):
                                    v = v.replace(apt.ENV_NAME, apt.HIDDEN[:len(apt.HIDDEN)-1])
                                if(i not in dest[k]):
                                    dest[k] += [i]
                    #otherwise normal overwrite
                    else:
                        if(isinstance(v,str)):
                            v = os.path.expandvars(v)
                        #do not allow a null value to overwrite an already established value
                        if(k in dest.keys() and v == cfg.NULL):
                            continue
                        dest[k] = v
                    #print to console the overloaded settings
                    log.info(next_level+" = "+str(v))
            return dest

        #set env variable
        os.environ["LEGOHDL_PRFL"] = self.getProfileDir()[:len(self.getProfileDir())-1]

        log.info("Importing profile "+self.getName()+"...")
        #overload available settings
        if(self.hasSettings()):
            act = (ask == False) or apt.confirmation("Import "+apt.SETTINGS_FILE+"?", warning=False)
            if(act):
                log.info('Overloading '+apt.SETTINGS_FILE+'...')
                with open(self.getProfileDir()+apt.SETTINGS_FILE, 'r') as f:
                    prfl_settings = cfg.load(f)
                    
                    dest_settings = copy.deepcopy(apt.SETTINGS)
                    dest_settings = deepMerge(prfl_settings, dest_settings)
                    apt.SETTINGS = dest_settings
            pass
        #copy in template folder
        if(self.hasTemplate()):
            act = (ask == False) or apt.confirmation("Import template?", warning=False)
            if(act):
                log.info('Importing template...')
                shutil.rmtree(apt.HIDDEN+"template/",onerror=apt.rmReadOnly)
                shutil.copytree(self.getProfileDir()+"template/", apt.HIDDEN+"template/")
            pass
        #copy in plugins
        if(self.hasPlugins()):
            act = (ask == False) or apt.confirmation("Import plugins?", warning=False)
            if(act):
                log.info('Importing plugins...')
                plugins = os.listdir(self.getProfileDir()+'plugins/')
                for scp in plugins:
                    log.info("Copying "+scp+" to built-in plugins folder...")
                    if(os.path.isfile(self.getProfileDir()+'plugins/'+scp)):
                        #copy contents into built-in plugin folder
                        prfl_plugin = open(self.getProfileDir()+'plugins/'+scp, 'r')
                        copied_plugin = open(apt.HIDDEN+'plugins/'+scp, 'w')
                        #transfer file data via writing it to file
                        plugin_data = prfl_plugin.readlines()
                        copied_plugin.writelines(plugin_data)
                        #close files
                        prfl_plugin.close()
                        copied_plugin.close()
                        pass
                    pass
                if(self.hasSettings()):
                    log.info('Overloading plugins in '+apt.SETTINGS_FILE+'...')
                    with open(self.getProfileDir()+apt.SETTINGS_FILE, 'r') as f:
                        prfl_settings = cfg.load(f)
                        dest_settings = copy.deepcopy(apt.SETTINGS)
                        dest_settings = deepMerge(prfl_settings, dest_settings, plugins_only=True)
                        apt.SETTINGS = dest_settings
            pass
        #write to log file
        with open(self.DIR+self.LOG_FILE, 'w') as f:
            f.write(self.getName())
        #save all modifications to legohdl settings
        apt.save()
        pass

    
    def readAbout(self):
        '''
        Gets the text within the .prfl file to be printed to the console.

        Parameters:
            None
        Returns:
            (str): text from .prfl file
        '''
        about_txt = ''
        with open(self.getProfileDir()+self.getName()+self.EXT, 'r') as prfl:
            for line in prfl.readlines():
                about_txt = about_txt + line
        return about_txt


    def refresh(self, quiet=False):
        '''
        If has a remote repository, checks with it to ensure the current branch
        is up-to-date and pulls any changes.
        
        Parameters:
            quiet (bool): determine if to display information to user or keep quiet
        Returns:
            None
        '''
        if(self._repo.remoteExists()):
            log.info("Refreshing profile "+self.getName()+"...")
            #check status from remote
            up2date, connected = self._repo.isLatest()
            if(connected == False):
                return
            if(up2date == False):
                log.info('Pulling new updates...')
                self._repo.pull()
                log.info("success")
            else:
                log.info("Already up-to-date.")
        elif(quiet == False):
            log.info("Profile "+self.getName()+" is local and does not require refresh.")
        pass


    @classmethod
    def reloadDefault(cls, importing=False):
        if('default' in cls.Jar.keys()):
            cls.Jar['default'].remove()
        log.info("Reloading default profile...")
        default = Profile("default")

        def_settings = dict()
        def_settings['plugin'] = \
        {
            'hello'  : 'python '+apt.ENV_NAME+'/plugins/hello_world.py',
        }
        def_settings['workspace'] = dict()
        def_settings['workspace']['primary'] = {'path' : None, 'vendors' : None}
        #create default legohdl.cfg
        with open(default.getProfileDir()+apt.SETTINGS_FILE, 'w') as f:
            cfg.save(def_settings, f)
            pass

        #create default template
        os.makedirs(default.getProfileDir()+"template/")
        os.makedirs(default.getProfileDir()+"template/src")
        os.makedirs(default.getProfileDir()+"template/test")
        os.makedirs(default.getProfileDir()+"template/constr")
        #create readme
        with open(default.getProfileDir()+'template/README.md', 'w') as f:
            f.write("# %BLOCK%")
            pass
        #create .gitignore
        with open(default.getProfileDir()+'template/.gitignore', 'w') as f:
            f.write("build/")
            pass

        #create template design
        with open(default.getProfileDir()+'template/src/TEMPLATE.vhd', 'w') as f:
            f.write('-- code here')
            pass

        #create default plugins
        os.makedirs(default.getProfileDir()+"plugins/")
        shutil.copyfile(apt.getProgramPath()+"data/hello.py", default.getProfileDir()+"plugins/hello.py")

        if(importing):
            default.importLoadout()
        Profile.save()
        pass


    def remove(self):
        '''
        Deletes the profile from the Jar and its directory.

        Parameters:
            None
        Returns:
            None
        '''
        log.info("Deleting profile "+self.getName()+"...")
        #remove profile dir
        shutil.rmtree(self.getProfileDir(), onerror=apt.rmReadOnly)
        #remove from Jar
        del self.Jar[self.getName()]
        pass


    @classmethod
    def tidy(cls):
        '''
        Remove any stale profiles from the profiles/ directory. A stale profile
        is one that is not listed in the settings and therefore not stored in the Jar.

        Parameters:
            None
        Returns:
            None
        '''
        #list all profiles
        prfl_files = glob.glob(cls.DIR+"**/*"+cls.EXT, recursive=True)
        for f in prfl_files:
            prfl_name = os.path.basename(f).replace(cls.EXT,'')
            #remove a profile that is not found in settings (Jar class container)
            if(prfl_name.lower() not in cls.Jar.keys()):
                log.info("Removing stale profile "+prfl_name+"...")
                prfl_dir = f.replace(os.path.basename(f),'')

                shutil.rmtree(prfl_dir, onerror=apt.rmReadOnly)
            pass
        pass


    def setName(self, n):
        '''
        Change the profile's name if the name is not already taken.

        Parameters:
            n (str): new name for profile
        Returns:
            (bool): true if name successfully altered and updated in Jar
        '''
        if(n == '' or n == None):
            log.error("Profile name cannot be empty.")
            return False

        #cannot name change if the name already exists
        if(n.lower() in self.Jar.keys()):
            log.error("Cannot change profile name to "+n+" due to name conflict.")
            return False
        #change is okay to occur
        log.info("Renaming profile "+self.getName()+" to "+n+"...")
        #delete the old value in Jar
        if(self.getName().lower() in self.Jar.keys()):
            del self.Jar[self.getName()]

        #rename the prfl file
        os.rename(self.getProfileDir()+self.getName()+self.EXT, self.getProfileDir()+n+self.EXT)
        new_prfl_dir = apt.fs(self.DIR+n)
        #rename the profile directory
        os.rename(self.getProfileDir(), new_prfl_dir)

        #update the import log if the name was the previous name
        if(self.ReadLastImport() == self):
                with open(self.DIR+self.LOG_FILE, 'w') as f:
                    f.write(n)

        #update attibute
        self._name = n
        #update the Jar
        self.Jar[self.getName()] = self
        pass


    @classmethod
    def load(cls):
        '''Load profiles from settings.'''

        prfls = apt.SETTINGS['general']['profiles']
        for p in prfls:
            Profile(p)
        pass


    @classmethod
    def save(cls):
        '''Save profiles to settings.'''

        serialize = []
        for prfl in cls.Jar.values():
            serialize += [prfl.getName()]
        apt.SETTINGS['general']['profiles'] = serialize
        apt.save()
        pass


    @classmethod
    def printList(cls, check_updates=False):
        '''
        Prints formatted list for profiles and indicates what is available in each one.

        Parameters:
            check_updates (bool): determine if to check with remotes if latest commits
        Returns:
            None
        '''
        last_prfl = cls.ReadLastImport()
        # :todo: also indicate if an update is available
        print('{:<16}'.format("Profile"),'{:<12}'.format("Last Import"),'{:<16}'.format(apt.SETTINGS_FILE),'{:<12}'.format("template/"),'{:<12}'.format("plugins/"))
        print("-"*16+" "+"-"*12+" "+"-"*16+" "+"-"*12+" "+"-"*12)
        for prfl in cls.Jar.values():
            #check remote repository if it is the latest commits locally
            if(check_updates):
                print(prfl.getName()+" has update? ",end='')
                print(str(not prfl._repo.isLatest()[0]))
            #collect information about each profile
            last_import = 'yes' if(last_prfl == prfl) else '-'
            has_template = 'yes' if(prfl.hasTemplate()) else '-'
            has_plugins = 'yes' if(prfl.hasPlugins()) else '-'
            has_settings = 'yes' if(prfl.hasSettings()) else '-'   
            #print the information in a nice format to the console            
            print('{:<16}'.format(prfl.getName()),'{:<12}'.format(last_import),'{:<16}'.format(has_settings),'{:<12}'.format(has_template),'{:<12}'.format(has_plugins))
            pass


    @classmethod
    def ReadLastImport(cls):
        '''
        Read from import.log the name of the last used profile is, if exists.
        Sets the class atribute LastImport Profile obj.

        Parameters:
            None
        Returns:
            cls.LastImport (Profile): the profile obj last used to import
        '''
        #open the import.log
        with open(cls.DIR+cls.LOG_FILE, 'r') as f:
            #read the profile's name
            prfl_name = f.readline().strip()
            #return that profile obj if the name is found in the Jar
            if(prfl_name.lower() in cls.Jar.keys()):
                #set the found profile obj as last import
                cls.LastImport = cls.Jar[prfl_name]

        return cls.LastImport


    def getName(self):
        return self._name


    def getProfileDir(self):
        return apt.fs(self.DIR+self.getName())


    def hasTemplate(self):
        return os.path.exists(self.getProfileDir()+"template/")


    def hasPlugins(self):
        return os.path.exists(self.getProfileDir()+"plugins/")


    def hasSettings(self):
        return os.path.exists(self.getProfileDir()+apt.SETTINGS_FILE)

    
    def isLastImport(self):
        return self == self.LastImport


    # uncomment to use for debugging
    # def __str__(self):
    #     return f'''
    #     ID: {hex(id(self))}
    #     Name: {self.getName()}
    #     Imported Last: {self.isLastImport()}
    #     settings: {self.hasSettings()}
    #     template: {self.hasTemplate()}
    #     plugins: {self.hasPlugins()}
    #         repo: {self._repo}
    #     '''


    pass