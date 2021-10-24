# Project: legohdl
# Script: workspace.py
# Author: Chase Ruskin
# Description:
#   The Workspace class. A Workspace object has a path and a list of available
#   markets. This is what the user keeps their work's scope within for a given
#   "organization".

import os, shutil
import logging as log
from datetime import datetime
from .market import Market
from .apparatus import Apparatus as apt
from .map import Map


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
                path = input("Enter workspace "+self.getName()+"'s path: ")
                while(self.setPath(path) == False):
                    path = input("Enter workspace "+self.getName()+"'s path: ")
        
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
            log.info("Workspace "+self.getName()+"'s local path cannot be empty.")
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
                log.info("Market "+mrkt_obj.getName(low=False)+" is already linked to this workspace.")
                return False
            else:
                log.info("Linking market "+mrkt_obj.getName(low=False)+" to the workspace...")
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
                log.info("Market "+mrkt_obj.getName(low=False)+" is already unlinked from the workspace.")
                return False
            else:
                log.info("Unlinking market "+mrkt_obj.getName(low=False)+" from the workspace...")
                self._markets.remove(mrkt_obj)
                return True
        else:
            log.warning("Could not unlink unknown market "+mrkt+" from "+self.getName()+".")
            return False


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
        active.

        Parameters:
            ws (str): workspace name
        Returns:
            (bool): true if active-workspace was set
        '''
        if(ws != None and ws.lower() in cls.Jar.keys()):
            re_assign = (cls._ActiveWorkspace != None)
            #set the active workspace obj from found workspace
            cls._ActiveWorkspace = cls.Jar[ws]
            #only give prompt if reassigning the active-workspace
            if(re_assign):
                log.info("Assigning workspace "+cls._ActiveWorkspace.getName()+" as active workspace...")

            return True
        elif(len(cls.Jar.keys()) and cls._ActiveWorkspace == None):
            random_ws = list(cls.Jar.keys())[0]
            cls._ActiveWorkspace = cls.Jar[random_ws]
            log.info("Workspace "+ws+" does not exist. Auto-assigning active workspace to "+cls._ActiveWorkspace.getName()+"...")
            return True
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


    def getName(self):
        return self._name


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
            mrkts = apt.ListToStr(ws.getMarkets(returnnames=True))
            act = 'yes' if(ws == cls.getActive()) else '-'
            print('{:<16}'.format(ws.getName()),'{:<6}'.format(act),'{:<40}'.format(ws.getPath()),'{:<14}'.format(mrkts))
            pass
        pass


    def isActive(self):
        return self == self.getActive()


    @classmethod
    def printAll(cls):
        for key,ws in cls.Jar.items():
            print('key:',key)
            print(ws)


    @classmethod
    def getActive(cls):
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