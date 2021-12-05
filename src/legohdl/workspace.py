# ------------------------------------------------------------------------------
# Project: legohdl
# Script: workspace.py
# Author: Chase Ruskin
# Description:
#   The Workspace class. A Workspace object has a path and a list of available
#   vendors. This is what the user keeps their work's scope within for a given
#   "organization".
# ------------------------------------------------------------------------------

import os, shutil, glob
import logging as log
from datetime import datetime

from .vendor import Vendor
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


    def __init__(self, name, path, vendors=[], ask=True):
        '''
        Create a workspace instance.

        Parameters:
            name (str): the identity for the workspace
            path (str): the local path where blocks will be looked for
            vendors ([str]): the list of vendors that are tied to this workspace
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
                    Workspace.save(inc_active=False)
                    print()
                    exit(log.info("Workspace not created."))
                while(self.setPath(path) == False):
                    try:
                        path = input("Enter path for workspace "+self.getName()+": ")
                    except KeyboardInterrupt:
                        Workspace.save(inc_active=False)
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

        self._vendors = []
        #find all vendor objects by name and store in list
        for vndr in vendors:
            if(vndr.lower() in Vendor.Jar.keys()):
                self._vendors += [Vendor.Jar[vndr]]
            else:
                log.warning("Could not link unknown vendor "+vndr+" to "+self.getName()+".")
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
                os.makedirs(p, exist_ok=True)
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


    def linkVendor(self, vndr):
        '''
        Attempts to add a vendor to the workspace's vendor list.

        Parameters:
            vndr (str): name of the vendor to add
        Returns:
            (bool): true if the vendor list was modified (successful add)
        '''
        if(vndr.lower() in Vendor.Jar.keys()):
            vndr_obj = Vendor.Jar[vndr]
            if(vndr_obj in self.getVendors()):
                log.info("Vendor "+vndr_obj.getName()+" is already linked to this workspace.")
                return False
            else:
                log.info("Linking vendor "+vndr_obj.getName()+" to the workspace...")
                self._vendors += [vndr_obj]
                return True
        else:
            log.warning("Could not link unknown vendor "+vndr+" to "+self.getName()+".")
            return False


    def unlinkVendor(self, vndr):
        '''
        Attempts to remove a vendor from the workspace's vendor list.

        Parameters:
            vndr (str): name of the vendor to remove
        Returns:
            (bool): true if the vendor list was modified (successful remove)
        '''
        if(vndr.lower() in Vendor.Jar.keys()):
            vndr_obj = Vendor.Jar[vndr]
            if(vndr_obj not in self.getVendors()):
                log.info("Vendor "+vndr_obj.getName()+" is already unlinked from the workspace.")
                return False
            else:
                log.info("Unlinking vendor "+vndr_obj.getName()+" from the workspace...")
                self._vendors.remove(vndr_obj)
                return True
        else:
            log.warning("Could not unlink unknown vendor "+vndr+" from "+self.getName()+".")
            return False

    
    def loadBlocks(self, id_dsgns=False):
        '''
        Loads all blocks found at all levels: dnld (workspace path), instl (workspace
        cache), avail (workspace vendors).

        When id_dsgns is True, this method uses the 'multi-develop' setting to 
        determine which level has precedence in loadHDL(). 
        
        'multi-develop' set to False will only loadHDL() from cache. 'multi-develop' 
        set to True will first try to loadHDL() from dnld, and if DNE, then try
        to loadHDL() from block's cache.

        Either way, if inside a current block, that block's HDL will be loaded over
        its cache.

        Dynamically creates _visible_blocks ([Block]) attribute to be reused.

        Parameters:
            id_dsgns (bool): identify design units (loadHDL) from blocks
        Returns:
            _visible_blocks ([Block]): list of all block objects in cache or path
        '''
        if(hasattr(self, "_visible_blocks")):
            return self._visible_blocks

        self._visible_blocks = []

        #read the setting for multi-develop
        mult_dev = apt.getMultiDevelop()

        #1. Search for downloaded blocks

        #glob on the local workspace path
        #print("Local Blocks on:",self.getPath())
        marker_files = glob.glob(self.getPath()+"**/*/"+apt.MARKER, recursive=True)
        #iterate through all found downloads
        for mf in marker_files:
            b = Block(mf, self, Block.Level.DNLD)
            #if the user is within a current block, load the HDL from its DNLD level (not INSTL)
            if(mult_dev == True or Block.getCurrent(bypass=True) == b):
                self._visible_blocks += [b]
                if(id_dsgns):
                    b.loadHDL()
            pass

        #2. Search for installed blocks

        #glob on the workspace cache path
        #print("Cache Blocks on:",self.getCachePath())
        marker_files = glob.glob(self.getCachePath()+"**/*/"+apt.MARKER, recursive=True)
        #iterate through all found installations
        for mf in marker_files:
            #the block must also have a valid git repository at its root
            root,_ = os.path.split(mf)
            #note: only the head installation has the git repository
            if(Git.isValidRepo(root, remote=False)):
                b = Block(mf, self, Block.Level.INSTL)
                #get the spot for this block's download 
                dnld_b = Block.Inventory[b.M()][b.L()][b.N()][Block.Level.DNLD.value]
                #add this block if a download DNE or the dnld does not match current when
                #not in multi-develop mode
                if(dnld_b == None or (mult_dev == False and Block.getCurrent(bypass=True) != dnld_b)):
                    self._visible_blocks += [b]
                    if(id_dsgns):
                        b.loadHDL()
            pass

        #3. Search for available blocks
            
        #glob on each vendor path
        marker_files = []
        #find all marker files in each of the workspace's vendors
        for vndr in self.getVendors():
            marker_files += glob.glob(vndr.getVendorDir()+"**/*/"+apt.MARKER, recursive=True)
        #iterate through all found availables
        for mf in marker_files:
            b = Block(mf, self, Block.Level.AVAIL)
            #do not add this block to list of visible blocks because it has no
            #units associated with it, only metadata
            pass

        #4. ID all specific version blocks if identifying designs (except current block)
        spec_vers_blocks = []
        for vis_block in self._visible_blocks:
            if(vis_block == Block.getCurrent(bypass=True)):
                continue
            for spec_block in vis_block.getInstalls().values():
                spec_vers_blocks += [spec_block]
                if(id_dsgns):
                    spec_block.loadHDL()
                pass
            pass
        self._visible_blocks += spec_vers_blocks

        return self._visible_blocks


    def shortcut(self, title, req_entity=False, visibility=True, ref_current=True):
        '''
        Returns the Block from a shortened title. If title is empty and 
        'ref_current' is set, then tries to refer to the current block.

        Sometimes an entity is required for certain commands; so it can be
        assumed entity (instead of block name) if only thing given.

        Parameters:
            title (str): partial or full M.L.N with optional E attached
            req_entity (bool): determine if only thing given then it is an entity
            visibility (bool): determine if to only look for visible blocks
            ref_current (bool): determine if to try to assign empty title to current block
        Returns:
            (Block): the identified block from the shortened title
        '''
        if(title == None):
            title = ''
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
        blocks = self.loadBlocks()      
        #use all blocks when visibility is off :todo: is this design intent?
        if(visibility == False):
            blocks = Block.getAllBlocks()
        
        #track list of possible blocks as moving up the chain
        possible_blocks = []

        #search for an entity
        if(len(entity)):
            #collect list of all entities
            reg = Map()
            reg[entity] = []
            #iterate through every block and create a mapping for their entity names
            for bk in blocks:
                #get the entity names from this block
                es = bk.loadHDL(returnnames=True)
                #create mappings of entity names to their block owners
                for e in es:
                    if(e.lower() not in reg.keys()):
                        reg[e] = []
                    reg[e] += [bk]

            #see how many blocks were fit to entity name's mapping
            num_blocks = len(reg[entity])
            #algorithm only detected one possible solution
            if(num_blocks == 1):
                #make sure rest of sections are correct before returning result
                potential = reg[entity][0]
                title = potential.getTitle(index=2, dist=2)
                #verify each part of block identifier matches what was requested
                for i in range(len(sects)):
                    #print(sects[i])
                    if(len(sects[i]) and sects[i].lower() != title[i].lower()):
                        return None
                    pass
                return potential
            #algorithm detected multiple possible solutions (cannot infer)
            elif(num_blocks > 1):
                possible_blocks = reg[entity]
                #only was given an entity name, algorithm cannot solve requested entity
                if(len(sects[2]) == 0):
                    log.info("Ambiguous unit; conflicts with")
                    #display the units/titles that conflict with input
                    for bk in reg[entity]:
                        print('\t '+bk.getFull()+":"+entity)
                    print()
                    exit()
            #no blocks matched the entity name being passed
            else:
                return None
            pass
        #search through all block names
        for start in range(len(sects)-1, -1, -1):
            term = sects[start]
            #exit loop if next term is empty
            if(len(term) == 0):
                break
            reg = Map()
            reg[term] = []
            for bk in blocks:
                t = bk.getTitle(index=start, dist=0)[0]
                #store the block under the given section name
                if(t.lower() not in reg.keys()):
                    reg[t] = []
                reg[t] += [bk]
            #count how many blocks occupy this same name
            num_blocks = len(reg[term])
            #algorithm only detected one possible solution
            if(num_blocks == 1):
                #make sure rest of sections are correct before returning result
                potential = reg[term][0]
                title = potential.getTitle(index=2, dist=2)
                #verify each part of block identifier matches what was requested
                for i in range(len(sects)):
                    #print(sects[i])
                    if(len(sects[i]) and sects[i].lower() != title[i].lower()):
                        return None
                    pass
                return potential
            #algorithm detected multiple solutions (cannot infer on this step)
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
                    #ran out of guesses...report the conflicting titles/units
                    if(req_entity):             
                        log.info("Ambiguous unit; conflicts with")
                    else:
                        log.info("Ambiguous title; conflicts with")
                    for bk in reg[term]:
                        if(req_entity):
                            print('\t '+bk.getFull()+":"+entity)
                        else:
                            print('\t '+bk.getFull())
                    exit(print())
            pass
        #using the current block if title is empty string
        if(ref_current and (title == '' or title == None)):
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
        blocks = self.loadBlocks()
        #print(blocks)
        log.info("Collecting all unit data...")
        for b in blocks:
            us = b.loadHDL()
            for u in us.values():
                u.getLanguageFile().decode(u, recursive=False)
        log.info("done.")
        pass


    def listBlocks(self, title, alpha=False, instl=False, dnld=False, avail=False):
        '''
        Print a formatted table of the available blocks.

        Parameters:
            title (str): block title to be broken into parts for searching
            alpha (bool): determine if to alphabetize the block list order
            instl (bool): determine if to capture only blocks that are installed
            dnld (bool): determine if to capture only blocks that are downloaded
            avail (bool): determine if to capture blocks available from vendor
        Returns:
            None
        '''
        #[!] load the necessary blocks
        self.loadBlocks()

        #split the title into parts
        M,L,N,_ = Block.snapTitle(title, inc_ent=False)

        #get all blocks from inventory
        print('{:<16}'.format("Library"),'{:<20}'.format("Block"),'{:<8}'.format("Status"),'{:<10}'.format("Version"),'{:<16}'.format("Vendor"))
        print("-"*16+" "+"-"*20+" "+"-"*8+" "+"-"*10+" "+"-"*16)
        #iterate through every vendor
        for vndr_k,vndrs in Block.Inventory.items():
            if(vndr_k.startswith(M.lower()) == False):
                continue
            #iterate through every library
            for lib_k,libs in vndrs.items():
                if(lib_k.startswith(L.lower()) == False):
                    continue
                #iterate through every block
                for blk_k,lvls in libs.items():
                    if(blk_k.startswith(N.lower()) == False):
                        continue
                    downloaded = installed = available = ' '
                    disp_d = disp_i = disp_a =  False
                    #if none were set on command-line default to display everything
                    if((dnld or instl or avail) == False):
                        dnld = instl = avail = True

                    #with each lower level, overwrite the block object to print
                    if(lvls[Block.Level.AVAIL.value] != None):
                        bk = lvls[Block.Level.AVAIL.value]
                        available = 'A'
                        disp_a = True
                    if(lvls[Block.Level.INSTL.value] != None):
                        bk = lvls[Block.Level.INSTL.value]
                        installed = 'I'
                        disp_i = True
                    if(lvls[Block.Level.DNLD.value] != None):
                        bk = lvls[Block.Level.DNLD.value]
                        downloaded = 'D'
                        disp_d = True
                    #one condition pair must be true to display the block
                    if((disp_a and avail) or (disp_i and instl) or (disp_d and dnld)):
                        pass
                    else:
                        continue
                    #character to separate different status bits
                    spacer = ' '
                    #format the status column's data
                    sts = downloaded + spacer + installed + spacer + available
                    #leave version empty if its been unreleased
                    v = '' if(bk.getVersion() == '0.0.0') else bk.getVersion()
                    #format the data to print to the console
                    print('{:<16}'.format(bk.L()),'{:<20}'.format(bk.N()),'{:<8}'.format(sts),'{:<10}'.format(v),'{:<16}'.format(bk.M()))
                    pass
        pass


    def listUnits(self, title, alpha=False, usable=False):
        '''
        Print a formatted table of all the design units.

        Parameters:
            title (str): block title to be broken into parts for searching
            alpha (bool): determine if to alphabetize the block list order
            usable (bool): determine if to display units that can be used
        Returns:
            None
        '''
        #[!] load blocks into inventory
        visible = self.loadBlocks()

        M,L,N,V,E = Block.snapTitle(title, inc_ent=True)
        print(M,L,N,V,E)
        print('{:<39}'.format("Block"),'{:<22}'.format("Unit"),'{:<7}'.format("Usable"),'{:<9}'.format("Type"))
        print("-"*39+" "+"-"*22+" "+"-"*7+" "+"-"*9)
        for bk in Block.getAllBlocks():
            #for lvl in Block.Inventory[bk.M()][bk.L()][bk.N()]:
            block_title = bk.getFull(inc_ver=False)
            if(bk.M().lower().startswith(M.lower()) == False):
                continue
            if(bk.L().lower().startswith(L.lower()) == False):
                continue
            if(bk.N().lower().startswith(N.lower()) == False):
                continue
            #collect all units
            if(apt.getMultiDevelop() == False):
                if(bk.getLvlBlock(Block.Level.INSTL) != None):
                    bk = bk.getLvlBlock(Block.Level.INSTL)
                #skip this block if only displaying usable units and multi-develop off
                elif(usable):
                    continue
            
            units = bk.loadHDL(returnnames=False).values()

            #print each unit and its data
            printed = False
            for u in units:
                if(len(E) and u.E().lower().startswith(E.lower()) == False):
                    continue
                #format if unit is visible/usable
                vis = '-'
                if(bk in visible):
                    vis = 'yes'
                #format design unit name according to its natural language
                dsgn = u.getDesign().name.lower()
                if(u.getLang() == u.Language.VERILOG and dsgn == 'entity'):
                    dsgn = 'module'
                print('{:<39}'.format(block_title),'{:<22}'.format(u.E()),'{:<7}'.format(vis),'{:<9}'.format(dsgn))
                block_title = ''
                printed = True
                pass
            if(printed and bk != Block.getAllBlocks()[-1]):
                print()
                pass

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
        Automatically refreshes all vendors for the given workspace. Reads its
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
            log.info("Automatically refreshing workspace "+self.getName()+" vendors... "+infoo)
            #refresh all vendors attached to this workspace
            for vndr in self.getVendors():
                vndr.refresh()
                pass

            #write updated time value to log file
            with open(self.getDir()+self.LOG_FILE, 'w') as lf:
                lf.write(str(cur_time))

        pass


    @classmethod
    def load(cls):
        '''Load all workspaces from settings.'''

        wspcs = apt.SETTINGS['workspace']
        
        for ws in wspcs.keys():
            if('path' in wspcs[ws].keys() and 'vendors' in wspcs[ws].keys()):
                Workspace(ws, wspcs[ws]['path'], wspcs[ws]['vendors'])
        pass


    @classmethod
    def save(cls, inc_active=True):
        '''
        Serializes the Workspace objects and saves them to the settings dictionary.

        Parameters:
            inc_active (bool): determine if to save the active workspace to settings
        Returns:
            None
        '''
        serialized = {}
        #serialize the Workspace objects into dictionary format for settings
        for ws in cls.Jar.values():
            #do not save any workspace that has no path
            if(ws.getPath() == ''):
                continue
            serialized[ws.getName()] = {}
            serialized[ws.getName()]['path'] = ws.getPath()
            serialized[ws.getName()]['vendors'] = ws.getVendors(returnnames=True, lowercase=False)
        
        #update settings dictionary
        apt.SETTINGS['workspace'] = serialized
        
        #update active workspace
        if(inc_active):
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
            msgi = "No active workspace set."
            if(ws != ''):
                msgi = "Workspace "+ws+" does not exist."
            log.info(msgi+" Auto-assigning active workspace to "+cls._ActiveWorkspace.getName()+"...")
            return True
        #still was not able to set the active workspace with the given argument
        elif(cls._ActiveWorkspace != None):
            log.info("Workspace "+ws+" does not exist. Keeping "+cls._ActiveWorkspace.getName()+" as active.")
        else:
            log.error("No workspace set as active.")

        return False


    def isLinked(self):
        return len(self.getVendors())


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


    def getVendors(self, returnnames=False, lowercase=True):
        '''
        Return the vendor objects associated with the given workspace.

        Parameters:
            returnnames (bool): true will return vendor names
            lowercase (bool): true will return lower-case names if returnnames is enabled
        Returns:
            ([Vendor]) or ([str]): list of available vendors
            
        '''
        if(returnnames):
            vndr_names = []
            for vndr in self._vendors:
                name = vndr.getName()
                if(lowercase):
                    name = name.lower()
                vndr_names += [name]
            return vndr_names
        else:
            return self._vendors

    
    @classmethod
    def printList(cls):
        '''
        Prints formatted list for workspaces with vendor availability and which is active.

        Parameters:
            None
        Returns:
            None
        '''
        print('{:<16}'.format("Workspace"),'{:<6}'.format("Active"),'{:<40}'.format("Path"),'{:<14}'.format("Vendors"))
        print("-"*16+" "+"-"*6+" "+"-"*40+" "+"-"*14+" ")
        for ws in cls.Jar.values():
            vndrs = apt.listToStr(ws.getVendors(returnnames=True))
            act = 'yes' if(ws == cls.getActive()) else '-'
            print('{:<16}'.format(ws.getName()),'{:<6}'.format(act),'{:<40}'.format(ws.getPath()),'{:<14}'.format(vndrs))
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


    # uncomment to use for debugging
    # def __str__(self):
    #     return f'''
    #     ID: {hex(id(self))}
    #     Name: {self.getName()}
    #     Path: {self.getPath()}
    #     Active: {self.isActive()}
    #     Hidden directory: {self.getDir()}
    #     Linked to: {self.isLinked()}
    #     Vendors: {self.getVendors(returnnames=True)}
    #     '''


    pass