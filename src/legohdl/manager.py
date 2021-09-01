#!/usr/bin/env python3
from genericpath import isfile
import os, sys, shutil
from re import M
import yaml
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
        l,n = Block.split(title, vhdl=False)
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
        elif(self.db.blockExists(title, "market")):
            block = self.db.getBlocks("market")[l][n]
        elif(self.db.blockExists(title, "local", updt=True)):
            block = self.db.getBlocks("local")[l][n]
            verify_url = True
        else:
            exit(log.error(title+" cannot be found anywhere."))

        #append to required_by list used to prevent cyclic recursive nature
        required_by.append(block.getTitle()+'('+block.getVersion()+')')
        #see if all cache blocks are available by looking at block's derives list
        for prereq in block.getMeta("derives"):
            if(prereq == block.getTitle() or prereq in required_by):
                continue
            #split prereq into library, name, and version
            L,N,verreq = block.splitDetachVer(prereq)

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
        #remove from cache
        l,n = Block.split(blk)
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
                        parent_meta = yaml.load(tmp_f, Loader=yaml.FullLoader)
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
                    #todo: also update the parent version to a new level or delete it
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
            L,N = Block.split(blk, vhdl=False)
            cached_ver = None
            #cast off version 
            v_index = N.rfind("(v")
            if(v_index > -1 and N.rfind(")")):
                cached_ver = N[v_index+1:len(N)-1]
                N = N[:v_index]
            #reassemble block name
            blk = L+'.'+N
            #assign tmp block to the current block
            if(block.getTitle() == blk):
                tmp = block
            #assign tmp block to block in downloads if multi-develop enabled and version is none
            elif(cached_ver == None and self.db.blockExists(blk, "local") and apt.SETTINGS['multi-develop']):
                tmp = self.db.getBlocks("local")[L][N]
            #assign tmp block to the cache block
            elif(self.db.blockExists(blk, "cache")):
                tmp = self.db.getBlocks("cache")[L][N]
            else:
                log.warning("Cannot locate block "+blk+" for label searching")
                continue

            #using the version that was latched onto the name, alter cache path setting?
            if(cached_ver != None):
                base_cache_path = os.path.dirname(tmp.getPath()[:len(tmp.getPath())-1])
                cached_ver = base_cache_path+"/"+cached_ver+"/"
                pass
            #add any recursive labels
            for label,ext in apt.SETTINGS['label']['recursive'].items():
                files = tmp.gatherSources(ext=[ext], path=cached_ver)
                for f in files:
                    labels.append("@"+label+" "+apt.fs(f))
            #add any project-level labels
            if(block.getTitle() == blk):
                for label,ext in apt.SETTINGS['label']['shallow'].items():
                    files = block.gatherSources(ext=[ext])
                    for f in files:
                        labels.append("@"+label+" "+apt.fs(f))

        #register what files the top levels originate from (transform variables in unit objects)
        if(tb != None):
            tb = block.grabCurrentDesigns()[block.getLib()][tb]
        if(top != None):
            top = block.grabCurrentDesigns()[block.getLib()][top]

        for l in labels:
            output.write(l+"\n")
        for f in file_order:
            #skip files if the file is a toplevel
            #if((topfile_tb != None and f.endswith(topfile_tb)) or (topfile_top != None and f.endswith(topfile_top))):
            #    continue
            output.write(f+"\n")

        #write current test dir where all testbench files are
        if(tb != None):
            line = '@'
            if(tb.getLanguageType() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(tb.getLanguageType() == Unit.Language.VERILOG):
                line = line+"VERI"
            output.write(line+"-SIM-TOP "+tb.getName(low=False)+" "+tb.getFile()+"\n")
        if(top != None):
            line = '@'
            if(top.getLanguageType() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(top.getLanguageType() == Unit.Language.VERILOG):
                line = line+"VERI"
            output.write(line+"-SRC-TOP "+top.getName(low=False)+" "+top.getFile()+"\n")
            
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
            line = '@'
            if(u.getLanguageType() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(u.getLanguageType() == Unit.Language.VERILOG):
                line = line+"VERI"
            #this unit comes from an external block so it is a library file
            if(u.getLib() != block.getLib() or u.getBlock() != block.getName()):
                line = line+'-LIB '+u.getLib()+' '
            #this unit is a simulation file
            elif(u.isTB()):
                line = line+'-SIM '
            #this unit is a source file
            else:
                line = line+'-SRC '
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
            log.info("Downloading "+blk.getTitle()+" from "+blk.getMeta('market')+' with '+blk.getMeta('remote')+"...")
            #use the remote git url to download/clone the block
            blk.downloadFromURL(blk.getMeta("remote"))
        #download from the cache
        elif(self.db.blockExists(title, "cache")):
            blk = self.db.getBlocks("cache")[l][n]
            dwnld_path = blk.getPath()
            if(blk.grabGitRemote() != None):
                dwnld_path = blk.grabGitRemote()
            log.info("Downloading "+blk.getTitle()+" from cache with "+dwnld_path+"...")
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

    def upload(self, block, msg=None, options=None):
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
        top_dog,_,_ = block.identifyTopDog(None, None)
        #update block requirements
        _,block_order = self.formGraph(block, top_dog)
        block.updateDerivatives(block_order)
        block.release(msg, ver, options)
        #don't look to market when updating if the block does not link to market anymore
        bypassMrkt = (block.getMeta('market') in apt.getMarkets())
        self.update(block.getTitle(low=False), block.getVersion(), bypassMrkt=bypassMrkt)

        log.info(block.getLib()+"."+block.getName()+" is now available as version "+block.getVersion()+".")
        pass

    #! === CONFIG COMMAND ===

    def setSetting(self, options, choice, delete=False):
        if(len(options) == 0):
            log.error("No setting was flagged to as an option")
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
                        #print(bad_directory)
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

        #invalid option flag
        if(not options[0] in apt.SETTINGS.keys()):
            exit(log.error("No setting exists under that flag"))
        elif(options[0] == 'market'):
            #@IDEA automatically appends new config to current workspace, can be skipped with -skip
            #remove from current workspace with -remove
            #append to current workspace with -append

            #allow for just referencing the market if trying to append to current workspace
            if(val == None and options.count("add") or options.count("remove")):
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
            if(options.count("add") and key not in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']): 
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
                    if(lp['local'] != None and lp['local'].lower() == apt.fs(val).lower()):
                        exit(log.error("A workspace already exists with this path."))
                #now insert value
                apt.SETTINGS[options[0]][key]['local'] = apt.fs(val)
                #will make new directories if needed when setting local path
                if(not os.path.isdir(apt.SETTINGS[options[0]][key]['local'])):
                    log.info("Making new local directory... "+apt.SETTINGS[options[0]][key]['local'])
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
                                log.info("Found "+blk.getTitle()+" as an already a released block.")
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

        if(startup):
            block.load()
        pass

    def validateMarketAndURL(self, options):
        mkt_sync = None
        git_url = None
        #try to find a valid market being used
        for mkt in self.db.getMarkets():
            for opt in options:
                if(mkt.getName() == opt):
                    log.info("Tying market "+mkt+" to this initialized block...")
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
        log.warning("No valid market is attached.")
        return git_url,mkt_sync

    #! === DEL COMMAND ===

    def cleanup(self, block, force=False):
        if(not block.isValid()):
            log.info('Block '+block.getName()+' does not exist locally.')
            return
        
        if(not block.isLinked() and (force or block.getVersion() == '0.0.0')):
            confirmed = apt.confirmation('No market is configured for '+block.getTitle()+', if it\'s deleted and uninstalled \
it may be unrecoverable. PERMANENTLY REMOVE '+block.getTitle()+'?')
        
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
            print('{:<16}'.format("Market"),'{:<50}'.format("URL"),'{:<12}'.format("Available"))
            print("-"*16+" "+"-"*50+" "+"-"*12)
            for key,val in apt.SETTINGS['market'].items():
                rec = 'no'
                if(key in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']):
                    rec = 'yes'
                if(val == None):
                    val = 'local'
                print('{:<16}'.format(key),'{:<50}'.format(val),'{:<12}'.format(rec))
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

    #! === UPDATE COMMAND ===

    def update(self, title, ver=None, bypassMrkt=False):
        l,n = Block.split(title)
        #check if market version is bigger than the installed version
        c_ver = '0.0.0'
        if(self.db.blockExists(title, "cache")):
            cache_block = self.db.getBlocks("cache")[l][n]
            c_ver = cache_block.getVersion()

        m_ver = ver
        if(not bypassMrkt and self.db.blockExists(title, "market")):
            mrkt_block = self.db.getBlocks("market")[l][n]
            m_ver = mrkt_block.getVersion()
        elif(ver == None):
            exit(log.error(title+" cannot be updated from any of the workspace's markets."))
        
        if((Block.biggerVer(m_ver,c_ver) == m_ver and m_ver != c_ver)):
            log.info("Updating "+title+" installation to v"+m_ver)
            #remove from cache's master branch to be reinstalled
            base_installation = apt.WORKSPACE+"cache/"+l+"/"+n+"/"+n+"/"
            if(os.path.isdir(base_installation)):
                shutil.rmtree(base_installation, onerror=apt.rmReadOnly)

            #also update locally if exists
            if(self.db.blockExists(title,"local")):
                self.download(title)
            #clone new project's progress into cache
            self.install(title, None)
        else:
            log.info(title+" already up-to-date. (v"+c_ver+")")
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
                ver = Block.stdVer(options[0])
            elif(len(options) > 1):
                exit(log.error("Invalid flags set for install command."))

            # #install version from cache
            # if(self.db.blockExists(package,"cache")):
            #     if(ver != None):
            #         log.info("Installing "+ver+" from cache...")
                    
            # elif(self.db.blockExists(package,"market")):
            #     ver_word = 'latest'
            #     if(ver != None):
            #         ver_word = ver
            #     log.info("Installing "+ver_word+" from market...")
                
            # else:
            #     exit(log.error("Block "+package+" does not exists for this workspace."))

            if(options.count('requirements')):
                if(self.blockCWD.isValid()):
                    log.info("Installing requirements...")
                else:
                    exit(log.error("Invalid block directory!"))
                #read the derives list of this block
                requirements = self.blockCWD.getMeta('derives')
                for req in requirements:
                    L,N,V = Block.splitDetachVer(req)
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
            if(options.count("open")):
                startup = True
                options.remove("open")

            git_url,mkt_sync = self.validateMarketAndURL(options)
            self.blockPKG = Block(title=package, new=True, market=mkt_sync, remote=git_url)

            if(startup):
                self.blockPKG.load()
            pass
        elif(command == "release" and self.blockCWD.isValid()):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            if(value == ''):
                value = None
            self.upload(self.blockCWD, value, options=options)

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
            if('open' in options):
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
            #package value is the market looking to refresh
            #if package value is null then all markets tied to this workspace refresh by default
            self.db.sync(value)
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
            #open template
            if(options.count("template")):
                log.info("Opening block template folder at... "+apt.fs(apt.TEMPLATE))
                os.system(apt.SETTINGS['editor']+" \""+apt.TEMPLATE+"\"")
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
                else:
                        log.info("Opening built-in script folder at... "+script_path)

                os.system(apt.SETTINGS['editor']+" "+script_path)
            #open settings
            elif(options.count("settings")):
                log.info("Opening settings YAML file at... "+apt.HIDDEN+"settings.yml")
                os.system(apt.SETTINGS['editor']+" \""+apt.HIDDEN+"/settings.yml\"")
            #open block
            elif(valid):
                self.blockPKG.load()
            else:
                exit(log.error("No block "+package+" exists in your workspace."))
        elif(command == "show" and 
            (self.db.blockExists(package, "local") or \
                self.db.blockExists(package, "cache") or \
                self.db.blockExists(package, "market"))):
            ver = None
            changelog = options.count('changelog')
            if(len(options) == 1 and (Block.validVer(options[0]) == True or Block.validVer(options[0], maj_place=True))):
                ver = Block.stdVer(options[0])
            #print available versions
            listVers = options.count("version")

            if(self.db.blockExists(package, "cache") == True):
                self.db.getBlocks("cache")[L][N].show(listVers, ver, changelog)
            elif(self.db.blockExists(package, "local") == True):
                self.db.getBlocks("local")[L][N].show(listVers, ver, changelog)
            elif(self.db.blockExists(package, "market") == True):
                self.db.getBlocks("market")[L][N].show(listVers, ver, changelog)

            pass
        elif(command == "update" and self.db.blockExists(package,"cache")):
            #perform install over remote url
            self.update(package)
            pass
        elif(command == "port"):
            mapp = pure_ent = False
            ent_name = None
            if(len(options) and 'map' in options):
                mapp = True
            if(len(options) and 'instance' in options):
                pure_ent = True
            if(package.count('.') == 2): #if provided an extra identifier, it is the entity in this given project
                ent_name = package[package.rfind('.')+1:]
                package = package[:package.rfind('.')]
            #grab the version number if it was in flags
            ver = None
            for o in options:
                if(Block.validVer(o) or Block.validVer(o, maj_place=True)):
                    ver = Block.stdVer(o)
                    break

            inserted_lib = L
            if(self.blockCWD.isValid() and self.blockCWD.getLib() == L):
                inserted_lib = 'work'
            
            if((self.db.blockExists(package, "local") or self.db.blockExists(package, "cache"))):
                print(self.db.getBlocks("local","cache")[L][N].ports(mapp,inserted_lib,pure_ent,ent_name,ver))
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
            print("COMMANDS:\n")
            def formatHelp(cmd, des):
                print('  ','{:<12}'.format(cmd),des)
                pass
            print("Development")
            formatHelp("init","initialize the current folder into a valid block format")
            formatHelp("new","create a templated empty block into workspace")
            formatHelp("open","opens the downloaded block with the configured text-editor")
            formatHelp("port","print ports list of specified entity")
            formatHelp("graph","visualize dependency graph for reference")
            formatHelp("export","generate a recipe file from labels")
            formatHelp("build","run a custom configured script")
            formatHelp("release","release a new version of the current block")
            formatHelp("del","deletes a configured setting or a block from local workspace")
            print()
            print("Management")
            formatHelp("list","print list of all blocks available")
            formatHelp("refresh","sync local markets with their remotes")
            formatHelp("install","grab block from its market for dependency use")
            formatHelp("uninstall","remove block from cache")
            formatHelp("download","grab block from its market for development")
            formatHelp("update","update installed block to be to the latest version")
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
            printFmt("init", "<block/value>","[-remote | -market | -summary]")
            rollover("""
If no flags are raised, transform the working directory into a valid block. This will
create a git repository if not available, and create the Block.lock file. If there is a
raised flag, then the block's flag will be altered with the <value>.
            """)
            print('{:<16}'.format("<block/value>"),"if no flags, transform current directory into a valid block")
            print()
            print('{:<16}'.format("-remote"),"provide a valid git URL as <value> to set for this block")
            print('{:<16}'.format("-market"),"provide a market name as <value> available from the workspace")
            print('{:<16}'.format("-summary"),"provide a string as <value> to set for this block's summary")
            pass
        elif(cmd == "new"):
            printFmt("new","<block>","[-open -<remote> -<market>]")
            rollover("""
Create a new block into the base of the workspace's local path. The block's default 
created path is <workspace-path>/<block-library>/<block-name>. The template folder 
will be copied and a git repository will be created. 
            """)
            print('{:<16}'.format("-open"),"open the new block upon creation")
            print('{:<16}'.format("-<remote>"),"provide a blank git URL to be configured")
            print('{:<16}'.format("-<market>"),"provide a market name that's available in this workspace")
            pass
        elif(cmd == "open"):
            printFmt("open","[<block/script>]","[-template -script -settings]")
            rollover("""
Open a variety of legohdl folders/files. With no flags raised, the block will be opened if
it is found in the workspace's local path. If the script flag is raised with no <script>,
it will open the built-in script folder. If a valid <script> is specified with the script 
flag raised, it will directly open its file.
            """)
            print('{:<16}'.format("<block/script>"),"open the downloaded block or the script")
            print('{:<16}'.format(""),"file if the `-script` flag is raised")
            print()
            print('{:<16}'.format("-template"),"open the template folder")
            print('{:<16}'.format("-script"),"open the built-in script folder if no script specified")
            print('{:<16}'.format("-settings"),"open the settings YAML file")
            pass
        elif(cmd == "release"):
            printFmt("release","[<message>]","[[-v0.0.0 | -maj | -min | -fix] -strict -soft]")
            rollover("""
Creates a valid legohdl release point to be used in other designs. This will auto-detect 
the toplevel unit, testbench unit, and determine the exact version dependencies required. 
It will then stage, commit, and tag any changes. If the block has a valid remote, it will 
push to the remote. If the block has a valid market, the Block.lock file will be updated there.
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
            printFmt("list","[[<search>]","[-alpha]] [-script | -label | -market | -workspace]")
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
            pass
        elif(cmd == "install"):
            printFmt("install","<block>","[-v0.0.0]")
            rollover("""
Clones the block's main branch to the cache. If the main branch is already found in the cache,
it will not clone/pull from the remote repository (see "update" command). Checkouts and copies 
the version (default is latest if unspecified) to have its own location in the cache. The 
entities of the install version are appeneded with its appropiate version (_v0_0_0). Each 
version install may also update the location for its major value (_v0) if its the highest yet. 
            """)
            print('{:<16}'.format("-v0.0.0"),"specify what version to install (replace 0's)")
            pass
        elif(cmd == "uninstall"):
            printFmt("uninstall","<block>","[-v0.0.0]")
            rollover("""
Removes installed versions from the cache. If no version is specified, then ALL versions will be
removed as well as the cloned main branch. Specifying a version will only remove that one, if its
been installed.
            """)
            print('{:<16}'.format("-v0.0.0"),"specify what version to uninstall (replace 0's)")
            pass
        elif(cmd == "download"):
            printFmt("download","<block>","[-open]")
            rollover("""
Grab a block from either its remote url (found via market) or from the cache. The block will
be downloaded to <workspace-path>/<block-library>/<block-name>. If the block is not installed to
the cache, it will also install the latest version to the cache.
            """)
            print('{:<16}'.format("-open"),"open the block upon download to be developed")
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
            printFmt("port","<block>","[-map -instance]")
            pass
        elif(cmd == "show"):
            printFmt("show","<block>","[-version | -v0.0.0]")
            pass
        elif(cmd == "config"):
            printFmt("config","<value>","""[-market [-add | -remove] | -author | -script [-link] | -label [-recursive] | -editor |\n\
                    \t\t-workspace [-<market-name> ...] | -active-workspace]\
            """)
            print("\n   Setting [-script], [-label], [-workspace], [-market] requires <value> to be <key>=\"<value>\"")
            print("   Using -add or -remove does not require the <value> to be <key>\"<value\"")
            print("   legohdl config lab=\"~/develop/hdl/\" -workspace") 
            pass
        print()
        exit()
        pass
    pass

def main():
    legoHDL()


if __name__ == "__main__":
    main()
