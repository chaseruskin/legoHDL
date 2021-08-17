#!/usr/bin/env python3
from genericpath import isfile
import os, sys, shutil
from .block import Block
from .__version__ import __version__
from .registry import Registry
from .apparatus import Apparatus as apt
from .market import Market
import logging as log
from .unit import Unit

class legoHDL:

    #! === INITIALIZE ===

    def __init__(self):

        command = package = ""
        options = []
        #store args accordingly from command-line
        for i, arg in enumerate(sys.argv):
            if(i == 0):
                continue
            elif(i == 1):
                command = arg
            elif(len(arg) and arg[0] == '-'):
                options.append(arg[1:])
            elif(package == ''):
                package = arg

        if(command == '--version'):
            print(__version__)
            exit()
        #load settings.yml
        apt.load()
        #dyamincally manage any registries that were added to settings.yml
        Registry.dynamicLoad(apt.getMarkets(workspace_level=False))
        apt.save()

        self.blockPKG = None
        self.blockCWD = None
        #defines path to dir of remote code base
        self.db = Registry(apt.getMarkets())
        if(not apt.inWorkspace() and (command != 'config' and command != 'help' and (command != 'open' or "settings" not in options))):
            exit()
        self.parse(command, package, options)
        pass

    #! === INSTALL COMMAND ===

    #install block to cache, and recursively install dependencies
    def install(self, title, ver=None, required_by=[]):
        l,n = Block.split(title)
        block = None
        cache_path = apt.WORKSPACE+"cache/"
        #does the package already exist in the cache directory?
        if(self.db.blockExists(title, "cache", updt=True)):
            block = self.db.getBlocks("cache")[l][n]
            if(ver == None):
                log.info("The block is already installed.")
                return
        elif(self.db.blockExists(title, "local", updt=True)):
            block = self.db.getBlocks("local")[l][n]
        elif(self.db.blockExists(title, "market")):
            block = self.db.getBlocks("market")[l][n]
        else:
            exit(log.error("The block cannot be found anywhere."))

        #print(block.getTitle()+" prereqs")
        #append to required_by list used to prevent cyclic recursive nature
        required_by.append(block.getTitle())
        #see if all cache designs are available by looking at block's derives list
        #? make download section have precedence over cache section?
        for prereq in block.getMeta("derives"):
            L,N = block.split(prereq)
            if(prereq == block.getTitle() or prereq in required_by):
                continue

            tmp_blk = Block(prereq)
            cache_designs = block.grabCacheDesigns(override=True)
            needs_instl = False
            if(L not in cache_designs.keys()):
                #needs to install
                print("Requires",prereq)
                self.install(prereq, required_by=required_by)
                needs_instl = True
            else:
                for U in tmp_blk.grabCurrentDesigns(override=True)[L].keys():
                    if U not in cache_designs[L].keys():
                        needs_instl = True
            if(needs_instl):
                self.install(prereq, required_by=required_by)
              
        log.info("Installing... ")
        #see what the latest version available is and clone from that version unless specified
        isInstalled = self.db.blockExists(title, "cache")
        #now check if block needs to be installed from market
        if(self.db.blockExists(title, "cache") == False):
            block.install(cache_path, block.getVersion(), block.getMeta("remote"))
            #now update to true because it was just cloned from remote
            isInstalled = True
        elif(self.db.blockExists(title, "market") == False):
            log.WARNING("Block "+title+" does not exist for this workspace or its markets.")

        #now try to install specific version if requested now that the whole branch was cloned from remote
        if(ver != None and isInstalled):
            block.install(cache_path, ver)

        log.info("success")
    
        #link it all together through writing paths into "map.toml"
        filename = apt.WORKSPACE+"map.toml"
        mapfile = open(filename, 'r')
        cur_lines = mapfile.readlines()
        mapfile.close()

        mapfile = open(filename, 'w')
        inc_paths = list()

        for f in block.gatherSources():
            inc_paths.append("\'"+f+"\',\n")
        inc = False
        found_lib = False
        if(len(cur_lines) <= 1):
            cur_lines.clear()
            mapfile.write("[libraries]\n")

        for line in cur_lines:
            if(line.count(block.getLib()+".files") > 0): #include into already established library section
                inc = True
                found_lib = True
            elif(inc and not line.count("]") > 0):
                if(line in inc_paths):
                    inc_paths.remove(line)   
            elif(inc and line.count("]") > 0): # end of section
                for p in inc_paths: #append rest of inc_paths
                    mapfile.write(p)
                inc = False
            mapfile.write(line)

        if(len(cur_lines) == 0 or not found_lib):
            #create new library section
            mapfile.write(block.getLib()+".files = [\n")
            for p in inc_paths:
                mapfile.write(p)
            mapfile.write("]\n")

        mapfile.close()
        #update current map.toml as well
        shutil.copy(filename, os.path.expanduser("~/.vhdl_ls.toml"))
        pass

    #! === UNINSTALL COMMAND ===

    def uninstall(self, blk, ver):
        #remove from cache
        l,n = Block.split(blk)
        base_cache_dir = apt.WORKSPACE+"cache/"+l+"/"+n+"/"
        if(self.db.blockExists(blk, "cache")):
            #delete all its block stuff in cache
            if(ver == None):
                shutil.rmtree(base_cache_dir, onerror=apt.rmReadOnly)
            #only delete the specified version
            elif(os.path.isdir(base_cache_dir+ver+"/")):
                shutil.rmtree(base_cache_dir+ver+"/", onerror=apt.rmReadOnly)
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

        #remove from 'map.toml'
        lines = list()
        filename = apt.WORKSPACE+"map.toml"
        with open(filename, 'r') as file:
            lines = file.readlines()
            file.close()
        with open(filename, 'w') as file:
            for lin in lines:
                if(lin.count(l) and (lin.count("/"+n+"/"))):
                    continue
                file.write(lin)
            file.close()
        #update current map.toml as well
        shutil.copy(filename, os.path.expanduser("~/.vhdl_ls.toml"))
        pass

    #! === BUILD COMMAND ===

    def build(self, script):
        arg_start = 3
        if(not isinstance(apt.SETTINGS['script'],dict)): #no scripts exist
            exit(log.error("No scripts are configured!"))
        elif(len(script) and script[0] == "@"):
            if(script[1:] in apt.SETTINGS['script'].keys()): #is it a name?
                cmd = apt.SETTINGS['script'][script[1:]]
            else:
                exit(log.error("Script name not found!"))
        elif("master" in apt.SETTINGS['script'].keys()): #try to resort to default
            cmd = apt.SETTINGS['script']['master']
            arg_start = 2
        elif(len(apt.SETTINGS['script'].keys()) == 1): #if only 1 then try to run the one
            cmd = apt.SETTINGS['script'][list(apt.SETTINGS['script'].keys())[0]]
            arg_start = 2
        else:
            exit(log.error("No scripts are configured!"))

        #remove quotes from command
        cmd = cmd.replace("\'","")
        cmd = cmd.replace("\"","")
        #add surround quotes to the command/alias
        # cmd = cmd.replace("\'","\"")
        # if(cmd.find("\"") != 0):
        #     cmd = "\"" + cmd
        # if(cmd.rfind("\"") != len(cmd)-1):
        #     cmd = cmd + "\""
        # #add any extra arguments that were found on legohdl command line
        for i,arg in enumerate(sys.argv):
            if(i < arg_start):
                continue
            else:
                cmd = cmd + " " + arg
        log.info(cmd)
        os.system(cmd)

    #! === EXPORT/GRAPH COMMAND ===

    def export(self, block, top=None, tb=None):
        log.info("Exporting...")
        log.info("Block's path: "+block.getPath())
        build_dir = block.getPath()+"build/"
        #create a clean build folder
        log.info("Cleaning build folder...")
        if(os.path.isdir(build_dir)):
            shutil.rmtree(build_dir, onerror=apt.rmReadOnly)
        os.mkdir(build_dir)

        log.info("Finding toplevel design...")

        top_dog,top,tb = block.identifyTopDog(top, tb)
        
        output = open(build_dir+"recipe", 'w')    

        #mission: recursively search through every src VHD file for what else needs to be included
        unit_order,block_order = self.formGraph(block, top_dog)
        file_order = self.compileList(block, unit_order)  

        #add labels in order from lowest-projects to top-level project
        labels = []
        for blk in block_order:
            L,N = Block.split(blk)
            #assign tmp block to the current block
            if(block.getTitle() == blk):
                tmp = block
            #assign tmp block to the cache block
            elif(self.db.blockExists(blk, "cache")):
                tmp = self.db.getBlocks("cache")[L][N]
            else:
                log.warning("Cannot locate block "+blk)
                continue

            if(block.getTitle() == blk):
                tmp = block
            #add any recursive labels
            for label,ext in apt.SETTINGS['label']['recursive'].items():
                files = tmp.gatherSources(ext=[ext])
                for f in files:
                    labels.append("@"+label+" "+apt.fs(f))
            #add any project-level labels
            if(block.getTitle() == blk):
                for label,ext in apt.SETTINGS['label']['shallow'].items():
                    files = block.gatherSources(ext=[ext])
                    for f in files:
                        labels.append("@"+label+" "+apt.fs(f))

        #register what files the top levels originate from
        topfile_tb = None
        if(tb != None):
            topfile_tb = block.grabCurrentDesigns()[block.getLib()][tb].getFile()
        topfile_top = None
        if(top != None):
            topfile_top = block.grabCurrentDesigns()[block.getLib()][top].getFile()

        for l in labels:
            output.write(l+"\n")
        for f in file_order:
            #skip files if the file is a toplevel
            #if((topfile_tb != None and f.endswith(topfile_tb)) or (topfile_top != None and f.endswith(topfile_top))):
            #    continue
            output.write(f+"\n")

        #write current test dir where all testbench files are
        if(tb != None):
            output.write("@SIM-TOP "+tb+" "+topfile_tb+"\n")
        if(top != None):
            output.write("@SRC-TOP "+top+" "+topfile_top+"\n")
            
        output.close()
        #update the derives section to give details into what blocks are required for this one
        block.updateDerivatives(block_order)
        print("success")
        pass

    def formGraph(self, block, top):
        log.info("Generating dependency tree...")
        #start with top unit (returns all units if no top unit is found (packages case))
        block.grabUnits(top, override=True)
        hierarchy = Unit.Hierarchy
        hierarchy.output()
        
        unit_order,block_order = hierarchy.topologicalSort()

        print('---ENTITY ORDER---')
        for i in range(0, len(unit_order)):
            u = unit_order[i]
            if(not u.isPKG()):
                print(u.getFull(),end='')
                if(i < len(unit_order)-1):
                    print(' -> ',end='')
        print()

        print('---BLOCK ORDER---')
        #ensure the current block is the last one on order
        block_order.remove(block.getTitle())
        block_order.append(block.getTitle())
        for i in range(0, len(block_order)):
            b = block_order[i]
            print(b,end='')
            if(i < len(block_order)-1):
                print(' -> ',end='')
        print()

        return unit_order,list(block_order)

    #given a dependency graph, write out the actual list of files needed
    def compileList(self, block, unit_order):
        recipe_list = []
        for u in unit_order:
            line = ''
            #this unit comes from an external block so it is a library file
            if(u.getLib() != block.getLib() or u.getBlock() != block.getName()):
                line = '@LIB '+u.getLib()+' '
            #this unit is a simulation file
            elif(u.isTB()):
                line = '@SIM '
            #this unit is a source file
            else:
                line = '@SRC '
            #append file onto line
            line = line + u.getFile()
            #add to recipe list
            recipe_list.append(line)
        return recipe_list

    #! === DOWNLOAD COMMAND ===

    #will also install project into cache and have respective pkg in lib
    def download(self, title):
        l,n = Block.split(title)
        #1. download
        #update local block if it has a remote
        if(self.db.blockExists(title, "local")):
            blk = self.db.getBlocks("local")[l][n]
            #pull from remote url
            blk.pull()
        #download from market
        elif(self.db.blockExists(title, "market")):
            blk = self.db.getBlocks("market")[l][n]
            #use the remote git url to download/clone the block
            blk.downloadFromURL(blk.getMeta("remote"))
        #download from the cache
        elif(self.db.blockExists(title, "cache")):
            blk = self.db.getBlocks("cache")[l][n]
            dwnld_path = blk.getPath()
            if(blk.grabGitRemote() != None):
                dwnld_path = blk.grabGitRemote()
            #use the cache directory to download/clone the block
            blk.downloadFromURL(dwnld_path)
            #now return the block if wanting to open it with -o option
            return
        else:
            exit(log.error('Block \''+title+'\' does not exist in any linked market for this workspace'))
        
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
  
        pass

    #! === RELEASE COMMAND ===

    def upload(self, block, options=None):
        err_msg = "Flag the next version for release with one of the following args:\n"\
                    "\t[-v0.0.0 | -maj | -min | -fix]"
        if(len(options) == 0):
                exit(log.error(err_msg))
            
        ver = None
        if(options[0][0] == 'v'):
            ver = options[0]
        
        if(options[0] != 'maj' and options[0] != 'min' and options[0] != 'fix' and ver == None):
            exit(log.error(err_msg))
        #ensure top has been identified for release
        top_dog,_,_ = block.identifyTopDog(None, None)
        #update block requirements
        _,block_order = self.formGraph(block, top_dog)
        block.updateDerivatives(block_order)
        block.release(ver, options)
        #remove from cache and library to be reinstalled
        if(os.path.isdir(apt.WORKSPACE+"cache/"+block.getLib()+"/"+block.getName())):
            shutil.rmtree(apt.WORKSPACE+"cache/"+block.getLib()+"/"+block.getName(), onerror=apt.rmReadOnly)
        if(os.path.isfile(apt.WORKSPACE+"lib/"+block.getLib()+"/"+block.getName()+"_pkg")):
            shutil.rmtree(apt.WORKSPACE+"lib/"+block.getLib()+"/"+block.getName()+"_pkg", onerror=apt.rmReadOnly)
        #clone new project's progress into cache
        self.install(block.getTitle(), None)
        log.info(block.getLib()+"."+block.getName()+" is now available as version "+block.getVersion()+".")
        pass

    #! === CONFIG COMMAND ===

    def setSetting(self, options, choice, delete=False):
        if(len(options) == 0):
            log.error("No setting was flagged to as an option")
            return

        if(options[0] == 'gl-token' or options[0] == 'gh-token'):
            self.db.encrypt(choice, options[0])
            return
        
        if(choice == 'null'):
            choice = ''

        eq = choice.find("=")
        key = choice[:eq]
        val = choice[eq+1:] #write whole value
        if(eq == -1):
            val = None
            key = choice
        #chosen to delete setting from settings.yml
        if(delete):
            log.info("Deleting from setting: "+options[0])
            st = options[0].lower()
            #delete a key/value pair from the labels
            if(st == 'label'):
                if(choice in apt.SETTINGS[st]['recursive'].keys()):
                    del apt.SETTINGS[st]['recursive'][choice]
                if(choice in apt.SETTINGS[st]['shallow'].keys()):
                    del apt.SETTINGS[st]['shallow'][choice]
            #delete a key/value pair from the scripts or workspaces
            elif(st == 'script' or st == 'workspace' or st == 'market'):
                if(choice in apt.SETTINGS[st].keys()):
                    #print("delete")
                    #update active workspace if user deleted the current workspace
                    if(st == 'workspace'):
                        if(apt.SETTINGS['active-workspace'] == choice):
                            apt.SETTINGS['active-workspace'] = None
                            #prompt user to verify to delete active workspace
                            verify = apt.confirmation("Are you sure you want to delete the active workspace?")
                            if(not verify):
                                log.info("Command cancelled.")
                                return
                        #move forward with workspace removal
                        bad_directory = apt.HIDDEN+"workspaces/"+choice
                        print(bad_directory)
                        if(os.path.isdir(bad_directory)):
                            shutil.rmtree(bad_directory, onerror=apt.rmReadOnly)
                            log.info("Deleted workspace directory: "+bad_directory)
                    elif(st == 'market'):
                        Market(key,val).delete()
                        #remove from all workspace configurations
                        for nm in apt.SETTINGS['workspace'].keys():
                            if(key in apt.SETTINGS['workspace'][nm]['market']):
                                apt.SETTINGS['workspace'][nm]['market'].remove(key)
                            pass
                    del apt.SETTINGS[st][choice]

            apt.save()
            log.info("Setting saved successfully.")
            return
        #chosen to config a setting in settings.yml
        if(options[0] == 'active-workspace'):
            if(choice not in apt.SETTINGS['workspace'].keys()):
                exit(log.error("Workspace not found!"))
            else:
                #copy the map.toml for this workspace into user root for VHDL_LS
                shutil.copy(apt.HIDDEN+"workspaces/"+choice+"/map.toml", os.path.expanduser("~/.vhdl_ls.toml"))
                pass
        #invalid option flag
        if(not options[0] in apt.SETTINGS.keys()):
            exit(log.error("No setting exists under that flag"))
        elif(options[0] == 'market'):
            #@IDEA automatically appends new config to current workspace, can be skipped with -skip
            #remove from current workspace with -remove
            #append to current workspace with -append

            #allow for just referencing the market if trying to append to current workspace
            if(val == None and options.count("append") or options.count("remove")):
                pass
            else:
                #add/change value to all-remote list
                mkt = Market(key,val) #create market object!  
                if(val == ''):
                    val = None
                #only create remote in the list
                if(key in apt.SETTINGS['market'].keys()):
                    #market name already exists
                    val = mkt.setRemote(val) 
                #set to null if the tried remote DNE
                if(not mkt.isRemote()):
                    val = None
                apt.SETTINGS['market'][key] = val
            # add to active workspace markets
            if(options.count("append") and key not in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']): 
                apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market'].append(key)
            # remove from active workspace markets
            elif(options.count("remove") and key in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']):
                apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market'].remove(key)
        # WORKSPACE CONFIGURATION
        elif(options[0] == 'workspace'):
            #create entire new workspace settings
            if(not isinstance(apt.SETTINGS[options[0]],dict)):
                apt.SETTINGS[options[0]] = dict()
            #insertion
            if(val != None):
                #initialize the workspace folders and structure
                apt.initializeWorkspace(key)
                #create new workspace profile
                for lp in apt.SETTINGS[options[0]].values():
                    if(lp['local'].lower() == apt.fs(val).lower()):
                        exit(log.error("Workspace already exists with this path."))
                if(key not in apt.SETTINGS[options[0]]):
                    apt.SETTINGS[options[0]][key] = dict()
                    apt.SETTINGS[options[0]][key]['market'] = list()
                    apt.SETTINGS[options[0]][key]['local'] = None
                #now insert value
                apt.SETTINGS[options[0]][key]['local'] = apt.fs(val)
                #will make new directories if needed when setting local path
                if(not os.path.isdir(apt.SETTINGS[options[0]][key]['local'])):
                    log.info("Making new directory "+apt.SETTINGS[options[0]][key]['local'])
                    os.makedirs(apt.fs(val), exist_ok=True)

                #otherwise that directory already exists, are there any blocks already there?
                else:
                    #go through all the found blocks and see if any are "released"
                    blks = self.db.getBlocks("local")
                    for sects in blks.values():
                        for blk in sects.values():
                            apt.WORKSPACE = apt.HIDDEN+"workspaces/"+key+"/"
                            if(Block.biggerVer(blk.getVersion(),'0.0.0') != '0.0.0'):
                                #install to cache
                                log.info("Found "+blk.getTitle()+" already a released block.")
                                self.install(blk.getTitle())
                        pass
                    pass
                for rem in options:
                    if rem == options[0]:
                        continue
                    if rem not in apt.SETTINGS[options[0]][key]['market']:
                        apt.SETTINGS[options[0]][key]['market'].append(rem)
            else:
                exit(log.error("Workspace not added. Provide a local path for the workspace"))
            pass
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
                if(os.path.isfile(pt)):
                    filepath = os.path.realpath(os.path.expanduser(pt)).replace("\\", "/")
                    #reinsert nice formatted path into the list of args
                    file_index = parsed.index(pt)
                    parsed[file_index] = filepath
                    break
            if(filepath == ''):
                exit(log.error("No script path found in value"))

            _,ext = os.path.splitext(filepath)

            #skip link option- copy file and rename it same as name 
            if(options.count("lnk") == 0 and val != ''):   
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
        elif(options[0] == 'multi-develop'):
            if(choice == '1' or choice.lower() == 'true'):
                choice = True
            elif(choice == '0' or choice.lower() == 'false'):
                choice = False
            else:
                exit(log.error("Setting takes true or false values"))
            apt.SETTINGS[options[0]] = choice
            pass
        elif(options[0] == 'template'):
            if(choice == ''):
                apt.SETTINGS[options[0]] = None
            else:
                apt.SETTINGS[options[0]] = apt.fs(choice)
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
            apt.SETTINGS[options[0]] = choice
        
        apt.save()
        log.info("Setting saved successfully.")
        pass

    #! === INIT COMMAND ===
    
    #TO-DO: implement
    def convert(self, title, value, options=[]):
        #must look through tags of already established repo
        l,n = Block.split(title)
        if((l == '' or n == '') and len(options) == 0):
            exit(log.error("Must provide a library.block"))
        cwd = apt.fs(os.getcwd())

        #make sure this path is witin our workspace's path before making it a block
        if(cwd.lower().count(apt.getLocal().lower()) == 0):
            exit(log.error("Cannot initialize outside of workspace"))
        block = None

        if(self.blockCWD.isValid() and options.count("market")):
            if(value.lower() != ""):
                if(value not in apt.SETTINGS['market'].keys()):
                    exit(log.error("No market is recognized under "+value))
                if(value not in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']):
                    exit(log.error("The current workspace does not have "+value+" configured as a market"))
            else:
                value = None
            self.blockCWD.bindMarket(value)
            return
        elif(self.blockCWD.isValid() and options.count("remote")):
            if(apt.isValidURL(value)):
                self.blockCWD.setRemote(value)
                return
            elif(value == ''):
                self.blockCWD.setRemote(None)
                return
            else:
                exit(log.error("Invalid git url."))
        elif(self.blockCWD.isValid() and options.count("summary")):
            self.blockCWD.getMeta()['summary'] = value
            self.blockCWD.save()
            return
        elif(len(options)):
            if(l == '' or n == ''):
                exit(log.error("Could not fulfill init option flag"))

        files = os.listdir(cwd)
        if apt.MARKER in files or self.db.blockExists(title, "local") or self.db.blockExists(title, "cache") or self.db.blockExists(title, "market"):
            exit(log.info("Already a block existing for "+title))

        log.info("Transforming project into block...")
        #check if we are wanting to initialize from a git url
        #option to create a new block

        startup = False
        if(options.count("open")):
            startup = True
            options.remove("open")

        git_url,mrkt_sync = self.validateMarketAndURL(options)

        #rename current folder to the name of library.project
        last_slash = cwd.rfind('/')
        if(last_slash == len(cwd)-1):
            last_slash = cwd[:cwd.rfind('/')].rfind('/')

        cwdb1 = cwd[:last_slash]+"/"+n+"/"
        if(git_url == None):
            os.rename(cwd, cwdb1)
        else:
            cwdb1 = apt.getLocal()+l+"/"+n
            os.makedirs(cwdb1,exist_ok=True)
        #print(cwd,cwdb1)
        git_exists = True
        if ".git" not in files and git_url == None:
            #see if there is a .git folder and create if needed
            log.info("Initializing git repository...")
            git_exists = False
            pass
        
        #create marker file
        block = Block(title=title, path=cwdb1, remote=git_url, market=mrkt_sync)
        log.info("Creating "+apt.MARKER+" file...")
        block.create(fresh=False, git_exists=git_exists)
        pass

    def validateMarketAndURL(self, options):
        mkt_sync = None
        git_url = None
        #try to find a valid market being used
        for mkt in self.db.getGalaxy():
            for opt in options:
                if(mkt.getName() == opt):
                    log.info("Tying market "+mkt+" to this initialized block")
                    mkt_sync = mkt
                    options.remove(opt)
                    break
            if(mkt_sync != None):
                break
        #now try to find a valid git url
        for opt in options:
            if(apt.isValidURL(opt)):
                git_url = opt
        #print(git_url,mkt_sync)
        return git_url,mkt_sync

    #! === DEL COMMAND ===

    def cleanup(self, block, force=False):
        if(not block.isValid()):
            log.info('Block '+block.getName()+' does not exist locally.')
            return
        
        if(not block.isLinked() and force):
            log.warning('No market is configured for this block, if this module is deleted and uninstalled\n\
            it may be unrecoverable. PERMANENTLY REMOVE '+block.getTitle()+'? [y/n]\
            ')
            response = ''
            while(True):
                response = input()
                if(response.lower() == 'y' or response.lower() == 'n'):
                    break
            if(response.lower() == 'n'):
                log.info("Keeping block "+block.getTitle()+' installation.')
                force = False
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

    #! === LIST COMMAND ===

    def inventory(self, search_for, options):
        self.db.listBlocks(search_for.lower(), options)
        print()
        pass

    def listLabels(self):
        if(isinstance(apt.SETTINGS['label'],dict)):
            print('{:<20}'.format("Label"),'{:<24}'.format("Extension"),'{:<14}'.format("Recursive"))
            print("-"*20+" "+"-"*24+" "+"-"*14+" ")
            for depth,pair in apt.SETTINGS['label'].items():
                rec = "-"
                if(depth == "recursive"):
                    rec = "yes"
                for key,val in pair.items():
                    print('{:<20}'.format(key),'{:<24}'.format(val),'{:<14}'.format(rec))
                pass
        else:
            log.info("No Labels added!")
        pass

    def listMarkets(self):
        if(isinstance(apt.SETTINGS['market'],dict)):
            print('{:<16}'.format("Market"),'{:<40}'.format("URL"),'{:<12}'.format("Connected"))
            print("-"*16+" "+"-"*40+" "+"-"*12+" ")
            for key,val in apt.SETTINGS['market'].items():
                rec = 'no'
                if(key in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']):
                    rec = 'yes'
                print('{:<16}'.format(key),'{:<40}'.format(val),'{:<12}'.format(rec))
                pass
        else:
            log.info("No markets added!")
        pass
    
    def listWorkspace(self):
        if(isinstance(apt.SETTINGS['workspace'],dict)):
            print('{:<16}'.format("Workspace"),'{:<6}'.format("Active"),'{:<40}'.format("Path"),'{:<14}'.format("Markets"))
            print("-"*16+" "+"-"*6+" "+"-"*40+" "+"-"*14+" ")
            for key,val in apt.SETTINGS['workspace'].items():
                act = '-'
                rems = ''
                for r in val['market']:
                    rems = rems + r + ','
                if(key == apt.SETTINGS['active-workspace']):
                    act = 'yes'
                print('{:<16}'.format(key),'{:<6}'.format(act),'{:<40}'.format(val['local']),'{:<14}'.format(rems))
                pass
        else:
            log.info("No labels added!")
        pass

    def listScripts(self):
        if(isinstance(apt.SETTINGS['script'],dict)):
            print('{:<12}'.format("Name"),'{:<12}'.format("Command"),'{:<54}'.format("Path"))
            print("-"*12+" "+"-"*12+" "+"-"*54)
            for key,val in apt.SETTINGS['script'].items():
                spce = val.find(' ')
                cmd = val[1:spce]
                path = val[spce:len(val)-1].strip()
                #command not found
                if(spce == -1): 
                    path = cmd
                    cmd = ''
                print('{:<12}'.format(key),'{:<12}'.format(cmd),'{:<54}'.format(path))
                pass
        else:
            log.info("No scripts added!")
        pass

    #! === PARSING ===

    def parse(self, cmd, pkg, opt):
        #check if we are in a project directory (necessary to run a majority of commands)
        self.blockCWD = Block(path=os.getcwd()+"/")
   
        command = cmd
        package = pkg
        options = opt
        
        value = package
        package = package.replace("-", "_")

        L,N = Block.split(package)

        if(apt.inWorkspace()):
            if(self.db.blockExists(package,"local")):
                self.blockPKG = self.db.getBlocks("local")[L][N]
            else:
                self.blockPKG = None

        valid = (self.blockPKG != None)
        
        #branching through possible commands
        if(command == "install"):
            ver = None
            #ensure version option is valid before using it to install
            if(len(options) == 1 and Block.validVer(options[0]) == True):
                ver = options[0]
            elif(len(options) > 1):
                exit(log.error("Invalid Flags set for install command."))

            #install version from cache
            if(self.db.blockExists(package,"cache")):
                if(ver != None):
                    log.info("Installing "+ver+" from cache...")
                    
            elif(self.db.blockExists(package,"market")):
                ver_word = 'latest'
                if(ver != None):
                    ver_word = ver
                log.info("Installing "+ver_word+" from market...")
                
            else:
                exit(log.error("Block "+package+" does not exists for this workspace."))

            #install block to cache
            self.install(package, ver)
            pass
        elif(command == "uninstall"):
            ver = None
            #ensure version option is valid before using it to install
            if(len(options) == 1 and Block.validVer(options[0]) == True):
                ver = options[0]
            elif(len(options) > 1):
                exit(log.error("Invalid Flags set for install command."))

            self.uninstall(package, ver)
            pass
        elif(command == "build" and self.blockCWD.isValid()):
            self.build(value)
        elif(not valid and command == "new" and len(package)):
            #option to create a new file
            if(options.count("file")):
                options.remove("file")
                if(self.blockCWD.isValid()):
                    if(len(options) == 0):
                        exit(log.error("Please specify a file from your template to copy from"))
                    self.blockCWD.fillTemplateFile(package, options[0])
                else:
                    exit(log.error("Cannot create a project file when not inside a project"))
                return
            #option to create a new block
            startup = False
            if(options.count("o")):
                startup = True
                options.remove("o")

            git_url,mkt_sync = self.validateMarketAndURL(options)
            self.blockPKG = Block(title=package, new=True, market=mkt_sync, remote=git_url)

            if(startup):
                self.blockPKG.load()
            pass
        elif(command == "release" and self.blockCWD.isValid()):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(self.blockCWD, options=options)
            if(len(options) == 2 and options.count('d')):
                self.cleanup(self.blockCWD, False)
            pass
        #a visual aide to help a developer see what package's are at the ready to use
        elif(command == 'graph' and self.blockCWD.isValid()):
            top = package
            tb = None
            if(top == ''):
                top = None
            if(len(options)):
                tb = options[0]
            top_dog,_,_ = self.blockCWD.identifyTopDog(top, tb)
            #generate dependency tree
            self.formGraph(self.blockCWD, top_dog)
        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            self.download(package)
            if('o' in options):
                self.db.getBlocks("local", updt=True)[L][N].load()
            pass
        elif(command == 'del'):
            #try to delete a block
            if(valid):
                force = options.count('uninstall')
                self.cleanup(self.blockPKG, force)
            #try to delete a setting
            elif(L == '' or N == ''):
                self.setSetting(options, value, delete=True)
            else:
                log.info("Block does not exist in local path.")

        elif(command == "list"): #a visual aide to help a developer see what package's are at the ready to use
            if(options.count("script")):
                self.listScripts()
            elif(options.count("label")):
                self.listLabels()
            elif(options.count("market")):
                self.listMarkets()
            elif(options.count("workspace")):
                self.listWorkspace()
            else:
                self.inventory(package,options)
            pass
        elif(command == "init"):
            self.convert(package, value, options)
        elif(command == "refresh"):
            self.db.sync()
        elif(command == "export" and self.blockCWD.isValid()):
            #'' and list() are default to pkg and options
            mod = package
            tb = None
            if(mod == ''):
                mod = None
            if(len(options) > 0):
                tb = options[0]
            self.export(self.blockCWD, mod, tb)
            pass
        elif(command == "open"):
            if(apt.SETTINGS['editor'] == None):
                exit(log.error("No text-editor configured!"))

            if(options.count("template")):
                os.system(apt.SETTINGS['editor']+" \""+apt.TEMPLATE+"\"")
            elif(options.count("script")):
                os.system(apt.SETTINGS['editor']+" \""+apt.HIDDEN+"/scripts\"")
            elif(options.count("settings")):
                os.system(apt.SETTINGS['editor']+" \""+apt.HIDDEN+"/settings.yml\"")
            elif(valid):
                self.blockPKG.load()
            else:
                exit(log.error("No module "+package+" exists in your workspace."))
        elif(command == "show" and 
            (self.db.blockExists(package, "local") or \
                self.db.blockExists(package, "cache") or \
                self.db.blockExists(package, "market"))):
            self.db.getBlocks("local","cache","market")[L][N].show()
            pass
        elif(command == "port"):
            mapp = pure_ent = False
            ent_name = None
            if(len(options) and 'map' in options):
                mapp = True
            if(len(options) and 'inst' in options):
                pure_ent = True
            if(package.count('.') == 2): #if provided an extra identifier, it is the entity in this given project
                ent_name = package[package.rfind('.')+1:]
                package = package[:package.rfind('.')]

            inserted_lib = L
            if(self.blockCWD.isValid() and self.blockCWD.getLib() == L):
                inserted_lib = 'work'
            
            if((self.db.blockExists(package, "local") or self.db.blockExists(package, "cache"))):
                print(self.db.getBlocks("local","cache")[L][N].ports(mapp,inserted_lib,pure_ent,ent_name))
            else:
                exit(log.error("No block exists in local path or workspace cache."))
        elif(command == "config"):
            self.setSetting(options, value)
            pass
        elif(command == "help" or command == ''):
            #list all of command details
            self.commandHelp(package)
            print('USAGE: \
            \n\tlegohdl <command> [block] [flags]\
            \n')
            print("COMMANDS:")
            def formatHelp(cmd, des):
                print('  ','{:<12}'.format(cmd),des)
                pass
            formatHelp("init","initialize the current folder into a valid block format")
            formatHelp("new","create a templated empty block into workspace")
            formatHelp("open","opens the downloaded block with the configured text-editor")
            formatHelp("release","release a new version of the current Block")
            formatHelp("list","print list of all blocks available")
            formatHelp("install","grab block from its market for dependency use")
            formatHelp("uninstall","remove block from cache")
            formatHelp("download","grab block from its market for development")
            formatHelp("update","update installed block to be to the latest version")
            print()
            formatHelp("graph","visualize dependency graph for reference")
            formatHelp("export","generate a recipe file to build the block")
            formatHelp("build","run a custom configured script")
            formatHelp("del","deletes a block from local workspace or a configured setting")
            formatHelp("refresh","sync local markets with their remotes")
            formatHelp("port","print ports list of specified entity")
            formatHelp("show","read further detail about a specified block")
            formatHelp("config","set package manager settings")
            print("\nType \'legohdl help <command>\' to read more on entered command.")
        else:
            print("Invalid command; type \"legohdl help\" to see a list of available commands")
        pass

    #! === HELP COMMAND ===

    def commandHelp(self, cmd):
        def printFmt(cmd,val,options=''):
            print("USAGE:")
            print("\tlegohdl "+cmd+" "+val+" "+options)
            pass
        if(cmd == ''):
            return
        elif(cmd == "init"):
            printFmt("init", "<block>","[-remote | -market | -summary]")
            pass
        elif(cmd == "new"):
            printFmt("new","<block>","[-o -<remote-url> -<market-name>")
            pass
        elif(cmd == "open"):
            printFmt("open","<block>","[-template -script -settings]")
            pass
        elif(cmd == "release"):
            printFmt("release","\b","[[-v0.0.0 | -maj | -min | -fix] -d -strict -soft]")
            print("\n   -strict -> won't add any uncommitted changes along with release")
            print("\n   -soft -> will push a side branch to the linked market")
            pass
        elif(cmd == "list"):
            printFmt("list","[search]","[-alpha -local -script -label -market -workspace]")
            pass
        elif(cmd == "install"):
            printFmt("install","<block>","[-v0.0.0]")
            pass
        elif(cmd == "uninstall"):
            printFmt("uninstall","<block>")
            pass
        elif(cmd == "download"):
            printFmt("download","<block>","[-v0.0.0 -o]")
            pass
        elif(cmd == "update"):
            printFmt("update","<block>")
            pass
        elif(cmd == "export"):
            printFmt("export","[toplevel]","[-testbench]")
            pass
        elif(cmd == "build"):
            printFmt("build","[@<script>]","[...]")
            print("\n   [...] is all additional arguments and will be passed directly into the called script")
            print("   If no script name is specified, it will default to looking for script \"master\"")
            pass
        elif(cmd == "del"):
            printFmt("del","<block/value>","[-uninstall | -market | -script | -label | -workspace]")
            pass
        elif(cmd == "port"):
            printFmt("port","<block>","[-map -inst]")
            pass
        elif(cmd == "show"):
            printFmt("show","<block>")
            pass
        elif(cmd == "summ"):
            printFmt("summ","[-:\"summary\"]")
            pass
        elif(cmd == "config"):
            printFmt("config","<value>","""[-market [-remove | -append] | -author | -script [-lnk] | -label [-recursive] | -editor |\n\
                    \t\t-workspace [-<market-name> ...] | -active-workspace]\
            """)
            print("\n   Setting [-script], [-label], [-workspace], [-market] requires <value> to be <key>=\"<value>\"")
            print("   Using -append or -remove does not require the <value> to be <key>\"<value\"")
            print("   legohdl config lab=\"~/develop/hdl/\" -workspace") 
            pass
        exit()
        pass
    pass

def main():
    legoHDL()


if __name__ == "__main__":
    main()
