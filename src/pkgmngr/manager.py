#!/usr/bin/env python3
import os, sys, git, shutil
import yaml
try:
    from pkgmngr import capsule as caps
except:
    import capsule as caps

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
        
        self.registry = None #list of all available modules in remote
        
        #defines path to dir of remote code base
        self.remote = self.settings['remote']
        self.remote = None #testing allowing option to not connect to a remote!
        #defines path to dir of local code base
        self.local = os.path.expanduser(self.settings['local'])+"/"
        self.hidden = os.path.expanduser("~/.legoHDL/") #path to registry and cache
        #defines how to open workspaces
        self.textEditor = self.settings['editor']
        
        os.environ['VHDL_LS_CONFIG'] = self.hidden+"mapping.toml" #directly works with VHDL_LS

        self.parse()
        pass

    def isValidPkg(self, pkg):
        return os.path.isfile(self.local+pkg+"/."+pkg+".yml")
        pass

    def syncRegistry(self, cap=None, rm=False, skip=False):
        msg = ''
        zero = '0.0.0'

        if(self.registry == None and not skip): # must check for changes
            folders=list()
            if(caps.Capsule.linkedRemote()):
                reg = git.Repo(self.hidden+"registry")
                reg.remotes.origin.pull(refspec='{}:{}'.format('master', 'master'))
            else: # check package directory for any changes to folder removals if only local setting
                capsules = list()
                for prj in os.listdir(self.local):
                    if self.isValidPkg(prj):
                        capsules.append(prj)

            self.registry = dict()
            with open(self.hidden+"registry/db.txt", 'r') as file:
                for line in file.readlines():
                    m = line.find('=')
                    key = line[:m]
                    val = line[m+1:len(line)-1]
                    self.registry[key] = val
            # if only local, keep registry in sync with all available folders in package dir
            for prj in list(self.registry.keys()):
                if not prj in capsules:
                    self.registry.pop(prj, None)
                    msg = 'Removes '+prj+' from the database.'
            
            for c in capsules:
                if not c in list(self.registry.keys()):
                    print("Found a new local valid package",c)
                    #load settings
                    self.syncRegistry(caps.Capsule(c), skip=True)

         
        if(cap != None and rm == True): #looking to remove a value from the registry
            self.registry.pop(cap.getName(), None)
            msg = 'Removes '+cap.getName()+' from the database.'

        elif(cap != None): #looking to write a value to registry
            if(cap.getName() in self.registry and (self.registry[cap.getName()] == cap.getVersion() \
                or (cap.getVersion() == zero))):
                return
            print('Syncing with registry...')
            self.registry[cap.getName()] = cap.getVersion() if cap.getVersion() != '0.0.0' else ''
            if(self.registry[cap.getName()] == ''):
                msg = 'Introduces '+cap.getName() +' to the database.'
            else:
                msg = 'Updates '+cap.getName() +' version to '+cap.getVersion()+'.'

        if(msg != ''):
            print(msg)
            with open(self.hidden+"registry/db.txt", 'w') as file:
                for key,val in self.registry.items():
                    if(val == zero):
                        val = ''
                    file.write(key+"="+val+"\n")
            
            reg = git.Repo(self.hidden+"registry")
            reg.git.add(update=True)
            reg.index.commit(msg)
            if(self.remote != None):
                reg.remotes.origin.push(refspec='{}:{}'.format('master', 'master'))
        pass


    def fetchVersion(self, cap, remote=True):
        self.syncRegistry()
        ver = self.registry[cap.getName()]
        if(not remote):
            ver = cap.getVersion()
        if(ver == None):
            return ''
        else:
            return ver

    def uninstall(self, package, options):
        #does this module exist in this project's scope?
        if not package in self.metadata['derives']:
            print("ERROR- No installed module exists under the name \"",package,"\".",sep='')
            return

        version = self.metadata['derives'][package]
        print("\nUninstalling", package, "version:",version,"\b...\n")

        #delete file from dependency directory
        os.remove(self.projectPath+"/libraries/"+package+".vhd")

        #update metadata of new removal
        del self.metadata['derives'][package]
        print("Successfully uninstalled ", package, " [",version,"] from the current project.",sep='')
        pass
    
    #to-do: REWORK INSTALL FUNCTION
    def install(self, package, options):
        #verify there is an existing module under this name
        if(not os.path.isdir(self.findPath(package))):
            print("ERROR- No module exists under the name \"",package,"\".",sep='')
            return
        
        if(not os.path.isdir(self.findPath(self.pkgName, False, 'derives'))):
            os.mkdir('libraries')

        #checkout latest version number
        version = self.fetchVersion(package)
        
        if(version == ''):
            print("ERROR- There are no available versions for this module! Cannot install.")
            return
        
        for opt in options:
            if(opt[0]=='v'): #checkout specified version number
                version = opt
            pass

        print("\nInstalling", package, "version:",version,"\b...\n")

        #formulate commands
        #suggestion: pull down from remote repo before doing checkouts
        cmd = "cd "+self.remote+package+"; git checkout "+version+" -q;" #-q options silences git output
        error = os.system(cmd)
        if(error != 256):
            cmd = "cd "+self.remote+package+\
            "; cp ./design/* "+self.projectPath+"/libraries/; git checkout - -q"
            os.system(cmd)
        else:
            print("ERROR- The version you are requesting for this module does not exist.")
            return

        #update metadata to list module under this project's dependency and compatible version
        self.metadata['derives'][package] = version
        
        print("Successfully installed ", package, " [",version,"] to the current project.",sep='')
        pass

    def download(self, cap):
        self.syncRegistry()

        if(not cap.linkedRemote()):
            print('No remote code base configured to download modules')
            return

        loc_catalog = os.listdir(self.local)

        if cap.getName() in self.registry:
            if cap.getName() in loc_catalog: #just give it an update!
                cap.pull()
            else: #oh man, go grab the whole thing!
                cap.clone()
        else:
            print('ERROR- Package \''+cap.getName()+'\' does not exist in remote storage.')
        pass

    def upload(self, cap, options=None):
        if(len(options) == 0):
                print("ERROR- please flag the next version for release with one of the following args:\n"\
                    "\t(-v0.0.0 | -maj | -min | -fix)")
                exit()
            
        ver = ''
        if(options[0][0] == 'v'):
            ver = options[0]
            print(ver)

        self.syncRegistry()

        cap.release(ver, options)        

        if not cap.getName() in self.registry.keys():
            print("Uploading a new package to remote storage...")
            #to-do: implement git python code for said commands
            #cmd = "git init; git add .; git commit -m \"Initial project creation.\"; git push --tags --set-upstream https://gitlab.com/chase800/"+self.pkgName+".git master"  
        elif caps.Capsule.linkedRemote():
            print("Updating remote package contents...")
            cap.__repo.remotes.origin.push()
        
        self.syncRegistry(cap)
        pass

    def setSetting(self, options, choice):
        if(len(options) != 1):
            print("ERROR- Invalid syntax; could not adjust setting")
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

    def list(self, options):
        self.syncRegistry() 
        catalog = self.registry

        tmp = list(os.listdir(self.local))
        local_catalog = list()
        for d in tmp:
            if(self.isValidPkg(d)):
                local_catalog.append(d)

        downloadedList = dict()
        
        for pkg in catalog:
            if(pkg in local_catalog):
                downloadedList[pkg] = True
            else:
                downloadedList[pkg] = False

        if(options.count('local') or self.remote == None):
            catalog = local_catalog
        if(options.count('alpha')):
            catalog = sorted(catalog)
        
        print("\nList of available modules:")
        print("\tModule\t\t\tlocal\t\tversion")
        print("-"*80)
        for pkg in catalog:
            cp = caps.Capsule(pkg)
            isDownloaded = '-'
            info = ''
            ver = self.fetchVersion(cp, True)
            if (downloadedList[pkg]):
                isDownloaded = 'y'
                loc_ver = ''
                loc_ver = self.fetchVersion(cp, False)
                if((ver != '' and loc_ver == '') or (ver != '' and ver > loc_ver)):
                    info = '(update)-> '+ver
                    ver = loc_ver
            print("\t",'{:<24}'.format(pkg),'{:<14}'.format(isDownloaded),'{:<10}'.format(ver),info)
        print()
        pass

    def cleanup(self, cap):
        if(not cap.isValid()):
            print('No module '+cap.getName()+' exists locally')
            return
        
        if(self.remote == None):
            print('WARNING- No remote code base is configured, if this module is deleted it may be unrecoverable.\n \
                DELETE '+cap.getName()+'? [y/n]\
                ')
            response = ''
            while(True):
                response = input()
                if(response.lower() == 'y' or response.lower() == 'n'):
                    break
            if(response.lower() == 'n'):
                print(cap.getName()+' not deleted')
                return
            #update registry if there is no remote 
            # (if there is a remote then the project still lives on, can be "redownloaded")
            self.syncRegistry(cap, rm=True)   
        #delete locally
        try:
            shutil.rmtree(self.local+cap.getName())
        except:
            print('No module '+cap.getName()+' exists locally')
            return
            
        #delete the module remotely?
        pass

        #c.metadata['summary'] = description
        #TO-DO: possibly scrap if going to auto-gen dependencies from vhdl file
        #installPkg = list()
        #if 'i' in options:
        #    for opt in options[1:]:
        #        if(opt == ','):
        #            self.install(installPkg[0], installPkg[1:])
        #            installPkg.clear()
        #        else:
        #            installPkg.append(opt)
        #    if(len(installPkg)): #perform last install
        #        self.install(installPkg[0], installPkg[1:])

        #add and commit package name to registry repo (pass in capsule obj)

    def parse(self):
        #set class capsule variable for user settings
        caps.Capsule.settings = self.settings
        caps.Capsule.pkgmngPath = self.pkgmngPath

        #check if we are in a project directory (necessary to run a majority of commands)
        pkgPath = os.getcwd()
        lastSlash = pkgPath.rfind('/') #determine project's name to know the YAML to open
        pkgCWD = pkgPath[lastSlash+1:]
        self.capsuleCWD = caps.Capsule(pkgCWD)
        if(not self.capsuleCWD.isValid()):
            print("NOT A CAPSULE DIRECTORY")
        
        command = package = description = ""
        options = []

        #store args accordingly from command-line
        for i, arg in enumerate(sys.argv):
            if(i == 1):
                command = arg
            elif(i > 1):
                if(i == 2 and arg[0] != '-'):
                    package = arg
                if(arg[0] == '-'): #parse any options
                    options.append(arg[1:])
                elif(len(options) and options.count('i') > 0):
                    options.append(arg)
                else:
                    pass


        description = package
        package = package.replace("-", "_")
        self.capsulePKG = caps.Capsule(package)
        
        #branching through possible commands
        if(command == "install" and self.capsuleCWD.isValid()):
            self.install(package, options) #TO-DO
            pass
        elif(command == "uninstall" and self.capsuleCWD.isValid()):
            self.uninstall(package, options) #TO-DO
            pass
        elif(command == "new" and len(package) and not self.capsulePKG.isValid()):
            self.capsulePKG = caps.Capsule(package, new=True)
            self.syncRegistry(self.capsulePKG)
            if(options.count("o") > 0):
                self.capsulePKG.load()
            pass
        elif(command == "upload" and self.capsuleCWD.isValid()):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(self.capsuleCWD, options=options)
            if(len(options) == 2 and options[1] == 'd'):
                self.cleanup(self.capsuleCWD)
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
            pass
        elif(command == 'del'):
            self.cleanup(self.capsulePKG)
        elif(command == "list"): #a visual aide to help a developer see what package's are at the ready to use
            self.list(options)
            pass
        elif(command == "open"):
            self.capsulePKG.load()
            pass
        elif(command == "show"):
            if(self.capsulePKG.isValid()):
                self.capsulePKG.show()
            pass
        elif(command == "ports" and self.capsulePKG.isValid()):
            self.capsulePKG.ports()
        elif(command == "template" and self.settings['editor'] != None):
            os.system(self.settings['editor']+" "+self.pkgmngPath+"/template")
            pass
        elif(command == "config"):
            self.setSetting(options, package)
            pass
        elif(command == "help" or command == ''):
            print('Usage: \
            \n\tlegohdl <command> [options]\
            \n')
            print("Commands:\
            \n\tinstall <package> [-v0.0.0]\n\t\t-fetch package from the code base to be available in current project\
            \n\n\tuninstall <package>\n\t\t-remove package from current project along with all dependency packages\
            \n\n\tdownload <package> [-o]\n\t\t-pull package from remote code base for further development\
            \n\n\tupload <-v0.0.0 | -maj | -min | -fix>\n\t\t-release the next new version of package\
            \n\n\tupdate <package> [-all]\n\t\t-update developed package to be to the latest version\
            \n\n\tlist [-alpha -local]\n\t\t-print list of all packages available from code base\
            \n\n\topen <package> \n\t\t-opens the package with the set text-editor\
            \n\n\tdel <package> \n\t\t-deletes the package from the local code base\
            \n\n\tconvert <package> \n\t\t-converts the current directory into a valid package format\
            \n\n\tsearch <package> [-local]\n\t\t-search remote (default) or local code base for specified package\
            \n\n\tshow <package> [-v0.0.0]\n\t\t-provide further detail into a specified package\
            \n\n\tports <package> [-v0.0.0]\n\t\t-print ports list of specified package\
            \n\n\tsumm \"description\"\n\t\t-add description to current project\
            \n\n\tnew <package> [-\"description\" -o -i <package> [-v0.0.0] , <package> [-v0.0.0] , ...]\n\t\t-create a standard empty package based on a template and pushes to remote code base\
            \n\n\tconfig <value/path> [-local | -remote | -editor | -author]\n\t\t-adjust package manager settings\
            \n\n\ttemplate\n\t\t-open the template in the configured text-editor to make custom configuration\
            \n")
            print("Options:\
            \n\t-v0.0.0\t\tspecify package version (insert values replacing 0's)\
            \n\t-i\t\tset installation flag to install package(s) on project creation\
            \n\t-alpha\t\talphabetical order\
            \n\t-o\t\topen the project\
            \n\t-d\t\tremoves the released package from your local codebase\
            \n\t-local\t\tidentify local path setting\
            \n\t-remote\t\tidentify remote path setting\
            \n\t-editor\t\tidentify text-editor setting\
            \n\t-author\t\tidentify author setting\
            \n\t-maj\t\trelease as next major update (^.0.0)\
            \n\t-min\t\trelease as next minor update (-.^.0)\
            \n\t-fix\t\trelease as next patch update (-.-.^)\
            ")
        else:
            print("Invalid command; type \"help\" to see a list of available commands")
        pass
    pass

def main():
    print('\n---legoHDL package manager---\n')
    legoHDL()


if __name__ == "__main__":
    main()
