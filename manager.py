import os, sys
import yaml
import collections
import requests
from requests.auth import HTTPBasicAuth
#<ideas>

#movtivation behind building our own Hardware HDL manager:
#   -direct control and flexibility to design to meet our needs/worklfow/situation
#   -complete customization to tackle our problem of managing our modules
#   -promotes more experimentation => seeks to find the best solution (not trying to conform to other's standards)
#   -in-house so it doesn't rely on outsiders to maintain and improve

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

#seperate program/framework to perform lint, synth, simulation/verification, place-and-route, bitstream? 

#add pin mapping to YAML file to allow program to place-and-route design post-synthesis

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

        r = requests.get('https://gitlab.com/chase800/andgate/-/raw/master/AndGate.yml')
        #r = requests.get('https://raw.githubusercontent.com/c-rus/Bored-Bucket/main/Makefile')
        #r = requests.get('https://gitlab.com/chase800/andgate/-/raw/master/AndGate.yml')
        print(r.text)

        self.isValidProject = False
        self.path = ""
        self.projectName = ""
        self.projectPath = os.getcwd()
        
        self.metadata = None
        
        #defines path to working dir of 'legoHDL' tool
        self.pkgmngPath = os.path.realpath(__file__)
        lastSlash = self.pkgmngPath.rfind('/')
        self.pkgmngPath = self.pkgmngPath[:lastSlash]

        #defines path to dir of remote code base relative to 'legoHDL' tool
        self.remote = self.pkgmngPath+"/../remote/"

        self.local = self.pkgmngPath+"/../local/"

        self.parse()
        if(self.isValidProject):
            self.save()
        pass

    #returns a string to a package directory
    def pkgPath(self, package, remote=True, folder=''):
        pathway = self.remote
        subdir = ''
        if(not remote):
            pathway = self.local
        if(folder != ''):
            subdir = "/"+folder+"/"
        return pathway+"packages/"+package+subdir


    def fetchVersion(self, package, remote=True):
        tmp_metadata = None
        with open(self.pkgPath(package, remote)+"/"+package+".yml", "r") as file:
            tmp_metadata = yaml.load(file, Loader=yaml.FullLoader)
        if(tmp_metadata['version'] == None):
            return ''
        return tmp_metadata['version']

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
        if(not os.path.isdir(self.pkgPath(package))):
            print("ERROR- No module exists under the name \"",package,"\".",sep='')
            return
        
        if(not os.path.isdir(self.pkgPath(self.projectName, False, 'dependencies'))):
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
        catalog = os.listdir(self.remote+"packages")
        loc_catalog = os.listdir(self.local+"packages")
        cmd = ''

        if package in catalog:
            if package in loc_catalog:
                cmd =   'cd '+self.local+'packages/'+package+';'\
                        'git pull --tags '+self.remote+'/packages/'+package
            else:
                cmd =   'cd '+self.local+'packages; mkdir '+package+'; cd '+package+';\
                        git init; git pull --tags '+self.remote+'packages/'+package
            os.system(cmd)
        else:
            print('ERROR- Package \''+package+'\' does not exist in remote storage.')
        pass

    def upload(self, release=''):
        catalog = os.listdir(self.remote+"packages")
        cmd = ''

        if(release != ''):
            self.metadata['version'] = float(release[1:])
            os.system('git tag '+release)

        if not self.projectName in catalog:
            print("Uploading a new package to remote storage...")
            cmd = "git init; git add .; git commit -m \"Initial project creation.\"; git push --tags --set-upstream https://gitlab.com/chase800/"+self.projectName+".git master"  
        else:
            print("Updating remote package contents...")
            cmd ='git push --tags'
        #copy the local repo into the remote repo code base
        #option to give a version too on upload? 
        os.system(cmd)
        pass

    def save(self):
        #write back YAML info
        tmp = collections.OrderedDict(self.metadata)
        tmp.move_to_end('dependencies')
        tmp.move_to_end('name', last=False)

        #a little magic to save YAML in custom order for easier readability
        with open("./"+self.projectName+".yml", "w") as file:
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
            os.system("chflags uchg "+self.projectPath+"/dependencies/*;")
        pass

    def list(self, options):
        #default checks catalog of remote packages
        catalog = set(os.listdir(self.pkgPath('')))
        local_catalog = set(os.listdir(self.pkgPath('', False)))
        downloadedList = dict()
        
        for pkg in catalog:
            if(pkg in local_catalog):
                downloadedList[pkg] = True
            else:
                downloadedList[pkg] = False

        if(options.count('local')):
            catalog = local_catalog
        if(options.count('alpha')):
            catalog = sorted(catalog)
        
        print("\nList of available modules:")
        print("\tModule\t\t\tlocal\t\tversion")
        print("-"*80)
        for pkg in catalog:
            isDownloaded = '-'
            info = ''

            ver = self.fetchVersion(pkg)
            if (downloadedList[pkg]):
                isDownloaded = 'y'
                loc_ver = self.fetchVersion(pkg, False)
                if((ver != '' and loc_ver == '') or (ver != '' and ver > loc_ver)):
                    info = '(update available)'
                    ver = self.fetchVersion(pkg, False)

            print("\t",pkg,"\t\t",isDownloaded,"\t\t",ver,"\t",info)
        pass

    def boot(self):
        with open("./"+self.projectName+".yml", "r") as file:
            self.metadata = yaml.load(file, Loader=yaml.FullLoader)

        self.isValidProject = True

        if(self.metadata['dependencies'] == None):
            self.metadata['dependencies'] = dict()
        
        #unlock all dependency files to enable editing
        #Linux: "chattr -i <file>"...macOS: chflags nouchg <file>"
        if(len(self.metadata['dependencies']) > 0):
            if(not os.path.isdir(self.local+"packages/"+self.projectName+"/dependencies")):
                os.mkdir("dependencies")
            os.system("chflags nouchg "+self.projectPath+"/dependencies/*;")
        pass

    def createProject(self, package, options, description):
        if(os.path.isdir(self.remote+package)):
                print("ERROR- That project already exists!\
                \n\tDownload it from the remote codebase by using \'legoHDL download "+package+"\' or find it on your\
                \n\tlocal codebase.\
                    ")
                return
        #run the commands to generate new project from template
        cmd =   "cd "+self.remote+"packages; mkdir "+package+";\
                cp -R "+self.pkgmngPath+"/template/ "+"./"+package+";\
                "
        os.system(cmd)
        dirr = self.remote+'packages/'+package+'/'
        #file to find/replace word 'template'
        file_swaps = [(dirr+'template.yml',dirr+package+'.yml'),(dirr+'design/template.vhd', dirr+'design/'+package+'.vhd'),
        (dirr+'testbench/template_tb.vhd', dirr+'testbench/'+package+'_tb.vhd')]
        for x in file_swaps:
            file_in = open(x[0], "r")
            file_out = open(x[1], "w")
            for line in file_in:
                file_out.write(line.replace("template", package))
            file_in.close()
            os.remove(x[0])
            file_out.close()

        self.projectPath = self.local + 'packages/' + package
        self.projectName = package
        print(self.projectPath)
        os.chdir(self.remote+'packages/'+package)
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
        cmd = "git init; git add .; git commit -m \"Initial project creation.\"; git push --tags --set-upstream https://gitlab.com/chase800/"+self.projectName+".git master"
        os.system(cmd)
        pass

    def describe(self, phrase):
        self.metadata['description'] = phrase
        pass

    def show(self, package):
        if(package == ''):
            print('ERROR- please provide a package name to show!')
            return
        with open(self.pkgPath(package)+"/"+package+".yml", 'r') as file:
            for line in file:
                print('\t',line,sep='',end='')
        pass

    def parse(self):
        #check if we are in a project directory (necessary to run a majority of commands)
        self.path = os.getcwd()
        lastSlash = self.projectPath.rfind('/') #determine project's name to know the YAML to open
        self.projectName = self.projectPath[lastSlash+1:]
        #read YAML
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
                if(arg[0] == '-'):
                    options.append(arg[1:])
                elif(len(options) and options[0] == 'd'):
                    description = arg
                    options.pop()
                elif(len(options) and options[0] == 'i'):
                    options.append(arg)
                else:
                    package = arg

        if(command == "install" and self.isValidProject):
            self.install(package, options)
            pass
        elif(command == "uninstall" and self.isValidProject):
            self.uninstall(package, options)
            pass
        elif(command == "new" and len(package)):
            self.createProject(package, options, description)
            self.download(package)
            exit()
            pass
        elif(command == "upload" and self.isValidProject):
            #upload is used when a developer finishes working on a project and wishes to push it back to the
            # remote codebase (all CI should pass locally before pushing up)
            self.upload(package)
            pass
        elif(command == "download"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            self.download(package)
            pass
        elif(command == "describe"):
            #download is used if a developer wishes to contribtue and improve to an existing package
            self.describe(package)
            pass
        elif(command == "list"):
            #a visual aide to help a developer see what package's are at the ready to use
            self.list(options)
            pass
        elif(command == "show"):
            self.show(package)
            pass
        elif(command == "help"):
            print("List of commands\
            \n\tinstall <package> [-v]\n\t\t-fetch package from the code base to be available in current project\
            \n\tuninstall <package>\n\t\t-remove package from current project along with all dependency packages\
            \n\tdownload <package> [-o]\n\t\t-pull package from remote code base for further development\
            \n\tupload <package> [-dismiss]\n\t\t-push package to remote code base to be available to others\
            \n\tupdate <package> [-all]\n\t\t-download available package to be updated to latest version\
            \n\tlist [-alpha -local]\n\t\t-print list of all packages available from code base\
            \n\tsearch <package> [-local]\n\t\t-search remote (default) or local code base for specified package\
            \n\tdetails <package> [-v]\n\t\t-provide further detail into a specified package\
            \n\tports <package> [-v]\n\t\t-print ports list of specified package\
            \n\tdescribe \"short description\"\n\t\t-add description to current project\
            \n\tnew <package> [-d \"description\" -i <package> [-v] , <package> [-v] , ...]\n\t\t-create a standard empty package based on a template and pushes to remote code base\
            \n")
            print("Optional flags\
            \n\t-v\t\tspecify what version (semantic versioning -v0.0)\
            \n\t-i\t\tset installation flag to install package(s) on project creation\
            \n\t-alpha\t\talphabetical order\
            \n\t-o\t\topen the project\
            \n\t-dismiss\tremove package from your local codebase\
            \n\t-local\t\tfilter set to packages located on your local code base\
            ")
        else:
            print("Invalid command; type \"help\" to see a list of available commands")
        pass


def main():
    print('\n---legoHDL package manager---\n')
    legoHDL() #create instance


if __name__ == "__main__":
    main()