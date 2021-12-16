# ------------------------------------------------------------------------------
# Project: legohdl
# Script: legohdl.py
# Author: Chase Ruskin
# Description:
#   This script is the entry-point to the legohdl program. 
# 
#   It parses the command-line arguments and contains a method for each valid 
#   command. This is the top-level script that interfaces with the user from
#   the command-line to determine what flags are raised, variables defined,
#   command requested, and determines how to route the program to the correct
#   method for the user.
# ------------------------------------------------------------------------------

import os, sys, shutil
from posixpath import dirname
import logging as log

from .__version__ import __version__
from .test import main as test

from .apparatus import Apparatus as apt
from .cfg import Cfg, Section, Key
from .workspace import Workspace
from .profile import Profile
from .block import Block
from .vendor import Vendor
from .plugin import Plugin
from .label import Label
from .git import Git
from .map import Map
from .unit import Unit
from .gui import GUI


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

        #create environment variables
        os.environ["LEGOHDL"] = apt.fs(apt.HIDDEN[:len(apt.HIDDEN)-1])

        #parse arguments
        self._command = self._item = ""
        #store args accordingly from command-line
        for i, arg in enumerate(sys.argv[1:]):
            #first is the command
            if(i == 0):
                self._command = arg.lower()
            #first arg without a starting '-' is the "item" (may not be used for all commands)
            elif(arg[0] != '-'):
                self._item = arg

            if(self._item != ""):
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
        #initialize all Vendors
        Vendor.load()
        Vendor.tidy()
        #initialize all Workspaces
        Workspace.load()
        Workspace.setActiveWorkspace(apt.CFG.get('general.active-workspace'))
        Workspace.tidy()
        #initialize all Profiles
        Profile.load()
        Profile.tidy()

        #save all legohdl.cfg changes
        apt.save()
        Workspace.save()
        Vendor.save()

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


    def getFlags(self):
        '''Returns ([str]) of all raised flags.'''
        return self._flags


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
        '''
        Prompt user to enter required preliminary information and/or enter a profile.

        At the end, it saves changes to the legohdl.cfg file.

        Parameters:
            None
        Returns:
            None 
        '''
        #prompt user to setup or bypass
        is_select = apt.confirmation("\
This looks like your first time running legoHDL! Would you like to \
use a profile (import settings, template, and plugins)?\
", warning=False)

        if(is_select):
            #give user options to proceeding to load a profile
            resp = input("""\
Enter:
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
        if(not is_select or len(apt.CFG.get('workspace', dtype=Section).keys()) == 0):
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
        if(feedback.strip() != Cfg.NULL):
            apt.setAuthor(feedback.strip())

        alter_editor = True
        #display what the current value is for the text-editor
        if(len(apt.getEditor())):
            alter_editor = apt.confirmation("Text editor is currently set to: \
                \n\n\t"+apt.getEditor()+"\n\nChange?",warning=False)
        #ask for text-editor to store in settings
        if(alter_editor):
            feedback = input("Enter your text-editor: ")
            if(feedback.strip() != Cfg.NULL):
                apt.setEditor(feedback.strip())

        #save changes to legohdl.cfg settings
        apt.save()
        pass


    def _build(self):
        '''Run the 'build' command.'''

        cur_block = Block(os.getcwd(), self.WS())
        #make sure within a valid block directory
        if(cur_block.isValid() == False):
            log.error("Cannot call a plugin from outside a block directory!")
            return
        #initialize all plugins
        Plugin.load()
        #get the plugin name
        plug_in = self.getItem()
        #make sure a valid plugin title is passed
        if(plug_in == None or plug_in[0] != '+'):
            log.error("Calling a plugin must begin with a '+'!")
            return
        #make sure the plugin exists
        elif(plug_in[1:].lower() not in Plugin.Jar.keys()):
            log.error("Plugin "+plug_in[1:]+" does not exist!")
            return
        #find index where build plugin name was called
        plugin_i = 0
        for i,arg in enumerate(sys.argv):
            #find by special plugin symbol
            if(arg.startswith('+')):
                plugin_i = i
                break
            
        #all arguments after plugin name are passed to the plugin
        plugin_args = sys.argv[plugin_i+1:]

        Plugin.Jar[plug_in[1:]].execute(plugin_args)
        pass


    def _graph(self):
        '''Run the 'graph' command.'''

        inc_tb = (self.hasFlag('ignore-tb') == False)
        disp_full = self.hasFlag('display-full')

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
        print(hierarchy.output(top_dog, compress=self.hasFlag('compress'), disp_full=disp_full))
        print()
        
        unit_order,block_order = hierarchy.topologicalSort()

        print('--- BLOCK ORDER ---')
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

        #trying to export a package file?
        if(self.hasFlag('pack')):
            #load blocks
            self.WS().loadBlocks(id_dsgns=False)
            #get the working block
            block = Block.getCurrent()
            #load the design units
            block.loadHDL()
            #reads lists 'omit' and 'inc' from command-line
            self.autoPackage(omit=apt.strToList(self.getVar('omit')), \
                inc=apt.strToList(self.getVar('inc')), \
                filepath=self.getVar('pack'))
            return

        #load labels
        Label.load()
        #load blocks and their designs
        self.WS().loadBlocks(id_dsgns=True)

        #get the working block
        block = Block.getCurrent()
     
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
                print(Unit.Hierarchy.output(top_dog, compress=True))
            pass

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
                    if(b.getLvl() == Block.Level.VER):
                        root,_ = os.path.split(b.getPath()[:len(b.getPath())-1])
                        path = root+'/v'+b.getVersion()+'/'

                    paths = b.gatherSources(ext=lbl.getExtensions(), path=path)
                    #add every found file identified with this label to the blueprint
                    for p in paths:
                        #only add files that have not already been added for this block's version
                        if(p in block_files[block_key]):
                            continue
                        #add label and file to blueprint data
                        blueprint_data += ['@'+lbl.getName()+' '+apt.fs(p)]
                        #note this file as added for this block's version
                        block_files[block_key] += [p]
                    pass
                #perform local-only label searching on current block
                if(b == block_order[-1]):
                    if(lbl.isGlobal() == False):
                        paths = block.gatherSources(ext=lbl.getExtensions())
                        #add every found file identified with this label to the blueprint
                        for p in paths:
                            blueprint_data += ['@'+lbl.getName()+' '+apt.fs(p)]
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
        block.updateRequires(quiet=(not verbose))
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
                align=apt.CFG.get('HDL-styling.auto-fit', dtype=bool), \
                hang_end=apt.CFG.get('HDL-styling.hanging-end', dtype=bool), \
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

        visibles = self.WS().loadBlocks(id_dsgns=False)
        
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
        if(apt.getMultiDevelop() == False and block != Block.getCurrent(bypass=True) and block.getLvl() == Block.Level.DNLD):
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
        block.get(entity=ent, \
                no_about=self.hasFlag('no-about'), \
                list_arch=self.hasFlag('arch'), \
                inst=self.hasFlag('inst'), \
                comp=self.hasFlag('comp'), \
                lang=lang, \
                edges=self.hasFlag('edges'))
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
        self.WS().loadBlocks(id_dsgns=False)

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
        self.WS().loadBlocks(id_dsgns=False)
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
            if(self.getItem().lower() not in Profile.Jar.keys()):
                log.error("Profile "+self.getItem()+" does not exist!")
                return
            #print the profile's information/summary
            print('\n'+Profile.Jar[self.getItem()].readAbout()+'\n')
            return
        
        if(self.hasFlag('vendor')):
            #make sure the requested vendor exists to be read
            if(self.getItem().lower() not in Vendor.Jar.keys()):
                log.error("Vendor "+self.getItem()+" does not exist!")
                return
            #print the vendor's information/summary
            print('\n'+Vendor.Jar[self.getItem()].readAbout()+'\n')
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
        #wishing to get information from metadata found in this block's vendor
        elif(self.hasFlag('a') and self.hasFlag('vers') == False):
            block = block.getLvlBlock(Block.Level.AVAIL)
            #no download to read from
            if(block == None):
                log.error("Block "+title+" is not available in a vendor!")
                return
            pass
        
        ver_range = ['0.0.0','']
        #properly format and verify the passed in version range
        if(self.getVar('vers') != None):
            window = self.getVar('vers').split(':')
            #validate first version range component (lower-bound, inclusive)
            if(len(window) and Block.validVer(window[0], places=[1,2,3])):
                ver_range[0] = Block.stdVer(window[0], rm_v=True, z_ext=True)
            #validate second version range component (upper-bound, exclusive)  
            if(len(window) > 1 and Block.validVer(window[1], places=[1,2,3])):
                ver_range[1] = Block.stdVer(window[1], rm_v=True, z_ext=True)
            
            #if a ':' DNE, then zoom into only the given version
            if(self.getVar('vers').find(':') == -1):
                ver_range[1] = '-'
            pass

        print(block.readInfo(self.hasFlag('more'),
            versions=self.hasFlag('vers'),
            only_instls=self.hasFlag('i'), 
            only_avail=self.hasFlag('a'),
            ver_range=ver_range,
            see_changelog=self.hasFlag('changelog')))
        pass


    def _config(self):
        '''Run 'config' command.'''

        #import a profile if a profile name is given as item.
        if(self.getItem(raw=True) in Profile.Jar.keys()):
            Profile.Jar[self.getItem(raw=True)].importLoadout(ask=self.hasFlag('ask'))
            return

        #generate list of all available keys/editable sections
        editable_keys = apt.CFG.getAllKeys()
        create_keys = ['vendor', 'plugin', 'placeholders',]
        editable_sects = apt.OPTIONS

        link = False
        unlink = False

        #set each setting listed in flags try to modify it
        for k in self.getFlags():
            #check if using appending or removal operator
            link   = k[-1] == '+'
            unlink = k[-1] == '-'

            #get the value from the flag (if exists)
            v = self.getVar(k)

            #remove operator from keypath
            if(link or unlink):
                k = k[:len(k)-1]

            #print(k,v)
            
            #split the keypath into components (if applicable)
            parts = k.lower().split('.')
            #first component is the section
            sect = parts[0]

            #first attempt to edit the key
            edit_k = (k.lower() in editable_keys)
            #allow user to create sections
            edit_s = (sect.lower() in editable_sects and (len(k.split(Cfg.S_DELIM)) > 1))
            crte_k = (sect.lower() in create_keys and (len(k.split(Cfg.S_DELIM)) > 1))

            #assign defaults to V if DNE
            if(v == None):
                #requesting to make an empty new section
                if(edit_s and crte_k == False):
                    v = Section(name=k)
                else:
                    v = ''

            if(isinstance(v, str)):
                v = v.strip()

            if(edit_k == False and edit_s == False):
                if(edit_k == False):
                    log.error("Cannot edit key: "+k)
                    continue
                #second attempt is to edit a section
                if(edit_s == False):
                    log.error("Cannot edit section: "+sect)
                    continue

            #[!] handle plugins
            if(sect == 'plugin' and (edit_k or crte_k)):
                #make sure command is a string
                if(isinstance(v, str) == False):
                    continue
                alias = parts[-1]
                #load in plugins
                Plugin.load()

                #modify existing plugins
                if(alias in Plugin.Jar.keys()):
                    Plugin.Jar[alias].setCommand(v)
                #create a new plugin
                else:
                    Plugin(alias, v)
                pass

            #[!] handle labels
            elif(sect == 'label' and (parts[1] == 'global' or parts[1] == 'local')):
                #cannot create sections
                if(isinstance(v, Section)):
                    continue
                #load labels
                Label.load()
                #verify proper format is passed in
                if(parts[1] == parts[-1]):
                    log.error("Must provide a label name to create/edit.")
                    continue
                lbl_name = parts[-1]
                #get list of file search extensions
                v = apt.strToList(v, delim=',')

                #modify existing label
                if(lbl_name in Label.Jar.keys()):
                    Label.Jar[lbl_name].setExtensions(v)
                    #get global attr
                    isglbl = Label.Jar[lbl_name].isGlobal()

                    #flip from global->local and vice versa depending on key
                    if(isglbl and parts[1] == 'local'):
                        apt.CFG.remove('label'+'.global.'+lbl_name, verbose=True)
                    elif(parts[1] == 'global' and not isglbl):
                        apt.CFG.remove('label'+'.local.'+lbl_name, verbose=True)

                    #modify global attr
                    Label.Jar[lbl_name].setGlobal((parts[1] == 'global'))
                    pass
                #create new label
                else:
                    Label(lbl_name, v, (parts[1] == 'global'))
                    pass
                #format to string without cfg list tokens
                v = Cfg.castStr(v, frmt_list=False)
                pass

            #[!] handle updating active workspace
            if(k == 'general.active-workspace'):
                Workspace.setActiveWorkspace(v)

            #[!] handle creating a workspace
            elif(sect == 'workspace'):
                #get the name of the workspace
                ws_name = parts[1]
                #check if also provided path name
                path = v if(parts[-1] == 'path') else ''

                #create new workspace!
                if(ws_name not in Workspace.Jar.keys()):
                    Workspace(ws_name, path)
                pass

            #[!] handle workspace's vendors
            if(edit_k and sect == 'workspace' and parts[-1] == 'vendors' and isinstance(v, str)):
                #get list of vendors passed by v
                vndrs = apt.strToList(v, delim=',')
                #iterate through all passed vendors
                for vndr in vndrs:
                    if(link):
                        self.WS().linkVendor(vndr)
                    elif(unlink):
                        self.WS().unlinkVendor(vndr)
                    pass
                #set the entire vendors list
                if((link or unlink) == False):
                    self.WS().setVendors(vndrs)
                #convert v to str from list for cfg write
                v = Cfg.castStr(self.WS().getVendors(returnnames=True, lowercase=False), drop_list=False)
                pass

            #[!] handle vendor creations/editing
            if(sect == 'vendor' and (edit_k or crte_k)):
                name = parts[-1]
                vndr = None
                url = self.getVar(k)
                #modify an existing vendor
                if(name in Vendor.Jar.keys()):
                    vndr = Vendor.Jar[name]
                    
                    #if its local and remote given try to set a remote
                    if(vndr.isRemote() == False and url != Cfg.NULL):
                        vndr.setRemoteURL(url)    
                    elif(vndr.isRemote() and url == Cfg.NULL):
                        vndr._repo.setRemoteURL(url, force=True)
                #vendor name is not found create new one
                else:
                    if(url == Cfg.NULL):
                        url = None
                    vndr = Vendor(name, url)
                pass

            #[!] handle profiles
            if(sect == 'general' and edit_k and parts[-1] == 'profiles'):
                prfls = apt.strToList(v, delim=',')

                avail_prfls = list(Profile.Jar.keys())
                #remove all non-listed profiles when setting key
                if((link or unlink) == False):
                    for prfl in avail_prfls:
                        #check if the profile is not listed
                        if(prfl not in prfls):
                            Profile.Jar[prfl].remove()
                        pass

                #iterate through all listed profiles from command-line
                for prfl in prfls:
                    #add new profiles when setting or adding
                    if((link or not unlink) and prfl not in Profile.Jar.keys()):
                        #reload default profile
                        if(prfl == 'default'):
                            Profile.reloadDefault()
                        elif(Git.isValidRepo(prfl) or Git.isValidRepo(prfl, remote=True)):
                            Profile('', url=prfl)
                        else:
                            Profile(prfl)
                    #remove profiles from existing list
                    elif(unlink and prfl in Profile.Jar.keys()):
                        Profile.Jar[prfl].remove()
                    pass

                #cast v to be a string
                v = Cfg.castStr(list(Profile.Jar.keys()), drop_list=False)
                pass

            #write to cfg
            if(edit_k):
                apt.CFG.set(k, v, verbose=True, override=True)
            elif(edit_s):
                apt.CFG.set(k, v, verbose=True, override=True)
            #check if needing to resave cfg
            if(apt.CFG._modified):
                apt.CFG.write()
                log.info("Updated settings.")

            Vendor.save()
            Workspace.save()
            Label.save()
            Plugin.save()
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


    def _download(self):
        '''Run 'download' command.'''

        #determine if the item passed is a url to directly clone
        from_url = False

        if(self.getItem() == None):
            log.error("Enter a block or repository to download.")
            return

        #get the block object from all possible blocks
        block = self.WS().shortcut(self.getItem(), visibility=False)

        #make sure the user passed in a value for the item
        if(block == None):
            #try to see if a remote was passed
            if(Git.isValidRepo(self.getItem(), remote=True)):
                from_url = True
            else:
                exit(log.error("Could not find a block as "+self.getItem()))

        #download from the identified block
        if(from_url == False):
            #successful download if block object is returned
            block = block.download(place=self.getVar('path'))
            pass
        #download directly from this repository
        else:
            block = None
            pass

        #cannot continue without downloaded block object
        if(block == None):
            return

        #open in-editor
        if(self.hasFlag('open')):
            block.openInEditor()
        pass


    def _update(self):
        '''Run 'update' command.'''

        print("NOT IMPLEMENTED YET")
        pass


    def _refresh(self):
        '''Run 'refresh' command.'''

        jar = Vendor.Jar
        target = 'vendors'
        #package value could be profile looking to refresh
        if(self.hasFlag('profile')):
            jar = Profile.Jar
            target = 'profiles'

        #package value is the vendor looking to refresh
        #if package value is null then all vendors tied to this workspace refresh by default
        if(self.hasFlag('all')):
            log.info("Refreshing all "+target+"...")
            for it in jar.values():
                it.refresh()
        #refresh all workspace vendors
        elif(self.getItem() == None and self.hasFlag('profile') == False):
            log.info("Refreshing all workspace "+self.WS().getName()+" vendors...")
            for vndr in self.WS().getVendors():
                vndr.refresh()
        #make sure an item was entered
        elif(self.getItem() == None):
            log.error("Enter a known "+target[:len(target)-1]+".")
        #check if item exists in its container
        elif(self.getItem() in jar.keys()):
            jar[self.getItem()].refresh()
        #could not locate the target
        else:
            log.error("Unknown "+target[:len(target)-1]+" "+self.getItem()+".")
        pass


    def _list(self):
        '''Run 'list' command.'''

        if(self.hasFlag("plugin")):
            #initialize all plugins
            Plugin.load()
            Plugin.printList()
        elif(self.hasFlag("label")):
            #load labels
            Label.load()
            Label.printList()
        elif(self.hasFlag("vendor")):
            Vendor.printList(self.WS().getVendors())
        elif(self.hasFlag("workspace")):
            Workspace.printList()
        elif(self.hasFlag("profile")):
            Profile.printList()
        elif(self.hasFlag("template")):
            #get all available template files
            tmplt_files = apt.getTemplateFiles(apt.getTemplatePath(), inc_hidden=True, is_hidden=False)
            #print the template files to the console along with if each is "hidden" or not
            log.info('Files available within the selected template: '+apt.getTemplatePath())
            print('{:<60}'.format("Relative Path"),'{:<8}'.format("Hidden"))
            print("-"*60+" "+"-"*8)
            for f in tmplt_files:
                status = '-' if(f[1] == False) else 'yes'
                print('{:<60}'.format(f[0]),'{:<8}'.format(status))
                pass
        elif(self.hasFlag('unit')):
            self.WS().listUnits(title=self.getItem(),
                alpha=self.hasFlag('alpha'),
                usable=(not self.hasFlag('all')),
                ignore_tb=self.hasFlag('ignore-tb')
                )
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

        #note: run export before release to make sure requirements are up-to-date?

        block.release(self.getItem(), msg=self.getVar("msg"), \
            dry_run=self.hasFlag('dry-run'), \
            only_meta=self.hasFlag('strict'), \
            no_install=self.hasFlag('no-install'), \
            skip_changelog=self.hasFlag('no-changelog'))
        pass


    def _open(self):
        '''Run 'open' command.'''

        valid_editor = apt.getEditor() != Cfg.NULL
        #open the settings (default is gui mode)
        if(self.hasFlag("settings")):
            gui_mode = True
            if('settings' in self._vars.keys()):
                gui_mode = not self.checkVar('settings', 'file')
            #try to open in gui
            if(gui_mode):
                #load labels
                Label.load()
                #load plugin
                Plugin.load()
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
        #open plugin
        elif(self.hasFlag("plugin")):
            #boot-up plugins
            Plugin.load()
            #want to open the specified plugin?
            plugin_path = apt.fs(apt.HIDDEN+"plugins/")

            #maybe open up the plugin file directly if given a value
            if(self._item.lower() in Plugin.Jar.keys()):
                #able to open plugin?
                plgn = Plugin.Jar[self._item.lower()]
                if(plgn.hasPath()):
                    plugin_path = plgn.getPath()
                    log.info("Opening plugin "+self._item+" at... "+plugin_path)
                else:
                    exit(log.error("Plugin "+self._item+" has no path to open."))
            elif(self.getItem() != None):
                exit(log.error("Plugin "+self._item+" does not exist."))
            else:
                log.info("Opening built-in plugins folder at... "+plugin_path)
            apt.execute(apt.getEditor(),plugin_path)
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
        #open vendor
        elif(self.hasFlag("vendor")):
            #open the specified path to the vendor if it exists
            if(self.getItem(raw=True).lower() in Vendor.Jar.keys()):
                vndr_path = Vendor.Jar[self.getItem(raw=True)].getVendorDir()
                log.info("Opening vendor "+self.getItem(raw=True)+" at... "+vndr_path)
                apt.execute(apt.getEditor(), vndr_path)
            else:
                log.error("Vendor "+self.getItem(raw=True)+" does not exist.")
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
                if(len(sep) > 1 and sep[0] == '*' and sep[1] == self.getItem(True).lower()):
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

        def formatHelp(cmd, des):
            print('  ','{:<12}'.format(cmd),des)
            pass

        print('\nUsage: \
        \n\tlegohdl <command> [argument] [flags]\
        \n')
        print("Commands:")

        print("Development")
        formatHelp("new","create a new legohdl block (project)")
        formatHelp("init","initialize existing code into a legohdl block")
        formatHelp("open","open a block with the configured text-editor")
        formatHelp("get","print instantiation code for an HDL unit")
        formatHelp("graph","visualize HDL dependency graph")
        formatHelp("export","generate a blueprint file")
        formatHelp("build","execute a custom configured plugin")
        formatHelp("release","set a newer version for the current block")
        formatHelp("del","delete a block from the local workspace path")
        print()
        print("Management")
        formatHelp("list","print list of all blocks available")
        formatHelp("refresh","sync local vendors with their remotes")
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
        
        #allow for 'build' command to be optional
        if(len(cmd) and cmd[0] == '+'):
            self._item = cmd
            cmd = 'build'
        #verify the help flag is intended for the legohdl program
        if(cmd != 'build' and (self.hasFlag('h') or self.hasFlag('help'))):
            self._item = cmd
            cmd = 'help'

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
            self._download()
            pass

        elif('update' == cmd):
            self._update()
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
        #notify user when a unknown command was entered
        else:
            log.error("Unknown command \""+cmd+"\"")
            pass
        pass


    # uncomment to use for debugging
    # def __str__(self):
    #     return f'''
    #     command: {self._command}
    #     item: {self.getItem()}
    #     flags: {self._flags}
    #     vars: {self._vars}
    #     '''


    pass


def main():
    legoHDL()


#entry-point
if __name__ == "__main__":
    main()
