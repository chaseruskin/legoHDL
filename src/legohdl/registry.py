################################################################################
#   Project: legohdl
#   Script: registry.py
#   Author: Chase Ruskin
#   Description:
#       This script is in charge of seeing what blocks are available in the
#   the current workspace and syncing blocks between user-end and market-end.
################################################################################

from enum import Enum
import git
import logging as log
import shutil
import os,glob
from collections import OrderedDict
from .block import Block
from .apparatus import Apparatus as apt
from .cfgfile import CfgFile as cfg
from .market import Market
from .workspace import Workspace

class Registry:
    class Mode(Enum):
        GITLAB = 1,
        GITHUB = 2,
        NONE = 3,
        GIT = 4,
        OTHER = 5
        pass

    def __init__(self, mrkts):
        '''
        Initialize all market objects that have been found for this workspace.
        '''
        #list of all markets for current workspace
        self.__mkts = mrkts
        pass

    def listBlocks(self, M, L, N, options):
        '''
        Print list of available blocks to console.

        Parameters
        ---
        M : market to restrict list to
        L : library to restrict list to
        N : name to restrict list to
        options : list of cli arguments (download, install, alpha)
        '''     
        reg = None

        #show blocks downloaded and installed
        if(options.count("download") and options.count("install")):
            reg = self.getBlocks("local","cache")
        #only show blocks downloaded
        elif(options.count("download")):
            reg = self.getBlocks("local")
        #only show blocks that are installed
        elif(options.count("install")):
            reg = self.getBlocks("cache")
        #select from all blocks
        else:
            reg = self.getBlocks("local","cache","market")

        #alpha sort done by library then name
        if(options.count('alpha')):
            lib_list = list()
            name_dict = dict()
            
            for lib,prj in reg.items():
                lib_list.append(lib)
                for nm in prj.keys():
                    if(lib not in name_dict.keys()):
                        name_dict[lib] = list()
                    #create list of names that are under this library
                    name_dict[lib].append(nm)
                name_dict[lib].sort() #names within each library are in order
            lib_list.sort() #libraries are in order
            #run through each sorted part to insert into ordered dictionary
            sortion = OrderedDict()
            for lib in lib_list:
                sortion[lib] = dict()
                for nm in name_dict[lib]:
                    sortion[lib][nm] = reg[lib][nm]
            reg = sortion #assign the sorted dictionary to reg
            pass

        print('{:<12}'.format("Library"),'{:<20}'.format("Block"),'{:<8}'.format("Status"),'{:<8}'.format("Version"),'{:<16}'.format("Market"))
        print("-"*12+" "+"-"*20+" "+"-"*8+" "+"-"*8+" "+"-"*16)
        for lib,prjs in reg.items():
            for blk in prjs.values():
                status = '-'
                ver = ''
                info = ''
                _,l,n,_ = Block.snapTitle(blk.getTitle())
                #this block does not fulfill the search requirements for L and N
                if(not (l.startswith(L) and n.startswith(N))):
                    continue

                if(self.blockExists(blk.getTitle(), "local")):
                    status = 'dnld'
                    ver = self.getProjectsLocal()[l][n].getMeta("version")
                    info = self.getProjectsLocal()[l][n].getMeta("market")
                elif(self.blockExists(blk.getTitle(), "cache")):
                    status = 'instl'
                    ver = self.getProjectsCache()[l][n].getMeta("version")
                    info = self.getProjectsCache()[l][n].getMeta("market")
                elif(self.blockExists(blk.getTitle(), "market")):
                    ver = self.getBlocks("market")[l][n].getMeta("version")
                    info = self.getBlocks("market")[l][n].getMeta("market")
                else:
                    continue

                #this block does not fulfill the search requirements for M
                if(M == '_'):
                    #only include all blocks without a market
                    if(info != None):
                        continue
                #only include blocks with markets starting with what was requested
                elif(str(info).lower().startswith(M.lower()) == False):
                    continue

                #check if this block has an update available (newer version)
                if(self.blockExists(blk.getTitle(), "market")):
                    rem_ver = self.getBlocks("market")[l][n].getMeta("version")
                    #indicate update if the market has a higher version
                    if(Block.biggerVer(ver,rem_ver) == rem_ver and rem_ver != ver):
                        info = '(update)-> '+rem_ver
                    pass
                #format info text
                if(info == None):
                    info = ''
                info = info.lower()
                #format version text
                ver = '' if (ver == '0.0.0') else ver

                #display to console
                print('{:<12}'.format(blk.getLib(low=False)),'{:<20}'.format(blk.getName(low=False)),'{:<8}'.format(status),'{:<8}'.format(ver),info)
        pass

    def parseURL(self, url, website):
        i =  url.find(website)
        i_2 = (url[i:]).find('/')

        tail_url = url[i+i_2:]
        base_url = url[:i+i_2]
        return  base_url,tail_url

    def getBlocks(self, *args, updt=False):
        folders = None
        if(args.count("market")):
            folders = self.getProjectsMarket(updt)
        if(args.count("cache")):
            if(folders == None):
                folders = self.getProjectsCache(updt)
            else:
                folders = apt.merge(folders,self.getProjectsCache(updt))
        if(args.count("local")):
            if(folders == None):
                folders = self.getProjectsLocal(updt)
            else:
                folders = apt.merge(folders,self.getProjectsLocal(updt))
        return folders

    def getProjectsLocal(self, updt=False):
        if hasattr(self,"_local_prjs") and not updt:
            return self._local_prjs
        self._local_prjs = dict()
        folders = glob.glob(apt.getLocal()+"/**/*/"+apt.MARKER, recursive=True)

        for file in folders:
            #print(file)
            #read .lock to get information
            file = apt.fs(file)
            with open(file, 'r') as f:
                tmp = cfg.load(f, ignore_depth=True)
                #print(tmp)
                if('block' not in tmp.keys() or tmp['block']['name'] == cfg.NULL):
                    log.warning("Invalid "+apt.MARKER+" file: "+file)
                    continue
                elif(tmp['block']['library'] == cfg.NULL):
                    log.warning("Invalid "+apt.MARKER+" file: "+file)
                    continue
            s = file.rfind('/')
            c = Block(path=file[:s+1])
            if(c.getLib() not in self._local_prjs.keys()):
                self._local_prjs[c.getLib()] = dict()
            self._local_prjs[c.getLib()][c.getName()] = c
        #print(self._local_prjs)
        #print("ran1")
        return self._local_prjs

    def getProjectsCache(self, updt=False):
        if hasattr(self,"_cache_prjs") and not updt:
            return self._cache_prjs
        path = Workspace.getActiveWorkspace().getWorkspaceDir()+"cache/"
        self._cache_prjs = dict()
        libs = os.listdir(path)
        for l in libs:
            if(l[0] == '.'):
                continue
            self._cache_prjs[l] = dict()
            blks = os.listdir(path+l+"/")
            for b in blks:
                if(b[0] == '.'):
                    continue
                #only exists if master branch lives within the block folder
                if(os.path.exists(path+l+"/"+b+"/"+b+"/")):
                    self._cache_prjs[l.lower()][b.lower()] = Block(path=path+l+"/"+b+"/"+b+"/")
        #print(self._cache_prjs)
        #print("ran2")
        return self._cache_prjs

    def getProjectsMarket(self, updt=False):
        #go through each remote
        if hasattr(self,"_remote_prjs") and not updt:
            return self._remote_prjs
        self._remote_prjs = dict()
        #identify .lock files from each remote set up with this workspace
        for mkt in self.getMarkets():
            lego_files = glob.glob(apt.MARKETS+mkt.getName()+"/**/"+apt.MARKER, recursive=True)
            #from each lego file, create a Block object
            #print(lego_files)
            for x in lego_files:
                path = apt.fs(x.replace(apt.MARKER,""))
                block = Block(path=path, excludeGit=True)

                _,L,N,_ = Block.snapTitle(block.getTitle())
                if(L not in self._remote_prjs.keys()):
                    self._remote_prjs[L] = dict()
                if(N not in self._remote_prjs[L].keys()):
                    self._remote_prjs[L][N] = block
                else:
                    #overwrite with highest version available
                    cur_ver = self._remote_prjs[L][N].getMeta("version")
                    challenger_ver = block.getMeta("version")
                    if(Block.biggerVer(cur_ver,challenger_ver) == challenger_ver):
                        self._remote_prjs[L][N] = block

        #print(self._remote_prjs)
        #print("ran3")
        return self._remote_prjs

    #check if any changes were made to market remotes for current workspace
    #updates all markets if '' is passed into parameter
    def sync(self, mrkt):
        for mrk in self.getMarkets():
            rep = git.Repo(mrk.getPath())
            if(mrkt.lower() == mrk.getName().lower() or mrkt == ''):
                if(mrk.isRemote()):
                    try:
                        log.info("Refreshing "+mrk.getName()+"... "+mrk.url)
                        rep.remotes.origin.pull(rep.head.reference)
                    except:
                        print(mrk.url)
                        if(apt.isRemoteBare(mrk.url)):
                             log.info("Skipping "+mrk.getName()+" because it is empty...")
                        else:
                            log.error("Could not refresh "+mrkt+".")                       
                else:
                    log.info("Skipping "+mrk.getName()+" because it is local...")
        pass

    def getMarkets(self):
        return self.__mkts

    def availableLibs(self):
        return list(self.getBlocks("local","cache","market").keys())

    def getTitleShortcutter(self):
        if(hasattr(self, "_title_tracker")):
            return self._title_tracker
        #name and library has keys = name of found library
        self._title_tracker = {'name' : {}, 'library' : {}}
        db = self.getBlocks("local","cache","market")
        for library in db.keys():
            #print('l:',library)
            for name in db[library].keys():
                #print('n:',name)
                if(name not in self._title_tracker['name'].keys()):
                    self._title_tracker['name'][name] = [library]
                else:
                    self._title_tracker['name'][name] += [library]
            # :todo: count conflicts with library name
            # if(library not in title_tracker['library'].keys()):
            #     title_tracker['library'][library] = 0
            # else:
            #     title_tracker['library'][library] += 1
            pass     
        return self._title_tracker

    def canShortcut(self, n):
        '''
        Returns true if a block title's library can be determined from just a 
        name.

        Parameters
        ---
        n : block's name
        '''
        #get map of names and libraries
        others = self.getTitleShortcutter()
        #name must appear in title_tracker map
        if(n != None and n in others['name'].keys()):
            #how many blocks use this name?
            unique_cnt = len(others['name'][n])
            #prompt user to resolve ambiguity on next call
            if(unique_cnt > 1):
                #print all titles in conflict
                err_msg = "\n\n"
                for l in others['name'][n]:
                    err_msg = err_msg + '\t'+l+'.'+n+'\n'
                #print error message
                exit(log.error("Ambiguous title; blocks are:"+err_msg))
            #can shortcut if name is found only once throughout workspace
            return (unique_cnt == 1)
        else:
            return False
        
    def shortcut(self, n):
        '''
        Returns M,L,N,V from just a block's name.

        Parameters
        ---
        n : block's name
        '''
        others = self.getTitleShortcutter()
        return '',others['name'][n][0],n,''

    #use title="lib.*" to check if library exists
    def blockExists(self, title, place, updt=False):
        folder = None
        _,l,n,_ = Block.snapTitle(title)
        if(place == "local"):
            folder = self.getProjectsLocal(updt)
        elif(place == "cache"):
            folder = self.getProjectsCache(updt)
        elif(place == "market"):
            folder = self.getProjectsMarket(updt)
        return (l in folder.keys() and (n in folder[l].keys() or n == '*'))
        pass
    
    # :todo: work with APIs to be able to allow a user to automatically create a new remote repo if DNE
    @DeprecationWarning
    def createProjectRemote(self, git_url):
        mode = None
        keyword = 'https://'
        if(git_url.count('gitlab') > 0):
            keyword = 'gitlab'
            mode = self.Mode.GITLAB
        elif(git_url.count('github') > 0):
            keyword = 'github'
            mode = self.Mode.GITHUB
        else:
            mode = self.Mode.OTHER
        base,tail = self.parseURL(git_url, keyword)
        tail = tail.replace(".git","")
        print(base,"---"+tail)
        pass