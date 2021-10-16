# Project: legohdl
# Script: profile.py
# Author: Chase Ruskin
# Description:
#   The Profile class. A Profile object can have legohdl settings, template,
#   and/or scripts that can be maintained and imported. They are mainly used
#   to save certain setting configurations (loadouts) and share settings across
#   users.

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
        success = True
        if(url != None):
            success = self.loadFromURL(url)
        else:
            #set profile's name
            self._name = name

            #create profile directory if DNE
            os.makedirs(self.getProfileDir(), exist_ok=True)
            #create profile market file if DNE
            if(os.path.exists(self.getProfileDir()+self.getName()+self.EXT) == False):
                open(self.getProfileDir()+self.getName()+self.EXT, 'w').close()
            
            #create git repository
            self._repo = Git(self.getProfileDir())
        
        #add to the catalog
        if(success):
            self.Jar[self.getName()] = self
        pass

    
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
        Load settings, template and/or scripts into legohdl from the profile.

        Parameters:
            ask (bool): explicitly prompt user at each stage in the process
        Returns:
            None
        '''


        def deepMerge(src, dest, setting="", scripts_only=False):
            '''
            Merge all values found in src to override destination into a modified
            dictionary.

            Parameters:
                src (dict): multi-level dictionary to grab values from
                dest (dict): multi-level dictionary to append values in
                scripts_only (bool): only add in script settings
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
                                #find replace all parts of string with ENV_NAME
                                if(isinstance(v,str)):
                                    v = v.replace(apt.ENV_NAME, apt.HIDDEN[:len(apt.HIDDEN)-1])
                                if(i not in dest[k]):
                                    dest[k] += [i]
                    #otherwise normal overwrite
                    else:
                        if(isinstance(v,str)):
                            v = v.replace(apt.ENV_NAME, apt.HIDDEN[:len(apt.HIDDEN)-1])
                        #do not allow a null value to overwrite an already established value
                        if(k in dest.keys() and v == cfg.NULL):
                            continue
                        dest[k] = v
                    #print to console the overloaded settings
                    log.info(next_level+" = "+str(v))
            return dest

        log.info("Importing profile "+self.getName()+"...")
        #overload available settings
        if(self.hasSettings()):
            act = (ask == False) or apt.confirmation("Import "+apt.SETTINGS_FILE+"?", warning=False)
            if(act):
                log.info('Overloading '+apt.SETTINGS_FILE+'...')
                with open(self.getPath()+apt.SETTINGS_FILE, 'r') as f:
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
        #copy in scripts
        if(self.hasScripts()):
            act = (ask == False) or apt.confirmation("Import scripts?", warning=False)
            if(act):
                log.info('Importing scripts...')
                scripts = os.listdir(self.getProfileDir()+'scripts/')
                for scp in scripts:
                    log.info("Copying "+scp+" to built-in scripts folder...")
                    if(os.path.isfile(self.getProfileDir()+'scripts/'+scp)):
                        #copy contents into built-in script folder
                        prfl_script = open(self.getProfileDir()+'scripts/'+scp, 'r')
                        copied_script = open(apt.HIDDEN+'scripts/'+scp, 'w')
                        #transfer file data via writing it to file
                        script_data = prfl_script.readlines()
                        copied_script.writelines(script_data)
                        #close files
                        prfl_script.close()
                        copied_script.close()
                        pass
                    pass
                if(self.hasSettings()):
                    log.info('Overloading scripts in '+apt.SETTINGS_FILE+'...')
                    with open(self.getProfileDir()+apt.SETTINGS_FILE, 'r') as f:
                        prfl_settings = cfg.load(f)
                        dest_settings = copy.deepcopy(apt.SETTINGS)
                        dest_settings = deepMerge(prfl_settings, dest_settings, scripts_only=True)
                        apt.SETTINGS = dest_settings
            pass
        #save all modifications to legohdl settings
        apt.save()
        pass


    def update(self):
        '''
        If has a remote repository, checks with it to ensure the current branch
        is up-to-date and pulls any changes.
        
        Parameters:
            None
        Returns:
            None
        '''
        # :todo: needs to handle reloading default profile
        log.info("Updating repository for profile "+self.getName()+"...")
        #check status from remote
        if(self._repo.isLatest() == False):
            log.info('Pulling new updates...')
            self._repo.pull()
            log.info("success")
        else:
            log.info("Already up-to-date.")
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
            #remove a market that is not found in settings (Jar class container)
            if(prfl_name.lower() not in cls.Jar.keys()):
                log.info("Removing stale profile "+prfl_name+"...")
                prfl_dir = f.replace(os.path.basename(f),'')
                #shutil.rmtree(mrkt_dir, onerror=apt.rmReadOnly)
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


    def hasScripts(self):
        return os.path.exists(self.getProfileDir()+"scripts/")


    def hasSettings(self):
        return os.path.exists(self.getProfileDir()+apt.SETTINGS_FILE)

    
    def isLastImport(self):
        return self == self.LastImport


    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        Name: {self.getName()}
        Imported Last: {self.isLastImport()}
        settings: {self.hasSettings()}
        template: {self.hasTemplate()}
        scripts: {self.hasScripts()}
            repo: {self._repo}
        '''

    pass