#!/usr/bin/env python3
import os, sys, shutil
import yaml, git, glob
from capsule import Capsule
from registry import Registry
from graph import Graph
from apparatus import Apparatus as apt

class legoHDL:
    def __init__(self):
        apt.load() #load settings.yml
        self.capsulePKG = None
        self.capsuleCWD = None

        if(apt.SETTINGS['local'] == None):
            exit("ERROR- Please specify a local path! See \'legohdl help config\' for more details")
        
        #defines path to dir of remote code base
        self.db = Registry(apt.SETTINGS['remote'])

        #set env variable for VHDL_LS
        os.environ['VHDL_LS_CONFIG'] = apt.HIDDEN+"map.toml" 

        self.parse()
        pass

    def genPKG(self, title):
        cap = None
        if(self.db.capExists(title, "cache", updt=True)):
            cache = self.db.getCaps("cache")
            l,n = Capsule.split(title)
            cap = cache[l][n]
        else:
            print("Error- the project is not located in the cache")
            return

        lib_path = apt.HIDDEN+"lib/"+cap.getLib()+"/"
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
        cache_path = apt.HIDDEN+"cache/"
        lib_path = apt.HIDDEN+"lib/"+l+"/"
        #does the package already exist in the cache directory?
        if(self.db.capExists(title, "cache")):
            print("Package is already installed.")
            return
        elif(not self.db.capExists(title, "remote") and False):
            pass
        elif(self.db.capExists(title, "local")):
            cap = self.db.getCaps("local")[l][n]
        else:
            print("Not found anywhere!")
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
        filename = apt.HIDDEN+"map.toml"
        mapfile = open(filename, 'r')
        cur_lines = mapfile.readlines()
        mapfile.close()

        mapfile = open(filename, 'w')
        inc_paths = list()
        inc_paths.append("\'"+lib_path+cap.getName()+"_pkg.vhd"+"\',\n")
        inc_paths.append("\'"+cap.fileSearch(cap.getMeta("toplevel"))[0].replace(cap.getMeta("toplevel"),"*.vhd")+"\',\n")
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
            if(len(os.listdir(apt.HIDDEN+"cache/"+l)) == 0):
                os.rmdir(apt.HIDDEN+"cache/"+l)
                pass
            #remove from lib
            lib_path = cache_path.replace("cache","lib")
            lib_path = lib_path[:len(lib_path)-1]+"_pkg.vhd"
            os.remove(lib_path)
            #if empty dir then do some cleaning
            if(len(os.listdir(apt.HIDDEN+"lib/"+l)) == 0):
                os.rmdir(apt.HIDDEN+"lib/"+l)
                pass

        #remove from 'map.toml'
        lines = list()
        filename = apt.HIDDEN+"map.toml"
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

    def recurseScan(self, grp, dep_list, top_mp, label_list):
        if(len(dep_list) == 0):
            return grp,top_mp,label_list
        #go to YML of dependencies and add edges to build dependency tree
        for d in dep_list:
            l,n = Capsule.split(d)
            n = n.replace("_pkg", "")
            if(os.path.isfile(apt.HIDDEN+"cache/"+l+"/"+n+"/.lego.lock")):
                #here is where we check for matching files with custom recursive labels
                for key,val in apt.SETTINGS['label'].items():
                    ext,recur = val
                    if(recur == True): #recursive
                        results = glob.glob(apt.HIDDEN+"cache/"+l+"/"+n+"/**/*"+ext, recursive=True)
                        for find in results:
                            label_list.append("@"+key+" "+find)
                        pass
                #open the metadata to retrieve data to be used to build dependency chain
                with open(apt.HIDDEN+"cache/"+l+"/"+n+"/.lego.lock", "r") as file:
                    tmp = yaml.load(file, Loader=yaml.FullLoader)
            else:
                continue
            top_mp[l+'.'+n] = tmp['toplevel']
            grp,top_mp,label_list = self.recurseScan(grp, tmp['derives'], top_mp, label_list)
            for z in tmp['derives']:
                grp.addEdge(d, z)
        return grp,top_mp,label_list

    #TO-DO: make std version option checker
    def validVersion(self, ver):
        pass

    def build(self, script):
        arg_start = 3
        if(not isinstance(apt.SETTINGS['build'],dict)): #no scripts exist
            exit("No scripts are configured!")
        elif(len(script) and script[0] == "@"):
            if(script[1:] in apt.SETTINGS['build'].keys()): #is it a name?
                cmd = apt.SETTINGS['build'][script[1:]]
            else:
                exit("Build script name not found!")
        elif("master" in apt.SETTINGS['build'].keys()): #try to resort to default
            cmd = apt.SETTINGS['build']['master']
            arg_start = 2
        elif(len(apt.SETTINGS['build'].keys()) == 1): #if only 1 then try to run the one
            cmd = apt.SETTINGS['build'][list(apt.SETTINGS['build'].keys())[0]]
            arg_start = 2
        else:
            exit("No scripts are configured!")

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
        if(os.path.isdir(build_dir)):
            shutil.rmtree(build_dir)
        os.mkdir(build_dir)

        #add export option to override auto detection
        if(top == None):
            cap.autoDetectTop()
            cap.autoDetectBench()
            top = cap.getMeta("toplevel")
            tb = cap.getMeta("bench")
        elif(top != None and tb == None):
            cap.autoDetectBench(top)
            tb = cap.getMeta("bench")
        
        if(top.count(".vhd") == 0):
            top = top+".vhd"
        if(tb.count(".vhd")== 0):
            tb = tb+".vhd"

        g= Graph()
        top_mp = dict()
        top_mp[cap.getTitle()] = top
        output = open(build_dir+"recipe", 'w')
        label_list = list()
        #mission: recursively search through every src VHD file for what else needs to be included
        src_dir,derivatives = cap.scanDependencies(file_target=top)
        for d in derivatives:
            g.addEdge(top, d)
        g,top_mp,label_list = self.recurseScan(g, derivatives, top_mp, label_list)
     
        g.output()
        #before writing recipe, the nodes must be topologically sorted as dependency tree
        hierarchy = g.topologicalSort() #flatten dependency tree into a list
        print(hierarchy)

        library = dict() #stores lists at dictionary keys
        for h in hierarchy:
            l,n = Capsule.split(h)
            n = n.replace("_pkg", "")
            #library must exist in lib to be included in recipe.txt (avoids writing external libs like IEEE)
            if(os.path.isdir(apt.HIDDEN+"lib/"+l)): #check lib exists
                if not l in library.keys():
                    library[l] = list() 
                library[l].append(n)

        #any user-defined labels to add? adds project-level labels (both recursive and non-recursive)
        for label,val in apt.SETTINGS['label'].items():
            ext,recur = val
            results = glob.glob(apt.fs(os.getcwd())+"/**/*"+ext, recursive=True)
            for r in results:
                label_list.append("@"+label+" "+r)

        #write all custom labels
        for finding in label_list:
            output.write(finding+"\n")
                
        #write these libraries and their required file paths to a file for exporting
        for lib in library.keys():
            for pkg in library[lib]:
                key = lib+'.'+pkg
                root_dir = apt.HIDDEN+"cache/"+lib+"/"+pkg+"/"
                #TO-DO: find better way to fix glob search to include root prj directory in search
                src_dir = glob.glob(root_dir+"/**/"+top_mp[key], recursive=True) 
                output.write("@LIB "+lib+" "+src_dir[0].replace(top_mp[key], "*.vhd")+"\n")
                output.write("@LIB "+lib+" "+apt.HIDDEN+"lib/"+lib+"/"+pkg+"_pkg.vhd\n")

        #write current src dir where all src files are as "work" lib
        output.write("@SRC "+cap.fileSearch(top)[0].replace(top, "*.vhd")+"\n")
        #write current test dir where all testbench files are
        output.write("@TB "+cap.fileSearch(tb)[0]+"\n")
        output.close()
        print("success")
        pass

    #will also install project into cache and have respective pkg in lib
    def download(self, title):
        l,n = Capsule.split(title)

        if(not apt.linkedRemote()):
            if(self.db.capExists(title, "cache") and not self.db.capExists(title, "local")):
                instl = self.db.getCaps("cache")[l][n]
                instl.clone(src=instl.getPath(), dst=apt.SETTINGS['local']+"/"+l)
                return self.db.getCaps("local",updt=True)[l][n]
            print('No remote code base configured to download modules')
            exit()

        if(not self.db.capExists(title, "remote")):
            print('ERROR- Package \''+title+'\' does not exist in remote')
            exit()

        #TO-DO: retesting
        if(self.db.capExists(title, "local")):
            print("Project already exists in local workspace- pulling from remote...",end=' ')
            self.db.getPrjs("local")[l][n].pull()
        else:
            print("Cloning from remote...",end=' ')
            self.db.getPrjs("remote")[l][n].clone()
    
        try: #remove cached project already there
            shutil.rmtree(apt.HIDDEN+"cache/"+l+"/"+n+"/")
        except:
            pass
        #install to cache and generate PKG VHD 
        cap = self.db.getPrjs("local")[l][n]  
        self.install(cap.getTitle(), cap.getVersion())

        print("success")
        pass

    def upload(self, cap, options=None):
        err_msg = "ERROR- please flag the next version for release with one of the following args:\n"\
                    "\t(-v0.0.0 | -maj | -min | -fix)"
        if(len(options) == 0):
                exit(err_msg)
            
        ver = ''
        if(options[0][0] == 'v'):
            ver = options[0]
        
        if(options[0] != 'maj' and options[0] != 'min' and options[0] != 'fix' and ver == ''):
            exit(err_msg)

        cap.autoDetectTop()
        cap.release(ver, options)

        if(os.path.isdir(apt.HIDDEN+"cache/"+cap.getLib()+"/"+cap.getName())):
            shutil.rmtree(apt.HIDDEN+"cache/"+cap.getLib()+"/"+cap.getName())
        #clone new project's progress into cache
        self.install(cap.getTitle(), cap.getVersion())

        if apt.linkedRemote():
            print("Updating remote package contents...",end=' ')
            cap.pushRemote()
            print("success")
            print(cap.getLib()+"."+cap.getName()+" is now available as version "+cap.getVersion())
        pass

    def setSetting(self, options, choice):
        if(len(options) == 0):
            print("ERROR- Invalid syntax; could not adjust setting")
            return

        if(options[0] == 'gl-token' or options[0] == 'gh-token'):
            self.db.encrypt(choice, options[0])
            return
        
        if(choice == 'null'):
            choice = ''

        if(not options[0] in apt.SETTINGS.keys()):
            print("ERROR- Invalid setting")
            return

        if(choice == ''):
            if(options[0] == 'remote'):
                print('WARNING- No remote code base is configured')
                choice = None
            elif(options[0] == 'local'):
                print('ERROR- Must include a local code base path')
                return

        
        if(options[0] == 'local'):
            os.makedirs(choice, exist_ok=True)

        if(options[0] == 'build'):
            #parse into key/value around '='
            eq = choice.find("=")
            key = choice[:eq]
            val = choice[eq+1:] #write whole value
            ext = val[val.rfind('.'):]
            cmd = val[:val.find(' ')]
            path = val[val.find(' '):].strip()
            if(path == ''): #signal for deletion
                    if(isinstance(apt.SETTINGS[options[0]],dict)):
                        if(key in apt.SETTINGS[options[0]].keys()):
                            val = apt.SETTINGS[options[0]][key]
                            ext = val[val.rfind('.'):len(val)-1]
                            del apt.SETTINGS[options[0]][key]
                            try:
                                os.remove(apt.HIDDEN+"scripts/"+key+ext)
                            except:
                                pass

            elif(options.count("lnk") == 0):  #copy file and rename it same as name  
                dst = apt.HIDDEN+"scripts/"+key+ext
                shutil.copyfile(path, dst)
                val = cmd+' '+dst
            
            if(not isinstance(apt.SETTINGS[options[0]],dict)):
                apt.SETTINGS[options[0]] = dict()
            if(path != ''):
                apt.SETTINGS[options[0]][key] = "\""+val+"\""
            pass
        elif(options[0] == 'label'):
            recur = False
            if(options.count("recur")):
                recur = True
            eq = choice.find("=")
            key = choice[:eq]
            val = choice[eq+1:] #write whole value
            if(val == ''): #signal for deletion
                if(isinstance(apt.SETTINGS[options[0]],dict)):
                    if(key in apt.SETTINGS[options[0]].keys()):
                        del apt.SETTINGS[options[0]][key]
            if(not isinstance(apt.SETTINGS[options[0]],dict)):
                apt.SETTINGS[options[0]] = dict()
            if(val != ''):
                apt.SETTINGS[options[0]][key] = [val, recur]
            pass
        else:
            apt.SETTINGS[options[0]] = choice
        
        apt.save()
        print("Saved setting successfully")
        pass
    
    #TO-DO: implement
    def convert(self, title):
        #add .GITIGNORE file if not present?
        #must look through tags of already established repo
        l,n = Capsule.split(title)
        cwd = apt.fs(os.getcwd()).lower()
        #find the src dir and testbench dir through autodetect top-level modules
        #name of package reflects folder, a library name must be specified though
        if(cwd.count(apt.SETTINGS['local'].lower()) == 0 or (cwd+"/" == apt.SETTINGS['local'].lower())):
            exit("Cannot initialize outside of local workspace")
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
            print("Already a packaged project")
            return
        else:
            #create .lego.lock file
            cap = Capsule(title=title, path=cwdb1)
            print("Creating .lego.lock file...")
            cap.create(fresh=False, git_exists=git_exists)
            pass
        
        
        pass

    def inventory(self, options):
        self.db.listCaps(options)
        print()
        pass

    def cleanup(self, cap, force=False):
        if(not cap.isValid()):
            print('Module '+cap.getName()+' does not exist locally')
            return
        
        if(apt.SETTINGS['remote'] == None and force):
            print('\
            WARNING- No remote code base is configured, if this module is deleted and uninstalled\n\
            it may be unrecoverable. PERMANENTLY REMOVE '+cap.getTitle()+'? [y/n]\
                ')
            response = ''
            while(True):
                response = input()
                if(response.lower() == 'y' or response.lower() == 'n'):
                    break
            if(response.lower() == 'n'):
                print("Module "+cap.getTitle()+' not uninstalled')
                force = False
        #if there is a remote then the project still lives on, can be "redownloaded"
        print(cap.getPath())
        shutil.rmtree(cap.getPath())
    
        #if empty dir then do some cleaning
        slash = cap.getPath()[:len(cap.getPath())-2].rfind('/')
        root = cap.getPath()[:slash+1]
        if(len(os.listdir(root)) == 0):
            os.rmdir(root)
        print('Deleted '+cap.getTitle()+' from local workspace')
        
        if(force):
            self.uninstall(cap.getTitle())
            print("Uninstalled "+cap.getTitle()+" from cache")
        #delete the module remotely?
        pass

    def listLabels(self):
        if(isinstance(apt.SETTINGS['label'],dict)):
            print("\nList of custom labels:")
            print("  ",'{:<14}'.format("Label"),'{:<20}'.format("ext"),'{:<10}'.format("recursive"))
            print("-"*80)
            for key,val in apt.SETTINGS['label'].items():
                rec = 'no'
                if(val[1]):
                    rec = 'yes'
                print("  ",'{:<14}'.format(key),'{:<22}'.format(val[0]),'{:<10}'.format(rec))
                pass
        else:
            print("No Labels added!")
        pass


    def listScripts(self):
        if(isinstance(apt.SETTINGS['build'],dict)):
            print("\nList of scripts:")
            print("  ",'{:<12}'.format("Name"),'{:<14}'.format("CMD"),'{:<10}'.format("Path"))
            print("-"*80)
            for key,val in apt.SETTINGS['build'].items():
                spce = val.find(' ')
                cmd = val[1:spce]
                path = val[spce:len(val)-1].strip()
                if(spce == -1): #command not found
                    path = cmd
                    cmd = ''
                print("  ",'{:<12}'.format(key),'{:<14}'.format(cmd),'{:<10}'.format(path))
                pass
        else:
            print("No scripts added!")
        pass

    def parse(self):
        #check if we are in a project directory (necessary to run a majority of commands)
        pkgPath = os.getcwd()
        lastSlash = pkgPath.rfind('/') #determine project's name to know the YAML to open
        pkgCWD = pkgPath[lastSlash+1:]

        self.capsuleCWD = Capsule(path=pkgPath+"/")

        
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

        for x in options:
            if(x[0] == ':'):
                description = x[1:]
                break
        
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
            self.install(self.capsulePKG, ver) #TO-DO
            pass
        elif(command == "uninstall"):
            self.uninstall(package, options) #TO-DO
            pass
        elif(command == "build" and self.capsuleCWD.isValid()):
            self.build(value)
        elif(command == "new" and len(package) and not self.capsulePKG.isValid()):
            if apt.linkedRemote():
                if(len(L) > 0 and apt.linkedRemote()): #try to make new subgroup if DNE
                    self.db.createSubgroup(L, self.db.accessGitlabAPI())

            self.capsulePKG = Capsule(package, new=True)
            
            if apt.linkedRemote(): #now fetch from db to grab ID
                self.capsulePKG.saveID(self.db.fetchProjectShallow(L,N)['id'])
            else: #assign tmp local id if no remote
                self.capsulePKG.saveID(self.db.assignRandomID())
            
            if(options.count("o") > 0):
                self.capsulePKG.load()
            pass
        elif(command == "release" and self.capsuleCWD.isValid()):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(self.capsuleCWD, options=options)
            if(len(options) == 2 and options[1] == 'd'):
                self.cleanup(self.capsuleCWD, False)
            pass
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
                if(options[0].lower() == 'f'):
                    force = True
            self.cleanup(self.db.getCaps("local")[L][N], force)
        elif(command == "list"): #a visual aide to help a developer see what package's are at the ready to use
            if(options.count("build")):
                self.listScripts()
            elif(options.count("label")):
                self.listLabels()
            else:
                self.inventory(options)
            pass
        elif(command == "init"):
            self.convert(package)
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
                    print("No text-editor configured!")
            elif(options.count("build") or package.lower() == "build"):
                if(apt.SETTINGS['editor'] != None):
                    os.system(apt.SETTINGS['editor']+" "+apt.HIDDEN+"/scripts")
                else:
                    print("No text-editor configured!")
            elif(self.db.capExists(package, "local")):
                self.db.getCaps("local")[L][N].load()
            else:
                exit("ERROR- No package exists in your local workspace")
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
            formatHelp("new","create a templated empty package")
            formatHelp("open","opens the package with the configured text-editor")
            formatHelp("release","release the next new version of the current package")
            formatHelp("list","print list of all packages available")
            formatHelp("install","grab package from remote for dependency use")
            formatHelp("uninstall","remove package from cache")
            formatHelp("download","grab package from remote for further development")
            formatHelp("update","update installed package to be to the latest version")
            formatHelp("export","generate a file of necessary paths to build the project")
            formatHelp("build","run a custom configured script")
            formatHelp("del","deletes the package from the local workspace")
            formatHelp("search","search remote or local workspace for specified package")
            formatHelp("port","print ports list of specified package")
            formatHelp("show","read further detail about a specified package")
            formatHelp("summ","add description to current project")
            formatHelp("config","set package manager settings")
            print("\nType \'legohdl help <command>\' to read more on entered command.")
            exit()
            print("\nOptions:\
            \n\t-v0.0.0\t\tspecify package version (insert values replacing 0's)\
            \n\t-:\" \"\t\tproject summary (insert between quotes)\
            \n\t-i\t\tset installation flag to install package(s) on project creation\
            \n\t-alpha\t\talphabetical order\
            \n\t-o\t\topen the project\
            \n\t-d\t\tremoves the released package from your local codebase\
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
            \n\t-build\t\tset a build script setting\
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
            printFmt("new","<package>","[-o]")
            pass
        elif(cmd == "open"):
            printFmt("open","<package>","[-template -build]")
            pass
        elif(cmd == "release"):
            printFmt("release","\b","[[-v0.0.0 | -maj | -min | -fix] -d -ac]")
            print("\n   -ac -> add and commit all changes with release")
            pass
        elif(cmd == "list"):
            printFmt("list","\b","[-alpha -local -build -label]")
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
            printFmt("del","<package>","[-f]")
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
            printFmt("config","<value>","[-local | -remote | -author | -build [-lnk] | -label [-recur] | -editor]")
            print("\n   Setting [-build] or [-label] requires <value> to be key=\"value\"")
            pass
        exit()
        pass
    pass

def main():
    #print('\n---legoHDL package manager---\n')
    legoHDL()



if __name__ == "__main__":
    main()
