#!/usr/bin/env python3
import os, sys, git, shutil
import requests
from bs4 import BeautifulSoup
import yaml
try:
    from pkgmngr import capsule as caps
    from pkgmnger import registry as reg
except:
    import capsule as caps
    import registry as reg

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
        remote_reg = reg.Registry(self.remote)
        remote_reg.fetch()
        exit()
        #self.remote = None #testing allowing option to not connect to a remote!
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
            capsules=list()
            if(caps.Capsule.linkedRemote()):
                reg = git.Repo(self.hidden+"registry")
                reg.remotes.origin.pull(refspec='{}:{}'.format('master', 'master'))
            else: # check package directory for any changes to folder removals if only local setting
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
            
            if(not caps.Capsule.linkedRemote()):
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
            self.registry.pop(cap.getTitle(), None)
            msg = 'Removes '+cap.getTitle()+' from the database.'

        elif(cap != None): #looking to write a value to registry
            if(cap.getTitle() in self.registry and (self.registry[cap.getTitle()] == cap.getVersion() \
                or (cap.getVersion() == zero))):
                return
            print('Syncing with registry...')
            self.registry[cap.getTitle()] = cap.getVersion() if cap.getVersion() != '0.0.0' else ''
            if(self.registry[cap.getTitle()] == ''):
                msg = 'Introduces '+ cap.getTitle() +' to the database.'
            else:
                msg = 'Updates '+ cap.getTitle() +' version to ' + cap.getVersion()+'.'

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
        print(self.registry)
        ver = self.registry[cap.getTitle()]
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
    def install(self, pkg, options):
        if(not caps.Capsule.linkedRemote()):
            print("ERROR- No remote link configured")
            return
        
        self.syncRegistry()
        #verify there is an existing module under this name
        if (self.registry.count(pkg) <= 0):
            print("ERROR- No module exists under the name \"",pkg,"\".",sep='')
            return  

        #perform install -> install will grab repo and put into cache, and then symlink src files to
        #lib folder along with creating a pkg vhd file

        cp = caps.Capsule(pkg)

        #checkout latest version number
        version = self.fetchVersion(cp, True)
        if(version == '0.0.0'):
            print("ERROR- There are no available versions for this module! Cannot install.")

        #clone to cache
        cp.cache(self.hidden)
        #create folder in library
        os.makedirs(self.hidden+"lib/"+cp.getLib())
        
        cp.install(options)

        return
        
        if(version == ''):
            print("ERROR- There are no available versions for this module! Cannot install.")
            return
        
        for opt in options:
            if(opt[0]=='v'): #checkout specified version number
                version = opt
            pass

        print("\nInstalling", pkg, "version:",version,"\b...\n")

        #formulate commands
        #suggestion: pull down from remote repo before doing checkouts
        cmd = "cd "+self.remote+pkg+"; git checkout "+version+" -q;" #-q options silences git output
        error = os.system(cmd)
        if(error != 256):
            cmd = "cd "+self.remote+pkg+\
            "; cp ./design/* "+self.projectPath+"/libraries/; git checkout - -q"
            os.system(cmd)
        else:
            print("ERROR- The version you are requesting for this module does not exist.")
            return

        #update metadata to list module under this project's dependency and compatible version
        self.metadata['derives'][package] = version
        
        print("Successfully installed ", pkg, " [",version,"] to the current project.",sep='')
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
        print(catalog)
        if(options.count('local') or not caps.Capsule.linkedRemote()):
            catalog = local_catalog
        if(options.count('alpha')):
            catalog = sorted(catalog)
        print(catalog)
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
            print("\t",'{:<24}'.format('.'+pkg),'{:<14}'.format(isDownloaded),'{:<10}'.format(ver),info)
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
            self.install(package, options) #TO-DO
            pass
        elif(command == "uninstall"):
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
            self.capsuleCWD.scanDependencies()
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
            w = str(24)
            print("VHDL's package manager")
            print('USAGE: \
            \n\tlegohdl <command> <package> [options]\
            \n')
            print("COMMANDS:")
            def formatHelp(cmd, des):
                print('{:<60}'.format(cmd),des)
                pass
            formatHelp("install <package> [-v0.0.0]","fetch package from the code base to be available in current project")
            formatHelp("uninstall <package>","remove package from current project along with all dependency packages")
            formatHelp("download <package> [-o]","pull package from remote code base for further development")
            formatHelp("upload [-v0.0.0 | -maj | -min | -fix]","release the next new version of package")
            formatHelp("update <package> [-all]","update developed package to be to the latest version")
            formatHelp("list [-alpha -local]","print list of all packages available from code base")
            formatHelp("open <package>","opens the package with the set text-editor")
            formatHelp("del <package>","deletes the package from the local code base")
            formatHelp("search <package> [-local]","search remote (default) or local code base for specified package")
            formatHelp("convert <package>","converts the current directory into a valid package format")
            formatHelp("show <package> [-v0.0.0]","provide further detail into a specified package")
            formatHelp("ports <package> [-v0.0.0]","print ports list of specified package")
            formatHelp("summ [-:\"description\"]","add description to current project")
            formatHelp("new <library.package> [-\"description\" -o]","create a standard empty package based on a template and pushes to remote code base")
            formatHelp("config <value/path> [-local | -remote | -editor | -author]","adjust package manager settings")
            formatHelp("template","open the template in the configured text-editor to make custom configuration")
            print("\nOptions:\
            \n\t-v0.0.0\t\tspecify package version (insert values replacing 0's)\
            \n\t-:\" \"\t\tproject summary (insert between quotes)\
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
