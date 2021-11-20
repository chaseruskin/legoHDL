# Project: legohdl
# Script: legohdl.py
# Author: Chase Ruskin
# Description:
#   This script is the entry-point to the legohdl program. It parses the
#   command-line arguments and contains a method for each valid command.

import os, sys, shutil
import logging as log

from .__version__ import __version__

from .apparatus import Apparatus as apt
from .cfgfile import CfgFile as cfg

from .block import Block
from .map import Map
from .unit import Unit
from .gui import GUI
from .test import main as test
from .market import Market
from .workspace import Workspace
from .profile import Profile
from .script import Script
from .label import Label
from .git import Git


class legoHDL:

    
    def __init__(self):
        '''
        Initialize the legoHDL tool. 
        
        This method specifically parses the command line arguments, loads tool-wide settings, 
        and initializes the registry.

        Parameters:
            None
        Returns:
            None
        '''
        #load the logging format
        log.basicConfig(format='%(levelname)s:\t%(message)s', level=log.INFO)

        #parse arguments
        self._command = self._item = ""
        #store args accordingly from command-line
        for i, arg in enumerate(sys.argv[1:]):
            #first is the command
            if(i == 0):
                self._command = arg.lower()
            #next is the "item" (may not be used for all commands)
            elif(i == 1):
                self._item = arg
            else:
                break

        #only display the program's version and exit
        if(self._command == '--version'):
            print(__version__)
            exit()

        #parse any remaining arguments
        self.parseArgs(sys.argv[1:])

        #load legohdl.cfg
        #ensure all necessary hidden folder structures exist
        intial_setup = apt.initialize()
        if(intial_setup):
            self.runSetup()

        apt.load()
        #initialize all Markets
        Market.load()
        Market.tidy()
        #initialize all Workspaces
        Workspace.load()
        Workspace.setActiveWorkspace(apt.SETTINGS['general']['active-workspace'])
        Workspace.tidy()
        #initialize all Profiles
        Profile.load()
        Profile.tidy()

        #save all legohdl.cfg changes
        apt.save()
        Workspace.save()

        #limit functionality if not in a workspace
        if(not Workspace.inWorkspace()):
            if(self._command == '' or \
                self._command == 'config' or \
                self._command == 'help' or \
                self._command == 'open' and (self.hasFlag('settings') or self.hasFlag('template'))):
                pass
            else:
                exit(log.error("Failed to run command because active workspace is not set."))
        else:
            self.WS().autoRefresh(rate=apt.getRefreshRate())

        #print(self)

        if('debug' == self._command):
            test()
        else:
            self.runCommand()
        pass


    def parseArgs(self, args):
        '''
        Creates a dictionary of arguments separated into 'flags' and 'vars'.

        Parameters:
            args ([str]): list of arguments to identify
        Returns:
            None
        '''
        self._flags = []
        self._vars = Map()

        for arg in args:
            #a flag/var begins with a '-' character
            if(arg[0] == '-' and len(arg) > 1):
                #a pair has a '=' character
                if(arg.find('=') > -1):
                    #find the first '=' and partition into key,value
                    eq_i = arg.find('=')
                    key, val = arg[1:eq_i], arg[eq_i+1:]
                    arg = '-'+key #update value to put into flags list
                    self._vars[key] = val
                #store lower-case of flag for evaluation purposes
                self._flags.append(arg[1:].lower())
                pass
        pass


    def WS(self):
        'Returns the active workspace.'
        return Workspace.getActive()


    def getVar(self, key):
        '''
        Get the value for the desired key. Returns None if DNE.
        
        Parameters:
            key (str): var's key
        Returns:
            val (str):
        '''
        if(key.lower() in self._vars.keys()):
            return self._vars[key]
        else:
            return None

    
    def getVerNum(self, places=[1,3]):
        '''
        Get the version from the version flag (if one was passed). Searches 
        flags for a valid version. Returns None if not found. 
        
        Parameters:
            places ([int]): the different places to test against
        Returns:
            _ver (str): valid version format (v0.0.0)
        '''
        if(hasattr(self, '_ver')):
            return self._ver

        self._ver = None
        #search through all flags
        for f in self._flags:
            if(Block.validVer(f, places=places)):
                self._ver = Block.stdVer(f)
                break

        return self._ver

    
    def getItem(self, raw=False):
        '''
        Get the value of the item argument. Returns None if item is empty
        string or item is a flag.

        Parameters:
            raw (bool): determine if to strictly return item
        Returns:
            (str): the item passed into legohdl
        '''
        it = self._item
        if(raw):
            return it
        #get the flag name if an '=' was used on the flag
        eq_i = len(it)
        if(it.count('=')):
            eq_i = it.find('=')
        #make sure the item is not a flag
        if(len(it) and it[1:eq_i].lower() in self._flags):
            it = None
        #make sure the item is not a blank string
        if(it == ''):
            it = None
        return it


    def hasFlag(self, flag):
        '''
        See if the flag is found within _flags.

        Parameters:
            flag (str): flag
        Returns:
            (bool): determine if flag is in _flags
        '''
        return (self._flags.count(flag) > 0)


    def checkVar(self, key, val):
        '''
        Checks if val equals the value stored behind the key in the
        _vars map. Returns false if key DNE.
        
        Parameters:
            key (str): key to check value behind in _vars
            val (str): value to compare with
        Returns:
            (bool): if val was equal to key's value in _vars
        '''
        if(key not in self._vars.keys()):
            return False
        else:
            return val == self._vars[key]

    
    def splitVar(self, val, delim=':'):
        '''
        Splits the value of the variable into two parts based
        on the delimiter. Returns '' for second component if delim DNE.

        Parameters:
            val (str): the variable value
            delim (str): the substring to find in val
        Returns:
            key (str): first component of val
            val (str): second component of val
        '''
        d_i = val.find(delim)
        if(d_i > -1):
            return val[0:d_i], val[d_i+1:]
        else:
            return val, ''


    def runSetup(self):
        is_select = apt.confirmation("This looks like your first time running \
legoHDL! Would you like to use a profile (import settings, template, and \
scripts)?", warning=False)
        if(is_select):
            #give user options to proceeding to load a profile
            resp = input("""Enter:
1) nothing for default profile
2) a path or git repository to a profile
3) 'exit' to cancel configuration
""")
            #continually prompt until get a valid response to move forward
            while True:
                if(resp.lower() == 'exit'):
                    log.info('Profile configuration skipped.')
                    break
                elif(resp == ''):
                    log.info("Setting up default profile...")
                    Profile.reloadDefault(importing=True)
                    break
                else:
                    p = Profile('', url=resp)
                    if(p.successful()):
                        p.importLoadout()
                        break
                resp = input()
                pass
        #decided to not run setup prompt or we have no workspaces
        if(not is_select or len(apt.SETTINGS['workspace'].keys()) == 0):
            #ask to create workspace
            ws_name = input("Enter a workspace name: ")
            while(len(ws_name) == 0 or ws_name.isalnum() == False):
                ws_name = input()
            ws_path = input("Enter a workspace path: ")
            while(len(ws_name) == 0):
                ws_path = input()
            Workspace(ws_name, ws_path)
            
        #ask for name to store in settings
        feedback = input("Enter your name: ")
        if(feedback.strip() != cfg.NULL):
            apt.setAuthor(feedback.strip())

        alter_editor = True
        #display what the current value is for the text-editor
        if(len(apt.getEditor())):
            alter_editor = apt.confirmation("Text editor is currently set to: \
                \n\n\t"+apt.getEditor()+"\n\nChange?",warning=False)
        #ask for text-editor to store in settings
        if(alter_editor):
            feedback = input("Enter your text-editor: ")
            if(feedback.strip() != cfg.NULL):
                apt.setEditor(feedback.strip())
        pass


    def _build(self):
        '''Run the 'build' command.'''

        cur_block = Block(os.getcwd(), self.WS())
        #make sure within a valid block directory
        if(cur_block.isValid() == False):
            log.error("Cannot call a script from outside a block directory!")
            return
        #initialize all Scripts
        Script.load()
        #get the script name
        script = self.getItem()
        #make sure a valid script title is passed
        if(script == None or script[0] != '+'):
            log.error("Calling a script must begin with a '+'!")
            return
        #make sure the script exists
        elif(script[1:].lower() not in Script.Jar.keys()):
            log.error("Script "+script[1:]+" does not exist!")
            return
        #find index where build script name was called
        script_i = sys.argv.index(script)
        #all arguments after script name are passed to the script
        script_args = sys.argv[script_i+1:]

        Script.Jar[script[1:]].execute(script_args)
        pass


    def _graph(self):
        '''Run the 'graph' command.'''

        inc_tb = (self.hasFlag('ignore-tb') == False)

        self.WS().loadBlocks(id_dsgns=True)
        block = Block.getCurrent()

        #capture the passed-in entity name
        top = self.getItem()
        #capture the command-line testbench
        explicit_tb = self.getVar('tb')

        top_dog,_,_ = block.identifyTopDog(top, expl_tb=explicit_tb, inc_tb=inc_tb)
        
        log.info("Generating dependency tree...")

        #start with top unit (returns all units if no top unit is found (packages case))
        block.getUnits(top_dog)

        hierarchy = Unit.Hierarchy
        
        #print the dependency tree
        print(hierarchy.output(top_dog, compress=self.hasFlag('compress')))
        print()
        
        unit_order,block_order = hierarchy.topologicalSort()

        print('---  BLOCK ORDER   ---')
        block_order.reverse()
        for i in range(0, len(block_order)):
            b = block_order[i]
            print('['+str(len(block_order)-i)+']^-\t'+b.getFull(inc_ver=True),end='\n')
        print()

        return unit_order,block_order


    def _export(self):
        '''Run the 'export' command.'''

        verbose = (self.hasFlag('quiet') == False)
        inc_tb = (self.hasFlag('ignore-tb') == False)

        #load labels
        Label.load()
        #load blocks and their designs
        self.WS().loadBlocks(id_dsgns=True)

        #get the working block
        block = Block.getCurrent()

        #trying to export a package file?
        if(self.hasFlag('pack')):
            #reads lists 'omit' and 'inc' from command-line
            self.autoPackage(omit=apt.strToList(self.getVar('omit')), \
                inc=apt.strToList(self.getVar('inc')), \
                filepath=self.getVar('pack'))
            return
     
        #capture the passed-in entity name
        top = self.getItem()
        #capture the command-line testbench
        explicit_tb = self.getVar('tb')

        top_dog,dsgn,tb = block.identifyTopDog(top, expl_tb=explicit_tb, inc_tb=inc_tb, verbose=verbose)

        #get all units
        if(self.hasFlag('all')):
            block.getUnits()
            pass
        #get only necessary units
        else:
            #start with top unit (returns all units if no top unit is found (packages case))
            block.getUnits(top_dog)
            if(verbose):
                Unit.Hierarchy.output(top_dog)
            pass

        unit_order,block_order = Unit.Hierarchy.topologicalSort()

        #store the text lines to write to the blueprint file
        blueprint_data = []

        #store what files each block's version has added to the blueprint
        block_files = Map()

        #get all label data from blocks
        for b in block_order:
            block_key = b.getFull(inc_ver=True)
            #create new keyslot for this block
            if(block_key not in block_files.keys()):
                block_files[block_key] = []
            #iterate through every label
            for lbl in Label.Jar.values():
                #get global labels from external blocks
                if(lbl.isGlobal() == True):
                    #gather files with specific label extension
                    path = None
                    #if partial version check its specific version path
                    if(b.getLvl(to_int=False) == Block.Level.VER):
                        root,_ = os.path.split(b.getPath()[:len(b.getPath())-1])
                        path = root+'/v'+b.getVersion()+'/'

                    paths = b.gatherSources(ext=lbl.getExtensions(), path=path)
                    #add every found file identified with this label to the blueprint
                    for p in paths:
                        #only add files that have not already been added for this block's version
                        if(p in block_files[block_key]):
                            continue
                        #add label and file to blueprint data
                        blueprint_data += ['@'+lbl.getName()+' '+p]
                        #note this file as added for this block's version
                        block_files[block_key] += [p]
                    pass
                #perform local-only label searching on current block
                if(b == block_order[-1]):
                    if(lbl.isGlobal() == False):
                        paths = block.gatherSources(ext=lbl.getExtensions())
                        #add every found file identified with this label to the blueprint
                        for p in paths:
                            blueprint_data += ['@'+lbl.getName()+' '+p]
                pass
            pass

        blueprint_data += self.compileList(block, unit_order)

        #write top-level testbench entity label
        if(tb != None and inc_tb):
            line = '@'
            if(tb.getLang() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(tb.getLang() == Unit.Language.VERILOG):
                line = line+"VLOG"
            #set simulation design unit by its entity name by default
            tb_name = tb.E()
            #set top bench design unit name by its configuration if exists
            if(tb.getConfig() != None):
                tb_name = tb.getConfig()
            #add to blueprint's data for top-level testbench
            blueprint_data += [line+"-SIM-TOP "+tb_name+" "+tb.getFile()]

        #write top-level design entity label
        if(dsgn != None):
            line = '@'
            if(dsgn.getLang() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(dsgn.getLang() == Unit.Language.VERILOG):
                line = line+"VLOG"
            #add to blueprint's data for top-level design
            blueprint_data += [line+"-SRC-TOP "+dsgn.E()+" "+dsgn.getFile()]
        
        build_dir = block.getPath()+apt.getBuildDirectory()

        #clean the build directory
        if(self.hasFlag('no-clean') == False):
            if(verbose):
                log.info("Cleaning build folder...")
            if(os.path.isdir(build_dir)):
                shutil.rmtree(build_dir, onerror=apt.rmReadOnly)
            pass

        #create the build directory
        os.makedirs(build_dir, exist_ok=True)

        if(verbose):
            log.info("Exporting blueprint...")
        
        #create the blueprint file
        blueprint_path = build_dir+"blueprint"
        blueprint = open(blueprint_path, 'w')

        #write all data to the blueprint
        for line in blueprint_data:
            blueprint.write(line+'\n')

        if(verbose):
            log.info("Blueprint found at: "+blueprint_path)

        #update block's dependencies
        block.updateRequires(quiet=(verbose == False))
        pass


    def autoPackage(self, filepath=None, omit=[], inc=[]):
        '''
        Auto-generate a VHDL package file for design units within the current block.

        By default, all available entities within the project are to be written
        as components in the VHDL package.

        If 'filepath' is None, then the default is the <project>_pkg.vhd at the
        block's root.
        
        Parameters:
            filepath (str): the optional relative filepath + filename
            omit ([str]): list of entity names to not include in package file
            inc ([str]): list of entity names to explicitly include in package file.
        Returns:
            None
        '''
        #get the current working block
        block = Block.getCurrent()
        #set the default package name
        pkg_name = (block.N()+"_pkg").replace('-','_')
        pkg_ext = '.vhd'
        extra_path = ''

        #override the default package name, file path, and extension
        if(filepath != None):
            extra_path,file_name = os.path.split(filepath)
            pkg_name,pkg_ext = os.path.splitext(file_name)

        #list of units to wrap in package file
        comp_names = []

        log.info("Exporting VHDL package file "+pkg_name+".vhd...")

        #get all unit objects
        unit_names = block.loadHDL().values()
        #iterate through project-level units
        for u in unit_names:
            #only add design units (entities)... skip others
            if(u.isTb() == True or u.isPkg() == True):
                continue
            #abide by the explicit include list (overrides exclude list)
            if(len(inc)):
                if(u.E().lower() in inc):
                    comp_names += [u.E()]
                continue
            #skip any explicitly excluded design units
            elif(u.E().lower() in omit):
                continue
            #add component name to the list to be implemented
            comp_names += [u.E()]
            pass
        #print(comp_names)

        #initially fill with comment header section
        pkg_data = ['-'*80] + \
            ['-- Project: %BLOCK%'] + \
            ['-- Created: %DATE%'] + \
            ['-- Package: TEMPLATE'] + \
            ['-- Description:'] + \
            ['--  Auto-generated package file by legoHDL. Components declared:'] + \
            [apt.listToGrid(comp_names, min_space=4, offset='--  \t')] + \
            ['-'*80] + \
            [' ']

        #calculate the package comment header lines length
        comment_len = len(pkg_data)

        #place package declaration
        pkg_data += [' '] + \
            ['package '+pkg_name+' is'] + \
            [' ']

        libs = []
        #track what libraries are needed from the 'use' packages
        libs_from_pkgs = []
        pkgs = []
        #get all units
        units = list(block.loadHDL().values())
        for dsgn in units:
            #only add design units (entities)
            if(dsgn.isTb() or dsgn.isPkg()):
                continue
            #only add designs that are in 'comp_names' list
            if(dsgn.E() not in comp_names):
                continue
            #copy any of their package declarations
            for pkg in dsgn.getPkgs():
                #ensure package has not already been added
                if(pkg.lower() not in pkgs):
                    #ensure package is not itself (cast to lower_case for evaluation)
                    pkg_parts = pkg.lower().split('.')
                    #skip if package is itself
                    if(len(pkg_parts) > 1 and pkg_parts[0] == 'work' and pkg_parts[1] == pkg_name.lower()):
                        continue
                    pkg_data.insert(comment_len+len(libs), 'use '+pkg+';')
                    pkgs += [pkg.lower()]
                    #add to list of libraries that will need to be included
                    libs_from_pkgs += [pkg_parts[0]]
            #copy any of their library declarations
            for lib in dsgn.getLibs():
                if(lib.lower() not in libs and lib.lower() in libs_from_pkgs):
                    pkg_data.insert(comment_len, 'library '+lib+';')
                    libs += [lib.lower()]

            #add component declaration
            pkg_data += [dsgn.getInterface().writeDeclaration(form=Unit.Language.VHDL, \
                align=apt.getField(['HDL-styling', 'auto-fit'], bool), \
                hang_end=apt.getField(['HDL-styling', 'hanging-end'], bool), \
                tabs=1)]
            #add newline
            pkg_data += [' ']
            pass
            
        pkg_data += ['end package;']

        #create package file
        pkg_path = apt.fs(block.getPath()+extra_path)
        #make sure directories exist
        os.makedirs(pkg_path, exist_ok=True)
        #add filename to the path
        pkg_path = pkg_path + pkg_name + pkg_ext
        #open the file to write the data
        pkg_file = open(pkg_path, 'w')

        #dump contents into package file
        for line in pkg_data:
            pkg_file.write(line+"\n")
        pkg_file.close()

        #fill placeholders
        block.fillPlaceholders(pkg_path, pkg_name)

        log.info("VHDL package file found at: "+pkg_path)
        pass


    def compileList(self, block, unit_order):
        '''
        Formats units with their file into the blueprint structure with respective labels.

        Parameters:
            block (Block): the current working block object
            unit_order ([Unit]): in-order list of units to synthesize
        Returns:
            data ([str]): list of lines for blueprint file
        '''
        data = []
        #iterate through each unit
        for dsgn in unit_order:
            line = '@'
            if(dsgn.getLang() == Unit.Language.VHDL):
                line = line+"VHDL"
            elif(dsgn.getLang() == Unit.Language.VERILOG):
                line = line+"VLOG"
            #this unit comes from an external block so it is a library file
            if(dsgn not in list(block.loadHDL().values())):
                line = line+'-LIB '+dsgn.L()+' '
            #this unit is a simulation file
            elif(dsgn.isTb()):
                line = line+'-SIM '
            #this unit is a source file
            else:
                line = line+'-SRC '
            #append file onto line
            line = line + dsgn.getFile()
            #add to blueprint list
            data.append(line)

        return data

    
    def _get(self):
        '''Run the 'get' command.'''

        visibles = self.WS().loadBlocks(id_dsgns=True)

        #make sure an entity is being requested
        if(self.getItem() == None):
            exit(log.error("Pass a unit name to get."))

        #verify a block under this name exists
        block = self.WS().shortcut(self.getItem(), req_entity=True, visibility=True)
        if(block == None):
            exit(log.error("Could not identify a block for unit "+self.getItem()+'.'))

        #remember title for error statement in case block becomes None
        title = block.getFull()
        #verify the block is visible to the user
        if(apt.getMultiDevelop() == False and block != Block.getCurrent(bypass=True)):
            block = block.getLvlBlock(Block.Level.INSTL)
          
        if(block not in visibles):
            if(apt.getMultiDevelop() == False):
                exit(log.error("Cannot use "+title+" because it is not installed!"))
            else:
                exit(log.error("Cannot use "+title+" because it is not downloaded or installed!"))

        #fill in all units if running 'edges' flag
        if(self.hasFlag('edges')):
            self.WS().decodeUnits()

        #get the entity name
        _,_,_,_,ent = Block.snapTitle(self.getItem(), inc_ent=True)

        #get what language was defined by the command-line ('inst' has high precedence
        #than 'comp')
        lang = self.getVar('inst')
        if(lang == None):
            lang = self.getVar('comp')

        #print the relevant information for the requested unit
        block.get(entity=ent, about=self.hasFlag('about'), \
                        list_arch=self.hasFlag('arch'), \
                        inst=self.hasFlag('inst'), \
                        comp=self.hasFlag('comp'), \
                        lang=lang, \
                        edges=self.hasFlag('edges')
                    )
        pass


    def _init(self):
        '''Run the 'init' command.'''

        cur_path = apt.fs(os.getcwd())
        #try to create a block at the current working directory
        block = Block(cur_path, self.WS())
        #intialize block attributes/itself
        block.initialize(self.getItem(), self.getVar('remote'), self.hasFlag('fork'), self.getVar('summary'))
        pass


    def _install(self):
        '''Run the 'install' command.'''

        #load blocks
        self.WS().loadBlocks()

        #shortcut name
        block = self.WS().shortcut(self.getItem(), visibility=False)

        if(block == None):
            log.error("Could not identify a block with "+self.getItem()+'.')
            return

        #recursively install each requirement
        if(self.hasFlag('requirements')):
            block.installReqs()
            return

        #first check if the block is found in install
        instl = block.getLvlBlock(Block.Level.INSTL)

        ver_num = self.getVerNum(places=[3])

        #install latest/controller for this block
        if(instl == None or Block.cmpVer(instl.V(), block.V()) != instl.V()):
            if(instl != None):
                instl.delete()
            instl = block.install()
            pass
        elif(ver_num == None):
            log.info("The latest version for "+instl.getFull()+" is already installed.")
        
        #install specific version if specifed
        if(instl != None and ver_num != None):
            instl.install(ver=self.getVerNum())

        pass

    
    def _uninstall(self):
        '''Run the 'uninstall' command.'''

        #load blocks
        self.WS().loadBlocks()
        #shortcut name
        block = self.WS().shortcut(self.getItem(), visibility=False)
        #check if block exists
        if(block == None):
            exit(log.error("Could not identify a block with "+self.getItem()+'.'))

        success = block.uninstall(self.getVerNum(places=[1,2,3]))

        if(success):
            log.info("Success.")
        pass

    
    def _info(self):
        '''Run the 'info' command.'''
        
        if(self.hasFlag('profile')):
            #make sure the requested profile exists to be read
            if(self.getItem() not in Profile.Jar.keys()):
                log.error("Profile "+self.getItem()+" does not exist!")
                return
            #print the profile's information
            print('\n'+Profile.Jar[self.getItem()].readAbout()+'\n')
            return

        #get the block object from all possible blocks
        block = self.WS().shortcut(self.getItem(), visibility=False)

        #make sure the user passed in a value for the item
        if(block == None):
            exit(log.error("Could not find a block as "+self.getItem()))

        #check which block to use
        title = block.getFull()
        #wishing to pull in information on the downloaded block
        if(self.hasFlag('d')):
            block = block.getLvlBlock(Block.Level.DNLD)
            #no download to read from
            if(block == None):
                log.error("Block "+title+" is not downloaded to the workspace path!")
                return
            pass
        #wishing to pull in information on the installed block
        elif(self.hasFlag('i') or self.getVerNum(places=[1,2,3]) != None):
            block = block.getLvlBlock(Block.Level.INSTL)
            #no installation to read from
            if(block == None):
                log.error("Block "+title+" is not installed to the cache!")
                return

            #check if needed a specific version to get info about
            if(self.getVerNum() != None):
                ver = Block.stdVer(self.getVerNum(), add_v=True)
                #try to find block object associated with speciifc version
                if(ver in block.getInstalls().keys()):
                    block = block.getInstalls()[ver]
                #could not identify specific version
                else:
                    log.error("Version "+ver+" may not exist or be installed to the cache!")
                    return
                pass
            pass
        #wishing to get information from metadata found in this block's market
        elif(self.hasFlag('a')):
            block = block.getLvlBlock(Block.Level.AVAIL)
            #no download to read from
            if(block == None):
                log.error("Block "+title+" is not available in a market!")
                return
            pass

        print(block.readInfo(self.hasFlag('stats'), \
            versions=self.hasFlag('vers'), \
            ver_range=self.getVar('vers')))
        pass


    def _config(self):
        '''Run 'config' command.'''

        #import a profile if a profile name is given as item.
        if(self.getItem(raw=True) in Profile.Jar.keys()):
            Profile.Jar[self.getItem(raw=True)].importLoadout(ask=self.hasFlag('ask'))
            return

        #set each setting listed in flags try to modify it
        for k,v in self._vars.items():
            #split the variable into two components (if applicable)
            var_key, var_val = self.splitVar(v)
            #print(var_key, var_val)
            #modify script
            if(k == 'script'):
                #load in script
                Script.load()
                #verify proper format is passed in
                if(var_key == ''):
                    log.error("Must provide a script alias.")
                    continue

                #check if the value has the ENV word in it to replace
                var_val = var_val.replace(apt.ENV_NAME, apt.HIDDEN)

                #modify existing script
                if(var_key.lower() in Script.Jar.keys()):
                    Script.Jar[var_key].setCommand(var_val)
                #create a new script
                else:
                    Script(var_key, var_val)

                #save script modifications
                Script.save()
                pass
            #modify label
            elif(k == 'label'):
                #load labels
                Label.load()
                #verify proper format is passed in
                if(var_key == ''):
                    log.error("Must provide a label name.")
                    continue

                #modify existing label
                if(var_key.lower() in Label.Jar.keys()):
                    Label.Jar[var_key].setExtensions(apt.strToList(var_val))
                    Label.Jar[var_key].setGlobal(self.hasFlag('global'))
                #create new label
                else:
                    Label(var_key, apt.listToStr(var_val), self.hasFlag('global'))
                #save any changes
                Label.save()
                pass
            #modify profile
            elif(k == 'profile'):
                #try to create a profile!
                if(v != ''):
                    #try url
                    if(Git.isValidRepo(v, remote=True) or Git.isValidRepo(v, remote=False)):
                        Profile('', url=v)
                    #try just new name
                    elif(v.lower() not in Profile.Jar.keys()):
                        if(v.lower() == 'default'):
                            Profile.reloadDefault()
                        else:
                            log.info("Creating new empty profile "+v+"...")
                            Profile(v)
                    else:
                        log.error("Profile "+v+" already exists.")
                        continue
                    
                Profile.save()
                pass
            #modify market
            elif(k == 'market'):
                #ensure a market name is given
                if(var_key == ''):
                    log.error("Must provide a market name.")
                    continue

                mrkt = None
                #modify an existing market
                if(var_key.lower() in Market.Jar.keys()):
                    mrkt = Market.Jar[var_key]

                    #if its local and remote given try to set a remote
                    if(mrkt.isRemote() == False and var_val != ''):
                        mrkt.setRemoteURL(var_val)
                #market name is not found
                else:
                    #try to create from the url
                    if(var_val != ''):
                        mrkt = Market(var_key, var_val)
               
                #alter the workspace's connections to markets
                if(mrkt != None and Workspace.inWorkspace()):
                    if(self.hasFlag('unlink')):
                        self.WS().unlinkMarket(mrkt.getName())
                    elif(self.hasFlag('link')):
                        self.WS().linkMarket(mrkt.getName())
                    pass
                    Workspace.save()
        
                #save adjustments
                Market.save()
                pass
            #modify workspace
            elif(k == 'workspace'):
                #verify proper format is passed in
                if(var_key == ''):
                    log.error("Must provide a workspace name.")
                    continue
                #modify existing workspace's path
                if(var_key.lower() in Workspace.Jar.keys()):
                    Workspace.Jar[var_key].setPath(var_val)
                #create new workspace!
                else:
                    Workspace(var_key, var_val)
                #save adjustments
                Workspace.save()
                pass
            #modify placeholders
            elif(k == 'placeholder'):
                apt.setField(var_val, ['placeholders', var_key])
                apt.save()
            #modify active workspace setting
            elif(k == 'active-workspace'):
                Workspace.setActiveWorkspace(v)
                Workspace.save()
            #modify refresh-rate
            elif(k == 'refresh-rate'):
                apt.setRefreshRate(v)
                apt.save()
            else:
                header = None
                #try to find what section the setting is under
                if(k.lower() in apt.SETTINGS['general'].keys()):
                    header = 'general'
                elif(k.lower() in apt.SETTINGS['HDL-styling'].keys()):
                    header = 'HDL-styling'
                #continue to write the value to the correct setting if found
                if(header != None):
                    #convert to booleans values for these settings
                    if(k == 'multi-develop' or k == 'overlap-global' or \
                        k == 'mixed-language' or k == 'newline-maps' or \
                        k == 'auto-fit' or k == 'hanging-end'):
                            v = cfg.castBool(v)
                    #write to setting
                    apt.setField(v, [header, k])
                pass          

                #save settings adjusments
                apt.save()
        pass


    def _del(self):
        '''Run the 'del' command.'''
        
        #make sure the block exists in downloaded workspace path
        block = self.WS().shortcut(self.getItem(), req_entity=False, visibility=False)

        if(block == None):
            exit(log.error("Could not identify a block with "+self.getItem()))

        if(block.getLvlBlock(Block.Level.DNLD) == None):
            log.error("Cannot delete block "+block.getFull()+" because it is not downloaded!")
            return

        #use the downloaded block object
        block = block.getLvlBlock(Block.Level.DNLD)
        #delete from downloaded space (and its library folder if empty)
        block.delete(squeeze=1)
        pass


    def _new(self):
        '''Run 'new' command.'''

        #create a new file
        if(self.hasFlag('file')):
            Block(os.getcwd(), self.WS())
            Block.getCurrent().newFile(self.getItem(raw=True), \
                tmplt_fpath=self.getVar("file"), \
                force=self.hasFlag('force'), \
                not_open=self.hasFlag('no-open'))
            return
        
        title = self.getItem()
        #make sure a valid title is captured
        if(Block.validTitle(title) == False):
            return
        M,L,N,_ = Block.snapTitle(title)

        #default path to make a new block
        block_path = self.WS().getPath()+L+"/"+N+"/"

        #override default path is specified on command-line
        if(self.getVar('path') != None):
            block_path = apt.fs(self.WS().getPath()+self.getVar('path'))

        #create block object
        b = Block(block_path, self.WS())
        #create the new block
        b.create(title, cp_template=(self.hasFlag('no-template') == 0), remote=self.getVar('remote'))
        #load the block
        if(self.hasFlag('open')):
            b.openInEditor()
        pass


    def _refresh(self):
        '''Run 'refresh' command.'''

        #package value is the market looking to refresh
        #if package value is null then all markets tied to this workspace refresh by default
        if(self.hasFlag('all')):
            log.info("Refreshing all markets...")
            for mkrt in Market.Jar.values():
                mkrt.refresh()
        elif(self.getItem() == None):
            log.info("Refreshing all workspace "+self.WS().getName()+" markets...")
            for mrkt in self.WS().getMarkets():
                mrkt.refresh()
        elif(self.getItem() in Market.Jar.keys()):
            Market.Jar[self.getItem()].refresh()
        pass


    def _list(self):
        '''Run 'list' command.'''

        if(self.hasFlag("script")):
            #initialize all Scripts
            Script.load()
            Script.printList()
        elif(self.hasFlag("label")):
            #load labels
            Label.load()
            Label.printList()
        elif(self.hasFlag("market")):
            Market.printList(self.WS().getMarkets())
        elif(self.hasFlag("workspace")):
            Workspace.printList()
        elif(self.hasFlag("profile")):
            Profile.printList()
        elif(self.hasFlag("template")):
            apt.getTemplateFiles()
        elif(self.hasFlag('unit')):
            self.WS().listUnits(title=self.getItem(), \
                alpha=self.hasFlag('alpha'), \
                usable=(not self.hasFlag('all')))
            #categorize by hidden files (skipped)
            #and visible files (files that are copied in on using template)
        else:
            self.WS().listBlocks(title=self.getItem(), \
                alpha=self.hasFlag('alpha'), \
                instl=self.hasFlag('i'), \
                dnld=self.hasFlag('d'), \
                avail=self.hasFlag('a'))
        pass


    def _release(self):
        '''Run the 'release' command.'''

        #load blocks and their designs
        self.WS().loadBlocks(id_dsgns=True)

        #identify current block
        block = Block.getCurrent()

        block.release(self.getItem(), msg=self.getVar("msg"), \
            dry_run=self.hasFlag('dry-run'), \
            only_meta=self.hasFlag('strict'), \
            no_install=self.hasFlag('no-install'))
        pass


    def _open(self):
        '''Run 'open' command.'''

        valid_editor = apt.getEditor() != cfg.NULL
        #open the settings (default is gui mode)
        if(self.hasFlag("settings")):
            gui_mode = True
            if('settings' in self._vars.keys()):
                gui_mode = not self.checkVar('settings', 'file')
            #try to open in gui
            if(gui_mode):
                #load labels
                Label.load()
                #load scripts
                Script.load()
                #enable GUI
                settings_gui = GUI()
                #adjust success if initialization failed
                gui_mode = settings_gui.initialized() 

            if(valid_editor and gui_mode == False):
                log.info("Opening settings CFG file at... "+apt.fs(apt.HIDDEN+apt.SETTINGS_FILE))
                apt.execute(apt.getEditor(), apt.fs(apt.HIDDEN+apt.SETTINGS_FILE))
                return
            elif(gui_mode == True):
                return
            pass
        #cannot open anything without a text-editor!
        if(valid_editor == False):
            exit(log.error("No text-editor configured!"))
        #open template
        if(self.hasFlag("template")):
            log.info("Opening block template folder at... "+apt.fs(apt.TEMPLATE))
            apt.execute(apt.getEditor(), apt.fs(apt.TEMPLATE))
            pass
        #open scripts
        elif(self.hasFlag("script")):
            #boot-up scripts
            Script.load()
            #want to open the specified script?
            script_path = apt.fs(apt.HIDDEN+"scripts")

            #maybe open up the script file directly if given a value
            if(self._item.lower() in Script.Jar.keys()):
                #able to open script?
                scpt = Script.Jar[self._item.lower()]
                if(scpt.hasPath()):
                    script_path = scpt.getPath()
                    log.info("Opening script "+self._item+" at... "+script_path)
                else:
                    exit(log.error("Script "+self._item+" has no path to open."))
            elif(self.getItem() == None):
                exit(log.error("Script "+self._item+" does not exist."))

            apt.execute(apt.getEditor(),script_path)
            pass
        #open profile
        elif(self.hasFlag("profile")):
            #open the specified path to the profile if it exists
            if(self.getItem(raw=True).lower() in Profile.Jar.keys()):
                prfl_path = Profile.Jar[self.getItem(raw=True)].getProfileDir()
                log.info("Opening profile "+self.getItem(raw=True)+" at... "+prfl_path)
                apt.execute(apt.getEditor(), prfl_path)
            else:
                log.error("Profile "+self.getItem(raw=True)+" does not exist.")
            pass
        #open block
        else:
            #search all blocks (visibility off)
            block = self.WS().shortcut(self.getItem(raw=True), visibility=False)
            if(block != None):
                #verify the block to open has download status
                if(block.getLvlBlock(Block.Level.DNLD) != None):
                    block.getLvlBlock(Block.Level.DNLD).openInEditor()
                else:
                    exit(log.error("Block "+block.getFull()+" is not downloaded!"))
            else:
                exit(log.error("No block "+self.getItem(raw=True)+" exists in your workspace."))
            pass
        pass
            

    def _help(self):
        '''
        Reads from provided manual.txt regarding the _item passed by
        user, given that the _command was 'help'.

        Parameters:
            None
        Returns:
            None
        '''
        #open the manual.txt
        with open(apt.getProgramPath()+'data/manual.txt', 'r') as man:
            info = man.readlines()

            disp = False
            for line in info:
                sep = line.split()
                #skip comments and empty lines
                if(len(sep) == 0):
                    if(disp == True):
                        print()
                    continue
                if(sep[0].startswith(';')):
                    continue
                #find where to start
                if(len(sep) > 1 and sep[0] == '*' and sep[1] == self._item.lower()):
                    disp = True
                elif(disp == True):
                    if(sep[0] == '*'):
                        break
                    else:
                        print(line,end='')       
            else:
                self._default()
        pass
    

    def _default(self):
        '''
        Display quick overview of legoHDL capabilites/commands.

        Parameters:
            None
        Returns:
            None
        '''
        print('USAGE: \
        \n\tlegohdl <command> [argument] [flags]\
        \n')
        print("COMMANDS:\n")
        def formatHelp(cmd, des):
            print('  ','{:<12}'.format(cmd),des)
            pass
        print("Development")
        formatHelp("new","create a new legohdl block (project)")
        formatHelp("init","initialize existing code into a legohdl block")
        formatHelp("open","open a block with the configured text-editor")
        formatHelp("get","print instantiation code for an HDL entity")
        formatHelp("graph","visualize HDL dependency graph")
        formatHelp("export","generate a blueprint file")
        formatHelp("build","execute a custom configured script")
        formatHelp("release","set a newer version for the current block")
        formatHelp("del","delete a block from the local workspace path")
        print()
        print("Management")
        formatHelp("list","print list of all blocks available")
        formatHelp("refresh","sync local markets with their remotes")
        formatHelp("install","bring a block to the cache for dependency use")
        formatHelp("uninstall","remove a block from the cache")
        formatHelp("download","bring a block to the workspace path for development")
        formatHelp("update","update an installed block to be its latest version")
        formatHelp("info","read further detail about a block")
        formatHelp("config","modify legohdl settings")
        print("\nType \'legohdl help <command>\' to read about the entered command.")
        pass


    def runCommand(self):
        '''
        Select from available commands what method to run. Case statement on
        self._command attr.

        Parameters:
            None
        Returns:
            None
        '''
        cmd = self._command

        if('new' == cmd):
            self._new()
            pass

        elif('init' == cmd):
            self._init()
            pass

        elif('open' == cmd):
            self._open()
            pass

        elif('get' == cmd):
            self._get()
            pass

        elif('graph' == cmd):
            self._graph()
            pass

        elif('export' == cmd):
            self._export()
            pass

        elif('build' == cmd):
            self._build()
            pass

        elif('release' == cmd):
            self._release()
            pass

        elif('del' == cmd):
            self._del()
            pass

        elif('list' == cmd):
            self._list()
            pass

        elif('refresh' == cmd):
            self._refresh()
            pass

        elif('install' == cmd):
            self._install()
            pass

        elif('uninstall' == cmd):
            self._uninstall()
            pass

        elif('download' == cmd):
            
            pass

        elif('update' == cmd):
            
            pass

        elif('info' == cmd):
            self._info()
            pass

        elif('config' == cmd):
            self._config()
            pass

        elif('help' == cmd):
            self._help()
            pass
        
        elif('' == cmd):
            self._default()
            pass
        #notify user when a unknown command was entereds
        else: 
            log.error("Unknown command - "+cmd+".")
            pass
        pass


    def __str__(self):
        return f'''
        command: {self._command}
        item: {self.getItem()}
        flags: {self._flags}
        vars: {self._vars}
        '''


    pass


def main():
    legoHDL()


#entry-point
if __name__ == "__main__":
    main()
