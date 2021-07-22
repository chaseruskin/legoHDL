#!/usr/bin/env python3
import os, sys, shutil
import yaml, git, glob
from capsule import Capsule
from registry import Registry
from graph import Graph
from apparatus import Apparatus as apt
from market import Market
import logging as log
from ordered_set import OrderedSet

class legoHDL:

    def __init__(self):
        
        apt.load() #load settings.yml
        self.capsulePKG = None
        self.capsuleCWD = None
        
        #defines path to dir of remote code base
        self.db = Registry(apt.getRemotes())
        Capsule.fetchLibs(self.db.availableLibs())

        #set env variable for VHDL_LS
        os.environ['VHDL_LS_CONFIG'] = apt.WORKSPACE+"map.toml" 

        self.parse()
        pass

    def genPKG(self, title):
        cap = None
        if(self.db.capExists(title, "cache", updt=True)):
            cache = self.db.getCaps("cache")
            l,n = Capsule.split(title)
            cap = cache[l][n]
        else:
            exit(log.error("The module is not located in the cache"))
            return

        lib_path = apt.WORKSPACE+"lib/"+cap.getLib()+"/"
        os.makedirs(lib_path, exist_ok=True)
        tmp_pkg = open(apt.PKGMNG_PATH+"/template_pkg.vhd", 'r')
        vhd_pkg = open(lib_path+cap.getName()+"_pkg.vhd", 'w')

        #need to look at toplevel VHD file to transfer correct library uses
        #search through all library uses and see what are chained dependencies
        src_dir,derivatives = cap.scanDependencies(cap.getMeta("toplevel"), update=False)
        #write in all library and uses
        print(derivatives)
        libs = set()
        for dep in derivatives:
            dot = dep.find('.')
            libline = "library "+dep[:dot]+";\n"
            if(not libline in libs):
                vhd_pkg.write(libline)
                libs.add(libline)
            vhd_pkg.write("use "+dep+"\n")

        # generate a PKG VHD file -> lib
        addedCompDec = False
        for line in tmp_pkg:
            line = line.replace("template", cap.getName())
            if not addedCompDec and line.count("package") > 0:
                addedCompDec = True
                comp = cap.ports(False)
                line = line + "\n" + comp
                pass
            vhd_pkg.write(line)
        vhd_pkg.close()
        tmp_pkg.close()
        pass

    def install(self, title, ver=None, opt=list()):
        l,n = Capsule.split(title)
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
        print("library files path:")

        #generate PKG VHD    
        self.genPKG(cap.getTitle())
        
        #link it all together through writing paths into "map.toml"
        filename = apt.WORKSPACE+"map.toml"
        mapfile = open(filename, 'r')
        cur_lines = mapfile.readlines()
        mapfile.close()

        mapfile = open(filename, 'w')
        inc_paths = list()
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
        pass

    def uninstall(self, pkg, opt=None):
        #remove from cache
        l,n = Capsule.split(pkg)
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
        pass

    def recurseScan(self, dep_list, label_list):
        if(len(dep_list) == 0):
            return label_list
        #go to YML of dependencies and add edges to build dependency tree
        for d in dep_list:
            l,n = Capsule.split(d)
            n = n.replace("_pkg", "")
            if(os.path.isfile(apt.WORKSPACE+"cache/"+l+"/"+n+"/.lego.lock")):
                #here is where we check for matching files with custom recursive labels
                for key,val in apt.SETTINGS['label'].items():
                    ext,recur = val
                    if(recur == True): #recursive
                        results = glob.glob(apt.WORKSPACE+"cache/"+l+"/"+n+"/**/*"+ext, recursive=True)
                        for find in results:
                            label_list.append("@"+key+" "+find)
                        pass
                #open the metadata to retrieve data to be used to build dependency chain
                with open(apt.WORKSPACE+"cache/"+l+"/"+n+"/.lego.lock", "r") as file:
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
        print("Exporting...",end=' ')
        print(cap.getPath())
        build_dir = cap.getPath()+"build/"
        #create a clean build folder
        log.info("Cleaning build folder...")
        if(os.path.isdir(build_dir)):
            shutil.rmtree(build_dir)
        os.mkdir(build_dir)

        log.info("Finding toplevel design...")
        #add export option to override auto detection
        if(top == None):
            cap.identifyTop()
            top = cap.getMeta("toplevel")
            tb = cap.getMeta("bench")
        elif(top != None and tb == None):
            cap.identifyBench(top)
            tb = cap.getMeta("bench")
        

        # g = Graph()
        # top_mp = dict()
        # top_mp[cap.getTitle()] = top
        #TO-DO fix recursive label scanning
        output = open(build_dir+"recipe", 'w')
        label_list = list()
        #mission: recursively search through every src VHD file for what else needs to be included
        #log.info("Grabbing dependencies...")
        _,derivatives = cap.scanDependencies(top.replace(".vhd",""))
        for d in derivatives:
            print('DERIV:',derivatives)
        #     g.addEdge(top, d)
        label_list = self.recurseScan(derivatives, label_list)
     
        # g.output()
        # #before writing recipe, the nodes must be topologically sorted as dependency tree
        # hierarchy = g.topologicalSort() #flatten dependency tree into a list
        # print(hierarchy)

        # library = dict() #stores lists at dictionary keys
        # for h in hierarchy:
        #     l,n = Capsule.split(h)
        #     n = n.replace("_pkg", "")
        #     #library must exist in lib to be included in recipe.txt (avoids writing external libs like IEEE)
        #     if(os.path.isdir(apt.WORKSPACE+"lib/"+l)): #check lib exists
        #         if not l in library.keys():
        #             library[l] = list() 
        #         library[l].append(n)

        #any user-defined labels to add? adds project-level labels (both recursive and non-recursive)
        for label,val in apt.SETTINGS['label'].items():
            ext,recur = val
            results = glob.glob(apt.fs(os.getcwd())+"/**/*"+ext, recursive=True)
            for r in results:
                label_list.append("@"+label+" "+r)
        log.info("Writing recipe...")
        #write all custom labels
        for finding in label_list:
            output.write(finding+"\n")

        hierarchy = self.formGraph(cap)
        order = self.compileList(hierarchy)  

        for f in order:
            output.write(f+"\n")
        # #write these libraries and their required file paths to a file for exporting
        # for lib in library.keys():
        #     for pkg in library[lib]:
        #         key = lib+'.'+pkg
        #         root_dir = apt.WORKSPACE+"cache/"+lib+"/"+pkg+"/"
        #         log.debug(top_mp[key])
        #         tmp = Capsule(path=root_dir)
        #         #TO-DO: find better way to fix glob search to include root prj directory in search
        #         src_dir = glob.glob(root_dir+"/**/"+top_mp[key], recursive=True) 
        #         for f in tmp.gatherSources(excludeTB=True):
        #             output.write("@LIB "+f+"\n")
        #         output.write("@LIB "+lib+" "+apt.WORKSPACE+"lib/"+lib+"/"+pkg+"_pkg.vhd\n")

        # #write current src dir where all src files are as "work" lib
        # for f in cap.gatherSources(excludeTB=True): #remove all testbench files
        #     output.write("@SRC "+f+"\n")
        
        #write current test dir where all testbench files are
        if(tb != None):
            #output.write("@TB "+cap.grabEntities()[cap.getMeta("bench")].getFile()+"\n")
            output.write("@TB-UNIT "+tb+"\n")

        if(top != None):
            output.write("@TOP-UNIT "+top+"\n")

        output.close()
        print("success")
        pass

    def recursiveGraph(self, cap, grph):
        #grab only source-design entities (its an external referenced project)
        ents = cap.grabEntities(excludeTB=True)
        for k,e in ents.items():
            grph.addLeaf(e)
            #make the connections between an entity and its dependency entity
            for dep in e.getDerivs():
                grph.addEdge(k, dep)
            #see what external packages are referenced
            for extern_lib in e.getExternal():
                L,N = self.grabExternalProject(extern_lib[1])
                #create project object based on this external package
                ext_cap = self.db.getCaps("cache")[L][N]
                #recursively feed into dependency tree
                grph = self.recursiveGraph(ext_cap, grph)
        return grph

    #search for the projects attached to the external package
    def grabExternalProject(self, path):
        #use its file to find out what project uses it
        path_parse = apt.fs(path).split('/')
        # if in lib {library}/{project}_pkg.vhd
        if("lib" in path_parse):
            i = path_parse.index("lib")
            pass
        #if in cache {library}/{project}/../.vhd
        elif("cache" in path_parse):
            i = path_parse.index("cache")
            pass
        else:
            return '',''
        L = path_parse[i+1]
        N = path_parse[i+2].replace("_pkg.vhd", "")
        return L,N

    def formGraph(self, cap):
        log.info("Generating dependency tree...")
        hierarchy = Graph()
        #grab current project's entity list
        ents = cap.grabEntities()
        for k,e in ents.items():
            hierarchy.addLeaf(e)
            #make the connections between an entity and its dependency entity
            for dep in e.getDerivs():
                hierarchy.addEdge(k, dep)
            #see what external packages are referenced
            for extern_lib in e.getExternal():
                L,N = self.grabExternalProject(extern_lib[1])
                #create project object based on this external package
                ext_cap = self.db.getCaps("cache")[L][N]
                #recursively feed into dependency tree
                hierarchy = self.recursiveGraph(ext_cap, hierarchy)

        hierarchy.output()
        es = hierarchy.topologicalSort()
        print('---BUILD ORDER---')
        for e in es:
            print(e.getFull(),end=' -> ')
        return hierarchy

    #given a dependency graph, write out the actual list of files needed
    def compileList(self, hierarchy):
        c_set = OrderedSet()
        c_list = []
        print("Topological:",hierarchy.topologicalSort())
        order = hierarchy.topologicalSort()
        for ent in order:
            for f in ent.getAllFiles():
                c_set.add(f)

        for f in c_set:
            lib,_ = self.grabExternalProject(f)
            if(len(lib)):
                lib = "@LIB "+lib+" "
            else:
                if(f in self.capsuleCWD.gatherSources(excludeTB=True)):
                    lib = "@SRC "
                else:
                    lib = "@TB "
            c_list.append(lib+f)
            #print(lib+f)
    
        return c_list

    #will also install project into cache and have respective pkg in lib
    def download(self, title):
        l,n = Capsule.split(title)

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
        if(options[0] == 'active-workspace' and choice not in apt.SETTINGS['workspace'].keys()):
            exit(log.error("Workspace not found!"))

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
                    os.makedirs(apt.SETTINGS[options[0]][key]['local'], exist_ok=True)
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
            ext = Capsule.getExt(val)
            if(ext != ''):
                ext = '.'+ext
            cmd = val[:val.find(' ')]
            path = val[val.find(' ')+1:].strip()
            #skip link option- copy file and rename it same as name 
            if(options.count("lnk") == 0 and val != ''):   
                dst = apt.HIDDEN+"scripts/"+key+ext
                oldPath = path[path.rfind(' ')+1:]
                shutil.copyfile(oldPath, dst)
                dst = path.replace(oldPath, dst)
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
                ext = Capsule.getExt(val)
                del apt.SETTINGS[options[0]][key]
                try:
                    os.remove(apt.HIDDEN+"scripts/"+key+ext)
                except:
                    pass
            pass
        # LABEL CONFIGURATION
        elif(options[0] == 'label'):
            recur = False
            if(options.count("recur")):
                recur = True
            if(val == ''): #signal for deletion
                if(isinstance(apt.SETTINGS[options[0]],dict)):
                    if(key in apt.SETTINGS[options[0]].keys()):
                        del apt.SETTINGS[options[0]][key]
            if(not isinstance(apt.SETTINGS[options[0]],dict)):
                apt.SETTINGS[options[0]] = dict()
            if(val != ''):
                apt.SETTINGS[options[0]][key] = [val, recur]
            pass
        # ALL OTHER CONFIGURATION
        else:
            apt.SETTINGS[options[0]] = choice
        
        apt.save()
        log.info("Setting saved successfully.")
        pass
    
    #TO-DO: implement
    def convert(self, title):
        #add .GITIGNORE file if not present?
        #must look through tags of already established repo
        l,n = Capsule.split(title)
        cwd = apt.fs(os.getcwd()).lower()
        #find the src dir and testbench dir through autodetect top-level modules
        #name of package reflects folder, a library name must be specified though
        if(cwd.count(apt.getLocal().lower()) == 0):
            exit(log.error("Cannot initialize outside of workspace"))
        cap = None
        files = os.listdir(cwd)
        #rename current folder to 
        cwdb1 = cwd[:cwd.rfind('/')]+"/"+n+"/"
        os.rename(cwd, cwdb1)
        git_exists = True
        if ".git" not in files:
            #see if there is a .git folder and create if needed
            print("Initializing git repository...")
            git_exists = False
            pass
        if ".lego.lock" in files:
            log.info("Already a packaged module")
            return
        else:
            #create .lego.lock file
            cap = Capsule(title=title, path=cwdb1)
            log.info("Creating .lego.lock file...")
            cap.create(fresh=False, git_exists=git_exists)
            pass
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
            for key,val in apt.SETTINGS['label'].items():
                rec = 'no'
                if(val[1]):
                    rec = 'yes'
                print('{:<20}'.format(key),'{:<24}'.format(val[0]),'{:<14}'.format(rec))
                pass
        else:
            log.info("No Labels added!")
        pass

    def listRemotes(self):
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

    def parse(self):
        #check if we are in a project directory (necessary to run a majority of commands)
        pkgPath = os.getcwd()
        lastSlash = pkgPath.rfind('/') #determine project's name to know the YAML to open
        pkgCWD = pkgPath[lastSlash+1:]

        self.capsuleCWD = Capsule(path=pkgPath+"/")
        #if(self.capsuleCWD.isValid()):
            #self.capsuleCWD.identifyTop()

        #exit()
        command = package = description = ""
        options = []
        #store args accordingly from command-line
        for i, arg in enumerate(sys.argv):
            if(i == 0):
                continue
            elif(i == 1):
                command = arg
            elif(arg[0] == '-'):
                options.append(arg[1:])
            elif(package == ''):
                package = arg

        
        description = package
        
        value = package
        package = package.replace("-", "_")
        
        self.capsulePKG = Capsule(title=package)

        L,N = Capsule.split(package)
        
        #branching through possible commands
        if(command == "install"):
            print(self.capsulePKG.getTitle())
            ver = None
            if(len(options)):
                ver = options[0]
            self.install(self.capsulePKG.getTitle(), ver)
            pass
        elif(command == "uninstall"):
            self.uninstall(package, options) #TO-DO
            pass
        elif(command == "build" and self.capsuleCWD.isValid()):
            self.build(value)
        elif(command == "new" and len(package) and not self.capsulePKG.isValid()):
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
            self.capsulePKG = Capsule(title=package, new=True, market=mkt_sync, remote=git_url)

            if(startup):
                self.capsulePKG.load()
            pass
        elif(command == "release" and self.capsuleCWD.isValid()):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(self.capsuleCWD, options=options)
            if(len(options) == 2 and options.count('d')):
                self.cleanup(self.capsuleCWD, False)
            pass
        elif(command == 'graph' and self.capsuleCWD.isValid()):
            #generate dependency tree
            self.formGraph(self.capsuleCWD)
        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            cap = self.download(package)
            if('o' in options):
                cap.load()
            pass
        elif(command == "summ" and self.capsuleCWD.isValid()):
            self.capsuleCWD.getMeta()['summary'] = description
            self.capsuleCWD.pushYML("Updates project summary")
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
                self.listRemotes()
            elif(options.count("workspace")):
                self.listWorkspace()
            else:
                self.inventory(options)
            pass
        elif(command == "init"):
            self.convert(package)
        elif(command == "refresh"):
            self.db.sync()
        elif(command == "export" and self.capsuleCWD.isValid()): #a visual aide to help a developer see what package's are at the ready to use
            #'' and list() are default to pkg and options
            mod = package
            tb = None
            if(mod == ''):
                mod = None
            if(len(options) > 0):
                tb = options[0]
            self.export(self.capsuleCWD, mod, tb)
            pass
        elif(command == "open"):
            if(options.count("template") or package.lower() == "template"):
                if(apt.SETTINGS['editor'] != None):
                    os.system(apt.SETTINGS['editor']+" "+apt.PKGMNG_PATH+"/template")
                else:
                    log.info("No text-editor configured!")
            elif(options.count("script") or package.lower() == "script"):
                if(apt.SETTINGS['editor'] != None):
                    os.system(apt.SETTINGS['editor']+" "+apt.HIDDEN+"/scripts")
                else:
                    log.info("No text-editor configured!")
            elif(self.db.capExists(package, "local")):
                self.db.getCaps("local")[L][N].load()
            else:
                exit(log.error("No module "+package+" exists in your workspace."))
        elif(command == "show" and (self.db.capExists(package, "local") or self.db.capExists(package, "cache"))):
            self.db.getCaps("local","cache")[L][N].show()
            pass
        elif(command == "port"):
            mapp = False
            if(len(options) and 'map' in options):
                mapp = True
            if((self.db.capExists(package, "local") or self.db.capExists(package, "cache"))):
                print(self.db.getCaps("local","cache")[L][N].ports(mapp))
        elif(command == "template" and apt.SETTINGS['editor'] != None):
            os.system(apt.SETTINGS['editor']+" "+apt.PKGMNG_PATH+"/template")
            pass
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
            formatHelp("export","generate a file of necessary paths to build the project")
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
            print("Invalid command; type \"help\" to see a list of available commands")
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
            printFmt("open","<package>","[-template -build]")
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
            printFmt("port","<package>","[-map]")
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
