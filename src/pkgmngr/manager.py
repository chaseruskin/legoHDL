#!/usr/bin/env python3
import os, sys, git, shutil
import collections, yaml
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
        self.local = os.path.expanduser(self.settings['local'])
        #defines how to open workspaces
        self.textEditor = self.settings['editor']
        self.parse()
        self.save()
        pass

    #returns a string to a package directory
    def findPath(self, package, remote=True, folder=''):
        pathway = self.remote
        subdir = ''
        if(not remote):
            pathway = self.local
        if(folder != ''):
            subdir = "/"+folder+"/"
        return pathway+"packages/"+package+subdir

    def syncRegistry(self, pkg=None, rm=False):
        msg = ''
        zero = '0.0.0'
        if(self.registry == None): # must check for changes
            if(self.remote != None):
                reg = git.Repo(self.local+"registry")
                reg.remotes.origin.pull(refspec='{}:{}'.format('master', 'master'))
            self.registry = dict()
            with open(self.local+"registry/db.txt", 'r') as file:
                for line in file.readlines():
                    m = line.find('=')
                    key = line[:m]
                    val = line[m+1:len(line)-1]
                    if(m != -1):
                        self.registry[key] = val
        if(pkg != None and rm == True): #looking to remove a value from the registry
            self.registry.pop(pkg, None)
            msg = 'Removes '+pkg+' from the database.'

        elif(pkg != None): #looking to write a value to registry
            if(pkg in self.registry and (self.registry[pkg] == self.metadata['version'] \
                or (self.metadata['version'] == zero))):
                return
            print('Syncing with registry...')
            self.registry[pkg] = self.metadata['version']
            if(self.registry[pkg] == ''):
                msg = 'Introduces '+self.pkgName+' to the database.'
            else:
                msg = 'Updates '+self.pkgName+' version to '+self.metadata['version']+'.'

        with open(self.local+"registry/db.txt", 'w') as file:
            for key,val in self.registry.items():
                if(val == zero):
                    val = ''
                file.write(key+"="+val+"\n")
        
        reg = git.Repo(self.local+"registry")
        reg.index.add('db.txt')
        reg.index.commit(msg)
        if(self.remote != None):
            reg.remotes.origin.push(refspec='{}:{}'.format('master', 'master'))
        pass


    def fetchVersion(self, package, remote=True):
        self.syncRegistry()
        ver = self.registry[package]
        if(not remote):
            with open(self.local+"packages/"+package+"/"+package+".yml", "r") as file:
                tmp_metadata = yaml.load(file, Loader=yaml.FullLoader)
            ver = tmp_metadata['version']
        if(ver == None):
            return ''
        else:
            return ver

    def uninstall(self, package, options):
        #does this module exist in this project's scope?
        if not package in self.metadata['dependencies']:
            print("ERROR- No installed module exists under the name \"",package,"\".",sep='')
            return

        version = self.metadata['dependencies'][package]
        print("\nUninstalling", package, "version:",version,"\b...\n")

        #delete file from dependency directory
        os.remove(self.projectPath+"/dependencies/"+package+".vhd")

        #update metadata of new removal
        del self.metadata['dependencies'][package]
        print("Successfully uninstalled ", package, " [",version,"] from the current project.",sep='')
        pass

    def install(self, package, options):
        #verify there is an existing module under this name
        if(not os.path.isdir(self.findPath(package))):
            print("ERROR- No module exists under the name \"",package,"\".",sep='')
            return
        
        if(not os.path.isdir(self.findPath(self.pkgName, False, 'dependencies'))):
            os.mkdir('dependencies')

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
        cmd = "cd "+self.remote+"packages/"+package+"; git checkout "+version+" -q;" #-q options silences git output
        error = os.system(cmd)
        if(error != 256):
            cmd = "cd "+self.remote+"packages/"+package+\
            "; cp ./design/* "+self.projectPath+"/dependencies/; git checkout - -q"
            os.system(cmd)
        else:
            print("ERROR- The version you are requesting for this module does not exist.")
            return

        #update metadata to list module under this project's dependency and compatible version
        self.metadata['dependencies'][package] = version
        
        print("Successfully installed ", package, " [",version,"] to the current project.",sep='')
        pass

    def download(self, package):
        self.syncRegistry()

        if(self.remote == None):
            print('No remote code base configured to download modules')
            return

        loc_catalog = os.listdir(self.local+"packages")

        if package in self.registry:
            if package in loc_catalog: #just give it an update!
                repo = git.Repo(self.local+"packages/"+package)
                repo.remotes.origin.pull(refspec='{}:{}'.format('master', 'master'))
            else: #oh man, go grab the whole thing!
                repo = git.Git(self.local+"packages/").clone(self.remote+package+".git")
        else:
            print('ERROR- Package \''+package+'\' does not exist in remote storage.')
        pass

    def load(self, package):
        cmd = self.textEditor+" "+self.local+"packages/"+package
        os.system(cmd)
        pass

    def upload(self, release=''):
        self.syncRegistry()

        repo = git.Repo(self.local+"packages/"+self.pkgName)
        print(release)
        if(release != ''):
            self.metadata['version'] = release[1:]
            repo.create_tag(release)

        if not self.pkgName in self.registry.keys():
            print("Uploading a new package to remote storage...")
            cmd = "git init; git add .; git commit -m \"Initial project creation.\"; git push --tags --set-upstream https://gitlab.com/chase800/"+self.pkgName+".git master"  
        elif self.remote != None:
            print("Updating remote package contents...")
            repo.remotes.origin.push()
        
        self.syncRegistry(self.pkgName)
        pass

    def setSetting(self, options, choice):
        if(len(options) != 1):
            print("ERROR- Invalid syntax; could not adjust setting")
            return

        if(options[0] == 'gl-token'):
            self.encrypt(choice, 'gl-token')
            return
        elif(options[0] == 'gh-token'):
            self.encrypt(choice, 'gh-token')
            return

        if(choice == ''):
            if(options[0] == 'remote'):
                print('WARNING- No remote code base is configured')
                choice = None
            elif(options[0] == 'local'):
                print('ERROR- Must include a local code base path')
                return
            elif(options[0] == 'editor'):
                choice = None

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
        tmp.move_to_end('dependencies')
        tmp.move_to_end('name', last=False)

        #a little magic to save YAML in custom order for easier readability
        with open(self.pkgPath+self.pkgName+".yml", "w") as file:
            while len(tmp):
                it = tmp.popitem(last=False)
                single_dict = {}
                single_dict[it[0]] = it[1]
                yaml.dump(single_dict, file)
                pass
            pass

        #lock all dependency files to disable editing
        #Linux: "chattr +i <file>"...macOS: chflags uchg <file>"
        if(len(self.metadata['dependencies']) > 0):
            os.system("chflags uchg "+self.pkgPath+"dependencies/*;")
        pass

    def list(self, options):
        self.syncRegistry() 
        catalog = self.registry
        #prevent any hidden directories from populating list
        tmp = list(os.listdir(self.local+"packages/"))
        local_catalog = list()
        for d in tmp:
            if(d[0] != '.'):
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
            print("\t",'{:<24}'.format(pkg),'{:<16}'.format(isDownloaded),'{:<10}'.format(ver),info)
        pass

    def cleanup(self, pkg):
        if(not os.path.isfile(self.local+"packages/"+pkg+"/"+pkg+".yml")):
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
            shutil.rmtree(self.local+"packages/"+pkg)
        except:
            print('No module '+pkg+' exists locally')
            return
            

        #delete the module remotely?
        pass

    def boot(self):
        with open(self.pkgPath+self.pkgName+".yml", "r") as file:
            self.metadata = yaml.load(file, Loader=yaml.FullLoader)

        self.isValidProject = True

        if(self.metadata['dependencies'] == None):
            self.metadata['dependencies'] = dict()
        
        #TO-DO: unlock all dependency files to enable editing
        # unlock .yaml?
        if(len(self.metadata['dependencies']) > 0):
            if(not os.path.isdir(self.pkgPath+"dependencies")):
                os.mkdir("dependencies")
            os.system("chflags nouchg "+self.pkgPath+"dependencies/*;")
        pass

    def createProject(self, package, options, description='Give a brief explanation here.'):
        #create a local repo
        self.pkgPath = self.local+"packages/"+package
        repo = None
        try:
            repo = git.Repo(self.pkgPath)
            print('Project already exists locally!')
            return
        except:
            if(self.remote != None):
                try: #if no error, that means the package exists on the remote!
                    repo = git.Git(self.local+"packages/").clone(self.remote+package+".git")
                    print('Project already exists on remote code base; downloading now...')
                    return
                except: 
                    pass
            else:
                print('No remote code bases to check from in settings')

            print('Initialzing new project...')
            shutil.copytree(self.pkgmngPath+"template/", self.pkgPath)
            repo = git.Repo.init(self.pkgPath)
            
            if(self.remote != None):
                repo.create_remote('origin', self.remote+package+".git") #attach to remote code base
            
        #run the commands to generate new project from template

        #file to find/replace word 'template'
        self.pkgPath+='/'
        file_swaps = [(self.pkgPath+'template.yml',self.pkgPath+package+'.yml'),(self.pkgPath+'design/template.vhd', self.pkgPath+'design/'+package+'.vhd'),
        (self.pkgPath+'testbench/template_tb.vhd', self.pkgPath+'testbench/'+package+'_tb.vhd')]
        for x in file_swaps:
            file_in = open(x[0], "r")
            file_out = open(x[1], "w")
            for line in file_in:
                file_out.write(line.replace("template", package))
            file_in.close()
            file_out.close()
            os.remove(x[0])

        self.projectName = self.pkgName = package
        print(self.pkgPath)
        print(options)
        self.boot()
        self.describe(description)

        installPkg = list()
        if 'i' in options:
            for opt in options[1:]:
                if(opt == ','):
                    self.install(installPkg[0], installPkg[1:])
                    installPkg.clear()
                else:
                    installPkg.append(opt)
            if(len(installPkg)): #perform last install
                self.install(installPkg[0], installPkg[1:])
        
        self.save()
        #initialize git repo
        repo.index.add(repo.untracked_files)
        repo.index.commit("Initializes project.")
        if(self.remote != None):
            print('Generating new remote repository...')
            repo.remotes.origin.push(refspec='{}:{}'.format('master', 'master'))
        else:
            print('No remote code base attached to local repository')

        #add and commit package name to registry repo
        self.syncRegistry(self.pkgName)
        pass

    def describe(self, phrase):
        self.metadata['description'] = phrase
        pass

    def show(self, package):
        if(package == ''):
            print('ERROR- please provide a package name to show!')
            return
        with open(self.local+"packages/"+package+"/"+package+".yml", 'r') as file:
            for line in file:
                print('\t',line,sep='',end='')
        pass

    def parse(self):
        #check if we are in a project directory (necessary to run a majority of commands)
        self.pkgPath = os.getcwd()
        lastSlash = self.pkgPath.rfind('/') #determine project's name to know the YAML to open
        self.pkgName = self.pkgPath[lastSlash+1:]
        self.pkgPath+='/'
        #try to read YAML
        try:
            self.boot()
        except:
            print('Not a package directory!')

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

        if(len(options) > 1 and options[1] == 'i'):
            description = options[0]
            options.remove(options[0])
        elif(len(options) == 1):
            description = options[0]

        if(command == "install" and self.isValidProject):
            self.install(package, options)
            pass
        elif(command == "uninstall" and self.isValidProject):
            self.uninstall(package, options)
            pass
        elif(command == "new" and len(package)):
            self.createProject(package, options, description)
            exit()
            pass
        elif(command == "upload" and self.isValidProject):
            ver = ''
            if(len(options)):
                ver = options[0]
            print(ver)
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(release=str(ver))
            if(len(options) == 2 and options[1] == 'd'):
                self.cleanup(self.pkgName)
            pass
        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            self.download(package)
            if('o' in options):
                self.load(package)
            pass
        elif(command == "describe"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            self.describe(package)
            pass
        elif(command == 'del'):
            self.cleanup(package)
        elif(command == "list"):
            #a visual aide to help a developer see what package's are at the ready to use
            self.list(options)
            pass
        elif(command == "open"):
            self.load(package)
            pass
        elif(command == "show"):
            self.show(package)
            pass
        elif(command == "set"):
            self.setSetting(options, package)
            pass
        elif(command == "help"):
            print("Command list\
            \n\tinstall <package> [-v0.0.0]\n\t\t-fetch package from the code base to be available in current project\
            \n\n\tuninstall <package>\n\t\t-remove package from current project along with all dependency packages\
            \n\n\tdownload <package> [-o]\n\t\t-pull package from remote code base for further development\
            \n\n\tupload [-v0.0.0 -d]\n\t\t-push package to remote code base to be available to others\
            \n\n\tupdate <package> [-all]\n\t\t-update local package to be to the latest version\
            \n\n\tlist [-alpha -local]\n\t\t-print list of all packages available from code base\
            \n\n\topen <package> \n\t\t-opens the package with the set text-editor\
            \n\n\tdel <package> \n\t\t-deletes the package from the local code base\
            \n\n\tconvert <package> \n\t\t-converts the existing files with names containing <package> into a package format\
            \n\n\tsearch <package> [-local]\n\t\t-search remote (default) or local code base for specified package\
            \n\n\tshow <package> [-v0.0.0]\n\t\t-provide further detail into a specified package\
            \n\n\tports <package> [-v0.0.0]\n\t\t-print ports list of specified package\
            \n\n\tdescribe \"description\"\n\t\t-add description to current project\
            \n\n\tnew <package> [-\"description\" -i <package> [-v0.0.0] , <package> [-v0.0.0] , ...]\n\t\t-create a standard empty package based on a template and pushes to remote code base\
            \n\n\tset [-local | -remote | -editor] <path>\n\t\t-adjust package manager settings\
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
            ")
        else:
            print("Invalid command; type \"help\" to see a list of available commands")
        pass


def main():
    print('\n---legoHDL package manager---\n')
    legoHDL()


if __name__ == "__main__":
    main()
