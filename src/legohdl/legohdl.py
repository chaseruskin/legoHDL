# Project: legohdl
# Script: legohdl.py
# Author: Chase Ruskin
# Description:
#   This script is the entry-point to the legohdl program. It parses the
#   command-line arguments and contains a method for each valid command.

import os, sys, shutil
import logging as log

from .__version__ import __version__

from .apparatus import Apparatus as apt
from .cfgfile import CfgFile as cfg

from .block import Block
from .map import Map
from .unit import Unit
from .gui import GUI
from .test import main as test
from .market import Market
from .workspace import Workspace
from .profile import Profile
from .script import Script
from .label import Label
from .git import Git


class legoHDL:

    #! === INITIALIZE ===

    def __init__(self):
        '''
        Initialize the legoHDL tool. 
        
        This method specifically parses the command line arguments, loads tool-wide settings, 
        and initializes the registry.

        Parameters:
            None
        Returns:
            None
        '''
        #load the logging format
        log.basicConfig(format='%(levelname)s:\t%(message)s', level=log.INFO)

        #parse arguments
        self._command = self._item = ""
        #store args accordingly from command-line
        for i, arg in enumerate(sys.argv[1:]):
            #first is the command
            if(i == 0):
                self._command = arg.lower()
            #next is the "item" (may not be used for all commands)
            elif(i == 1):
                self._item = arg
            else:
                break

        #only display the program's version and exit
        if(self._command == '--version'):
            print(__version__)
            exit()

        #parse any remaining arguments
        self.parseArgs(sys.argv[1:])

        #load legohdl.cfg
        #ensure all necessary hidden folder structures exist
        intial_setup = apt.initialize()
        if(intial_setup):
            self.runSetup()

        apt.load()
        #initialize all Markets
        Market.load()
        Market.tidy()
        #initialize all Workspaces
        Workspace.load()
        Workspace.setActiveWorkspace(apt.SETTINGS['general']['active-workspace'])
        Workspace.tidy()
        #initialize all Profiles
        Profile.load()
        Profile.tidy()
        #initialize all Scripts
        Script.load()
        #initialize all Labels
        Label.load()

        #Workspace.printAll()

        #save all legohdl.cfg changes
        apt.save()
        Workspace.save()
        
        self.blockPKG = None
        #self.working_block = Block(os.getcwd())
        
        #initialize registry with the workspace-level markets
        if(Workspace.inWorkspace()):
            #self.db = Registry(Workspace.getActive().getMarkets())
            #Workspace.getActive().loadLocalBlocks()
            #Workspace.getActive().loadCacheBlocks()
            #Workspace.getActive().loadMarketBlocks()
            pass

        #limit functionality if not in a workspace
        if(not Workspace.inWorkspace()):
            if(self._command == '' or \
                self._command == 'config' or \
                self._command == 'help' or \
                self._command == 'open' and (self.hasFlag('settings') or self.hasFlag('template'))):
                pass
            else:
                exit(log.error("Failed to run command because active workspace is not set."))
        else:
            self.WS().autoRefresh(rate=apt.getRefreshRate())

        print(self)

        #Block('/Users/chase/develop/eel4712c/lab4/', ws_path=Workspace.getActive().getPath())

        if('debug' == self._command):
            test()
        else:
            self.runCommand()
        pass


    def parseArgs(self, args):
        '''
        Creates a dictionary of arguments separated into 'flags' and 'vars'.

        Parameters:
            args ([str]): list of arguments to identify
        Returns:
            None
        '''
        self._flags = []
        self._vars = Map()

        for arg in args:
            #a flag/var begins with a '-' character
            if(arg[0] == '-' and len(arg) > 1):
                #a pair has a '=' character
                if(arg.find('=') > -1):
                    #find the first '=' and partition into key,value
                    eq_i = arg.find('=')
                    key, val = arg[1:eq_i], arg[eq_i+1:]
                    arg = '-'+key #update value to put into flags list
                    self._vars[key] = val
                #store lower-case of flag for evaluation purposes
                self._flags.append(arg[1:].lower())
                pass
        pass


    def WS(self):
        'Returns the active workspace.'
        return Workspace.getActive()


    def getVar(self, key):
        '''
        Get the value for the desired key. Returns None if DNE.
        
        Parameters:
            key (str): var's key
        Returns:
            val (str):
        '''
        if(key.lower() in self._vars.keys()):
            return self._vars[key]
        else:
            return None

    
    def getItem(self, raw=False):
        '''
        Get the value of the item argument. Returns None if item is empty
        string or item is a flag.

        Parameters:
            raw (bool): determine if to strictly return item
        Returns:
            (str): the item passed into legohdl
        '''
        it = self._item
        if(raw):
            return it
        #make sure the item is not a flag
        if(len(it) and it[1:] in self._flags):
            it = None
        #make sure the item is not a blank string
        if(it == ''):
            it = None
        return it


    def hasFlag(self, flag):
        '''
        See if the flag is found within _flags.

        Parameters:
            flag (str): flag
        Returns:
            (bool): determine if flag is in _flags
        '''
        return (self._flags.count(flag) > 0)


    def __str__(self):
        return f'''
        command: {self._command}
        item: {self.getItem()}
        flags: {self._flags}
        vars: {self._vars}
        '''


    def runSetup(self):
        is_select = apt.confirmation("This looks like your first time running \
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
                    Profile.reloadDefault(importing=True)
                    break
                elif(Profile('', url=resp)):
                    break
                resp = input()
                pass
        #decided to not run setup prompt or we have no workspaces
        if(not is_select or len(apt.SETTINGS['workspace'].keys()) == 0):
            #ask to create workspace
            ws_name = input("Enter a workspace name: ")
            while(len(ws_name) == 0 or ws_name.isalnum() == False):
                ws_name = input()
            apt.SETTINGS['workspace'][ws_name] = dict()
            
        #ask for name to store in settings
        feedback = input("Enter your name: ")
        apt.SETTINGS['general']['author'] = apt.SETTINGS['general']['author'] if(feedback.strip() == cfg.NULL) else feedback.strip()
        #ask for test-editor to store in settings
        feedback = input("Enter your text-editor: ")
        apt.SETTINGS['general']['editor'] = apt.SETTINGS['general']['editor'] if(feedback.strip() == cfg.NULL) else feedback.strip()
        pass

    #! === INSTALL COMMAND ===

    #install block to cache, and recursively install dependencies
    def install(self, title, ver=None, required_by=[]):
        '''
        This method performs the install command. It will recursively install
        any dependencies and ensure no duplicate installation attempts through the
        'required_by' argument. If ver=None, it will install the latest version.
        Title consists of a block's L and N.
        '''
        _,l,n,_ = Block.snapTitle(title)
        block = None
        cache_path = apt.WORKSPACE+"cache/"
        verify_url = False
        already_installed = False
        #does the package already exist in the cache directory?
        if(self.db.blockExists(title, "cache", updt=True)):
            block = self.db.getBlocks("cache")[l][n]
            #list all versions available in cache
            vers_instl = os.listdir(cache_path+l+"/"+n+"/")
            #its already installed if its in cache with no specific version or the version folder exists
            if(ver == None):
                log.info(title+" is already installed.")
                already_installed = True
            elif(ver in vers_instl):
                log.info(title+"("+ver+") is already installed.")
                already_installed = True
        elif(self.db.blockExists(title, "local", updt=True)):
            block = self.db.getBlocks("local")[l][n]
            verify_url = True
        elif(self.db.blockExists(title, "market")):
            block = self.db.getBlocks("market")[l][n]
        else:
            exit(log.error(title+" cannot be found anywhere."))
        #append to required_by list used to prevent cyclic recursive nature
        required_by.append(block.getTitle()+'('+block.getVersion()+')')
        #see if all cache blocks are available by looking at block's derives list
        for prereq in block.getMeta("derives"):
            if(prereq == block.getTitle() or prereq in required_by):
                continue
            #split prereq into library, name, and version
            M,L,N,verreq = block.snapTitle(prereq)

            needs_instl = False
            if(self.db.blockExists(prereq, "cache", updt=True) == False):
                #needs to install
                log.info("Requires "+prereq)
                #auto install dependency to cache if not found in cache
                needs_instl = True
            else:
                cache_blk = self.db.getBlocks("cache")[L][N]
                #auto install dependency to cache if version is not found in cache
                vers = os.listdir(cache_blk.getPath()+"../")
                if verreq not in vers:
                    needs_instl = True
            if(needs_instl):
                self.install(L+'.'+N, ver=verreq, required_by=required_by)
              
        #no work needed to be done on this block if already installed (version found in cache)
        if(already_installed):
            return
        #see what the latest version available is and clone from that version unless specified
        isInstalled = self.db.blockExists(title, "cache")
        #now check if block needs to be installed from market
        if(not isInstalled):
            if(verify_url):
                if(apt.isValidURL(block.getMeta("remote")) == False):
                    log.warning("No remote to install from.")

            clone_path = block.getMeta("remote")
            #must use the local path of the local block if no remote
            if(clone_path == None):
                clone_path = block.getPath()

            block.install(cache_path, block.getVersion(), clone_path)
            #now update to true because it was just cloned from remote
            isInstalled = True
        elif(self.db.blockExists(title, "market") == False and self.db.blockExists(title, "cache") == False):
            log.warning(title+" does not exist for this workspace or its markets.")

        #now try to install specific version if requested now that the whole branch was cloned from remote
        if(ver != None and isInstalled):
            block.install(cache_path, ver)

        pass

    #! === UNINSTALL COMMAND ===

    def uninstall(self, blk, ver):
        '''
        This method performs the uninstall command. A warning with a preview of
        the directories/versions that will be deleted are issued to the user
        before proceeding to delete the installations. If deleting a version
        that is also the major version, it will attempt to find a new 
        replacement for being the highest major version.
        '''
        #remove from cache
        _,l,n,_ = Block.snapTitle(blk)
        base_cache_dir = apt.WORKSPACE+"cache/"+l+"/"+n+"/"
        if(self.db.blockExists(blk, "cache")):
            vers_instl = os.listdir(base_cache_dir)
            
            #delete all its block stuff in cache
            if(ver == None):
                prmpt = 'Are you sure you want to uninstall the following?\n'
                #print all folders that will be deleted
                for v in vers_instl:
                    if(Block.validVer(v) or Block.validVer(v, maj_place=True) or v.lower() == n):
                        prmpt = prmpt + base_cache_dir+v+"/\n"
                #ask for confirmation to delete installations
                confirm = apt.confirmation(prmpt)
                if(confirm):
                    shutil.rmtree(base_cache_dir, onerror=apt.rmReadOnly)
                else:
                    exit(log.info("Did not uninstall block "+blk+"."))
            #only delete the specified version
            elif(os.path.isdir(base_cache_dir+ver+"/")):
                #track what versions will no longer be available
                rm_vers = []
                tmp_blk = self.db.getBlocks("cache")[l][n]
                remaining_vers = tmp_blk.sortVersions(tmp_blk.getTaggedVersions())
                prmpt = 'Are you sure you want to uninstall the following?\n'
                prmpt = prmpt + base_cache_dir+ver+"/\n"
                
                #determine this version's parent
                parent_ver = ver[:ver.find('.')]
                #removing an entire parent version space
                if(ver.find('.') == -1):
                    parent_ver = ver
                    for v in vers_instl:
                        if(v[:v.find('.')] == parent_ver):
                            rm_vers.append(v)
                            prmpt = prmpt + base_cache_dir+v+"\n"
                
                rm_vers.append(ver)

                next_best_ver = None
                #open the project and see what version is being used
                if(os.path.isdir(base_cache_dir+parent_ver+"/")):
                    parent_meta = dict()
                    with open(base_cache_dir+parent_ver+"/"+apt.MARKER, 'r') as tmp_f:
                        parent_meta = cfg.load(tmp_f, ignore_depth=True)
                        tmp_f.close()
                    #will have to try to revert down a version if its being used in parent version
                    rm_parent = (parent_meta['version'] == ver[1:])

                    if(rm_parent and parent_ver != ver):
                        prmpt = prmpt + base_cache_dir+parent_ver+"\n"
    
                        #grab the highest version found that left from installed
                        remaining_vers.remove(ver)
                        
                        for v in remaining_vers:
                            if(v[:v.find('.')] == parent_ver and v in vers_instl and v not in rm_vers):
                                next_best_ver = v
                        print(remaining_vers)
                        print(next_best_ver)

                confirm = apt.confirmation(prmpt)
                
                if(confirm):
                    for v in rm_vers:
                        shutil.rmtree(base_cache_dir+v+"/", onerror=apt.rmReadOnly)
                    #delete parent if specified
                    if(rm_parent):
                        shutil.rmtree(base_cache_dir+parent_ver+"/", onerror=apt.rmReadOnly)
                    #if found, update parent version to next best available level
                    if(next_best_ver != None):
                        tmp_blk.install(apt.WORKSPACE+"cache/", next_best_ver)
                else:
                    exit(log.info("Did not uninstall block "+blk+"."))
            else:
                exit(log.error("Block "+blk+" version "+ver+" is not installed to the workspace's cache."))
            #if empty dir then do some cleaning
            clean = True
            for d in os.listdir(apt.WORKSPACE+"cache/"+l):
                if(d.startswith('.') == False):
                    clean = False
            if(clean):
                shutil.rmtree(apt.WORKSPACE+"cache/"+l+"/", onerror=apt.rmReadOnly)
        else:
            exit(log.error("Block "+blk+" is not installed to the workspace's cache."))

        log.info("Successfully uninstalled block "+blk+".")

        pass

    #! === BUILD COMMAND ===

    def build(self, script):
        '''
        This method performs the build command. It will search the available
        scripts in the settings and call it accordingly. Arguments found after
        the script name on the command line are passed to the build script.
        '''
        script_identifier = "+"
        arg_start = 3
        
        if(not isinstance(apt.SETTINGS['script'],dict)): #no scripts exist
            exit(log.error("No scripts are configured!"))
        elif(len(script) and script.startswith(script_identifier)):
            stripped_name = script[len(script_identifier):]
            if(stripped_name in apt.SETTINGS['script'].keys()): #is it a name?
                cmd = apt.SETTINGS['script'][stripped_name]
            else:
                exit(log.error("Build script "+stripped_name+" not found!"))
        elif("master" in apt.SETTINGS['script'].keys()): #try to resort to default
            cmd = apt.SETTINGS['script']['master']
            arg_start = 2
        elif(len(apt.SETTINGS['script'].keys()) == 1): #if only 1 then try to run the one
            cmd = apt.SETTINGS['script'][list(apt.SETTINGS['script'].keys())[0]]
            arg_start = 2
        else:
            exit(log.error("No master script is configured!"))

        #remove quotes from command
        cmd = cmd.replace("\'","")
        cmd = cmd.replace("\"","")

        for i,arg in enumerate(sys.argv):
            if(i < arg_start):
                continue
            else:
                cmd = cmd + " " + arg
        
        apt.execute(cmd, quiet=False)

    #! === EXPORT/GRAPH COMMAND ===

    def export(self, block, top=None, options=[]):
        '''
        This method performs the export command. The requirements are organized 
        into a topologically sorted graph and written to the blueprint file. It
        also searches for recursive/shallow custom labels within the required
        blocks.
        '''
        log.info("Exporting...")
        log.info("Block's path: "+block.getPath())
        build_dir = block.getPath()+"build/"
        #create a clean build folder
        log.info("Cleaning build folder...")
        if(os.path.isdir(build_dir)):
            shutil.rmtree(build_dir, onerror=apt.rmReadOnly)
        os.mkdir(build_dir)

        inc_sim = (options.count('ignore-tb') == 0)

        blueprint_filepath = build_dir+"blueprint"

        log.info("Finding toplevel design...")

        #get the Unit objects for the top_dog, top design, and top testbench
        top_dog,top,tb = block.identifyTopDog(top, inc_sim=inc_sim)
        #print(top_dog,top,tb)
        
        output = open(blueprint_filepath, 'w')   

        #mission: recursively search through every src VHD file for what else needs to be included
        unit_order,block_order = self._graph(block, top_dog)
        file_order = self.compileList(block, unit_order)  

        #add labels in order from lowest-projects to top-level project
        labels = []
        #track what labels have already been defined by the same block
        latest_defined = dict()
        for blk in block_order:
            spec_path = None
            #break into market, library, name, version
            M,L,N,V = Block.snapTitle(blk)
            #reassemble block title
            blk = L+'.'+N
            #assign tmp block to the current block
            if(block.getTitle() == blk):
                tmp = block
            #assign tmp block to block in downloads if multi-develop enabled and version is none
            elif(V == None and self.db.blockExists(blk, "local") and apt.SETTINGS['general']['multi-develop']):
                tmp = self.db.getBlocks("local")[L][N]
            #assign tmp block to the cache block
            elif(self.db.blockExists(blk, "cache")):
                tmp = self.db.getBlocks("cache")[L][N]
            else:
                log.warning("Cannot locate block "+blk+" for label searching")
                continue

            spec_path = tmp.getPath()

            #using the version that was latched onto the name, alter cache path setting?
            if(V != None):
                #print(tmp.getPath())
                base_cache_path = os.path.dirname(tmp.getPath()[:len(tmp.getPath())-1])
                spec_path = base_cache_path+"/"+V+"/"
                pass
            #create new element if DNE
            if(blk not in latest_defined.keys()):
                latest_defined[blk] = ['0.0.0', dict()]
            #update latest defined if a bigger version has appeared
            overwrite = False
            #determine the current version being processed
            if(V == None):
                V = tmp.getVersion()
            #will overwrite the label values for this block if its a higher version
            if(Block.biggerVer(latest_defined[blk][0], V) == V):
                overwrite = True
                latest_defined[blk][0] = V

            #add any recursive labels
            for label,ext in apt.SETTINGS['label']['recursive'].items():
                files = tmp.gatherSources(ext=[ext], path=spec_path)
                for f in files:
                    lbl = "@"+label+" "+apt.fs(f)
                    #is used when duplicate-recursive-labels is enabled
                    labels.append(lbl)
                    #is used when duplicate-recursive-labels is disabled
                    if(overwrite):
                        basename = os.path.basename(f).lower()
                        latest_defined[blk][1][basename] = lbl
                    pass
            #add any project-level labels
            if(block.getTitle() == blk):
                for label,ext in apt.SETTINGS['label']['shallow'].items():
                    files = block.gatherSources(ext=[ext])
                    for f in files:
                        lbl = "@"+label+" "+apt.fs(f)
                        #is used when duplicate-recursive-labels is enabled
                        labels.append(lbl)
                        #is used when duplicate-recursive-labels is disabled
                        basename = os.path.basename(f).lower()
                        latest_defined[blk][1][basename] = lbl
                        pass
        #determine if to write all recursive labels or not
        if(not apt.SETTINGS['general']['overlap-recursive']):
            labels = []
            for blk in latest_defined.keys():
                for lbl in latest_defined[blk][1].values():
                    labels.append(lbl)

        for l in labels:
            output.write(l+"\n")
        for f in file_order:
            output.write(f+"\n")

        #write top-level testbench entity label
        if(tb != None):
            line = '@'
            if(tb.getLanguageType() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(tb.getLanguageType() == Unit.Language.VERILOG):
                line = line+"VLOG"
            #set simulation design unit by its entity name by default
            tb_name = tb.getName(low=False)
            #set top bench design unit name by its configuration if exists
            if(tb.getConfig() != None):
                tb_name = tb.getConfig()
            output.write(line+"-SIM-TOP "+tb_name+" "+tb.getFile()+"\n")

        #write top-level design entity label
        if(top != None):
            line = '@'
            if(top.getLanguageType() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(top.getLanguageType() == Unit.Language.VERILOG):
                line = line+"VLOG"
            output.write(line+"-SRC-TOP "+top.getName(low=False)+" "+top.getFile()+"\n")
            
        output.close()
        #update the derives section to give details into what blocks are required for this one
        block.updateDerivatives(block_order)

        log.info("Blueprint located at: "+blueprint_filepath)
        log.info("success")
        pass


    def _graph(self):
        '''Run the 'graph' command.'''

        self.WS().loadLocalBlocks(id_dsgns=True)
        block = Block.getCurrent()

        top = self.getItem()
        top_dog,_,_ = block.identifyTopDog(top, inc_tb=True)
        
        log.info("Generating dependency tree...")
        #start with top unit (returns all units if no top unit is found (packages case))
        block.getUnits(top_dog.E())
        hierarchy = Unit.Hierarchy

        #print the dependency tree
        hierarchy.output(top_dog)
        print()
        
        unit_order,block_order = hierarchy.topologicalSort()

        print('---  BLOCK ORDER   ---')
        #ensure the current block is the last one on order
        block_order.remove(block.getFull())
        block_order.append(block.getFull())
        for i in range(0, len(block_order)):
            b = block_order[i]
            print(str(i+1)+' >\t'+b,end='\n')
            if(i < len(block_order)-1):
                print(' ',end='')
        print()

        return unit_order,block_order


    def _export(self):
        '''Run the 'graph' command.'''

        self.WS().loadLocalBlocks(id_dsgns=True)
        block = Block.getCurrent()

        #trying to export a package file?
        if(self.hasFlag('pack')):
            self.autoPackage()
            return

        top = self.getItem()
        top_dog,dsgn,tb = block.identifyTopDog(top, inc_tb=True)
        #start with top unit (returns all units if no top unit is found (packages case))
        block.getUnits(top_dog.E())

        unit_order,block_order = Unit.Hierarchy.topologicalSort()

        #get all label data :todo:
        for title in block_order:
            for lbl in Label.Jar.values():
                print(lbl.getName(),lbl.getExtensions())
                #gatherSources(lbl.getExtensions())
            pass

        blueprint_data = self.compileList(block, unit_order)

        #write top-level testbench entity label
        if(tb != None):
            line = '@'
            if(tb.getLang() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(tb.getLang() == Unit.Language.VERILOG):
                line = line+"VLOG"
            #set simulation design unit by its entity name by default
            tb_name = tb.E()
            #set top bench design unit name by its configuration if exists
            if(tb.getConfig() != None):
                tb_name = tb.getConfig()
            #add to blueprint's data for top-level testbench
            blueprint_data += [line+"-SIM-TOP "+tb_name+" "+tb.getFile()]

        #write top-level design entity label
        if(dsgn != None):
            line = '@'
            if(dsgn.getLang() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(dsgn.getLang() == Unit.Language.VERILOG):
                line = line+"VLOG"
            #add to blueprint's data for top-level design
            blueprint_data += [line+"-SRC-TOP "+dsgn.E()+" "+dsgn.getFile()]

        log.info("Exporting blueprint...")
        log.info("Block's path: "+block.getPath())
        
        #clean the build directory
        log.info("Cleaning build folder...")
        build_dir = block.getPath()+"build/"
        if(os.path.isdir(build_dir)):
            shutil.rmtree(build_dir, onerror=apt.rmReadOnly)
        #create the build directory
        os.makedirs(build_dir, exist_ok=True)

        #create the blueprint file
        blueprint_path = build_dir+"blueprint"
        blueprint = open(blueprint_path, 'w')

        #write all data to the blueprint
        for line in blueprint_data:
            blueprint.write(line+'\n')

        pass


    def autoPackage(self):
        '''
        Auto-generate a VHDL package file for design units within the current block.
        
        Parameters:
            None
        Returns:
            None
        '''
        block = Block.getCurrent()

        pkg_name = block.N()+"_pkg"

        pkg_data = ['-- Auto-generated package file by legoHDL.'] + ['package '+pkg_name] + [' ']


        libs = []
        pkgs = []

        #get all units
        units = block.loadHDL().values()
        for dsgn in units:
            #only add design units (entities)
            if(dsgn.isTb() or dsgn.isPkg()):
                continue
            #copy any of their library declarations
            for lib in dsgn.getLibs():
                if(lib.lower() not in libs):
                    pkg_data.insert(1, 'library '+lib+';')
                    libs += [lib.lower()]
            #copy any of their package declarations
            for pkg in dsgn.getPkgs():
                if(pkg.lower() not in pkgs):
                    pkg_data.insert(2, 'use '+pkg+';')
                    pkgs += [pkg.lower()]

            pkg_data += ['\tcomponent '+dsgn.E()]
            pkg_data += ['\tend component;'] + [' ']
            
        pkg_data += ['end package;']

        #create package file
        pkg_path = block.getPath()+pkg_name+'.vhd'
        pkg_file = open(pkg_path, 'w')

        #dump contents into package file
        for line in pkg_data:
            pkg_file.write(line+"\n")

        pass


    def compileList(self, block, unit_order):
        '''
        Formats units with their file into the blueprint structure with respective labels.

        Parameters:
            block (Block): the current working block object
            unit_order ([Unit]): in-order list of units to synthesize
        Returns:
            data ([str]): list of lines for blueprint file
        '''
        data = []
        #iterate through each unit
        for dsgn in unit_order:
            line = '@'
            if(dsgn.getLang() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(dsgn.getLang() == Unit.Language.VERILOG):
                line = line+"VLOG"
            #this unit comes from an external block so it is a library file
            if(dsgn not in list(block.loadHDL().values())):
                line = line+'-LIB '+dsgn.L()+' '
            #this unit is a simulation file
            elif(dsgn.isTb()):
                line = line+'-SIM '
            #this unit is a source file
            else:
                line = line+'-SRC '
            #append file onto line
            line = line + dsgn.getFile()
            #add to blueprint list
            data.append(line)

        return data


    #! === DOWNLOAD COMMAND ===
    #will also install project into cache and have respective pkg in lib
    def download(self, title, reinstall=True):
        '''
        This method performs the download command. It will force a reinstallation
        when 'reinstall' is True. A title is a block's L and N. It will try to
        clone from a git repository if available, else it will clone from the
        cache.
        '''
        _,l,n,_ = Block.snapTitle(title)
        success = True
        #1. download
        #update local block if it has a remote
        if(self.db.blockExists(title, "local")):
            blk = self.db.getBlocks("local")[l][n]
            #pull from remote url
            blk.pull()
        #download from market
        elif(self.db.blockExists(title, "market")):
            blk = self.db.getBlocks("market")[l][n]
            log.info("Downloading "+blk.getTitle()+" from "+str(blk.getMeta('market'))+' with '+blk.getMeta('remote')+"...")
            #use the remote git url to download/clone the block
            success = blk.downloadFromURL(blk.getMeta("remote"))
        #download from the cache
        elif(self.db.blockExists(title, "cache")):
            blk = self.db.getBlocks("cache")[l][n]
            dwnld_path = blk.getPath()
            if(blk.grabGitRemote() != None):
                dwnld_path = blk.grabGitRemote()
            log.info("Downloading "+blk.getTitle()+" from cache with "+dwnld_path+"...")
            #use the cache directory to download/clone the block
            success = blk.downloadFromURL(dwnld_path)
            #now return the block if wanting to open it with -o option
            return success
        else:
            exit(log.error('Block \''+title+'\' does not exist in any linked market for this workspace'))
        
        if(not reinstall):
            return success
        #2. perform re-install
        cache_block = None
        in_cache = self.db.blockExists(blk.getTitle(), "cache")
        if(in_cache):
            cache_block = self.db.getBlocks(blk.getTitle(), "cache")[l][n]
        if(not in_cache or Block.biggerVer(blk.getVersion(), cache_block.getVersion()) == blk.getVersion() and blk.getVersion() != cache_block.getVersion()):
            try: #remove cached project already there
                shutil.rmtree(apt.WORKSPACE+"cache/"+l+"/"+n+"/"+n+"/", onerror=apt.rmReadOnly)
            except:
                pass
            #update cache installation if a new version is available
            self.install(title, None)
        
        return success


    #! === RELEASE COMMAND ===
    def upload(self, block, msg=None, options=None):
        '''
        This method performs the release command. A block becomes released and
        gains a release point with a special git tag. Users can optionally pass
        a 'msg' for the git commit.
        '''
        err_msg = "Flag the next version for release with one of the following args:\n"\
                    "\t[-v0.0.0 | -maj | -min | -fix]"
        if(len(options) == 0):
                exit(log.error(err_msg))
            
        ver = None
        #find the manually entered version number
        for opt in options:
            if(Block.validVer(opt)):
                ver = Block.stdVer(opt)
                break
        
        if(options[0] != 'maj' and options[0] != 'min' and options[0] != 'fix' and ver == None):
            exit(log.error(err_msg))
        #ensure top has been identified for release
        # :todo: allow user to specify what is top level explictly?
        top_dog,_,_ = block.identifyTopDog(None)
        #update block requirements
        _,block_order = self._graph(block, top_dog)
        block.updateDerivatives(block_order)
        block.release(msg, ver, options)
        #don't look to market when updating if the block does not link to market anymore
        bypassMrkt = (block.getMeta('market') not in apt.getMarkets())
        self.update(block.getTitle(low=False), block.getVersion(), bypassMrkt=bypassMrkt)

        log.info(block.getLib()+"."+block.getName()+" is now available as version "+block.getVersion()+".")
        pass


    #! === INIT COMMAND ===
    def convert(self, value, options=[]):
        '''
        This method performs the init command. It takes an existing project
        and tries to convert it into a valid block by creating a Block.cfg 
        file, and a git repository if needed.
        '''
        #must look through tags of already established repo
        m,l,n,_ = Block.snapTitle(value, lower=False)
        if((l == '' or n == '') and len(options) == 0):
            exit(log.error("Must provide a block title <library>.<block-name>"))
        #get the current directory where its specified to initialize
        cwd = apt.fs(os.getcwd())
        #make sure this path is witin our workspace's path before making it a block
        if(apt.isSubPath(apt.getLocal(), cwd) == False):
            exit(log.error("Cannot initialize outside or at root of workspace path "+apt.getLocal()))

        block = None
        #check if we are trying to init something other than an actual project to block
        if(self.blockCWD.isValid()):
            #alter market name
            if(options.count("market")):
                #try to validate market
                mkt_obj = self.identifyMarket(value)
                if(mkt_obj == None):
                    exit(log.error("No market is recognized under "+value))
                #pass the market name to set in metadata
                self.blockCWD.bindMarket(mkt_obj.getName(low=False))
            #alter remote repository link
            elif(options.count("remote")):
                #link to this remote if its valid
                if(apt.isValidURL(value)):
                    self.blockCWD.setRemote(value)
                #remove a remote if value is blank
                elif(value == ''):
                    log.info("Removing any possible linkage to a remote...")
                    self.blockCWD.setRemote(None)
                #else display error
                else:
                    exit(log.error("Invalid git url."))
            #alter summary description
            elif(options.count("summary")):
                self.blockCWD.setMeta('summary', value)
                self.blockCWD.save()
            #no other flags are currently supported
            elif(len(options)):
                    exit(log.error("Could not fulfill init option flag '"+options[0]+"'"))
            #done initializing this already existing block
            return

        #proceed with initializing current files/folder into a block format

        #check if a block already exists at this folder
        files = os.listdir(cwd)
        if apt.MARKER in files:
            exit(log.info("This folder already has a Block.cfg file."))
        else:
            log.info("Transforming project into block...")
       
        #determine if the project should be opened after creation
        startup = options.count("open")
        #determine if the repository used to initialize should be kept or removed
        fork = options.count("fork")

        #try to find a valid git url
        git_url = None
        for opt in options:
            if(apt.isValidURL(opt)):
                git_url = opt
                break

        #check if wanting to initialize from a git url
        #is this remote bare? If not, clone from it
        if(git_url != None and apt.isRemoteBare(git_url) == False):
            #clone the repository if it is not bare, then add metadata
            #git.Git(cwd).clone(git_url)
            #replace url_name with given name
            url_name = git_url[git_url.rfind('/')+1:git_url.rfind('.git')]
            cwd = apt.fs(cwd + '/' + url_name)
            files = os.listdir(cwd)
            #print(cwd)

        #rename current folder to the name of library.project
        last_slash = cwd.rfind('/')
        #maybe go one additional slash back to get past name
        if(last_slash == len(cwd)-1):
            last_slash = cwd[:cwd.rfind('/')].rfind('/')

        cwdb1 = cwd[:last_slash]+"/"+n+"/"
        #print(cwdb1)
        try:
            os.rename(cwd, cwdb1)
        except PermissionError:
            log.warning("Could not rename project folder to "+cwdb1+".")
            pass

        git_exists = False
        #see if there is a .git folder
        if(".git" in files):
            git_exists = True
            pass
        else:
            log.info("Initializing git repository...")
            #git.Repo.init(cwdb1)                
            git_exists = True
            pass

        #try to validate market
        mkt_obj = self.identifyMarket(m)

        #create marker file
        block = Block(title=l+'.'+n, path=cwdb1, remote=git_url, market=mkt_obj)
        block.genRemote(push=False)
        log.info("Creating "+apt.MARKER+" file...")
        block.create(fresh=False, git_exists=git_exists, fork=fork)

        if(startup):
            block.openInEditor()
        pass

    def identifyMarket(self, m):
        '''
        Return a market object if the market name is found within the workspace.

        Parameters
        ---
        m : market name
        '''
        #try to attach a market
        for mkt in self.db.getMarkets():
            if(m.lower() == mkt.getName()):
                log.info("Identified "+mkt.getName()+" as block's market.")
                return mkt
        if(len(m)):
            log.warning("No market "+m+" can be configured for this block.")
        return None

    #! === DEL COMMAND ===

    def cleanup(self, block, force=False):
        '''
        This method performs the del command. The force parameter will also
        remove all installations from the cache. If this is all that is left of
        a block, a warning will be issued to the user before deletion.
        '''
        if(not block.isValid()):
            log.info('Block '+block.getName()+' does not exist locally.')
            return
        #ask to confirm if it has no releases OR its not linked and we are forcing it to be uninstalled too
        if(block.getVersion() == '0.0.0' or (not block.isLinked() and force)):
            confirmed = apt.confirmation('No market is configured or any released versions for '+block.getTitle()+'. \
If it is deleted and uninstalled, it may be unrecoverable. PERMANENTLY REMOVE '+block.getTitle()+'?')
        
            if(not confirmed):
                exit(log.info("Did not remove nor uninstall "+block.getTitle()+'.'))

        #if there is a remote then the project still lives on, can be "redownloaded"
        log.info("Deleting "+block.getTitle()+" block found here: "+block.getPath())
        try:
            shutil.rmtree(block.getPath(), onerror=apt.rmReadOnly)
        except PermissionError:
            log.warning("Could not delete block's root folder from local workspace because it is open in another process.")

        #if empty dir then do some cleaning
        slash = block.getPath()[:len(block.getPath())-2].rfind('/')
        root = block.getPath()[:slash+1]
        clean = True
        for d in os.listdir(root):
            if(d.startswith('.') == False):
                clean = False
        if(clean):
            shutil.rmtree(root, onerror=apt.rmReadOnly)
        log.info('Deleted '+block.getTitle()+' from local workspace.')
        
        if(force):
            self.uninstall(block.getTitle(), None)
        #delete the module remotely?
        pass


    #! === UPDATE COMMAND ===
    def update(self, title, ver=None, bypassMrkt=False):
        '''
        This method perfoms the update command for blocks and/or profiles. The
        bypassMrkt parameter is set True when a block is being newly released,
        it won't look to market when updating if the block does not link to 
        market anymore to perform re-installation. Update will perform git pull
        on the cache and update the cache's main/master git commit line.
        '''
        _,l,n,_ = Block.snapTitle(title)
        #check if market version is bigger than the installed version
        c_ver = '0.0.0'
        if(self.db.blockExists(title, "cache")):
            cache_block = self.db.getBlocks("cache", updt=True)[l][n]
            c_ver = cache_block.getVersion()

        m_ver = ver
        if(not bypassMrkt and self.db.blockExists(title, "market")):
            mrkt_block = self.db.getBlocks("market", updt=True)[l][n]
            m_ver = mrkt_block.getVersion()
        elif(ver == None):
            exit(log.error(title+" cannot be updated from any of the workspace's markets."))
        
        if((Block.biggerVer(m_ver,c_ver) == m_ver and m_ver != c_ver)):
            log.info("Updating "+title+" installation to v"+m_ver)
            #remove from cache's master branch to be reinstalled
            base_installation = apt.WORKSPACE+"cache/"+l+"/"+n+"/"+n+"/"
            
            if(os.path.isdir(base_installation)):
                shutil.rmtree(base_installation, onerror=apt.rmReadOnly)
            
            #clone new project's progress into cache
            self.install(title, None)

            #also update locally if exists
            if(self.db.blockExists(title,"local")):
                self.download(title, reinstall=False)
            
        else:
            log.info(title+" already up-to-date. (v"+c_ver+")")
        pass


    def checkVar(self, key, val):
        '''
        Checks if val equals the value stored behind the key in the
        _vars map. Returns false if key DNE.
        
        Parameters:
            key (str): key to check value behind in _vars
            val (str): value to compare with
        Returns:
            (bool): if val was equal to key's value in _vars
        '''
        if(key not in self._vars.keys()):
            return False
        else:
            return val == self._vars[key]

    
    def splitVar(self, val, delim=':'):
        '''
        Splits the value of the variable into two parts based
        on the delimiter. Returns '' for second component if delim DNE.

        Parameters:
            val (str): the variable value
            delim (str): the substring to find in val
        Returns:
            key (str): first component of val
            val (str): second component of val
        '''
        d_i = val.find(delim)
        if(d_i > -1):
            return val[0:d_i], val[d_i+1:]
        else:
            return val, ''

    
    def _get(self):
        '''Run the 'get' command.'''

        self.WS().loadLocalBlocks()
        if(self.hasFlag('about')):
            self.WS().decodeUnits()
        #make sure an entity is being requested
        if(self.getItem() == None):
            exit(log.error("Pass an entity name to get."))
        block = self.WS().shortcut(self.getItem(), req_entity=True)
        #:todo: make better
        _,_,_,_,ent = Block.snapTitle(self.getItem(), inc_ent=True)
        if(block == None):
            exit(log.error("Could not identify a block with "+self.getItem()))
        block.get(ent, self.hasFlag('about'), self.hasFlag('arch'), self.hasFlag('inst'), lang=(self.getVar('inst')))
        pass


    def _init(self):
        '''Run the 'init' command.'''
        cur_path = apt.fs(os.getcwd())
        
        block = Block(cur_path, self.WS())
        block.initialize(self.getItem(), self.getVar('remote'), self.hasFlag('fork'), self.getVar('summary'))
        pass

    
    def _info(self):
        '''Run the 'info' command.'''
        #make sure the user passed in a value for the item
        if(self.getItem() == None):
            exit(log.error("Include a block's title to get its information."))

        block = self.WS().shortcut(self.getItem())
        if(block != None):
            print(block.readInfo(self.hasFlag('all'), self.hasFlag('stats'), self.hasFlag('versions'))) 
        pass


    def _config(self):
        '''Run 'config' command.'''

        #import a profile if a profile name is given as item.
        if(self.getItem(raw=True) in Profile.Jar.keys()):
            Profile.Jar[self.getItem(raw=True)].importLoadout(ask=self.hasFlag('ask'))
            return

        #set each setting listed in flags try to modify it
        for k,v in self._vars.items():
            #split the variable into two components (if applicable)
            var_key, var_val = self.splitVar(v)
            #print(var_key, var_val)
            #modify script
            if(k == 'script'):
                #verify proper format is passed in
                if(var_key == ''):
                    log.error("Must provide a script alias.")
                    continue

                #modify existing script
                if(var_key.lower() in Script.Jar.keys()):
                    Script.Jar[var_key].setCommand(var_val)
                #create a new script
                else:
                    Script(var_key, var_val)

                #save script modifications
                Script.save()
                pass
            #modify label
            elif(k == 'label'):
                #verify proper format is passed in
                if(var_key == ''):
                    log.error("Must provide a label name.")
                    continue

                #modify existing label
                if(var_key.lower() in Label.Jar.keys()):
                    Label.Jar[var_key].setExtensions(apt.strToList(var_val))
                    Label.Jar[var_key].setRecursive(self.hasFlag('recursive'))
                #create new label
                else:
                    Label(var_key, apt.listToStr(var_val), self.hasFlag('recursive'))
                #save any changes
                Label.save()
                pass
            #modify profile
            elif(k == 'profile'):
                #try to create a profile!
                if(v != ''):
                    #try url
                    if(Git.isValidRepo(v, remote=True) or Git.isValidRepo(v, remote=False)):
                        Profile('', url=v)
                    #try just new name
                    elif(v.lower() not in Profile.Jar.keys()):
                        log.info("Creating new empty profile "+v+"...")
                        Profile(v)
                    else:
                        log.error("Profile "+v+" already exists.")
                        continue
                    
                Profile.save()
                pass
            #modify market
            elif(k == 'market'):
                #ensure a market name is given
                if(var_key == ''):
                    log.error("Must provide a market name.")
                    continue

                mrkt = None
                #modify an existing market
                if(var_key.lower() in Market.Jar.keys()):
                    mrkt = Market.Jar[var_key]

                    #if its local and remote given try to set a remote
                    if(mrkt.isRemote() == False and var_val != ''):
                        mrkt.setRemoteURL(var_val)
                #market name is not found
                else:
                    #try to create from the url
                    if(var_val != ''):
                        mrkt = Market(var_key, var_val)
               
                #alter the workspace's connections to markets
                if(mrkt != None and Workspace.inWorkspace()):
                    if(self.hasFlag('unlink')):
                        self.WS().unlinkMarket(mrkt.getName())
                    elif(self.hasFlag('link')):
                        self.WS().linkMarket(mrkt.getName())
                    pass
                    Workspace.save()
        
                #save adjustments
                Market.save()
                pass
            #modify workspace
            elif(k == 'workspace'):
                #verify proper format is passed in
                if(var_key == ''):
                    log.error("Must provide a workspace name.")
                    continue
                #modify existing workspace's path
                if(var_key.lower() in Workspace.Jar.keys()):
                    Workspace.Jar[var_key].setPath(var_val)
                #create new workspace!
                else:
                    Workspace(var_key, var_val)
                #save adjustments
                Workspace.save()
                pass
            elif(k in apt.SETTINGS['general'].keys()):
                if(k == 'active-workspace'):
                    Workspace.setActiveWorkspace(v)
                    Workspace.save()
                elif(k == 'refresh-rate'):
                    apt.setRefreshRate(v)
                else:
                    #convert to booleans values for these settings
                    if(k == 'multi-develop' or k == 'overlap-recursive'):
                        v = cfg.castBool(v)
                    apt.SETTINGS['general'][k] = v
                #save settings adjusments
                apt.save()
        pass


    def _new(self):
        '''Run 'new' command.'''

        #create a new file
        if(self.hasFlag('file')):
            Block(os.getcwd(), self.WS())
            Block.getCurrent().newFile(self.getItem(raw=True), self.getVar("file"), self.hasFlag('force'))
            return
        
        title = self.getItem()
        #make sure a valid title is captured
        if(Block.validTitle(title) == False):
            return
        M,L,N,_ = Block.snapTitle(title)

        #default path to make a new block :todo: allow user's to edit a setting to specify default download path
        block_path = self.WS().getPath()+L+"/"+N+"/"
        #create block object
        b = Block(block_path, self.WS())
        #create the new block
        b.create(title, cp_template=(self.hasFlag('no-template') == 0), remote=self.getVar('remote'))
        #load the block
        if(self.hasFlag('open')):
            b.load()
        pass


    def _refresh(self):
        '''Run 'refresh' command.'''

        #package value is the market looking to refresh
        #if package value is null then all markets tied to this workspace refresh by default
        if(self.hasFlag('all')):
            log.info("Refreshing all markets...")
            for mkrt in Market.Jar.values():
                mkrt.refresh()
        elif(self.getItem() == None):
            log.info("Refreshing all workspace markets...")
            for mrkt in self.WS().getMarkets():
                mrkt.refresh()
        elif(self.getItem() in Market.Jar.keys()):
            Market.Jar[self.getItem()].refresh()
        pass


    def _list(self):
        '''Run 'list' command.'''

        if(self.hasFlag("script")):
            Script.printList()
        elif(self.hasFlag("label")):
            Label.printList()
        elif(self.hasFlag("market")):
            Market.printList(self.WS().getMarkets())
        elif(self.hasFlag("workspace")):
            Workspace.printList()
        elif(self.hasFlag("profile")):
            Profile.printList()
        elif(self.hasFlag("template")):
            apt.getTemplateFiles()
        elif(self.hasFlag('entity')):
            self.WS().listUnits()
            #categorize by hidden files (skipped)
            #and visible files (files that are copied in on using template)
        else:
            M,L,N,_ = Block.snapTitle(self.getItem())
            self.WS().listBlocks(M, N, L)
        pass


    def _open(self):
        '''Run 'open' command.'''

        valid_editor = apt.getEditor() != cfg.NULL
        #open the settings (default is gui mode)
        if(self.hasFlag("settings")):
            gui_mode = True
            if('settings' in self._vars.keys()):
                gui_mode = not self.checkVar('settings', 'file')
            #try to open in gui
            if(gui_mode):
                settings_gui = GUI()
                #adjust success if initialization failed
                gui_mode = settings_gui.initialized() 

            if(valid_editor and gui_mode == False):
                log.info("Opening settings CFG file at... "+apt.fs(apt.HIDDEN+apt.SETTINGS_FILE))
                apt.execute(apt.getEditor(), apt.fs(apt.HIDDEN+apt.SETTINGS_FILE))
            elif(gui_mode == True):
                return
            pass
        #cannot open anything without a text-editor!
        if(valid_editor == False):
            exit(log.error("No text-editor configured!"))
        #open template
        if(self.hasFlag("template")):
            log.info("Opening block template folder at... "+apt.fs(apt.TEMPLATE))
            apt.execute(apt.getEditor(), apt.fs(apt.TEMPLATE))
            pass
        #open scripts
        elif(self.hasFlag("script")):
            #want to open the specified script?
            script_path = apt.fs(apt.HIDDEN+"scripts")

            #maybe open up the script file directly if given a value
            if(self._item.lower() in Script.Jar.keys()):
                #able to open script?
                scpt = Script.Jar[self._item.lower()]
                if(scpt.hasPath()):
                    script_path = scpt.getPath()
                    log.info("Opening script "+self._item+" at... "+script_path)
                else:
                    exit(log.error("Script "+self._item+" has no path to open."))
            elif(self.getItem() == None):
                exit(log.error("Script "+self._item+" does not exist."))

            apt.execute(apt.getEditor(),script_path)
            pass
        #open profile
        elif(self.hasFlag("profile")):
            #open the specified path to the profile if it exists
            if(self._item.lower() in Profile.Jar.keys()):
                prfl_path = Profile.Jar[self._item].getProfileDir()
                log.info("Opening profile "+self._item+" at... "+prfl_path)
                apt.execute(apt.getEditor(), prfl_path)
            else:
                log.error("Profile "+self._item+" does not exist.")
            pass
        #open block
        else: # :todo:
            block = self.WS().shortcut(self.getItem())
            if(block != None):
                block.openInEditor()
            else:
                exit(log.error("No block "+self._item+" exists in your workspace."))
            pass
        pass
            

    def _help(self):
        '''
        Reads from provided manual.txt regarding the _item passed by
        user, given that the _command was 'help'.

        Parameters:
            None
        Returns:
            None
        '''
        #open the manual.txt
        with open(apt.getProgramPath()+'data/manual.txt', 'r') as man:
            info = man.readlines()

            disp = False
            for line in info:
                sep = line.split()
                #skip comments and empty lines
                if(len(sep) == 0):
                    if(disp == True):
                        print()
                    continue
                if(sep[0].startswith(';')):
                    continue
                #find where to start
                if(len(sep) > 1 and sep[0] == '*' and sep[1] == self._item.lower()):
                    disp = True
                elif(disp == True):
                    if(sep[0] == '*'):
                        break
                    else:
                        print(line,end='')       
            else:
                self._default()
        pass
    

    def _default(self):
        '''
        Display quick overview of legoHDL capabilites/commands.

        Parameters:
            None
        Returns:
            None
        '''
        print('USAGE: \
        \n\tlegohdl <command> [argument] [flags]\
        \n')
        print("COMMANDS:\n")
        def formatHelp(cmd, des):
            print('  ','{:<12}'.format(cmd),des)
            pass
        print("Development")
        formatHelp("new","create a new legohdl block (project)")
        formatHelp("init","initialize existing code into a legohdl block")
        formatHelp("open","open a block with the configured text-editor")
        formatHelp("get","print instantiation code for an HDL entity")
        formatHelp("graph","visualize HDL dependency graph")
        formatHelp("export","generate a blueprint file")
        formatHelp("build","execute a custom configured script")
        formatHelp("release","set a newer version for the current block")
        formatHelp("del","delete a block from the local workspace path")
        print()
        print("Management")
        formatHelp("list","print list of all blocks available")
        formatHelp("refresh","sync local markets with their remotes")
        formatHelp("install","bring a block to the cache for dependency use")
        formatHelp("uninstall","remove a block from the cache")
        formatHelp("download","bring a block to the workspace path for development")
        formatHelp("update","update an installed block to be its latest version")
        formatHelp("info","read further detail about a block")
        formatHelp("config","modify legohdl settings")
        print("\nType \'legohdl help <command>\' to read more on entered command.")
        pass


    def runCommand(self):
        '''
        Select from available commands what method to run. Case statement on
        self._command attr.

        Parameters:
            None
        Returns:
            None
        '''
        cmd = self._command

        if('new' == cmd):
            self._new()
            pass

        elif('init' == cmd):
            self._init()
            pass

        elif('open' == cmd):
            self._open()
            pass

        elif('get' == cmd):
            self._get()
            pass

        elif('graph' == cmd):
            self._graph()
            pass

        elif('export' == cmd):
            self._export()
            pass

        elif('build' == cmd):
            
            pass

        elif('release' == cmd):
            
            pass

        elif('del' == cmd):
            
            pass

        elif('list' == cmd):
            self._list()
            pass

        elif('refresh' == cmd):
            self._refresh()
            pass

        elif('install' == cmd):
            
            pass

        elif('uninstall' == cmd):
            
            pass

        elif('download' == cmd):
            
            pass

        elif('update' == cmd):
            
            pass

        elif('info' == cmd):
            self._info()
            pass

        elif('config' == cmd):
            self._config()
            pass

        elif('help' == cmd):
            self._help()
            pass
        
        elif('' == cmd):
            self._default()
            pass
        #notify user when a unknown command was entereds
        else: 
            log.error("Unknown command - "+cmd+".")
            pass

        pass


def main():
    legoHDL()


#entry-point
if __name__ == "__main__":
    main()


# ==============================================================================
# ==============================================================================
# ==============================================================================
# ===== ARCHIVED CODE....TO DELETE ======
# ==============================================================================
# ==============================================================================
# ==============================================================================
#! === PARSING ===
    @DeprecationWarning
    def parse(self, cmd, pkg, opt):
        '''
        This method is the logic for branching between the available commands
        for legoHDL. Some commands can only be ran from within the root of a 
        block's directory.
        '''
        #check if we are in a project directory (necessary to run a majority of commands)
        self.blockCWD = Block(path=os.getcwd()+"/")
        
        command = cmd
        package = pkg
        options = opt
        #try to locate an entity name (used in port command)
        ent_name = None
        e_index = package.rfind(apt.ENTITY_DELIM)
        if(cmd == 'port' and e_index > -1):
            ent_name = package[e_index+1:]
            package = package[:e_index]

        value = package
        M,L,N,_ = Block.snapTitle(package)

        package = package.replace("-", "_")

        #first identify if automatic-refresh should occur on markets
        #if(apt.inWorkspace() and apt.readyForRefresh() and apt.linkedMarket()):
            #self.db.sync('')
        #is the user trying to shortcut?
        if(Workspace.inWorkspace() and L == '' and cmd != 'new' and self.db.canShortcut(N)):
            #rewrite MLNV based on shortcut if possible
            M,L,N,_ = self.db.shortcut(N)
            if(cmd != 'export' and cmd != 'graph' and cmd != 'run' and cmd != 'build'):
                package = L+'.'+N

        if(Workspace.inWorkspace()):
            if(self.db.blockExists(package,"local")):
                self.blockPKG = self.db.getBlocks("local")[L][N]
            else:
                self.blockPKG = None

        valid = (self.blockPKG != None)
        if(Workspace.inWorkspace()):
            exists = self.db.blockExists(package,"local") or \
                    self.db.blockExists(package,"cache") or \
                    self.db.blockExists(package,"market")
        else:
            exists = False

        #branching through possible commands
        if(command == "install"):
            ver = None
            #ensure version option is valid before using it to install
            if(len(options) == 1 and Block.validVer(options[0]) == True):
                ver = Block.stdVer(options[0])
            elif(len(options) > 1):
                exit(log.error("Invalid flags set for install command."))
            #install directly from Block.cfg 'derives' list
            if(options.count('requirements')):
                if(self.blockCWD.isValid()):
                    log.info("Installing requirements...")
                else:
                    exit(log.error("Invalid block directory!"))
                #read the derives list of this block
                requirements = self.blockCWD.getMeta('derives')
                for req in requirements:
                    M,L,N,V = Block.snapTitle(req)
                    self.install(L+'.'+N, V)
            else:
                #install block to cache
                self.install(package, ver)
            pass

        elif(command == "uninstall"):
            ver = None
            #ensure version option is valid before using it to install
            if(len(options) == 1 and (Block.validVer(options[0]) or Block.validVer(options[0], maj_place=True))):
                ver = Block.stdVer(options[0])
            elif(len(options) > 1):
                exit(log.error("Invalid Flags set for install command."))

            self.uninstall(package, ver)
            pass

        elif(command == "build" and self.blockCWD.isValid()):
            self.build(value)
            pass

        elif(command == "new"):
            if(N == ''):
                exit(log.error("A block must have a name as part of its title."))
            elif(L == ''):
                exit(log.error("A block must have a library as part of its title."))
            if(exists):
                exit(log.error("A block already exists as "+package))

            #option to create a new block
            startup = False
            if(options.count("open")):
                startup = True
                options.remove("open")

            #try to find a valid git url
            git_url = None
            for opt in options:
                if(apt.isValidURL(opt)):
                    git_url = opt

            #if this remote is bare, we cannot create a blank project from it.
            if(git_url != None and apt.isRemoteBare(git_url) == False):
                exit(log.error("Cannot configure with remote because it is not empty! Try using the 'init' command"))

            #try to validate market
            mkt_obj = self.identifyMarket(M)
            #option to skip the template?
            use_template = (not options.count('no-template'))

            self.blockPKG = Block(title=L+'.'+N, market=mkt_obj, remote=git_url)
            #create new block
            self.blockPKG.create(fresh=True, remote=git_url, inc_template=use_template)

            if(startup):
                self.blockPKG.load()
            pass

        elif(command == "release" and self.blockCWD.isValid()):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            if(value == ''):
                value = None
            self.upload(self.blockCWD, value, options=options)
            pass

        #a visual aide to help a developer see what package's are at the ready to use
        elif(command == 'graph' and self.blockCWD.isValid()):
            top = package.lower()
            if(top == ''):
                top = None
            inc_sim = (options.count('ignore-tb') == 0)
            top_dog,_,_ = self.blockCWD.identifyTopDog(top, inc_sim=inc_sim)
            #generate dependency tree
            self.formGraph(self.blockCWD, top_dog)
            pass

        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            success = self.download(package)
            if('open' in options):
                local_blocks = self.db.getBlocks("local", updt=True)
                if(success):
                    if(L in local_blocks.keys() and N in local_blocks[L].keys()):
                        local_blocks[L][N].load()
                    else:
                        log.warning(L+"."+N+" is no longer identified by this title.")
                else:
                    log.error("Could not open block due to failed download.")
            pass

        elif(command == 'del'):
            #try to delete a block
            if(valid):
                force = options.count('uninstall')
                self.cleanup(self.blockPKG, force)
            #try to delete a setting
            elif(L == '' or N == ''):
                self.configure(options, value, delete=True)
            else:
                #print(L,N)
                log.info("Block "+L+'.'+N+" does not exist in local path.")
            pass

        elif(command == "list"): #a visual aide to help a developer see what package's are at the ready to use
            if(options.count("script")):
                Script.printList()
            elif(options.count("label")):
                Label.printList()
            elif(options.count("market")):
                Market.printList(self.WS().getMarkets())
            elif(options.count("workspace")):
                Workspace.printList()
            elif(options.count("profile")):
                Profile.printList()
            elif(options.count("template")):
                apt.getTemplateFiles()
                #categorize by hidden files (skipped)
                #and visible files (files that are copied in on using template)
            else:
                self.inventory(M,L,N,options)
            pass

        elif(command == "init"):
            #option to create a new file
            if(options.count("file")):
                options.remove("file")
                if(self.blockCWD.isValid()):
                    if(len(options) == 0):
                        #no template file was specified
                        log.info("No template file was specified.")
                        if(os.path.exists(value) == False):
                            log.info("Creating new empty file "+value+"...")
                            rel_path = value[:value.rfind(os.path.basename(value))]
                            if(len(rel_path)):
                                if(rel_path[0] != '.'):
                                    rel_path = '.' + rel_path
                                    value = '.' + value
                                os.makedirs(rel_path, exist_ok=True)
                            open(value,'w').close()
                        else:
                            exit(log.error("A file of same name already exists here."))
                        return
                    # a template file was specified to be used
                    else:
                        self.blockCWD.fillTemplateFile(value, options[0])
                else:
                    exit(log.error("Cannot create a project file when not inside a project!"))
                return
            if(exists):
                exit(log.error("A block already exists as "+package))
            self.convert(value, options)
            pass

        elif(command == "refresh"):
            #package value is the market looking to refresh
            #if package value is null then all markets tied to this workspace refresh by default
            if(value == ''):
                log.info("Refreshing all markets...")
                for mkrt in Market.Jar.values():
                    mkrt.refresh()
            elif(value.lower() in Market.Jar.keys()):
                Market.Jar[value].refresh()
            pass

        elif(command == "export" and self.blockCWD.isValid()):
            #'' and list() are default to pkg and options
            top = package.lower()
            if(top == ''):
                top = None
            self.export(self.blockCWD, top, options)
            pass

        elif(command == "run" and self.blockCWD.isValid()):
            self.export(self.blockCWD, top=None, options=options)
            self.build(value)
            pass

        elif(command == "open"):
            if(apt.SETTINGS['general']['editor'] == cfg.NULL):
                exit(log.error("No text-editor configured!"))
            #open template
            if(options.count("template")):
                log.info("Opening block template folder at... "+apt.fs(apt.TEMPLATE))
                apt.execute(apt.SETTINGS['general']['editor'], apt.fs(apt.TEMPLATE))
            #open scripts
            elif(options.count("script")):
                #want to open the specified script?
                script_path = apt.fs(apt.HIDDEN+"scripts")
                #maybe open up the script file directly if given a value
                if(value in apt.SETTINGS['script']):
                    for pt in apt.SETTINGS['script'][value].split()[1:]:
                        #find first case a arg is a path
                        pt = pt.replace("\"",'').replace("\'",'')
                        if(os.path.isfile(pt)):
                            script_path = apt.fs(pt)
                            log.info("Opening script "+value+" at... "+script_path)
                            break
                    else:
                        log.info("Opening built-in script folder at... "+script_path)
                elif(value == ''):
                        log.info("Opening built-in script folder at... "+script_path)
                else:
                    exit(log.error("Script "+value+" does not exist"))

                apt.execute(apt.SETTINGS['general']['editor'],script_path)
            #open profile
            elif(options.count("profile")):
                if(value.lower() in apt.getProfileNames().keys()):
                    value = apt.getProfileNames()[value.lower()]
                    log.info("Opening profile "+value+" at... "+apt.getProfiles()[value])
                    apt.execute(apt.SETTINGS['general']['editor'], apt.getProfiles()[value])
                else:
                    log.error("No profile exists as "+value)
            #open settings
            elif(options.count("settings")):
                settings_gui = None
                if(options.count("file") == 0):
                    settings_gui = GUI()
                if(settings_gui == None or settings_gui.initialized() == False):
                    log.info("Opening settings CFG file at... "+apt.fs(apt.HIDDEN+apt.SETTINGS_FILE))
                    apt.execute(apt.SETTINGS['general']['editor'], apt.fs(apt.HIDDEN+apt.SETTINGS_FILE))
            #open block
            elif(valid):
                self.blockPKG.load()
            else:
                exit(log.error("No block "+package+" exists in your workspace."))
            pass

        elif(command == "show" and 
            (self.db.blockExists(package, "local") or \
                self.db.blockExists(package, "cache") or \
                self.db.blockExists(package, "market"))):
            ver = None
            changelog = options.count('changelog')
            for opt in options:
                if(Block.validVer(opt) == True or Block.validVer(opt, maj_place=True)):
                    ver = Block.stdVer(opt)
                    break
            #print available versions
            listVers = options.count("version")

            if(self.db.blockExists(package, "cache") == True):
                self.db.getBlocks("cache")[L][N].show(listVers, ver, changelog)
            elif(self.db.blockExists(package, "local") == True):
                self.db.getBlocks("local")[L][N].show(listVers, ver, changelog)
            elif(self.db.blockExists(package, "market") == True):
                self.db.getBlocks("market")[L][N].show(listVers, ver, changelog)
            pass

        elif(command == "update"):
            if(options.count('profile')):
                if(value.lower() in Profile.Jar.keys() or value.lower() == 'default'):
                    if(value.lower() != 'default'):
                        Profile.Jar[value].update()
                    else:
                        Profile.reloadDefault()
                else:
                    log.error("No profile exists as "+value+".")
            elif(self.db.blockExists(package,"cache")):
                #perform install over remote url
                self.update(package)
            pass

        elif(command == "profile" and package != ''):
            asking = options.count('ask')
            #import new settings from an existing profile
            if(value.lower() in Profile.Jar.keys()):
                Profile.Jar[value].importLoadout(ask=asking)
            #try to create new profile from url and import
            else:
                tmp = Profile('', url=value)
                if(tmp in Profile.Jar.values()):
                    tmp.importLoadout(ask=asking)
                #save new profile
                Profile.save()

            #reinitialize all settings/perform safety measures
            apt.load()
            pass

        elif(command == "port"):
            #show component instantiation?
            mapp = (len(options) and 'map' in options)
            #show direct entity instantiation?
            pure_ent = (len(options) and 'instance' in options)
            
            show_arc = (len(options) and 'arch' in options)
            #grab the version number if it was in flags
            ver = None
            for o in options:
                if(Block.validVer(o) or Block.validVer(o, maj_place=True)):
                    ver = Block.stdVer(o)
                    break
            #trying to reference a unit from the current block for internal usage
            within_block = (self.blockCWD.isValid() and self.blockCWD.getLib() == L and self.blockCWD.getName() == N)
            #swap the library name from its original to using 'work'
            inserted_lib = L
            if(within_block): 
                inserted_lib = 'work'

            carry_on = (within_block) or (self.db.blockExists(package, "local") and apt.SETTINGS['general']['multi-develop'])
            
            if(carry_on or self.db.blockExists(package, "cache")):
                #allow blocks to be from local path as well if using multi-develop
                if(apt.SETTINGS['general']['multi-develop']):
                    domain = self.db.getBlocks("local","cache")
                    if(self.db.blockExists(package, "local") and ver == None):
                        log.warning("Using this block may be unstable as ports are locally referenced.")
                #only allowed to search in cache for ports
                else:
                    if(within_block == True):
                        domain = {L : {N : self.blockCWD}}
                    else:
                        domain = self.db.getBlocks("cache")
                #print the port mapping/listing to the console for user aide
                print(domain[L][N].ports(mapp,inserted_lib,pure_ent,ent_name,ver,show_arc), end='')
            #could not use this block because it is only available locally
            elif(not within_block and apt.SETTINGS['general']['multi-develop'] == False and self.db.blockExists(package, "local")):
                exit(log.error("Cannot use "+package+" because it has no installed release points and multi-develop is set to OFF."))
            #this block does not exist
            else:
                exit(log.error("No block "+package+" exists in local path or workspace cache."))
            pass

        elif(command == "config"):
            self.configure(options, value)
            pass
        
        elif(command == "help" or command == ''):
            pass
    pass

@DeprecationWarning
def commandHelp(self, cmd):
    '''
    This method performs the help command. It prints additional information
    regarding a requrest command, such as description, format, and 
    arguments.
    '''
    def printFmt(cmd,val,options='',quiet=False):
        if(not quiet):
            print("USAGE:")
        print("\tlegohdl "+cmd+" "+val+" "+options)
        pass

    def rollover(txt,limit=60):
        cur_line = 0
        print("\nDESCRIPTION:")
        for word in txt.split():
            cur_line = cur_line + len(word) + 1
            if(cur_line > limit):
                cur_line = len(word) + 1
                print()
            print(word,end=' ')
        print()
        print("\nARGUMENTS:")
        pass

    if(cmd == ''):
        return
    elif(cmd == "init"):
        printFmt("init", "<block>","[-<remote>]")
        printFmt("init","<value>","(-market | -remote | -summary)",quiet=True)
        printFmt("init","<file>","-file [-<template-file>]",quiet=True)
        rollover("""
If no flags are raised, transform the working directory into a valid block. This will
create a git repository if not available, and create the Block.cfg file. If there is a git
repository and it is linked to a remote, the remote will also automatically be configured within the
Block.cfg file. If providing a market name, prepend it to the block's title. If there is a supported 
raised flag for <value>, then the block's respective field will be altered with the <value>. 
        """)
        print('{:<16}'.format("<block>"),"the block's title to be initialized from the current folder")
        print('{:<16}'.format("<value>"),"value to be given to current block based on the flag raised")
        print('{:<16}'.format("<file>"),"file path to create new file within block")
        print()
        print('{:<16}'.format("-<remote>"),"an empty git url to set for this block")
        print('{:<16}'.format("-market"),"provide a market name as <value> available from the workspace")
        print('{:<16}'.format("-remote"),"provide a valid git URL as <value> to set for this block")
        print('{:<16}'.format("-summary"),"provide a string as <value> to set for this block's summary")
        print('{:<16}'.format("-file"),"create a new file for the current block")
        print('{:<16}'.format("-<template-file>"),"define template file to use upon file creation")
        pass
    elif(cmd == "new"):
        printFmt("new","<block>","[-open -<remote> -no-template]")
        rollover("""
Create a new block into the base of the workspace's local path. The block's default 
created path is <workspace-path>/<block-library>/<block-name>. The template folder 
will be copied and a git repository will be created. If providing a remote git URL, make sure
it is an empty repository. If you have a nonempty repository, try the 'init' command. If
providing a market name, prepend it to the block's title.
        """)
        print('{:<16}'.format("<block>"),"the block's title to be created")
        print()
        print('{:<16}'.format("-open"),"open the new block upon creation")
        print('{:<16}'.format("-<remote>"),"provide a blank git URL to be configured")
        print('{:<16}'.format("-no-template"),"do not import configured template")
        pass
    elif(cmd == "open"):
        printFmt("open","<block>")
        printFmt("open","[<script-name>] -script",quiet=True)
        printFmt("open","<profile-name> -profile",quiet=True)
        printFmt("open","(-template | -settings)",quiet=True)
        rollover("""
Open a variety of legohdl folders/files. With no flags raised, the block will be opened if
it is found in the workspace's local path. If the script flag is raised with no <script>,
it will open the built-in script folder. If a valid <script-name> is specified with the script 
flag raised, it will directly open its file. If a valid <profile-name> is specified with the profile
flag raised, it will open the profile to make edits.
        """)
        print('{:<16}'.format("<block>"),"the block's title to be opened by the text-editor")
        print('{:<16}'.format("<script-name>"),"script's name found in legohdl settings")
        print('{:<16}'.format("<profile-name>"),"available profile found in legohdl settings")
        print()
        print('{:<16}'.format("-template"),"open the template folder")
        print('{:<16}'.format("-script"),"open the built-in script folder if no script specified")
        print('{:<16}'.format("-profile"),"open the specified profile to edit")
        print('{:<16}'.format("-settings"),"open the settings CFG file")
        pass
    elif(cmd == "release"):
        printFmt("release","[<message>]","(-v0.0.0 | -maj | -min | -fix) [-strict -soft]")
        rollover("""
Creates a valid legohdl release point to be used in other designs. This will auto-detect 
the toplevel unit, testbench unit, and determine the exact version dependencies required. 
It will then stage, commit, and tag any changes. If the block has a valid remote, it will 
push to the remote. If the block has a valid market, the Block.cfg file will be updated there.
If the -v0.0.0 flag is not properly working, -v0_0_0 is also valid.
        """)
        print('{:<16}'.format("<message>"),"the message for the release point's tagged commit")
        print()
        print('{:<16}'.format("-v0.0.0"),"manual setting for the next version (replace 0's)")
        print('{:<16}'.format("-maj"),"bump version to next major ^.0.0")
        print('{:<16}'.format("-min"),"bump version to next minor -.^.0")
        print('{:<16}'.format("-fix"),"bump version to next patch -.-.^")
        print('{:<16}'.format("-strict"),"won't add any unstaged changes into the release")
        print('{:<16}'.format("-soft"),"push a side branch to the linked market for merge")
        pass
    elif(cmd == "list"):
        printFmt("list","[[<search>]","[-alpha -install -download]] [-script | -label | -market | -workspace | -profile | -template]")
        rollover("""
Provide a formatted view for a variety of groups. The default is to list the active
workspace's blocks. When listing blocks, you can also search by providing a partial block 
title  as <search> and alphabetically organize results with the alpha flag. Raising script, 
label, market, or workspace, will print their respective group found within the settings.
        """)
        print('{:<16}'.format("<search>"),"partial or full block title to be searched")
        print()
        print('{:<16}'.format("-alpha"),"alphabetically organize blocks")
        print('{:<16}'.format("-script"),"view scripts as name, command, path")
        print('{:<16}'.format("-label"),"view labels as label, extension, recursive")
        print('{:<16}'.format("-market"),"view markets as market, url, linked to workspace")
        print('{:<16}'.format("-workspace"),"view workspaces as workspace, active, path, markets")
        print('{:<16}'.format("-profile"),"view available profiles to overload configurations")
        print('{:<16}'.format("-template"),"list all available files found in current template")
        pass
    elif(cmd == "install"):
        printFmt("install","((<block>","[-v0.0.0]) | -requirements)")
        rollover("""
Clones the block's main branch to the cache. If the main branch is already found in the cache,
it will not clone/pull from the remote repository (see 'update' command). Checkouts and copies 
the version (default is latest if unspecified) to have its own location in the cache. The 
entities of the install version are appeneded with its appropiate version (_v0_0_0). Each 
version install may also update the location for its major value (_v0) if its the highest yet.
If the -v0.0.0 flag is not properly working, -v0_0_0 is also valid.
        """)
        print('{:<16}'.format("<block>"),"the block's title to be installed to cache")
        print()
        print('{:<16}'.format("-v0.0.0"),"specify what version to install (replace 0's)")
        print('{:<16}'.format('-requirements'),'reads the "derives" list and installs all dependent blocks')
        pass
    elif(cmd == "uninstall"):
        printFmt("uninstall","<block>","[-v0.0.0]")
        rollover("""
Removes installed versions from the cache. If no version is specified, then ALL versions will be
removed as well as the cached main branch. Specifying a version will only remove that one, if its
been installed. Can also remove by major version value (ex: -v1). If the -v0.0.0 flag is not 
properly working, -v0_0_0 is also valid.
        """)
        print('{:<16}'.format("<block>"),"the block's title to be uninstalled from cache")
        print()
        print('{:<16}'.format("-v0.0.0"),"specify what version to uninstall (replace 0's)")
        pass
    elif(cmd == "download"):
        printFmt("download","<block>","[-open]")
        rollover("""
Grab a block from either its remote url (found via market) or from the cache. The block will
be downloaded to <workspace-path>/<block-library>/<block-name>. If the block is not installed to
the cache, it will also install the latest version to the cache.
        """)
        print('{:<16}'.format("<block>"),"the block's title to be downloaded to the local path")
        print()
        print('{:<16}'.format("-open"),"open the block after download for development")
        pass
    elif(cmd == "run"):
        printFmt("run","[+<script-name>]","[...]")
        rollover("""
Generate a blueprint file through 'export' and then build the design with a custom configured script
through 'build' all in this command. The toplevel and testbench will be auto-detected and ask
the user to select one if multiple exist. If no script name is specified, it will default look for
the script named 'master'. If only 1 script is configured, it will default to that script regardless of name.
        """)
        print('{:<16}'.format("+<script-name>"),"the script name given by the user to legohdl")
        print()
        print('{:<16}'.format("..."),"arguments to be passed to the called script")
    elif(cmd == "graph"):
        printFmt("graph","[<toplevel>] [-ignore-tb]")
        rollover("""
Create the dependency tree for the current design. This command is used as an aide and will not
alter the Block.cfg file. The toplevel and testbench will be auto-detected and ask
the user to select one if multiple exist. It helps the user gain a better picture of how the design
will be ultimately combined. If the toplevel is not a testbench, legohdl will attempt to find its
respective testbench and add it to the graph.
        """)
        print('{:<16}'.format("<toplevel>"),"explicitly set the toplevel entity/module")
        print()
        print('{:<16}'.format("-ignore-tb"),"do not include toplevel testbenchs")
    elif(cmd == "update"):
        printFmt("update","<block>")
        printFmt("update","<profile> -profile",quiet=True)
        rollover("""
Update an installed block to have the latest version available. In order for a block to be updated
it must be installed. All previous version installations will be unaffected. Can also update a profile
if it is a repository and has a remote URL.
        """)
        print('{:<16}'.format("<block>"),"the cached block to have its tracking master branch updated")
        print('{:<16}'.format("<profile>"),"the profile to be updated from its remote git URL")
        print()
        print('{:<16}'.format("-profile"),"indicate that a profile is being targeted for an update")
        pass
    elif(cmd == "export"):
        printFmt("export","[<toplevel>] [-ignore-tb]")
        rollover("""
Create the dependency tree for the current design and generate the blueprint file. The blueprint is stored
into a clean directory called 'build' on every export. It will update the Block.cfg files with the
current dependencies being used to export the design. The toplevel and testbench will be auto-detected and ask
the user to select one if multiple exist. If the toplevel is not a testbench, legohdl will attempt to find its
respective testbench and add it to the graph.
        """)
        print('{:<16}'.format("<toplevel>"),"explicitly set the toplevel entity/module")
        print()
        print('{:<16}'.format("-ignore-tb"),"do not include toplevel testbenchs")
        pass
    elif(cmd == "build"):
        printFmt("build","[+<script-name>]","[...]")
        rollover("""
Build the design with a custom configured script. If no script name is specified, it will default look for
the script named 'master'. If only 1 script is configured and no script name is specified, it will default 
to that script regardless of name.
        """)
        print('{:<16}'.format("+<script-name>"),"the script name given by the user to legohdl")
        print()
        print('{:<16}'.format("..."),"arguments to be passed to the called script")
        pass
    elif(cmd == "del"):
        printFmt("del","<block>","[-uninstall]")
        printFmt("del","<value>","(-market | -script | -label | -workspace | -profile)",quiet=True)
        rollover("""
Delete a block from the local path, typically used after releasing a new version and development
is complete. If deleting a workspace, the local path will be preserved but all legohdl settings and structure
regarding the workspace will be forgotten. If deleting a market, it will be no longer available
for any workspaces. If deleting a script or label, the set values will be removed. A script
will not be deleted from its path.
        """)
        print('{:<16}'.format("<block>"),"the block's title to remove from local path")
        print('{:<16}'.format("<value>"),"a previously defined legohdl setting value")
        print()
        print('{:<16}'.format("-uninstall"),"fully uninstall the block from cache")
        print('{:<16}'.format("-market"),"delete the market from all workspaces and settings")
        print('{:<16}'.format("-script"),"forget the script")
        print('{:<16}'.format("-label"),"forget the label")
        print('{:<16}'.format("-workspace"),"keeps local path, but remove from settings")
        print('{:<16}'.format("-profile"),"remove the folder found in legoHDL containing this profile")
    elif(cmd == "port"):
        printFmt("port","<block>[:<entity>]","[(-map -instance) | -arch]")
        rollover("""
Print component information needed by an upper-level design to instantiate an entity. The output is
designed to be copied and pasted into a source file with little-to-no modification. A specific
entity can be requested by appending it to its block name.
        """)
        print('{:<16}'.format("<block>"),"the block's title telling where to get the entity")
        print('{:<16}'.format("<entity>"),"explicitly indicate what entity to display")
        print()
        print('{:<16}'.format("-map"),"additionally display IO signals and component instantation")
        print('{:<16}'.format("-instance"),"additionally display IO signals and direct entity instantation")
        pass
    elif(cmd == "show"):
        printFmt("show","<block>","[-version | -v0.0.0]")
        rollover("""
Print detailed information (Block.cfg) about a block. Can also print a specific
version's information if it is intstalled to the cache. Can also show by major version 
value (ex: -v1). If the -v0.0.0 flag is not properly working, -v0_0_0 is also valid.            
        """)
        print('{:<16}'.format("<block>"),"the block's title to show metdata about")
        print()
        print('{:<16}'.format("-version"),"List the available versions and which ones are installed.")
        print('{:<16}'.format("-v0.0.0"),"Show this specific version or constrain the version list to this version")
        pass
    elif(cmd == "config"):
        printFmt("config","<value>","(-market (-add | -remove) | -active-workspace | -author | -editor | -template | -multi-develop | -overlap-recursive | -refresh-rate | -profile)")
        printFmt("config","<key>="+'"<value>"',"(-script [-link] | -label [-recursive] | -workspace | -market [-add | -remove])",quiet=True)
        rollover("""
Configure settings for legoHDL. This is the command-line alternative to opening 
the legohdl.cfg file for visual editing. If only a market name is given as <value>, then it will
be used as a reference to either -add or -remove the market from the current workspace. If raising
-template, it requests the path to a folder to create new blocks from. If the <value> is empty, it will
reference the built-in template folder. Valid <value> for -multi-develop and -overlap-recursive flags are either
'true', 'false', 1, or 0. The flag -refresh-rate takes an integer for <value> and determines how many times per day
to automatically refresh the markets tied to the workspace. If <value> is -1, then it will perform refresh on every
legohdl command. Any other value (up to 1440) will evenly space out that many intervals throughout the day to 
perform refresh.
        """)
        print('{:<16}'.format("<value>"),"respective to the raised flag")
        print('{:<16}'.format("<key>"),"an identifier/name respective to the raised flag")
        print()
        print('{:<16}'.format("-market"),"indicate the key or value to be a market")
        print('{:<16}'.format("-add"),"add the market to the active workspace")
        print('{:<16}'.format("-remove"),"remove the market from the active workspace")
        print('{:<16}'.format("-active-workspace"),"the current workspace")
        print('{:<16}'.format("-author"),"the user's preferred name")
        print('{:<16}'.format("-editor"),"a text-editor to open various folders and files")
        print('{:<16}'.format("-template"),"indicate where the template folder is found")
        print('{:<16}'.format("-profile"),"create a new blank profile with the name from <value>")
        print('{:<16}'.format("-multi-develop"),"prioritize using downloaded blocks over installed blocks")
        print('{:<16}'.format("-overlap-recursive"),"include all found labels regardless of possible duplication")
        print('{:<16}'.format("-refresh-rate"),"integer for how often to automatically refresh markets per day")
        print('{:<16}'.format("-script"),"indicate the key/value to be a script name and the command")
        print('{:<16}'.format("-link"),"reference the script from its original location")
        print('{:<16}'.format("-label"),"indicate the key/value to be a label and glob-pattern")
        print('{:<16}'.format("-recursive"),"categorize this label to be searched for in all dependencies")
        print('{:<16}'.format("-workspace"),"provide a workspace name and a local path for key/value")
        pass
    elif(cmd == 'profile'):
        printFmt("profile","<profile>","[-ask]")
        rollover("""
Import configuration settings, template, and/or scripts from one location. This is
the fast and more efficient way to share settings and save different configurations.
<profile> can be an existing profile, a git remote url pointing to a valid profile, or
a local path to a valid profile. A profile is valid if the folder contains a .prfl file.
The name of the .prfl file is the name of the profile itself.            
        """)
        print('{:<16}'.format("<profile>"),"an existing profile name, git repository, or path")
        print()
        print('{:<16}'.format("-ask"),"prompt the user what portions of profile to import")
        pass
    print()
    exit()
pass

@DeprecationWarning
def configure(self, options, choice, delete=False):
    '''
    This method performs the config command. It is in charge of handling
    setting settings through the command-line interface.
    '''
    if(len(options) == 0):
        log.error("No field was flagged to as an option to modify.")
        return
    
    choice = choice.replace(apt.ENV_NAME,apt.HIDDEN[:len(apt.HIDDEN)-1])

    eq = choice.find("=")
    key = choice[:eq]
    val = choice[eq+1:] #write whole value
    if(eq == -1):
        val = None
        key = choice
    #chosen to delete setting from legohdl.cfg
    if(delete):
        possibles = ['label', 'workspace', 'market', 'script', 'profile']
        st = options[0].lower()
        if(st not in possibles):
            exit(log.error("Cannot use del command on "+st+" setting."))
        #ensure this is a valid key to remove
        if(st != 'profile' and choice not in apt.SETTINGS[st].keys()):
            #check within both branches of label setting, 'shallow' and 'recursive'
            if(st == 'label'):
                if(choice not in apt.SETTINGS[st]['shallow'].keys() and choice not in apt.SETTINGS[st]['recursive'].keys()):
                    exit(log.error("No key '"+choice+"' exists under '"+st+"' setting."))
            else:
                exit(log.error("No key '"+choice+"' exists under '"+st+"' setting."))

        #delete a key/value pair from the labels
        if(st == 'label'):
            if(choice in apt.SETTINGS[st]['recursive'].keys()):
                del apt.SETTINGS[st]['recursive'][choice]
            if(choice in apt.SETTINGS[st]['shallow'].keys()):
                del apt.SETTINGS[st]['shallow'][choice]
        elif(st == 'profile'):
            choice = choice.lower()
            if(choice in apt.getProfiles()):
                #remove directory
                shutil.rmtree(apt.getProfiles()[choice], onerror=apt.rmReadOnly)
                #remove from settings
                apt.SETTINGS['general'][st+'s'].remove(choice)
            else:
                exit(log.error("Profile "+choice+" does not exist."))
        #delete a key/value pair from the scripts or workspaces
        elif(st == 'script' or st == 'workspace' or st == 'market'):
            if(choice in apt.SETTINGS[st].keys()):
                #print("delete")
                #update active workspace if user deleted the current workspace
                if(st == 'workspace'):
                    if(apt.SETTINGS['general']['active-workspace'] == choice):
                        apt.SETTINGS['general']['active-workspace'] = None
                        #prompt user to verify to delete active workspace
                        verify = apt.confirmation("Are you sure you want to delete the active workspace?")
                        if(not verify):
                            log.info("Command cancelled.")
                            return
                    #move forward with workspace removal
                    bad_directory = apt.HIDDEN+"workspaces/"+choice
                    #print(bad_directory)
                    if(os.path.isdir(bad_directory)):
                        shutil.rmtree(bad_directory, onerror=apt.rmReadOnly)
                        log.info("Deleted workspace directory: "+bad_directory)
                elif(st == 'market'):
                    #case insensitive
                    key = key.lower()
                    Market(key,val).delete()
                    #remove from all workspace configurations
                    for nm in apt.SETTINGS['workspace'].keys():
                        #traverse through all markets listed for this workspace
                        for mrkt_nm in apt.SETTINGS['workspace'][nm]['market']:
                            #remove any matches to this newly deleted workspace
                            if(key == mrkt_nm.lower()):
                                apt.SETTINGS['workspace'][nm]['market'].remove(mrkt_nm)
                        pass
                del apt.SETTINGS[st][choice]

        apt.save()
        log.info("Setting saved successfully.")
        return

    #chosen to config a setting in legohdl.cfg
    if(options[0] == 'active-workspace'):
        if(choice not in apt.SETTINGS['workspace'].keys()):
            exit(log.error("Workspace "+choice+" not found!"))

    #invalid option flag
    if(options[0] not in apt.OPTIONS and options[0] != 'profile'):
        exit(log.error("No field exists as '"+options[0]+"' that can be modified."))
    elif(options[0] == 'market'):
        #try to link existing market into markets
        if(val == None):
            if(key.lower() not in apt.getMarketNames().keys()):
                result = apt.loadMarket(key)
                if(result == False):
                    exit(log.error("Setting not saved."))
                key = result
                val = apt.getMarkets(workspace_level=False)[key]
            else:
                key = apt.getMarketNames()[key]
        else:
            if(val == cfg.NULL):
                val = None
            if(key.lower() in apt.getMarketNames().keys()):
                if(key != apt.getMarketNames()[key.lower()]):
                    exit(log.error("Market name conflicts with market "+apt.getMarketNames()[key.lower()]+"."))
                #only create remote in the list
                else:
                    #market name already exists
                    confirm = apt.confirmation("You are about to reconfigure the already existing market "+key+". Are you sure you want to do this?")
                    if(not confirm):
                        exit(log.info("Setting not saved."))
                pass
            else:
                log.info("Creating new market "+key+"...")
            #create market object!  
            mkt = Market(key,val) 
            #set to null if the tried remote DNE
            if(not mkt.isRemote()):
                val = None
            val = mkt.setRemote(val)
            #update settings to accurately reflect
            apt.SETTINGS['market'][key] = val
        
        # add to active workspace markets
        if(options.count("add") and key not in apt.getWorkspace('market')): 
            log.info("Adding "+key+" market to active workspace...")
            apt.getWorkspace('market').append(key)
        # remove from active workspace markets
        elif(options.count("remove") and key in apt.getWorkspace('market')):
            log.info("Removing "+key+" market to active workspace...")
            apt.getWorkspace('market').remove(key)
    # WORKSPACE CONFIGURATION
    elif(options[0] == 'workspace'):
        #create entire new workspace settings
        if(not isinstance(apt.SETTINGS[options[0]],dict)):
            apt.SETTINGS[options[0]] = dict()
        #insertion
        if(val != None):
            #ensure there is no conflict with making this workspace key/val pair
            if(apt.isConflict(apt.getWorkspaceNames(), key) == True):
                exit(log.error("Setting not saved."))
            #create new workspace profile
            for lp in apt.SETTINGS[options[0]].values():
                if(lp['path'] != cfg.NULL and lp['path'].lower() == apt.fs(val).lower()):
                    exit(log.error("A workspace already exists with this path."))
            #initialize the workspace folders and structure
            apt.initializeWorkspace(key, apt.fs(val))
            
            # :todo: needs to override local path as the newly configured path to perform this functionality
            #are there any blocks already there at local path?
            # print(apt.getLocal())
            # #go through all the found blocks in this already existing path and see if any are "released"
            # blks = self.db.getBlocks("local")
            # print(blks)
            # for sects in blks.values():
            #     for blk in sects.values():
            #         #temporarily set the workspace path to properly install any found blocks to cache
            #         apt.WORKSPACE = apt.HIDDEN+"workspaces/"+key+"/"
            #         if(Block.biggerVer(blk.getVersion(),'0.0.0') != '0.0.0'):
            #             #install to cache
            #             log.info("Found "+blk.getTitle()+" as an already a released block.")
            #             self.install(blk.getTitle())
            #    pass
            for rem in options:
                if rem == options[0]:
                    continue
                if rem not in apt.SETTINGS[options[0]][key]['market']:
                    apt.SETTINGS[options[0]][key]['market'].append(rem)
        else:
            exit(log.error("Workspace not added. Provide a local path for the workspace"))
        pass
    elif(options[0] == 'profile'):
        if(choice.lower() not in apt.getProfileNames().keys()):
            #add to settings
            apt.loadProfile(choice, append=True)
        else:
            exit(log.error("A profile already exists as "+apt.getProfileNames()[choice.lower()]+"."))
    # BUILD SCRIPT CONFIGURATION
    elif(options[0] == 'script'):
        if(val == None):
            val = ''
        #parse into cmd and filepath
        val = val.replace("\"","").replace("\'","")
        parsed = val.split()
        if(len(parsed) == 1):
            exit(log.error("At a minimum requires a command and a path"))
        #take first component to be the command
        cmd = parsed[0]
        filepath = ''
        file_index = -1
        for pt in parsed:
            if(pt == cmd):
                continue
            if(os.path.isfile(os.path.expanduser(pt))):
                filepath = os.path.realpath(os.path.expanduser(pt)).replace("\\", "/")
                #reinsert nice formatted path into the list of args
                file_index = parsed.index(pt)
                parsed[file_index] = filepath
                break
        if(filepath == ''):
            exit(log.error("No script path found in value"))

        _,ext = os.path.splitext(filepath)

        #skip link option- copy file and rename it same as name 
        if(options.count("link") == 0 and val != ''):   
            dst = apt.HIDDEN+"scripts/"+key+ext
            #try to copy and catch exception if its the same file
            try:
                shutil.copyfile(filepath, dst)
            except shutil.SameFileError:
                pass
            dst = filepath.replace(filepath, dst)
            #reassign the value for the filepath
            parsed[file_index] = dst

        #reassemble val with new file properly formatted filepath
        val = apt.fs(cmd)
        for pt in parsed:
            if(pt == cmd):
                continue
            val = val + " " + apt.fs(pt)
            
        #initialization
        if(not isinstance(apt.SETTINGS[options[0]],dict)):
            apt.SETTINGS[options[0]] = dict()
        #insertion
        if(filepath != ''):
            apt.SETTINGS[options[0]][key] = "\""+val+"\""
        #deletion
        elif(isinstance(apt.SETTINGS[options[0]],dict) and key in apt.SETTINGS[options[0]].keys()):
            val = apt.SETTINGS[options[0]][key]
            _,ext = os.path.splitext(val)
            del apt.SETTINGS[options[0]][key]
            try:
                os.remove(apt.HIDDEN+"scripts/"+key+ext)
            except:
                pass
        pass
    elif(options[0] == 'multi-develop' or options[0] == 'overlap-recursive'):
        apt.SETTINGS['general'][options[0]] = cfg.castBoolean(choice)
        pass
    elif(options[0] == 'template'):
        apt.SETTINGS['general'][options[0]] = apt.fs(choice)
        pass
    elif(options[0] == 'refresh-rate'):
        if(choice.isdecimal()):
            digit_choice = int(choice)
            if(digit_choice > apt.MAX_RATE):
                digit_choice = apt.MAX_RATE
            elif(digit_choice < apt.MIN_RATE):
                digit_choice = apt.MIN_RATE
            apt.SETTINGS[options[0]] = digit_choice
        else:
            exit(log.error("refresh-rate option takes an integer value"))
    # LABEL CONFIGURATION
    elif(options[0] == 'label'):
        depth = "shallow"
        if(options.count("recursive")):
            depth = "recursive"
        if(not isinstance(apt.SETTINGS[options[0]],dict)):
            apt.SETTINGS[options[0]] = dict()
            apt.SETTINGS[options[0]]["shallow"] = dict()
            apt.SETTINGS[options[0]]["recursive"] = dict()
        if(val != None):
            if(depth == "shallow" and key in apt.SETTINGS[options[0]]["recursive"].keys()):
                del apt.SETTINGS[options[0]]["recursive"][key]
            if(depth == "recursive" and key in apt.SETTINGS[options[0]]["shallow"].keys()):
                del apt.SETTINGS[options[0]]["shallow"][key]
            apt.SETTINGS[options[0]][depth][key] = val
        pass
    # ALL OTHER CONFIGURATION
    else:
        apt.SETTINGS['general'][options[0]] = choice
    
    apt.save()
    log.info("Setting saved successfully.")
    pass