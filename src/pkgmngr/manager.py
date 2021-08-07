#!/usr/bin/env python3
from genericpath import isdir
import os, sys, shutil
import yaml, glob
from .block import Block
from .__version__ import __version__
from .registry import Registry
from .graph import Graph
from .apparatus import Apparatus as apt
from .market import Market
import logging as log
from ordered_set import OrderedSet
from .unit import Unit

class legoHDL:

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
            pass
        
        apt.load() #load settings.yml
        self.BlockPKG = None
        self.BlockCWD = None
        #defines path to dir of remote code base
        self.db = Registry(apt.getMarkets())
        if(apt.inWorkspace()):
            Block.fetchLibs(self.db.availableLibs())
        if(not apt.inWorkspace() and (command != 'config' and command != 'help' and (command != 'open' or "settings" not in options))):
            exit()
        self.parse(command, package, options)
        pass

    def genPKG(self, title):
        cap = None
        if(self.db.capExists(title, "cache", updt=True)):
            cache = self.db.getCaps("cache")
            l,n = Block.split(title)
            cap = cache[l][n]
        else:
            exit(log.error("The module is not located in the cache"))
            return

        lib_path = apt.WORKSPACE+"lib/"+cap.getLib()+"/"
        os.makedirs(lib_path, exist_ok=True)
        
        vhd_pkg = open(lib_path+cap.getName()+"_pkg.vhd", 'w')

        pkg_entry = "package "+cap.getName()+"_pkg is"
        pkg_close = "end package;"

        pkg_body_entry = "\n\npackage body "+cap.getName()+"_pkg is"
        pkg_body_close = "\nend package body;"

        pkg_lines = [pkg_entry, pkg_close, pkg_body_entry, pkg_body_close]

        #need to look at toplevel VHD file to transfer correct library uses
        #search through all library uses and see what are chained dependencies
        derivatives = cap.scanLibHeaders(cap.getMeta("toplevel"))
        #write in all library and uses
        #print(derivatives)
        for dep in derivatives:
            vhd_pkg.write(dep)

        vhd_pkg.write("\n")

        # generate a PKG VHD file -> lib
        addedCompDec = False
        for line in pkg_lines:
            if not addedCompDec and line.startswith("package"):
                addedCompDec = True
                comp = cap.ports(False)
                comp_break = comp.split('\n')

                line = line + "\n"
                for c in comp_break:
                    line = line + "\t" + c + "\n"
                pass
            vhd_pkg.write(line)
        vhd_pkg.close()
        pass

    def install(self, title, ver=None, opt=list()):
        l,n = Block.split(title)
        cap = None
        cache_path = apt.WORKSPACE+"cache/"
        lib_path = apt.WORKSPACE+"lib/"+l+"/"
        #does the package already exist in the cache directory?
        if(self.db.capExists(title, "cache", updt=True)):
            log.info("The module is already installed.")
            return
        elif(self.db.capExists(title, "market")):
            cap = self.db.getCaps("market")[l][n]
            pass
        elif(self.db.capExists(title, "local")):
            cap = self.db.getCaps("local")[l][n]
        else:
            log.error("The module cannot be found anywhere.")
            return
        # clone the repo -> cache      
        #possibly make directory for cached project
        print("Installing... ",end='')
        cache_path = cache_path+cap.getLib()+"/"
        os.makedirs(cache_path, exist_ok=True)
        #see what the latest version available is and clone from that version unless specified
        #print(rep.git_url)#print(rep.last_version)
        cap.install(cache_path, ver)
        print("success")
    
        #link it all together through writing paths into "map.toml"
        filename = apt.WORKSPACE+"map.toml"
        mapfile = open(filename, 'r')
        cur_lines = mapfile.readlines()
        mapfile.close()

        mapfile = open(filename, 'w')
        inc_paths = list()
        #generate PKG VHD
        if(cap.getMeta("toplevel") != None):
            self.genPKG(cap.getTitle())
            inc_paths.append("\'"+lib_path+cap.getName()+"_pkg.vhd"+"\',\n")

        for f in cap.gatherSources():
            inc_paths.append("\'"+f+"\',\n")
        inc = False
        found_lib = False
        if(len(cur_lines) <= 1):
            cur_lines.clear()
            mapfile.write("[libraries]\n")

        for line in cur_lines:
            if(line.count(cap.getLib()+".files") > 0): #include into already established library section
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
            mapfile.write(cap.getLib()+".files = [\n")
            for p in inc_paths:
                mapfile.write(p)
            mapfile.write("]\n")

        mapfile.close()
        #update current map.toml as well
        shutil.copy(filename, os.path.expanduser("~/.vhdl_ls.toml"))
        pass

    def uninstall(self, pkg, opt=None):
        #remove from cache
        l,n = Block.split(pkg)
        if(self.db.capExists(pkg, "cache")):
            cache = self.db.getCaps("cache")
            cache_path = cache[l][n].getPath()
            shutil.rmtree(cache_path)
            #if empty dir then do some cleaning
            if(len(os.listdir(apt.WORKSPACE+"cache/"+l)) == 0):
                os.rmdir(apt.WORKSPACE+"cache/"+l)
                pass
            #remove from lib
            lib_path = cache_path.replace("cache","lib")
            lib_path = lib_path[:len(lib_path)-1]+"_pkg.vhd"
            os.remove(lib_path)
            #if empty dir then do some cleaning
            if(len(os.listdir(apt.WORKSPACE+"lib/"+l)) == 0):
                os.rmdir(apt.WORKSPACE+"lib/"+l)
                pass

        #remove from 'map.toml'
        lines = list()
        filename = apt.WORKSPACE+"map.toml"
        with open(filename, 'r') as file:
            lines = file.readlines()
            file.close()
        with open(filename, 'w') as file:
            for lin in lines:
                if(lin.count(l) and (lin.count("/"+n+"/") or lin.count("/"+n+"_pkg"))):
                    continue
                file.write(lin)
            file.close()
        #update current map.toml as well
        shutil.copy(filename, os.path.expanduser("~/.vhdl_ls.toml"))
        pass
    
    @DeprecationWarning
    def recurseScan(self, dep_list, label_list):
        if(len(dep_list) == 0):
            return label_list
        #go to YML of dependencies and add edges to build dependency tree
        for d in dep_list:
            l,n = Block.split(d)
            n = n.replace("_pkg", "")
            if(os.path.isfile(apt.WORKSPACE+"cache/"+l+"/"+n+"/"+apt.MARKER)):
                #here is where we check for matching files with custom recursive labels
                for key,val in apt.SETTINGS['label'].items():
                    ext,recur = val
                    if(recur == True): #recursive
                        results = glob.glob(apt.WORKSPACE+"cache/"+l+"/"+n+"/**/*"+ext, recursive=True)
                        for find in results:
                            label_list.append("@"+key+" "+find)
                        pass
                #open the metadata to retrieve data to be used to build dependency chain
                with open(apt.WORKSPACE+"cache/"+l+"/"+n+"/"+apt.MARKER, "r") as file:
                    tmp = yaml.load(file, Loader=yaml.FullLoader)
            else:
                continue
            label_list = self.recurseScan(tmp['derives'], label_list)
        return label_list

    #TO-DO: make std version option checker
    def validVersion(self, ver):
        pass

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

        cmd = "\""+cmd+"\" "
        for i,arg in enumerate(sys.argv):
            if(i < arg_start):
                continue
            else:
                cmd = cmd + arg + " "
        os.system(cmd)

    def export(self, cap, top=None, tb=None):
        log.info("Exporting...")
        log.info(cap.getPath())
        build_dir = cap.getPath()+"build/"
        #create a clean build folder
        log.info("Cleaning build folder...")
        if(os.path.isdir(build_dir)):
            shutil.rmtree(build_dir)
        os.mkdir(build_dir)

        log.info("Finding toplevel design...")
        #add export option to override auto detection
        if(top == None):
            top = cap.getMeta("toplevel")
            tb = cap.getMeta("bench")
        elif(top != None and tb == None):
            tb = cap.getMeta("bench")
            bench_ent = cap.identifyBench(top)
            if(bench_ent != None):
                tb = bench_ent.getName()
        
        output = open(build_dir+"recipe", 'w')    

        #mission: recursively search through every src VHD file for what else needs to be included
        unit_order,block_order = self.formGraph(cap)
        file_order = self.compileList(cap, unit_order)  

        #add labels in order from lowest-projects to top-level project
        labels = []
        for blk in block_order:
            L,U = Block.split(blk)
            tmp = self.db.getCaps("cache")[L][U]
            #reassign tmp block to the current block
            if(cap.getTitle() == blk):
                tmp = cap
            #add any recursive labels
            for label,ext in apt.SETTINGS['label']['recursive'].items():
                files = tmp.gatherSources(ext=[ext])
                for f in files:
                    labels.append("@"+label+" "+f)
            #add any project-level labels
            if(cap.getTitle() == blk):
                for label,ext in apt.SETTINGS['label']['shallow'].items():
                    files = cap.gatherSources(ext=[ext])
                    for f in files:
                        labels.append("@"+label+" "+f)

        for l in labels:
            output.write(l+"\n")
        for f in file_order:
            output.write(f+"\n")

        #write current test dir where all testbench files are
        if(tb != None):
            output.write("@SIM-TOP "+tb+"\n")

        if(top != None):
            output.write("@SRC-TOP "+top+"\n")

        output.close()

        cap.updateDerivatives()
        print("success")
        pass

    def recursiveGraph(self, cap, grph, lbls, viewed):
        #find any project-level labels (must be enabled as recursive)
        for label,ext in apt.SETTINGS['label']['recursive'].items():
            files = cap.gatherSources(ext=[ext])
            for f in files:
                lbls.append("@"+label+" "+f)

        #grab only source-design entities (its an external referenced project)
        units = cap.grabUnits(excludeTB=True)
        for name,unit in list(units[cap.getLib()].items()):
            #print(name)
            grph.addLeaf(unit)
            #make the connections between a unit and its dependencies
            for dep in unit.getRequirements():
                grph.addEdge(unit.getFull(), dep.getFull())
                pass
                #only go to cache if the if the requirement is not a part of the current block
                if(dep.getLib() != cap.getLib() and dep.getBlock() != cap.getName()):
                    #create project object based on this external package
                    ext_cap = self.db.getCaps("cache")[dep.getLib()][dep.getBlock()]
                    blk = ext_cap.getTitle()
                    if(blk not in viewed):
                        #print("NEXT CAP:",ext_cap.getTitle())
                        viewed.append(ext_cap.getTitle())
                        #recursively feed into dependency tree
                        grph, lbls, viewed = self.recursiveGraph(ext_cap, grph, lbls, viewed)
            pass
        return grph, lbls, viewed

    def formGraph(self, cap):
        log.info("Generating dependency tree...")
        #start with top unit (returns all units if no top unit is found (packages case))
        units = cap.getHighestUnit()
        
        hierarchy = Unit.Hierarchy
        hierarchy.output()
        unit_order,block_order = hierarchy.topologicalSort()
        print('---BUILD ORDER---')
        for u in unit_order:
            if(not u.isPKG()):
                print(u.getFull(),end=' -> ')
        print()

        print('---BLOCK ORDER---')
        for b in block_order:
            print(b,end=' -> ')
        print()

        return unit_order,block_order

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

    #will also install project into cache and have respective pkg in lib
    def download(self, title):
        l,n = Block.split(title)

        if(True):
            if(self.db.capExists(title, "cache") and not self.db.capExists(title, "local")):
                instl = self.db.getCaps("cache")[l][n]
                instl.clone(src=instl.getPath())
                return self.db.getCaps("local",updt=True)[l][n]
            exit(log.error("No remote code base configured to download modules"))

        if(not self.db.capExists(title, "market")):
            exit(log.error('Module \''+title+'\' does not exist in market'))

        #TO-DO: retesting
        if(self.db.capExists(title, "local")):
            log.info("Module already exists in local workspace- pulling from remote...")
            self.db.getCaps("local")[l][n].pull()
        else:
            log.info("Cloning from market...")
            self.db.getCaps("market")[l][n].clone()
    
        try: #remove cached project already there
            shutil.rmtree(apt.WORKSPACE+"cache/"+l+"/"+n+"/")
        except:
            pass
        #install to cache and generate PKG VHD 
        cap = self.db.getCaps("local", updt=True)[l][n]  
        self.install(cap.getTitle(), cap.getVersion())

        print("success")
        pass

    def upload(self, cap, options=None):
        err_msg = "Flag the next version for release with one of the following args:\n"\
                    "\t[-v0.0.0 | -maj | -min | -fix]"
        if(len(options) == 0):
                exit(log.error(err_msg))
            
        ver = ''
        if(options[0][0] == 'v'):
            ver = options[0]
        
        if(options[0] != 'maj' and options[0] != 'min' and options[0] != 'fix' and ver == ''):
            exit(log.error(err_msg))
        
        cap.identifyTop()
        cap.updateDerivatives()
        cap.release(ver, options)
        if(os.path.isdir(apt.WORKSPACE+"cache/"+cap.getLib()+"/"+cap.getName())):
            shutil.rmtree(apt.WORKSPACE+"cache/"+cap.getLib()+"/"+cap.getName())
        #clone new project's progress into cache
        self.install(cap.getTitle(), cap.getVersion())
        log.info(cap.getLib()+"."+cap.getName()+" is now available as version "+cap.getVersion()+".")
        pass

    def setSetting(self, options, choice):
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
            val = ''
            key = choice
        if(options[0] == 'active-workspace'):
            if(choice not in apt.SETTINGS['workspace'].keys()):
                exit(log.error("Workspace not found!"))
            else:
                #copy the map.toml for this workspace into user root for VHDL_LS
                shutil.copy(apt.HIDDEN+choice+"/map.toml", os.path.expanduser("~/.vhdl_ls.toml"))
                pass

        if(options[0] == 'market-append' and key in apt.SETTINGS['market'].keys()):
            if(key not in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']):
                apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market'].append(key)
            pass
        elif(options[0] == 'market-rm'):
            if(key in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']):
                apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market'].remove(key)
            pass
        elif(options[0] == 'market'):
            #@IDEA automatically appends new config to current workspace, can be skipped with -skip
            #entire wipe if wihout args and value is None
            #remove only from current workspace with -rm
            #append to current -workspace with -append
            #add/change value to all-remote list
            mkt = Market(key,val) #create market object!    
            if(val != ''): #only create remote in the list
                if(key in apt.SETTINGS['market'].keys()):
                    mkt.setRemote(val) #market name already exists
                apt.SETTINGS['market'][key] = val
                
                if(options.count("append") and key not in apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market']): # add to active workspaces
                    apt.SETTINGS['workspace'][apt.SETTINGS['active-workspace']]['market'].append(key)
            elif(key in apt.SETTINGS['market'].keys()):
                del apt.SETTINGS['market'][key]
                mkt.delete()
                #remove from all workspace configurations
                for nm,ws in apt.SETTINGS['workspace'].items():
                    if(key in apt.SETTINGS['workspace'][nm]['market']):
                        apt.SETTINGS['workspace'][nm]['market'].remove(key)
                    pass
        elif(not options[0] in apt.SETTINGS.keys()):
            exit(log.error("No setting exists under that flag"))
            return
        # WORKSPACE CONFIGURATION
        elif(options[0] == 'workspace'):
            #create entire new workspace settings
            if(not isinstance(apt.SETTINGS[options[0]],dict)):
                apt.SETTINGS[options[0]] = dict()
            #insertion
            if(val != ''):
                #create new workspace profile
                for item,lp in apt.SETTINGS[options[0]].items():
                    if(lp['local'].lower() == apt.fs(val).lower()):
                        exit(log.error("Workspace already exists with this path."))
                if(key not in apt.SETTINGS[options[0]]):
                    apt.SETTINGS[options[0]][key] = dict()
                    apt.SETTINGS[options[0]][key]['market'] = list()
                    apt.SETTINGS[options[0]][key]['local'] = None
                    apt.initializeWorkspace(key)
                #now insert value
                apt.SETTINGS[options[0]][key]['local'] = apt.fs(val)
                #will make new directories if needed when setting local path
                if(not os.path.isdir(apt.SETTINGS[options[0]][key]['local'])):
                    log.info("Making new directory "+apt.SETTINGS[options[0]][key]['local'])
                    os.makedirs(apt.fs(val), exist_ok=True)
                for rem in options:
                    if rem == options[0]:
                        continue
                    if rem not in apt.SETTINGS[options[0]][key]['market']:
                        apt.SETTINGS[options[0]][key]['market'].append(rem)
            #empty value -> deletion of workspace from list
            else:
                #will not delete old workspace directories but can remove from list
                if(key in apt.SETTINGS[options[0]].keys()):
                    del apt.SETTINGS[options[0]][key]
            pass
        # BUILD SCRIPT CONFIGURATION
        elif(options[0] == 'script'):
            #parse into cmd and filepath
            ext = Block.getExt(val)
            if(ext != ''):
                ext = '.'+ext
                if(ext.count("/") or ext.count("\\")):
                    ext = ''
            cmd = val[:val.find(' ')]
            args = val[val.find(' ')+1:].strip().split()

            path = oldPath = ''
            #find which part of the args is the path to the file being used as the script
            for p in args:
                if(os.path.isfile(p)):
                    path = os.path.realpath(os.path.expanduser(p)).replace("\\", "/")
                    oldPath = p
                    break
            if(path == ''):
                 exit(log.error("Could not an accepted file"))
            #reassemble val with new file properly formatted filepath
            val = cmd
            for i in range(len(args)):
                if(args[i] == oldPath):
                    val = val + " " +path
                else:
                    val = val + " " + args[i]
            
            #skip link option- copy file and rename it same as name 
            if(options.count("lnk") == 0 and val != ''):   
                dst = apt.HIDDEN+"scripts/"+key+ext
                shutil.copyfile(path, dst)
                dst = path.replace(path, dst)
                val = cmd+' '+dst
            #initialization
            if(not isinstance(apt.SETTINGS[options[0]],dict)):
                apt.SETTINGS[options[0]] = dict()
            #insertion
            if(path != ''):
                apt.SETTINGS[options[0]][key] = "\""+val+"\""
            #deletion
            elif(isinstance(apt.SETTINGS[options[0]],dict) and key in apt.SETTINGS[options[0]].keys()):
                val = apt.SETTINGS[options[0]][key]
                ext = Block.getExt(val)
                del apt.SETTINGS[options[0]][key]
                try:
                    os.remove(apt.HIDDEN+"scripts/"+key+ext)
                except:
                    pass
            pass
        elif(options[0] == 'template'):
            if(choice == ''):
                apt.SETTINGS[options[0]] = None
            else:
                apt.SETTINGS[options[0]] = apt.fs(choice)
        # LABEL CONFIGURATION
        elif(options[0] == 'label'):
            depth = "shallow"
            if(options.count("recur")):
                depth = "recursive"
            if(val == ''): #signal for deletion
                if(isinstance(apt.SETTINGS[options[0]],dict)):
                    if(key in apt.SETTINGS[options[0]][depth].keys()):
                        del apt.SETTINGS[options[0]][depth][key]
            if(not isinstance(apt.SETTINGS[options[0]],dict)):
                apt.SETTINGS[options[0]] = dict()
                apt.SETTINGS[options[0]]["shallow"] = dict()
                apt.SETTINGS[options[0]]["recursive"] = dict()
            if(val != ''):
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
    
    #TO-DO: implement
    def convert(self, title):
        #must look through tags of already established repo
        l,n = Block.split(title)
        if(l == '' or n == ''):
            exit(log.error("Must provide a library.block"))
        cwd = apt.fs(os.getcwd())
        #find the src dir and testbench dir through autodetect top-level modules
        #name of package reflects folder, a library name must be specified though
        if(cwd.lower().count(apt.getLocal().lower()) == 0):
            exit(log.error("Cannot initialize outside of workspace"))
        cap = None

        files = os.listdir(cwd)
        if apt.MARKER in files or self.db.capExists(title, "local") or self.db.capExists(title, "cache") or self.db.capExists(title, "market"):
            log.info("Already a packaged module")
            return

        log.info("Transforming project into lego...")
        #add .gitignore file if not present and it is present in template project
        if(os.path.isfile(apt.TEMPLATE+".gitignore")):
            if(not os.path.isfile(cwd+"/.gitignore")):
                shutil.copy(apt.TEMPLATE+".gitignore",cwd+"/.gitignore")
            pass
        #rename current folder to the name of library.project
        last_slash = cwd.rfind('/')
        if(last_slash == len(cwd)-1):
            last_slash = cwd[:cwd.rfind('/')].rfind('/')

        cwdb1 = cwd[:last_slash]+"/"+n+"/"
        os.rename(cwd, cwdb1)
        git_exists = True
        if ".git" not in files:
            #see if there is a .git folder and create if needed
            log.info("Initializing git repository...")
            git_exists = False
            pass
        
        #create marker file
        cap = Block(title=title, path=cwdb1)
        log.info("Creating "+apt.MARKER+" file...")
        cap.create(fresh=False, git_exists=git_exists)
        pass

    def inventory(self, options):
        self.db.listCaps(options)
        print()
        pass

    def cleanup(self, cap, force=False):
        if(not cap.isValid()):
            log.info('Module '+cap.getName()+' does not exist locally.')
            return
        
        if(not cap.isLinked() and force):
            log.warning('No market is configured for this package, if this module is deleted and uninstalled\n\
            it may be unrecoverable. PERMANENTLY REMOVE '+cap.getTitle()+'? [y/n]\
            ')
            response = ''
            while(True):
                response = input()
                if(response.lower() == 'y' or response.lower() == 'n'):
                    break
            if(response.lower() == 'n'):
                log.info("Module "+cap.getTitle()+' not uninstalled.')
                force = False
        #if there is a remote then the project still lives on, can be "redownloaded"
        print(cap.getPath())
        shutil.rmtree(cap.getPath())
    
        #if empty dir then do some cleaning
        slash = cap.getPath()[:len(cap.getPath())-2].rfind('/')
        root = cap.getPath()[:slash+1]
        if(len(os.listdir(root)) == 0):
            os.rmdir(root)
        log.info('Deleted '+cap.getTitle()+' from local workspace.')
        
        if(force):
            self.uninstall(cap.getTitle())
            log.info("Uninstalled "+cap.getTitle()+" from cache.")
        #delete the module remotely?
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
            print('{:<12}'.format("Name"),'{:<14}'.format("Command"),'{:<54}'.format("Path"))
            print("-"*12+" "+"-"*14+" "+"-"*54)
            for key,val in apt.SETTINGS['script'].items():
                spce = val.find(' ')
                cmd = val[1:spce]
                path = val[spce:len(val)-1].strip()
                if(spce == -1): #command not found
                    path = cmd
                    cmd = ''
                print('{:<12}'.format(key),'{:<14}'.format(cmd),'{:<54}'.format(path))
                pass
        else:
            log.info("No scripts added!")
        pass

    def parse(self, cmd, pkg, opt):
        #check if we are in a project directory (necessary to run a majority of commands)
        self.BlockCWD = Block(path=os.getcwd()+"/")
   
        command = cmd
        package = pkg
        options = opt
        
        description = package
        value = package
        package = package.replace("-", "_")
        if(apt.inWorkspace()):
            self.BlockPKG = Block(title=package)

        L,N = Block.split(package)
        
        #branching through possible commands
        if(command == "install"):
            print(self.BlockPKG.getTitle())
            ver = None
            if(len(options)):
                ver = options[0]
            self.install(self.BlockPKG.getTitle(), ver)
            pass
        elif(command == "uninstall"):
            self.uninstall(package, options) #TO-DO
            pass
        elif(command == "build" and self.BlockCWD.isValid()):
            self.build(value)
        elif(command == "new" and len(package) and not self.BlockPKG.isValid()):
            if(options.count("file")):
                options.remove("file")
                if(self.BlockCWD.isValid()):
                    if(len(options) == 0):
                        exit(log.error("Please specify a file from your template to copy from"))
                    self.BlockCWD.fillTemplateFile(package, options[0])
                else:
                    exit(log.error("Cannot create a project file when not inside a project"))
                return
            mkt_sync = None
            git_url = None
            startup = False
            if(options.count("o")):
                startup = True
                options.remove("o")

            mkts = self.db.getGalaxy()
            for mkt in mkts:
                for opt in options:
                    if(mkt.getName() == opt):
                        print("Identified market to synchronize with!")
                        mkt_sync = mkt
                        options.remove(opt)
                        break
                if(mkt_sync != None):
                    break

            for opt in options:
                if(apt.isValidURL(opt)):
                    git_url = opt
            print(git_url,mkt_sync)
            log.debug("package name: "+package)
            self.BlockPKG = Block(title=package, new=True, market=mkt_sync, remote=git_url)

            if(startup):
                self.BlockPKG.load()
            pass
        elif(command == "release" and self.BlockCWD.isValid()):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(self.BlockCWD, options=options)
            if(len(options) == 2 and options.count('d')):
                self.cleanup(self.BlockCWD, False)
            pass
        elif(command == 'graph' and self.BlockCWD.isValid()):
            #generate dependency tree
            self.formGraph(self.BlockCWD)
        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            cap = self.download(package)
            if('o' in options):
                cap.load()
            pass
        elif(command == "summ" and self.BlockCWD.isValid()):
            self.BlockCWD.getMeta()['summary'] = description
            self.BlockCWD.pushYML("Updates project summary")
            pass
        elif(command == 'del' and self.db.capExists(package, "local")):
            force = False
            if(len(options) > 0):
                if(options[0].lower() == 'u'):
                    force = True
            self.cleanup(self.db.getCaps("local")[L][N], force)
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
                self.inventory(options)
            pass
        elif(command == "init"):
            self.convert(package)
        elif(command == "refresh"):
            self.db.sync()
        elif(command == "export" and self.BlockCWD.isValid()): #a visual aide to help a developer see what package's are at the ready to use
            #'' and list() are default to pkg and options
            mod = package
            tb = None
            if(mod == ''):
                mod = None
            if(len(options) > 0):
                tb = options[0]
            self.export(self.BlockCWD, mod, tb)
            pass
        elif(command == "open"):
            if(apt.SETTINGS['editor'] == None):
                exit(log.error("No text-editor configured!"))
            if(options.count("template") or package.lower() == "template"):
                os.system(apt.SETTINGS['editor']+" \""+apt.TEMPLATE+"\"")
            elif(options.count("script") or package.lower() == "script"):
                    os.system(apt.SETTINGS['editor']+" \""+apt.HIDDEN+"/scripts\"")
            elif(options.count("settings") or package.lower() == "settings"):
                os.system(apt.SETTINGS['editor']+" \""+apt.HIDDEN+"/settings.yml\"")
            elif(self.db.capExists(package, "local")):
                self.db.getCaps("local")[L][N].load()
            else:
                exit(log.error("No module "+package+" exists in your workspace."))
        elif(command == "show" and (self.db.capExists(package, "local") or self.db.capExists(package, "cache"))):
            self.db.getCaps("local","cache")[L][N].show()
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
            if(self.BlockCWD.isValid() and self.BlockCWD.getLib() == L):
                inserted_lib = 'work'
            
            if((self.db.capExists(package, "local") or self.db.capExists(package, "cache"))):
                print(self.db.getCaps("local","cache")[L][N].ports(mapp,inserted_lib,pure_ent,ent_name))
            else:
                exit(log.error("No block exists in local path or workspace cache."))
        elif(command == "config"):
            self.setSetting(options, value)
            pass
        elif(command == "help" or command == ''):
            #list all of command details
            self.commandHelp(package)
            #print("VHDL's package manager")
            print('USAGE: \
            \n\tlegohdl <command> [package] [args]\
            \n')
            print("COMMANDS:")
            def formatHelp(cmd, des):
                print('  ','{:<12}'.format(cmd),des)
                pass
            formatHelp("init","initialize the current folder into a valid package format")
            formatHelp("new","create a templated empty package into workspace")
            formatHelp("open","opens the downloaded package with the configured text-editor")
            formatHelp("release","release a new version of the current package")
            formatHelp("list","print list of all packages available")
            formatHelp("install","grab package from its market for dependency use")
            formatHelp("uninstall","remove package from cache")
            formatHelp("download","grab package from its market for development")
            formatHelp("update","update installed package to be to the latest version")
            formatHelp("export","generate a recipe file to build the project")
            formatHelp("build","run a custom configured script")
            formatHelp("del","deletes the package from the local workspace")
            formatHelp("search","search markets or local workspace for specified package")
            formatHelp("refresh","sync local markets with their remotes")
            formatHelp("port","print ports list of specified package")
            formatHelp("show","read further detail about a specified package")
            formatHelp("summ","add description to current package")
            formatHelp("config","set package manager settings")
            print("\nType \'legohdl help <command>\' to read more on entered command.")
            exit()
            print("\nOptions:\
            \n\t-v0.0.0\t\tspecify package version (insert values replacing 0's)\
            \n\t-:\" \"\t\tproject summary (insert between quotes)\
            \n\t-i\t\tset installation flag to install package(s) on project creation\
            \n\t-alpha\t\talphabetical order\
            \n\t-o\t\topen the project\
            \n\t-rm\t\tremoves the released package from your local codebase\
            \n\t-f\t\tforce project uninstallation alongside deletion from local codebase\
            \n\t-map\t\tprint port mapping of specified package\
            \n\t-local\t\tset local path setting\
            \n\t-remote\t\tset remote path setting\
            \n\t-build\t\tenable listing build scripts\
            \n\t-editor\t\tset text-editor setting\
            \n\t-author\t\tset author setting\
            \n\t-gl-token\t\tset gitlab access token\
            \n\t-gh-token\t\tset github access token\
            \n\t-maj\t\trelease as next major update (^.0.0)\
            \n\t-min\t\trelease as next minor update (-.^.0)\
            \n\t-fix\t\trelease as next patch update (-.-.^)\
            \n\t-script\t\tset a script setting\
            \n\t-label\t\tset a export label setting\
            \n\t-template\t\ttrigger the project template to open\
            \n\t-lnk\t\tuse the build script from its specified location- default is to copy\
            ")
        else:
            print("Invalid command; type \"legohdl help\" to see a list of available commands")
        pass

    def commandHelp(self, cmd):
        def printFmt(cmd,val,options=''):
            print("USAGE:")
            print("\tlegohdl "+cmd+" "+val+" "+options)
            pass
        if(cmd == ''):
            return
        elif(cmd == "init"):
            printFmt("init", "<package>")
            pass
        elif(cmd == "new"):
            printFmt("new","<package>","[-o -<remote-url> -<market-name>")
            pass
        elif(cmd == "open"):
            printFmt("open","<package>","[-template -script -settings]")
            pass
        elif(cmd == "release"):
            printFmt("release","\b","[[-v0.0.0 | -maj | -min | -fix] -d -strict -request]")
            print("\n   -strict -> won't add any uncommitted changes along with release")
            print("\n   -request -> will push a side branch to the linked market")
            pass
        elif(cmd == "list"):
            printFmt("list","\b","[-alpha -local -script -label -market -workspace]")
            pass
        elif(cmd == "install"):
            printFmt("install","<package>","[-v0.0.0]")
            pass
        elif(cmd == "uninstall"):
            printFmt("uninstall","<package>")
            pass
        elif(cmd == "download"):
            printFmt("download","<package>","[-v0.0.0 -o]")
            pass
        elif(cmd == "update"):
            printFmt("update","<package>")
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
            printFmt("del","<package>","[-u]")
            pass
        elif(cmd == "search"):
            printFmt("search","<package>")
            pass
        elif(cmd == "port"):
            printFmt("port","<package>","[-map -inst]")
            pass
        elif(cmd == "show"):
            printFmt("show","<package>")
            pass
        elif(cmd == "summ"):
            printFmt("summ","[-:\"summary\"]")
            pass
        elif(cmd == "config"):
            printFmt("config","<value>","""[-market [-rm | -append] | -author | -script [-lnk] | -label [-recur] | -editor |\n\
                    \t\t-workspace [-<market-name> ...] | -active-workspace | -market-append | -market-rm]\
            """)
            print("\n   Setting [-script], [-label], [-workspace], [-market] requires <value> to be <key>=\"<value>\"")
            print("   An empty value will signal to delete the key") 
            print("   legohdl config myWorkspace=\"~/develop/hdl/\" -workspace") 
            pass
        exit()
        pass
    pass

def main():
    legoHDL()


if __name__ == "__main__":
    main()
