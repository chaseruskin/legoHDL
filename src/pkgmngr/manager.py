#!/usr/bin/env python3
import os, sys, shutil
import yaml, git, glob
try:
    from pkgmngr import capsule as caps
    from pkgmnger import registry as reg
    from pkgmnger import graph
except:
    import capsule as caps
    import registry as reg
    import graph

class legoHDL:
    def __init__(self):

        self.capsulePKG = None
        self.capsuleCWD = None
        #defines path to working dir of 'legoHDL' tool
        self.pkgmngPath = os.path.realpath(__file__)
        self.pkgmngPath = self.pkgmngPath[:self.pkgmngPath.rfind('/')+1]

        self.settings = dict()
        with open(self.pkgmngPath+"settings.yml", "r") as file:
            self.settings = yaml.load(file, Loader=yaml.FullLoader)
        
        # !!! UNCOMMENT LINE BELOW TO DISABLE REMOTE !!!
        #self.settings['remote'] = None #testing allowing option to not connect to a remote!
        #defines path to dir of remote code base
        self.remote = self.settings['remote']

        #set class capsule variable for user settings
        caps.Capsule.settings = self.settings
        caps.Capsule.pkgmngPath = self.pkgmngPath
        
        self.db = reg.Registry(self.remote)
        
        #defines path to dir of local code base
        self.local = os.path.expanduser(self.settings['local'])+"/"
        self.hidden = os.path.expanduser("~/.legohdl/") #path to registry and cache
        #defines how to open workspaces
        self.textEditor = self.settings['editor']

        self.db.findProjectsLocal(self.local)
        if(caps.Capsule.linkedRemote()): #fetch remote servers
            self.db.fetch()
        self.db.sync()
        
        os.environ['VHDL_LS_CONFIG'] = self.hidden+"mapping.toml" #directly works with VHDL_LS

        self.parse()
        pass

    def genPKG(self, cap):
        lib_path = self.hidden+"lib/"+cap.getLib()+"/"
        os.makedirs(lib_path, exist_ok=True)
        tmp_pkg = open(self.pkgmngPath+"/template_pkg.vhd", 'r')
        vhd_pkg = open(lib_path+cap.getName()+"_pkg.vhd", 'w')

        #need to look at toplevel VHD file to transfer correct library uses
        #search through all library uses and see what are chained dependencies
        src_dir,derivatives = cap.scanDependencies()
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
                comp = cap.ports().replace("entity", "component")
                line = line + "\n" + comp
                pass
            vhd_pkg.write(line)
            print(line,end='')
        print()
        vhd_pkg.close()
        tmp_pkg.close()
        pass

    #TO-DO: IMPLEMENT
    def install(self, cap, opt):
        cache_path = self.hidden+"cache/"
        lib_path = self.hidden+"lib/"+cap.getLib()+"/"
        # grab the ID to search for the project
        iden,rep = self.db.findPrj(cap.getLib(), cap.getName())
        cap = caps.Capsule(rp=rep) #update info into a capsule obj
        # clone the repo -> cache
        if(iden != -1):
            print(rep.name)
        self.db.findProjectsLocal(cache_path, cached=True)
        #does the package already exist in the cache directory?
        if(iden in self.db.getCachePrjs().keys()):
            print("Package is already installed.")
            return
        #possibly make directory for cached project
        print("Installing... ",end='')
        cache_path = cache_path+cap.getLib()+"/"
        os.makedirs(cache_path, exist_ok=True)
        #see what the latest version available is and clone from that version unless specified
        #print(rep.git_url)#print(rep.last_version)
        ver = None
        if(len(opt) and opt[0][0] != 'v'):
            print("ERROR- Invalid args")
            return
        elif(len(opt)):
            ver = opt[0]

        cap.install(cache_path, ver)
        print("success")
        print("library files path:")
        #generate PKG VHD
        self.genPKG(cap)
        
        #link it all together through writing paths into "mapping.toml"
        cur_lines = list()
        mapper = open(self.hidden+"mapping.toml", 'r')
        cur_lines = mapper.readlines()
        mapper.close()

        mapper = open(self.hidden+"mapping.toml", 'w')
        inc_paths = list()
        inc_paths.append("\'"+lib_path+"*.vhd"+"\',\n")
        inc_paths.append("\'"+cap.findPath(cap.getMeta("toplevel")).replace(cap.getMeta("toplevel"),"*.vhd")+"\',\n")
        inc = False
        found_lib = False
        if(len(cur_lines) <= 1):
            cur_lines.clear()
            mapper.write("[libraries]\n")
        for line in cur_lines:
            if(line.count(cap.getLib()+".files") > 0): #include into already established library section
                inc = True
                found_lib = True
            elif(inc and not line.count("]") > 0):
                if(line in inc_paths):
                    inc_paths.remove(line)   
            elif(inc and line.count("]") > 0): # end of section
                for p in inc_paths: #append rest of inc_paths
                    mapper.write(p)
                inc = False
            mapper.write(line)

        if(len(cur_lines) == 0 or not found_lib):
            if(line.count(cap.getLib()+".files") == 0): #create new library section
                mapper.write(cap.getLib()+".files = [\n")
                for p in inc_paths:
                    mapper.write(p)
                mapper.write("]\n")

        mapper.close()
        pass

    #TO-DO: IMPLEMENT
    def uninstall(self, pkg, opt):
        #remove from cache

        #remove from 'mapping.toml'

        #remove from lib
        pass

    def recurseScan(self, grp, d_list, top_mp):
        if(len(d_list) == 0):
            return grp,top_mp
        #go to YML of dependencies and add edges to build dependency tree
        for d in d_list:
            l,n = caps.Capsule.siftLibName(d)
            n = n.replace("_pkg", "")
            try:
                with open(self.hidden+"cache/"+l+"/"+n+"/."+n+".yml", "r") as file:
                    tmp = yaml.load(file, Loader=yaml.FullLoader)
            except:
                continue
            top_mp[l+'.'+n] = tmp['toplevel']
            grp,top_mp = self.recurseScan(grp, tmp['derives'], top_mp)
            for z in tmp['derives']:
                grp.addEdge(d, z)
        return grp,top_mp

    def libExists(self, lib):
        return os.path.isdir(self.hidden+"lib/"+lib)

    def export(self, cap, top=None, tb=None):
        print("Exporting...",end=' ')
        build_dir = cap.getPath()+"/build/"
        #create a clean build folder
        try:
            os.mkdir(build_dir)
        except:
            shutil.rmtree(build_dir)
            os.mkdir(build_dir)
        
        #add export option to override auto detection
        if(top == None):
            cap.autoDetectTop()
            cap.autoDetectBench()
            top = cap.getMeta("toplevel")
            tb = cap.getMeta("verification")
        elif(top != None and tb == None):
            cap.autoDetectBench(top)
            tb = cap.getMeta("verification")
        
        if(top.count(".vhd") == 0):
            top = top+".vhd"
        if(tb.count(".vhd")== 0):
            tb = tb+".vhd"

        g= graph.Graph()
        top_mp = dict()
        top_mp[cap.getLib()+'.'+cap.getName()] = cap.getMeta('toplevel')
        output = open(build_dir+"recipe", 'w')
        #mission: recursively search through every src VHD file for what else needs to be included
        src_dir,derivatives = cap.scanDependencies()
        for d in derivatives:
            g.addEdge(top, d)
        g,top_mp = self.recurseScan(g, derivatives, top_mp)

        g.output()
        #before writing recipe, the nodes must be topologically sorted as dependency tree
        hierarchy = g.topologicalSort() #flatten dependency tree
        print(hierarchy)

        library = dict() #stores lists at dictionary keys
        for h in hierarchy:
            l,n = caps.Capsule.siftLibName(h)
            n = n.replace("_pkg", "")
            #print(l,n)
            #library must exist in lib to be included in recipe.txt (avoids writing external libs like IEEE)
            if(self.libExists(l)): #check lib exists
                if not l in library.keys():
                    library[l] = list() 
                library[l].append(n)
                
        #write these libraries and their required file paths to a file for exporting
        for lib in library.keys():
            for pkg in library[lib]:
                key = lib+'.'+pkg
                root_dir = self.hidden+"cache/"+lib+"/"+pkg+"/"
                src_dir = glob.glob(root_dir+"/**/"+top_mp[key], recursive=True)
                output.write("LIB "+lib+" "+src_dir[0].replace(top_mp[key], "*.vhd")+"\n")
                output.write("LIB "+lib+" "+self.hidden+"lib/"+lib+"/"+pkg+"_pkg.vhd\n")

        #write current src dir where all src files are as "work" lib
        output.write("SRC "+cap.findPath(top).replace(top, "*.vhd")+"\n")
        #write current test dir where all testbench files are
        output.write("TB "+cap.findPath(tb)+"\n")
        output.close()
        print("success")
        pass

    def download(self, cap):
        if(not cap.linkedRemote()):
            print('No remote code base configured to download modules')
            return

        iden,rep = self.db.findPrj(cap.getLib(), cap.getName())
        print(rep.local_path)

        if(iden == -1):
            print('ERROR- Package \''+cap.getName()+'\' does not exist in remote')
            return

        if iden in self.db.getCurPrjs().keys(): #just give it an update!
            print("Project already exists in local workspace- pulling from remote...",end=' ')
            cap.pull() 
        else: #oh man, go grab the whole thing!
            print("Cloning from remote...",end=' ')
            cap.clone()
        
    
        try: #symbolically link the downloaded project folder to the cache
            shutil.rmtree(self.hidden+"cache/"+cap.getLib()+"/"+cap.getName()+"/")
        except:
            pass
        #generate PKG VHD
        opt = list()
        opt.append("v"+cap.getVersion())   
        self.install(caps.Capsule(rp=rep), opt)

        print("success")
        pass

    def upload(self, cap, options=None):
        err_msg = "ERROR- please flag the next version for release with one of the following args:\n"\
                    "\t(-v0.0.0 | -maj | -min | -fix)"
        if(len(options) == 0):
                print(err_msg)
                exit()
            
        ver = ''
        if(options[0][0] == 'v'):
            ver = options[0]
        
        if(options[0] != 'maj' and options[0] != 'min' and options[0] != 'fix' and ver == ''):
            print(err_msg)
            exit()

        cap.autoDetectTop()
        cap.release(ver, options)

        try: shutil.rmtree(self.hidden+"cache/"+cap.getLib()+"/"+cap.getName())
        except: pass
        #clone new project's progress into cache
        tmp = caps.Capsule(cap.getLib()+'.'+cap.getName())
        tmp.install(self.hidden+"cache/"+cap.getLib()+"/", "v"+cap.getVersion(), src_url=cap.getPath())

        if caps.Capsule.linkedRemote():
            print("Updating remote package contents...",end=' ')
            cap.pushRemote()
            print("success")
            print(cap.getLib()+"."+cap.getName()+" is now available as version "+cap.getVersion())
        pass

    def setSetting(self, options, choice):
        if(len(options) != 1):
            print("ERROR- Invalid syntax; could not adjust setting")
            return

        if(options[0] == 'gl-token' or options[0] == 'gh-token'):
            self.db.encrypt(choice, options[0])
            return

        if(not options[0] in self.settings.keys()):
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

        self.settings[options[0]] = choice

        with open(self.pkgmngPath+"settings.yml", "w") as file:
            yaml.dump(self.settings, file)
            pass
    
    #TO-DO: implement
    def convert(self, package):
        #find the src dir and testbench dir through autodetect top-level modules

        #see if there is a .git folder
        #create a YML
        pass

    def inventory(self, options):
        self.db.listCaps(options)
        print()
        pass

    def cleanup(self, cap, force):
        iden,rep = self.db.findPrj(cap.getLib(), cap.getName())
        cap = caps.Capsule(rp=rep)
        if(not cap.isValid()):
            print('No module '+cap.getName()+' exists locally')
            return
        
        if(self.remote == None and force):
            print('\
                WARNING- No remote code base is configured, if this module is deleted it may be unrecoverable.\n \
                DELETE '+cap.getName()+'? [y/n]\
                ')
            response = ''
            while(True):
                response = input()
                if(response.lower() == 'y' or response.lower() == 'n'):
                    break
            if(response.lower() == 'n'):
                print(cap.getName()+' not deleted')
                force = False
        #if there is a remote then the project still lives on, can be "redownloaded"
        #MOVES THE PROJECT TO THE CACHE AND GENERATES A PKG FILE

        try:
            if(force):
                shutil.rmtree(rep.local_path)
            else:
                shutil.rmtree(rep.local_path, ignore_errors=True)
                shutil.move(rep.local_path, self.hidden+"cache/"+cap.getLib()+"/")
                self.genPKG(cap)
            print('Deleted '+cap.getName()+' from local workspace')
        except:
            print('No module '+cap.getName()+' exists locally')
            return
        #delete the module remotely?
        pass

    def parse(self):
        #check if we are in a project directory (necessary to run a majority of commands)
        pkgPath = os.getcwd()
        lastSlash = pkgPath.rfind('/') #determine project's name to know the YAML to open
        pkgCWD = pkgPath[lastSlash+1:]
        self.capsuleCWD = caps.Capsule(pkgCWD)
        #is there a .yaml here? if so, grab the id and then load the project from the repo
        if(os.path.isfile(pkgPath+'/.'+pkgCWD+".yml")):
            with open(pkgPath+'/.'+pkgCWD+".yml", 'r') as f:
                tmp = yaml.load(f, Loader=yaml.FullLoader)
                f.close()
                pass
            if tmp['id'] in self.db.getCurPrjs().keys():
                self.capsuleCWD = caps.Capsule(rp=self.db.getCurPrjs()[tmp['id']])
            pass

        if(not self.capsuleCWD.isValid()):
            #print("NOT A CAPSULE DIRECTORY")
            pass
        else:
            #print("VALID CAPSULE DIRECTORY")
            pass
        
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
            else:
                print("ERROR- Cannot parse input!")
                return

        for x in options:
            if(x[0] == ':'):
                description = x[1:]
                break

        package = package.replace("-", "_")
        self.capsulePKG = caps.Capsule(package)
        
        #branching through possible commands
        if(command == "install"):
            self.install(self.capsulePKG, options) #TO-DO
            pass
        elif(command == "uninstall"):
            self.uninstall(package, options) #TO-DO
            pass
        elif(command == "new" and len(package) and not self.capsulePKG.isValid()):
            if caps.Capsule.linkedRemote():
                i = package.find('.')
                lib = package[:i]
                name = package[i+1:]
                if(len(lib) > 0 and caps.Capsule.linkedRemote()): #try to make new subgroup if DNE
                    self.db.createSubgroup(lib, self.db.accessGitlabAPI())

            self.capsulePKG = caps.Capsule(package, new=True)
            
            if caps.Capsule.linkedRemote(): #now fetch from db to grab ID
                self.capsulePKG.saveID(self.db.fetchProjectShallow(lib,name)['id'])
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
                self.cleanup(self.capsuleCWD, True)
            pass
        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            self.download(self.capsulePKG)
            if('o' in options):
                self.capsulePKG.load()
            pass
        elif(command == "summ" and self.capsuleCWD.isValid()):
            self.capsuleCWD.getMeta()['summary'] = description
            self.capsuleCWD.pushYML("Updates project summary")
            self.capsuleCWD.scanDependencies()
            pass
        elif(command == 'del'):
            force = False
            if(len(options) > 0):
                if(options[0].lower() == 'f'):
                    force = True
            self.cleanup(self.capsulePKG, force)
        elif(command == "list"): #a visual aide to help a developer see what package's are at the ready to use
            self.inventory(options)
            pass
        elif(command == "init"):
            self.convert(package)
        elif(command == "export"): #a visual aide to help a developer see what package's are at the ready to use
            #'' and list() are default to pkg and options
            mod = package
            tb = None
            if(mod == ''):
                mod = None
            if(len(options) > 0):
                tb = options[0]
            self.export(self.capsuleCWD, mod, tb)
            pass
        elif(command == "open" and self.capsulePKG.isValid()):
            self.capsulePKG.load()
            pass
        elif(command == "show" and self.capsulePKG.isValid()):
            self.capsulePKG.show()
            pass
        elif(command == "ports" and self.capsulePKG.isValid()):
            print(self.capsulePKG.ports())
        elif(command == "template" and self.settings['editor'] != None):
            os.system(self.settings['editor']+" "+self.pkgmngPath+"/template")
            pass
        elif(command == "config"):
            self.setSetting(options, package)
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
            formatHelp("install","grab package from remote for dependency use")
            formatHelp("uninstall","remove package from cache")
            formatHelp("download","grab package from remote for further development")
            formatHelp("release","release the next new version of the current package")
            formatHelp("update","update installed package to be to the latest version")
            formatHelp("list","print list of all packages available")
            formatHelp("open","opens the package with the configured text-editor")
            formatHelp("del","deletes the package from the local workspace")
            formatHelp("search","search remote or local workspace for specified package")
            formatHelp("init","initialize the current folder into a valid package format")
            formatHelp("export","generate a file of necessary paths to build the project")
            formatHelp("show","read further detail about a specified package")
            formatHelp("ports","print ports list of specified package")
            formatHelp("summ","add description to current project")
            formatHelp("new","create a templated empty package")
            formatHelp("config","set package manager settings")
            formatHelp("template","open the template in the configured text-editor")
            formatHelp("recipe","open the recipe file in the configured text-editor")
            print("\nType \'legohdl help <command>\' to read more on entered command.")
            exit()
            print("\nOptions:\
            \n\t-v0.0.0\t\tspecify package version (insert values replacing 0's)\
            \n\t-:\" \"\t\tproject summary (insert between quotes)\
            \n\t-i\t\tset installation flag to install package(s) on project creation\
            \n\t-alpha\t\talphabetical order\
            \n\t-o\t\topen the project\
            \n\t-d\t\tremoves the released package from your local codebase\
            \n\t-F\t\tforce project uninstallation alongside deletion from local codebase\
            \n\t-local\t\tset local path setting\
            \n\t-remote\t\tset remote path setting\
            \n\t-editor\t\tset text-editor setting\
            \n\t-author\t\tset author setting\
            \n\t-gl-token\t\tset gitlab access token\
            \n\t-gh-token\t\tset github access token\
            \n\t-maj\t\trelease as next major update (^.0.0)\
            \n\t-min\t\trelease as next minor update (-.^.0)\
            \n\t-fix\t\trelease as next patch update (-.-.^)\
            ")
        else:
            print("Invalid command; type \"help\" to see a list of available commands")
        pass

    def commandHelp(self, cmd):
        if(cmd == ''):
            return
        #TO-DO: if-elif block of all commands
        exit()
        pass
    pass

def main():
    #print('\n---legoHDL package manager---\n')
    legoHDL()


if __name__ == "__main__":
    main()
