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

import os,shutil,glob
import logging as log

from .apparatus import Apparatus as apt
from .cfg import Cfg, Section, Key
from .git import Git
from .map import Map


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

            new = (os.path.exists(self.getProfileDir()) == False)

            #create profile directory if DNE
            os.makedirs(self.getProfileDir(), exist_ok=True)
            #create profile marker file if DNE
            if(os.path.exists(self.getProfileDir()+self.getName()+self.EXT) == False):
                open(self.getProfileDir()+self.getName()+self.EXT, 'w').close()

            #create blanks for new profiles
            if(new):
                #add plugins folder
                os.makedirs(self.getProfileDir()+'plugins/', exist_ok=True)
                #add templates folder
                os.makedirs(self.getProfileDir()+'template/', exist_ok=True)
                #add commented out legohdl.cfg file
                c = Cfg(self.getProfileDir()+'legohdl.cfg', data=Section(apt.LAYOUT), comments=apt.getComments())
                c.write(empty=True)
                pass
            
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
        log.info("Importing profile "+self.getName()+"...")
        s_file = self.getProfileDir()+apt.SETTINGS_FILE

        prfl_settings = None
        #load the profile's configured settings
        if(self.hasSettings()):
            prfl_settings = Cfg(s_file, data=Section())
            prfl_settings.read()

        #overload available settings
        if(self.hasSettings()):
            act = (ask == False) or apt.confirmation("Import "+apt.SETTINGS_FILE+"?", warning=False)
            if(act):
                log.info('Overloading '+apt.SETTINGS_FILE+'...')
                #update all keys
                apt.CFG.set('', prfl_settings._data, verbose=True)
            pass

        #copy in template folder
        if(self.hasTemplate()):
            act = (ask == False) or apt.confirmation("Import template?", warning=False)
            if(act):
                log.info('Importing template...')
                shutil.rmtree(apt.HIDDEN+"template/",onerror=apt.rmReadOnly)
                shutil.copytree(self.getProfileDir()+"template/", apt.HIDDEN+"template/")
                #update template key
                if(self.hasSettings()):
                    log.info("Overloading template in "+apt.SETTINGS_FILE+"...")
                    apt.CFG.set('general.template', prfl_settings.get('general.template', dtype=str), verbose=True)
                pass
            pass

        #copy in plugins
        if(self.hasPlugins()):
            act = (ask == False) or apt.confirmation("Import plugins?", warning=False)
            if(act):
                log.info('Importing plugins...')
                plugins = os.listdir(self.getProfileDir()+'plugins/')

                #iterate through everything found in the plugins/ folder
                for plg in plugins:
                    log.info("Copying "+plg+" to built-in plugins folder...")
                    #make sure the plugin path is a file
                    if(os.path.isfile(self.getProfileDir()+'plugins/'+plg)):
                        #copy contents into built-in plugin folder
                        prfl_plugin = open(self.getProfileDir()+'plugins/'+plg, 'r')
                        copied_plugin = open(apt.HIDDEN+'plugins/'+plg, 'w')

                        #transfer file data via writing it to file
                        plugin_data = prfl_plugin.readlines()
                        copied_plugin.writelines(plugin_data)

                        #close files
                        prfl_plugin.close()
                        copied_plugin.close()
                        pass
                    pass
                #update settings for plugins
                if(self.hasSettings()):
                    log.info('Overloading plugins in '+apt.SETTINGS_FILE+'...')
                    #update plugin section
                    apt.CFG.set('plugin', prfl_settings.get('plugin', dtype=Section), verbose=True)
                pass
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
        #remove default from jar to recreate
        if('default' in cls.Jar.keys()):
            cls.Jar['default'].remove()

        #create new default profile
        log.info("Reloading default profile...")
        default = Profile("default")

        #define cfg settings
        def_settings = {
            'plugin' : {
                'hello' : 'python $LEGOHDL/plugins/hello_world.py'
            },
            'workspace' : {
                'primary' : {
                    'path' : '',
                    'vendors' : ''
                }
            }
        }

        #write simple cfg settings
        def_cfg = Cfg(default.getProfileDir()+apt.SETTINGS_FILE, data=Section(def_settings), comments=apt.getComments())
        def_cfg.write()

        #create default template
        os.makedirs(default.getProfileDir()+"template/", exist_ok=True)
        os.makedirs(default.getProfileDir()+"template/src", exist_ok=True)
        os.makedirs(default.getProfileDir()+"template/test", exist_ok=True)

        #create readme
        with open(default.getProfileDir()+'template/README.md', 'w') as f:
            f.write("# __%BLOCK%__")
            pass

        #create .gitignore
        with open(default.getProfileDir()+'template/.gitignore', 'w') as f:
            f.write("build/")
            pass

        #create template design
        with open(default.getProfileDir()+'template/src/TEMPLATE.vhd', 'w') as f:
            f.write('-- design code here')
            pass

        #create template testbench
        with open(default.getProfileDir()+'template/test/TEMPLATE_tb.vhd', 'w') as f:
            f.write('-- testbench code here')
            pass

        #create default plugins
        os.makedirs(default.getProfileDir()+"plugins/", exist_ok=True)
        shutil.copyfile(apt.getProgramPath()+"data/hello.py", default.getProfileDir()+"plugins/hello.py")

        #check if to also import this profile
        if(importing):
            default.importLoadout()

        #save changes to Profiles
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

        prfls = apt.CFG.get('general.profiles', dtype=list)
        #create profiles from list of profile names
        [Profile(p) for p in prfls]
        pass


    @classmethod
    def save(cls):
        '''Save profiles to settings.'''

        serialize = []
        for prfl in cls.Jar.values():
            serialize += [prfl.getName()]
        apt.CFG.set('general.profiles', Cfg.castStr(serialize, tab_cnt=1, frmt_list=True))
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
        '''Returns (bool) if a template folder exists.'''
        return os.path.exists(self.getProfileDir()+"template/")


    def hasPlugins(self):
        '''Returns (bool) if a plugins folder exists and has at least one file.'''
        return os.path.exists(self.getProfileDir()+"plugins/")


    def hasSettings(self):
        '''Returns (bool) if a legohdl.cfg file exists and has data to import'''
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