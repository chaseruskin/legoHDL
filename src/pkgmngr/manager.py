#!/usr/bin/env python3
import os, sys, git, shutil
import collections, yaml
from datetime import date
try:
    from pkgmngr import capsule as caps
except:
    import capsule as caps
#<ideas>


#export project as a vivado project, with symbolic links to the VHDL files

#on a version release, have a dedicated zipped file of the vhd and .yaml?
#faster for an install, but may have to be reworked if then deciding to download

#allow remote to be null,
#allow user to open settings file
#allow user to open template folder
#movtivation behind building a Hardware HDL manager:
#   -direct control and flexibility to design to meet our needs/worklfow/situation
#   -complete customization to tackle our problem of managing our modules
#   -promotes more experimentation => seeks to find the best solution (not trying to conform to other's standards)

#some idea python scripts to be made:
#   toolbelt.py // helps automate use of tools for lint, anaylsis, sim
#   testkit.py // module to store common functions related to testbenches
#   manager.py // package manager to handle collections of IPs

#the dependencies folder is not tracked by git because there would be major overlap of code/resources. Code should be 
# tried to restricted into a single location. Tracking the YAML file and its list of dependencies will be enough and 
# will trigger installs when required by a download

#when installing dependency, follow directed acyclic graph with topological sort
#when installing dependency, automatically paste the component declaration into top-level design
#when installing dependency, allow for adding multiple dependencies in one command by using ',' between modules
#example: legoHDL install flipflop -v1.0 , combinational , asyncCounter -v2.1

#use filenames with the version (in dependency folder) to allow for designs that require multiple versions of a module that 
# is used by different entities

#prompt to move all current projects to new local directory when changing setting? nah

#seperate program/framework to perform lint, synth, simulation/verification, place-and-route, bitstream? 

#add pin mapping to YAML file to allow program to place-and-route design post-synthesis

#search all design VHD files to determine which is top-level design
#then find which testbench instantiates that design

#alternate method: dependency folder has files that point to the git commits of those versions?

#use 'sync tb' to sync ports of design to the testbench vhdl and across testbench.py file for use 
# -(will also auto make generic testbench) (can be embedded into CI with analysis of design file) -toolkit.py-

#eventually make a GUI with tkinter for easier & visual package management

#SCENARIO: developer is working on improving a VHDL module that has been previouly released (v1.0). Other higher-level
# module packages now use v1.0 in their design as a dependency. Developer now releases v1.1. A new moudle package now
# uses v1.1 of this lower-level module, and now another newer high-level module uses the modules that depend on v1.0 
# and the module that depends on v1.1. What's the resolve?
#   -all MINOR (0.X) version updates should try to update the dependency list of those who depend on it and rerun verification
#   to ensure module is still valid. If the build fails in CI, automate a git revert to the commit previous to the "Updates 
#   'x' dependency module version to '#.#'.
#   -all MAJOR (X.0) version updates will not automatically trigger the chain because of it has altered the core
#   functionality and can be assumed to break all other builds

#program should handle most git version control behind the scenes (pushing and pulling, maybe even tags)

#what if a developer never had to touch a VHDL file when verifying a module?
# motivation:
#   -faster development time as it is all rooted in a single source (python testbench file)
#   -VHDL files can very repetitive in nature when setting up a testbench using I/O files
#   -command-line automatic scripts will handle copying and pasting the right lines of code into the tb
#   -python is source of verification because it is very readable, easy to build up a library of helpful code, 
#   and easy to write with minimal lines
#   -software languages are the best at writing software; why try to do so in a restricted HW language in confusing ways
#   when software languages are available to do the job (there are great data science modules available scipy, matplotlib, pandas)

# a "library" is no more than a collection of VHDL files with respective packages. Every new release gets new component declarations
# for that specific version added to that project's pkg VHDL file. library "name"; use "name".projectpkg.component_ver (library.packagefile.comp)
# continually updates. The top-level to a project is the only component that gets added to the pkg file. Adding versioning to the end
# of component names may allow for preserving and using multiple designs
#</ideas>

