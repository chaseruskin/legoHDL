# Project: legohdl
# Script: workspace.py
# Author: Chase Ruskin
# Description:
#   The Workspace class. A Workspace object has a path and a list of available
#   markets. This is what the user keeps their work's scope within for a given
#   "organization".

import os, shutil, glob
import logging as log
from datetime import datetime

from legohdl.language import Language
from .market import Market
from .apparatus import Apparatus as apt
from .map import Map
from .git import Git
from .block import Block


class Workspace:

    #store all workspaces in dictionary
    Jar = Map()

    #active-workspace is a workspace object
    _ActiveWorkspace = None

    DIR = apt.fs(apt.HIDDEN+"workspaces/")
    LOG_FILE = "refresh.log"

    MIN_RATE = -1
    MAX_RATE = 1440


    def __init__(self, name, path, markets=[], ask=True):
        '''
        Create a workspace instance.

        Parameters:
            name (str): the identity for the workspace
            path (str): the local path where blocks will be looked for
            markets ([str]): the list of markets that are tied to this workspace
            ask (bool): will ask user if wishing to enter workspace path
        Returns:
            None
        '''
        self._name = name
        #do not create workspace if the name is already taken
        if(self.getName().lower() in self.Jar.keys()):
            log.error("Skipping workspace "+self.getName()+" due to duplicate naming conflict.")
            return

        #set the path
        self._path = ''
        self.setPath(path)
        #do not create workspace if the path is empty
        if(self.getPath() == ''):
            if(ask == False):
                log.error("Skipping workspace "+self.getName()+" due to empty local path.")
                return
            else:
                #keep asking to set path until one is decided/input
                try:
                    path = input("Enter path for workspace "+self.getName()+": ")
                except KeyboardInterrupt:
                    print()
                    exit(log.info("Workspace not created."))
                while(self.setPath(path) == False):
                    try:
                        path = input("Enter path for workspace "+self.getName()+": ")
                    except KeyboardInterrupt:
                        print()
                        exit(log.info("Workspace not created."))
        
        self._ws_dir = apt.fs(self.DIR+self.getName()+"/")
        
        #ensure all workspace hidden directories exist
        if(os.path.isdir(self.getDir()) == False):
            log.info("Creating hidden workspace directory for "+self.getName()+"...")
            os.makedirs(self.getDir(), exist_ok=True)
        #create workspace's cache where installed blocks will be stored
        os.makedirs(self.getDir()+"cache", exist_ok=True)
        #create the refresh log if DNE
        if(os.path.isfile(self.getDir()+self.LOG_FILE) == False):
            open(self.getDir()+self.LOG_FILE, 'w').close()

        self._markets = []
        #find all market objects by name and store in list
        for mrkt in markets:
            if(mrkt.lower() in Market.Jar.keys()):
                self._markets += [Market.Jar[mrkt]]
            else:
                log.warning("Could not link unknown market "+mrkt+" to "+self.getName()+".")
            pass

        #add to class Jar
        self.Jar[self.getName()] = self
        pass


    def setPath(self, p):
        '''
        Set the workspace's local path to a new value. Will ask user if okay
        to create the path if DNE.

        Parameters:
            p (str): the path string
        Returns:
            (bool): true if successfully changed the path attribute
        '''
        #cannot set an empty path
        if(p == '' or p == None):
            log.info("Local path for workspace "+self.getName()+" cannot be empty.")
            return False

        p = apt.fs(p)
        #create the workspace's local path if it does not exist
        if(os.path.exists(p) == False):
            #prompt user
            carry_on = apt.confirmation("Workspace "+self.getName()+"'s local path does not exist. Create "+p+"?")
            if(carry_on):
                os.mkdir(p)
                self._path = p
                return True
            else:
                log.info("Did not set "+p+" as local path.")
                return False
        else:
            self._path = p
            return True


    def setName(self, n):
        '''
        Change the workspace's name if the name is not already taken.

        Parameters:
            n (str): new name for workspace
        Returns:
            (bool): true if name successfully altered and updated in Jar
        '''
        if(n == '' or n == None):
            log.error("Workspace name cannot be empty.")
            return False

        if(n.lower() in self.Jar.keys()):
            log.error("Cannot rename workspace to "+n+" due to name conflict.")
            return False
        else:
            #remove old name from Jar
            if(self.getName().lower() in self.Jar.keys()):
                del self.Jar[self.getName()]

            #rename hidden directory if exists
            new_dir = apt.fs(self.DIR+n+"/")
            if(hasattr(self, "_ws_dir")):
                os.rename(self.getDir(), new_dir)
            #set the hidden workspace directory
            self._ws_dir = new_dir

            #change to new name
            self._name = n
            #update the Jar
            self.Jar[self.getName()] = self
            return True


    def remove(self):
        '''
        Removes the workspace object from the Jar and its hidden directory.

        Parameters:
            None
        Returns:
            None
        '''
        log.info("Removing workspace "+self.getName()+"...")
        #delete the hidden workspace directory
        shutil.rmtree(self.getDir(), onerror=apt.rmReadOnly)
        #remove from class Jar
        del self.Jar[self.getName()]
        pass


    def linkMarket(self, mrkt):
        '''
        Attempts to add a market to the workspace's market list.

        Parameters:
            mrkt (str): name of the market to add
        Returns:
            (bool): true if the market list was modified (successful add)
        '''
        if(mrkt.lower() in Market.Jar.keys()):
            mrkt_obj = Market.Jar[mrkt]
            if(mrkt_obj in self.getMarkets()):
                log.info("Market "+mrkt_obj.getName()+" is already linked to this workspace.")
                return False
            else:
                log.info("Linking market "+mrkt_obj.getName()+" to the workspace...")
                self._markets += [mrkt_obj]
                return True
        else:
            log.warning("Could not link unknown market "+mrkt+" to "+self.getName()+".")
            return False


    def unlinkMarket(self, mrkt):
        '''
        Attempts to remove a market from the workspace's market list.

        Parameters:
            mrkt (str): name of the market to remove
        Returns:
            (bool): true if the market list was modified (successful remove)
        '''
        if(mrkt.lower() in Market.Jar.keys()):
            mrkt_obj = Market.Jar[mrkt]
            if(mrkt_obj not in self.getMarkets()):
                log.info("Market "+mrkt_obj.getName()+" is already unlinked from the workspace.")
                return False
            else:
                log.info("Unlinking market "+mrkt_obj.getName()+" from the workspace...")
                self._markets.remove(mrkt_obj)
                return True
        else:
            log.warning("Could not unlink unknown market "+mrkt+" from "+self.getName()+".")
            return False


    def getAvailableBlocks(self, multi_develop=False):
        '''
        Returns all available blocks. Some may be hidden under others (cache overwrites
        positions of downloaded blocks when multi-develop is False).
        
        Parameters:
            multi_develop (bool): determine if download blocks have precedence over cache
        Returns:
            map
        '''

        pass

    
    def loadLocalBlocks(self):
        '''
        Find all valid blocks within the local workspace path. Updates the 
        _local_blocks Map.

        Parameters:
            None
        Returns:
            None
        '''
        if(hasattr(self, "_local_blocks")):
            return self._local_blocks

        # :todo: all local blocks only need to be loaded if multi-develop is ON

        self._local_blocks = []
        #glob on the local workspace path
        print("Local Blocks on:",self.getPath())
        marker_files = glob.glob(self.getPath()+"**/*/"+apt.MARKER, recursive=True)
        #print(marker_files)
        for mf in marker_files:
            b = Block(mf, self)
            self._local_blocks += [b]
            
        return self._local_blocks


    def loadCacheBlocks(self):
        '''
        Find all valid blocks within the workspace cache. Updates the 
        _cache_blocks Map.

        Parameters:
            None
        Returns:
            None
        '''
        #glob on the workspace cache path
        print("Cache Blocks on:",self.getCachePath())
        marker_files = glob.glob(self.getCachePath()+"**/*/"+apt.MARKER, recursive=True)
       
        cache_markers = []
        for mf in marker_files:
            #the block must also be a valid git repository at its root
            root,_ = os.path.split(mf)
            if(Git.isValidRepo(root, remote=False)):
                cache_markers += [mf]
        print(cache_markers)
        pass

    
    def loadMarketBlocks(self):
        '''
        Find all valid blocks within the workspace cache. Updates the 
        _market_blocks Map.

        Parameters:
            None
        Returns:
            None
        '''
        #glob on each market path
        marker_files = []
        for mrkt in self.getMarkets():
            marker_files += glob.glob(mrkt.getMarketDir()+"**/*/"+apt.MARKER, recursive=True)
        print(marker_files)
        pass


    def shortcut(self, title, req_entity=False):
        '''
        Returns the Block from a shortened title. If title is empty, then
        it refers to the current block.

        Sometimes an entity is required for certain commands; so it can be
        assumed entity (instead of block name) if only thing given.

        Parameters:
            title (str): partial or full M.L.N with optional E attached
            req_entity (bool): determine if only thing given then it is an entity
        Returns:
            (Block): the identified block from the shortened title
        '''
        #split into pieces
        pieces = title.split('.')
        sects = ['']*3
        diff = 3 - len(pieces)
        for i in range(len(pieces)-1, -1, -1):
            sects[diff+i] = pieces[i]
        #check final piece if it has an entity attached
        entity = ''
        if(sects[2].count(apt.ENTITY_DELIM)):
            i = sects[2].find(apt.ENTITY_DELIM)
            entity = sects[2][i+1:]
            sects[2] = sects[2][:i]
        #assume only name given is actually the entity
        elif(req_entity):
            entity = sects[2]
            sects[2] = ''

        # [!] load all necessary blocks before searching
        l_blocks = self.loadLocalBlocks()
        
        #track list of possible blocks as moving up the chain
        possible_blocks = []

        #search for an entity
        if(len(entity)):
            #collect list of all entities
            reg = Map()
            reg[entity] = []
            for bk in l_blocks:
                es = bk.loadHDL(returnnames=True)
                for e in es:
                    if(e.lower() not in reg.keys()):
                        reg[e] = []
                    reg[e] += [bk]
                
            num_blocks = len(reg[entity])
            if(num_blocks == 1):
                #:todo: make sure rest of sections are correct before returning result
                return reg[entity][0]
            elif(num_blocks > 1):
                possible_blocks = reg[entity]
                if(len(sects[2]) == 0):
                    log.info("Ambiguous title; conflicts with")
                    for bk in reg[entity]:
                        print('\t'+bk.getFull()+":"+entity)
                    exit(print())
            pass
        #search through all block names
        for start in range(len(sects)-1, -1, -1):
            term = sects[start]
            #exit loop if next term is empty
            if(len(term) == 0):
                break
            reg = Map()
            reg[term] = []
            for bk in l_blocks:
                t = bk.getTitle(index=start, dist=0)[0]
                if(t.lower() not in reg.keys()):
                    reg[t] = []
                reg[t] += [bk]
            #count how many blocks occupy this same name
            num_blocks = len(reg[term])
            if(num_blocks == 1):
                #print("FOUND:",reg[term][0].getTitle(index=2, dist=2))
                #:todo: make sure rest of sections are correct before returning result
                return reg[term][0]
            elif(num_blocks > 1):
                #compare with blocks for a match and dwindle down choices
                next_blocks = []
                for bk in reg[term]:
                    if(bk in possible_blocks or (start == len(sects)-1 and entity == '')):
                        next_blocks += [bk]
                #dwindled down to a single block
                if(len(next_blocks) == 1):
                    #print("FOUND:",next_blocks[0].getTitle(index=2, dist=2))
                    return next_blocks[0]
                #carry on to using next title section
                if(len(sects[start-1])):
                    #continue to using next term
                    possible_blocks = next_blocks
                    continue
                else:
                    #ran out of guesses...report the conflicting titles
                    log.info("Ambiguous title; conflicts with")
                    for bk in reg[term]:
                        print('\t'+bk.getFull())
                    exit(print())
            pass
        #using the current block if title is empty string
        if(title == '' or title == None):
            return Block.getCurrent()
        #return None if all attempts have failed and not returned anything yet
        return None

    
    def decodeUnits(self):
        '''
        Decodes every available unit to get the complete graphing data structure.

        Parameters:
            None
        Returns:
            None
        '''
        blocks = self.loadLocalBlocks()
        for b in blocks:
            us = b.loadHDL()
            for u in us.values():
                Language.ProcessedFiles[u.getFile()].decode(u)
        pass


    def listBlocks(self, M, L, N, alpha=False, instl=False, dnld=False):
        '''
        Print a formatted table of the available blocks.

        Parameters:
            :todo:
        Returns:
            None
        '''
        # [!] load the necessary blocks
        blocks = self.loadLocalBlocks()
        
        print('{:<12}'.format("Library"),'{:<20}'.format("Block"),'{:<8}'.format("Status"),'{:<8}'.format("Version"),'{:<16}'.format("Market"))
        print("-"*12+" "+"-"*20+" "+"-"*8+" "+"-"*8+" "+"-"*16)
        for bk in blocks:
            v = '' if(bk.getVersion() == '0.0.0') else bk.getVersion()
            print('{:<12}'.format(bk.L()),'{:<20}'.format(bk.N()),'{:<8}'.format("dnld"),'{:<8}'.format(v),'{:<16}'.format(bk.M()))
        pass


    def listUnits(self):
        '''
        Print a formatted table of all the available entities.

        Parameters:
            None
        Returns:
            None
        '''
        # [!] load the necessary blocks
        blocks = self.loadLocalBlocks()
        
        #collect all units
        units = []
        for bk in blocks:
            units += bk.loadHDL(returnnames=False).values()
        #print(units)
        print('{:<14}'.format("Library"),'{:<14}'.format("Unit"),'{:<8}'.format("Type"),'{:<14}'.format("Block"),'{:<10}'.format("Language"))
        print("-"*14+" "+"-"*14+" "+"-"*8+" "+"-"*14+" "+"-"*10+" ")
        for u in units:
            print('{:<14}'.format(u.L()),'{:<14}'.format(u.E()),'{:<8}'.format(u._dsgn.name),'{:<14}'.format(u.N()),'{:<10}'.format(u.getLang().name))


    @classmethod
    def tidy(cls):
        '''
        Removes any stale hidden workspace directories that aren't mapped to a
        workspace found in the class Jar container.

        Parameters:
            None
        Returns:
            None
        '''
        #list all hidden workspace directories
        hidden_dirs = os.listdir(cls.DIR)
        for hd in hidden_dirs:
            if(hd.lower() not in cls.Jar.keys()):
                log.info("Removing stale hidden workspace directory for "+hd+"...") 
                if(os.path.isdir(cls.DIR+hd)):
                    shutil.rmtree(cls.DIR+hd, onerror=apt.rmReadOnly)
                #remove all files from workspace directory
                else:
                    os.remove(cls.DIR+hd)
        pass


    def autoRefresh(self, rate):
        '''
        Automatically refreshes all markets for the given workspace. Reads its
        log file to determine if past next interval for refresh.

        Parameters:
            rate (int): how often to ask a refresh within a 24-hour period
        Returns:
            None
        '''


        def timeToFloat(prt):
            '''
            Converts a time object into a float type.

            Parameters:
                prt (datetime): iso format of current time
            Returns:
                (float): 0.00 (inclusive) - 24.00 (exclusive)
            '''
            time_stamp = str(prt).split(' ')[1]
            time_sects = time_stamp.split(':')
            hrs = int(time_sects[0])
            #convert to 'hours'.'minutes'
            time_fmt = (float(hrs)+(float(float(time_sects[1])/60)))
            return time_fmt

        refresh = False
        last_punch = None
        stage = 1
        cur_time = datetime.now()

        #do not perform refresh if the rate is 0
        if(rate == 0):
            return
        #always refresh if the rate is set below 0 (-1)
        elif(rate <= self.MIN_RATE):
            refresh = True

        #divide the 24 hour period into even checkpoints
        max_hours = float(24)
        spacing = float(max_hours / rate)
        intervals = []
        for i in range(rate):
            intervals += [spacing*i]
        
        #ensure log file exists
        if(os.path.exists(self.getDir()+self.LOG_FILE) == False):
            open(self.getDir()+self.LOG_FILE, 'w').close()

        #read log file
        #read when the last refresh time occurred
        with open(self.getDir()+self.LOG_FILE, 'r') as log_file:
            #read the latest date
            data = log_file.readlines()
            #no refreshes have occurred so automatically need a refresh
            if(len(data) == 0):
                last_punch = cur_time
                refresh = True
            else:
                last_punch = datetime.fromisoformat(data[0])
                #determine if its time to refresh
                #get latest time that was punched
                last_time_fmt = timeToFloat(last_punch)
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
                next_day = cur_time.year > last_punch.year or cur_time.month > last_punch.month or cur_time.day > last_punch.day
                #print(next_day)
                #print("currently",cur_time_fmt)
                #determine if the current time has passed the next checkpoint or if its a new day
                if(next_day or cur_time_fmt >= next_checkpoint):
                    last_punch = cur_time
                    refresh = True
            log_file.close()

        #determine if its time to refresh
        if(refresh):
            #display what interval is being refreshed on the day
            infoo = "("+str(stage)+"/"+str(rate)+")" if(rate > 0) else ''
            log.info("Automatically refreshing workspace markets... "+infoo)
            #refresh all markets attached to this workspace
            for mrkt in self.getMarkets():
                mrkt.refresh()
                pass

            #write updated time value to log file
            with open(self.getDir()+self.LOG_FILE, 'w') as lf:
                lf.write(str(cur_time))

        pass


    @classmethod
    def load(cls):
        '''
        Load all workspaces from settings.

        '''
        wspcs = apt.SETTINGS['workspace']

        for ws in wspcs.keys():
            Workspace(ws, wspcs[ws]['path'], wspcs[ws]['market'])
        pass


    @classmethod
    def save(cls):
        '''
        Serializes the Workspace objects and saves them to the settings dictionary.

        Parameters:
            None
        Returns:
            None
        '''
        serialized = {}
        #serialize the Workspace objects into dictionary format for settings
        for ws in cls.Jar.values():
            serialized[ws.getName()] = {}
            serialized[ws.getName()]['path'] = ws.getPath()
            serialized[ws.getName()]['market'] = ws.getMarkets(returnnames=True, lowercase=False)
        #update settings dictionary
        apt.SETTINGS['workspace'] = serialized
        #update active workspace
        if(cls.getActive() != None):
            apt.SETTINGS['general']['active-workspace'] = cls.getActive().getName()
        else:
            apt.SETTINGS['general']['active-workspace'] = ''

        apt.save()
        pass


    @classmethod
    def inWorkspace(cls):
        '''
        Determine if an active workspace is selected.

        Parameters:
            None
        Returns:
            (bool): true if ActiveWorkspace is not None
        '''
        return cls._ActiveWorkspace != None


    @classmethod
    def setActiveWorkspace(cls, ws):
        '''
        Set the active workspace after initializing all workspaces into Jar. If
        the input name is invalid, it will set the first workspace in the Jar as
        active if one is not already assigned.

        Parameters:
            ws (str): workspace name
        Returns:
            (bool): true if active-workspace was set
        '''
        #properly set the active workspace from one found in Jar
        if(ws != None and ws.lower() in cls.Jar.keys()):
            re_assign = (cls._ActiveWorkspace != None)
            #set the active workspace obj from found workspace
            cls._ActiveWorkspace = cls.Jar[ws]
            #only give prompt if reassigning the active-workspace
            if(re_assign):
                log.info("Assigning workspace "+cls._ActiveWorkspace.getName()+" as active workspace...")

            return True
        #try to randomly assign active workspace if not already assigned.
        elif(len(cls.Jar.keys()) and cls._ActiveWorkspace == None):
            random_ws = list(cls.Jar.keys())[0]
            cls._ActiveWorkspace = cls.Jar[random_ws]
            log.info("Workspace "+ws+" does not exist. Auto-assigning active workspace to "+cls._ActiveWorkspace.getName()+"...")
            return True
        #still was not able to set the active workspace with the given argument
        elif(cls._ActiveWorkspace != None):
            log.info("Workspace "+ws+" does not exist. Keeping "+cls._ActiveWorkspace.getName()+" as active.")
        else:
            log.error("No workspace set as active.")

        return False


    def isLinked(self):
        return len(self.getMarkets())


    def getPath(self):
        return self._path


    def getDir(self):
        return self._ws_dir


    def getCachePath(self):
        return self.getDir()+"cache/"


    def getName(self):
        return self._name


    def isActive(self):
        return self == self.getActive()


    def getMarkets(self, returnnames=False, lowercase=True):
        '''
        Return the market objects associated with the given workspace.

        Parameters:
            returnnames (bool): true will return market names
            lowercase (boll): true will return lower-case names if returnnames is enabled
        Returns:
            ([Market]) or ([str]): list of available markets
            
        '''
        if(returnnames):
            mrkt_names = []
            for mrkt in self._markets:
                name = mrkt.getName()
                if(lowercase):
                    name = name.lower()
                mrkt_names += [name]
            return mrkt_names
        else:
            return self._markets

    
    @classmethod
    def printList(cls):
        '''
        Prints formatted list for workspaces with market availability and which is active.

        Parameters:
            None
        Returns:
            None
        '''
        print('{:<16}'.format("Workspace"),'{:<6}'.format("Active"),'{:<40}'.format("Path"),'{:<14}'.format("Markets"))
        print("-"*16+" "+"-"*6+" "+"-"*40+" "+"-"*14+" ")
        for ws in cls.Jar.values():
            mrkts = apt.listToStr(ws.getMarkets(returnnames=True))
            act = 'yes' if(ws == cls.getActive()) else '-'
            print('{:<16}'.format(ws.getName()),'{:<6}'.format(act),'{:<40}'.format(ws.getPath()),'{:<14}'.format(mrkts))
            pass
        pass


    @classmethod
    def printAll(cls):
        for key,ws in cls.Jar.items():
            print('key:',key)
            print(ws)


    @classmethod
    def getActive(cls):
        if(cls._ActiveWorkspace == None):
            exit(log.error("Not in a workspace!"))
        return cls._ActiveWorkspace


    def __str__(self):
        return f'''
        ID: {hex(id(self))}
        Name: {self.getName()}
        Path: {self.getPath()}
        Active: {self.isActive()}
        Hidden directory: {self.getDir()}
        Linked to: {self.isLinked()}
        Markets: {self.getMarkets(returnnames=True)}
        '''

    pass