class legoHDL:

    def __init__(self):
        
        #defines path to working dir of 'legoHDL' tool
        self.pkgmngPath = os.path.realpath(__file__)
        self.pkgmngPath = self.pkgmngPath[:self.pkgmngPath.rfind('/')+1]

        self.settings = dict()
        with open(self.pkgmngPath+"settings.yml", "r") as file:
            self.settings = yaml.load(file, Loader=yaml.FullLoader)

        self.isValidProject = False
        self.path = ""
        self.pkgName = ""
        self.pkgPath = ""
        
        self.registry = None #list of all available modules in remote
        self.metadata = None
        
        #defines path to dir of remote code base
        self.remote = self.settings['remote']
        self.remote = None #testing allowing option to not connect to a remote!

        #defines path to dir of local code base
        self.local = os.path.expanduser(self.settings['local'])+"/"

        self.hidden = os.path.expanduser("~/.legoHDL/") #path to registry and cache
        #defines how to open workspaces
        self.textEditor = self.settings['editor']
        
        self.parse()
        self.save()
        pass

    def isValidPackage(self, pkg):
        return os.path.isfile(self.local+pkg+"/."+pkg+".yml")
        pass

    #returns a string to a package directory
    def findPath(self, package, remote=True, folder=''):
        pathway = self.remote
        subdir = ''
        if(not remote):
            pathway = self.local
        if(folder != ''):
            subdir = "/"+folder+"/"
        return pathway+package+subdir

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
                    if self.isValidPackage(prj):
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
            if(cap.getName() in self.registry and (self.registry[cap.getName()] == cap.getMeta()['version'] \
                or (cap.getMeta()['version'] == zero))):
                return
            print('Syncing with registry...')
            self.registry[cap.getName()] = cap.getMeta()['version'] if cap.getMeta()['version'] != '0.0.0' else ''
            if(self.registry[cap.getName()] == ''):
                msg = 'Introduces '+cap.getName() +' to the database.'
            else:
                msg = 'Updates '+cap.getName() +' version to '+cap.getMeta()['version']+'.'

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


    def fetchVersion(self, package, remote=True):
        self.syncRegistry()
        ver = self.registry[package]
        if(not remote):
            with open(self.local+package+"/."+package+".yml", "r") as file:
                tmp_metadata = yaml.load(file, Loader=yaml.FullLoader)
            ver = tmp_metadata['version']
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

    def upload(self, release='', options=None):
        self.syncRegistry()
        last_ver = self.metadata['version']
        first_dot = last_ver.find('.')
        last_dot = last_ver.rfind('.')

        major = int(last_ver[:first_dot])
        minor = int(last_ver[first_dot+1:last_dot])
        patch = int(last_ver[last_dot+1:])
        print('last version:',major,minor,patch)
        if(release == ''):
            if(options[0] == "maj"):
                major += 1
                minor = patch = 0
                pass
            elif(options[0] == "min"):
                minor += 1
                patch = 0
                pass
            elif(options[0] == "fix"):
                patch += 1
                pass
            release = 'v'+str(major)+'.'+str(minor)+'.'+str(patch)

        repo = git.Repo(self.local+self.pkgName)
        print(release)
        if(release != ''):
            self.metadata['version'] = release[1:]
            self.save()
            repo.git.add(update=True)
            repo.index.commit("Release version -> "+self.metadata['version'])
            repo.create_tag(release)

        if not self.pkgName in self.registry.keys():
            print("Uploading a new package to remote storage...")
            #to-do: implement git python code for said commands
            #cmd = "git init; git add .; git commit -m \"Initial project creation.\"; git push --tags --set-upstream https://gitlab.com/chase800/"+self.pkgName+".git master"  
        elif self.remote != None:
            print("Updating remote package contents...")
            repo.remotes.origin.push()
        
        self.syncRegistry(self.pkgName)
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

    def save(self):
        if(not self.isValidProject): 
            return
        #write back YAML info
        print(self.metadata['version'])
        tmp = collections.OrderedDict(self.metadata)
        tmp.move_to_end('derives')
        tmp.move_to_end('name', last=False)

        #a little magic to save YAML in custom order for easier readability
        with open(self.pkgPath+"."+self.pkgName+".yml", "w") as file:
            while len(tmp):
                it = tmp.popitem(last=False)
                single_dict = {}
                single_dict[it[0]] = it[1]
                yaml.dump(single_dict, file)
                pass
            pass

        #lock all dependency files to disable editing
        #Linux: "chattr +i <file>"...macOS: chflags uchg <file>"
        #to-do: implement with python code
        if(len(self.metadata['derives']) > 0):
            os.system("chflags uchg "+self.pkgPath+"libraries/*;")
        pass

    def list(self, options):
        self.syncRegistry() 
        catalog = self.registry
        #prevent any hidden directories from populating list
        tmp = list(os.listdir(self.local))

        local_catalog = list()
        for d in tmp:
            if(self.isValidPackage(d)):
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
            isDownloaded = '-'
            info = ''

            ver = self.fetchVersion(pkg, True)
            if (downloadedList[pkg]):
                isDownloaded = 'y'
                loc_ver = ''
                loc_ver = self.fetchVersion(pkg, False)
                if((ver != '' and loc_ver == '') or (ver != '' and ver > loc_ver)):
                    info = '(update)-> '+ver
                    ver = loc_ver
            print("\t",'{:<24}'.format(pkg),'{:<14}'.format(isDownloaded),'{:<10}'.format(ver),info)
        print()
        pass

    def cleanup(self, pkg):
        if(not os.path.isfile(self.local+pkg+"/."+pkg+".yml")):
            print('No module '+pkg+' exists locally')
            return
        
        if(self.remote == None):
            print('WARNING- No remote code base is configured, if this module is deleted it may be unrecoverable.\n \
                DELETE '+pkg+'? [y/n]\
                ')
            response = ''
            while(True):
                response = input()
                if(response.lower() == 'y' or response.lower() == 'n'):
                    break
            if(response.lower() == 'n'):
                print(pkg+' not deleted')
                return
            #update registry if there is no remote 
            # (if there is a remote then the project still lives on, can be "redownloaded")
            self.syncRegistry(pkg, rm=True)
        
        #delete locally
        try:
            shutil.rmtree(self.local+pkg)
        except:
            print('No module '+pkg+' exists locally')
            return
            

        #delete the module remotely?
        pass

    def boot(self):
        with open(self.pkgPath+"."+self.pkgName+".yml", "r") as file:
            self.metadata = yaml.load(file, Loader=yaml.FullLoader)

        self.isValidProject = True

        if(self.metadata['derives'] == None):
            self.metadata['derives'] = dict()
        
        #TO-DO: unlock all dependency files to enable editing
        # unlock .yaml?
        if(len(self.metadata['derives']) > 0):
            if(not os.path.isdir(self.pkgPath+"libraries")):
                os.mkdir("libraries")
            os.system("chflags nouchg "+self.pkgPath+"libraries/*;")
        pass

    def createProject(self, package, options, description='Give a brief explanation here.'):
        #create a local repo
        
        c = caps.Capsule(package, True)
        self.projectName = self.pkgName = package
        print('here')
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
        self.syncRegistry(c)
        print('hehehe')
        return c
        pass

    def describe(self, phrase):
        self.metadata['summary'] = phrase
        pass

    def parse(self):
        #set class capsule variable for user settings
        caps.Capsule.settings = self.settings
        
        caps.Capsule.pkgmngPath = self.pkgmngPath
        #check if we are in a project directory (necessary to run a majority of commands)
        self.pkgPath = os.getcwd()
        lastSlash = self.pkgPath.rfind('/') #determine project's name to know the YAML to open
        self.pkgName = self.pkgPath[lastSlash+1:]
        self.pkgPath+='/'

        capsuleCWD = caps.Capsule(self.pkgName)
        if(not capsuleCWD.isValid()):
            print("NOT A CAPSULE DIRECTORY")
        

        command = ""
        package = ""
        options = []
        description = ''
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

        package = package.replace("-", "_")

        capsulePKG = caps.Capsule(package)

        if(len(options) > 1 and options[1] == 'i'):
            description = options[0]
            options.remove(options[0])
        elif(len(options) == 1):
            description = options[0]

        if(command == "install" and capsuleCWD.isValid()):
            self.install(package, options)
            pass
        elif(command == "uninstall" and capsuleCWD.isValid()):
            self.uninstall(package, options)
            pass
        elif(command == "new" and len(package)):
            cap = caps.Capsule(package, new=True)
            self.syncRegistry(cap)
            if(options.count("o") > 0):
                cap.load()
            pass
        elif(command == "upload" and capsuleCWD.isValid()):
            if(len(options) == 0):
                print("ERROR- please flag the next version for release with one of the following args:\n"\
                    "\t(-v0.0.0 | -maj | -min | -fix)")
                exit()
            
            ver = ''
            if(options[0][0] == 'v'):
                ver = options[0]
                print(ver)
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(release=str(ver), options=options)
            if(len(options) == 2 and options[1] == 'd'):
                self.cleanup(self.pkgName)
            pass
        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            self.download(capsulePKG)
            if('o' in options):
                capsulePKG.load()
            pass
        elif(command == "summary" and capsuleCWD.isValid()):
            capsuleCWD.getMeta()['summary'] = package
            capsuleCWD.push("Updates project summary")
            pass
        elif(command == 'del'):
            self.cleanup(package)
        elif(command == "list"):
            #a visual aide to help a developer see what package's are at the ready to use
            self.list(options)
            pass
        elif(command == "open"):
            capsulePKG.load()
            pass
        elif(command == "show"):
            if(capsulePKG.isValid()):
                capsulePKG.show()
            pass
        elif(command == "template" and self.settings['editor'] != None):
            os.system(self.settings['editor']+" "+self.pkgmngPath+"/template")
            pass
        elif(command == "set"):
            self.setSetting(options, package)
            pass
        elif(command == "help"):
            print("Command list\
            \n\tinstall <package> [-v0.0.0]\n\t\t-fetch package from the code base to be available in current project\
            \n\n\tuninstall <package>\n\t\t-remove package from current project along with all dependency packages\
            \n\n\tdownload <package> [-o]\n\t\t-pull package from remote code base for further development\
            \n\n\tupload <-v0.0.0 | -maj | -min | -fix>\n\t\t-release the next new version of package\
            \n\n\tupdate <package> [-all]\n\t\t-update developed package to be to the latest version\
            \n\n\tlist [-alpha -local]\n\t\t-print list of all packages available from code base\
            \n\n\topen <package> \n\t\t-opens the package with the set text-editor\
            \n\n\tdel <package> \n\t\t-deletes the package from the local code base\
            \n\n\tconvert <package> \n\t\t-converts the existing files with names containing <package> into a package format\
            \n\n\tsearch <package> [-local]\n\t\t-search remote (default) or local code base for specified package\
            \n\n\tshow <package> [-v0.0.0]\n\t\t-provide further detail into a specified package\
            \n\n\tports <package> [-v0.0.0]\n\t\t-print ports list of specified package\
            \n\n\tsummary \"description\"\n\t\t-add description to current project\
            \n\n\tnew <package> [-\"description\" -o -i <package> [-v0.0.0] , <package> [-v0.0.0] , ...]\n\t\t-create a standard empty package based on a template and pushes to remote code base\
            \n\n\tset <value/path> [-local | -remote | -editor | -author]\n\t\t-adjust package manager settings\
            \n\n\ttemplate\n\t\t-open the template in the configured text-editor to make custom configuration\
            \n")
            print("Optional flags\
            \n\t-v0.0.0\t\tspecify package version (insert values replacing 0's)\
            \n\t-i\t\tset installation flag to install package(s) on project creation\
            \n\t-alpha\t\talphabetical order\
            \n\t-o\t\topen the project\
            \n\t-warp\t\tremoves the released package from your local codebase\
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


def main():
    print('\n---legoHDL package manager---\n')
    legoHDL()


if __name__ == "__main__":
    main()
