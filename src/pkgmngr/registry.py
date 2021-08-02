#registry.py is in charge of seeing what packages are hosted remotely and syncing
#packages between user and remote
from enum import Enum
import copy,git,yaml
import os,random,requests,json,glob
from collections import OrderedDict
from .block import Block
from .apparatus import Apparatus as apt
from .market import Market
import logging as log

class Registry:
    class Mode(Enum):
        GITLAB = 1,
        GITHUB = 2,
        NONE = 3,
        GIT = 4,
        OTHER = 5
        pass

    #TO-DO: fix how to store and use remotes
    #things to consider: where to host remote central store (can have multiple)
    #what is a project's remote url when making a new one?
    def __init__(self, mrkts):
        self.__url = ''
        self.__galaxy = list() #list of all clusters for current workspace
        if(apt.inWorkspace() and apt.linkedMarket()):
            for rem,val in mrkts.items():
                self.__galaxy.append(Market(rem,val))
        self.__registry_path = apt.HIDDEN+"registry/"
        pass

    def listCaps(self, options):
        reg = None
        if(options.count("local") or not apt.linkedMarket()):
            reg = self.getCaps("local","cache")
        else:
            reg = self.getCaps("local","cache","market")
        #alpha sort
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

        print('{:<12}'.format("Library"),'{:<22}'.format("Module"),'{:<12}'.format("Status"),'{:<10}'.format("Version"))
        print("-"*12+" "+"-"*22+" "+"-"*12+" "+"-"*8)
        for lib,prjs in reg.items():
            for name,cp in prjs.items():
                status = '-'
                ver = ''
                info = ''
                L,N = Block.split(cp.getTitle())
                if(self.capExists(cp.getTitle(), "local")):
                    status = 'dnld'
                    ver = self.getProjectsLocal()[L][N].getMeta("version")
                elif(self.capExists(cp.getTitle(), "cache")):
                    status = 'instl' 
                    ver = self.getProjectsCache()[L][N].getMeta("version")
                elif(self.capExists(cp.getTitle(), "market")):
                    ver = self.getMarketLatestVer(self.getCaps("market")[L][N])
                else:
                    continue

                if(self.capExists(cp.getTitle(), "market")):
                    #does this version have a later update available? check its marker files
                    rem_ver = self.getMarketLatestVer(self.getCaps("market")[L][N])
                    
                    if(Block.biggerVer(ver,rem_ver) == rem_ver and rem_ver != ver):
                        info = '(update)-> '+rem_ver
                    pass
                ver = '' if (ver == '0.0.0') else ver
                print('{:<12}'.format(L),'{:<22}'.format(N),'{:<12}'.format(status),'{:<8}'.format(ver),info)
        pass

    def getMarketLatestVer(self, cap):
        pathway = apt.fs(cap.getPath()).split('/')
        #remove any additional path that is a specific version
        if(cap.getVersion() in pathway):
            pathway.remove(cap.getVersion())
        ver_dir = ''
        for p in pathway:
            ver_dir = ver_dir + p + "/"
        #list all version folders
        versions = os.listdir(ver_dir)

        for v in versions:
            if(v[0] == '.'):
                versions.remove(v)
        if(len(versions) == 0):
            return '0.0.0'
        latest = versions[0]
        #determine biggest version
        for v in versions:
            if(v[0] != '.' and Block.biggerVer(latest,v) == v):
                latest = v

        return latest

    def parseURL(self, url, website):
        i =  url.find(website)
        i_2 = (url[i:]).find('/')

        tail_url = url[i+i_2:]
        base_url = url[:i+i_2]
        return  base_url,tail_url

    def getCaps(self, *args, updt=False):
        folders = None
        if(args.count("market")):
            folders = self.getProjectsMarket(updt)
        if(args.count("cache")):
            if(folders == None):
                folders = self.getProjectsCache(updt)
            else:
                folders = self.merge(folders,self.getProjectsCache(updt))
        if(args.count("local")):
            if(folders == None):
                folders = self.getProjectsLocal(updt)
            else:
                folders = self.merge(folders,self.getProjectsLocal(updt))
        return folders

    #merge: place1 <- place2 (place2 has precedence)
    def merge(self, place1, place2):
        tmp = copy.deepcopy(place1)
        for lib,prjs in place1.items(): #go through each current lib
            if lib in place2.keys(): #is this lib already in merging lib?
                for prj in place2[lib]:
                    tmp[lib][prj] = place2[lib][prj]
        
        for lib,prjs in place2.items(): #go through all libs not in current lib
            if not lib in place1.keys():
                tmp[lib] = dict()
                for prj in place2[lib]:
                    tmp[lib][prj] = place2[lib][prj]
        return tmp

    def getProjectsLocal(self, updt=False):
        if hasattr(self,"_local_prjs") and not updt:
            return self._local_prjs
        self._local_prjs = dict()
        folders = glob.glob(apt.getLocal()+"/**/"+apt.MARKER, recursive=True)
        folders = folders + glob.glob(apt.getLocal()+"/*/"+apt.MARKER, recursive=False)

        for file in folders:
            #read .lock to get information
            file = apt.fs(file)
            with open(file, 'r') as f:
                tmp = yaml.load(f, Loader=yaml.FullLoader)
                #print(tmp)
            s = file.rfind('/')
            c = Block(path=file[:s+1])
            if(c.getLib() not in self._local_prjs.keys()):
                self._local_prjs[c.getLib()] = dict()
            self._local_prjs[c.getLib()][c.getName()] = c
        #print(self._local_prjs)
        return self._local_prjs
        pass

    def getProjectsCache(self, updt=False):
        if hasattr(self,"_cache_prjs") and not updt:
            return self._cache_prjs
        path = apt.WORKSPACE+"cache/"
        self._cache_prjs = dict()
        libs = os.listdir(path)
        for l in libs:
            if(l[0] == '.'):
                continue
            self._cache_prjs[l] = dict()
            pkgs = os.listdir(path+l+"/")
            for p in pkgs:
                if(p[0] == '.'):
                    continue
                self._cache_prjs[l][p] = Block(path=path+l+"/"+p+"/")
        return self._cache_prjs
        pass

    def getProjectsMarket(self, updt=False):
        #go through each remote
        if hasattr(self,"_remote_prjs") and not updt:
            return self._remote_prjs
        self._remote_prjs = dict()
        #identify .lock files from each remote set up with this workspace
        for clst in self.__galaxy:
            lego_files = glob.glob(self.__registry_path+clst.getName()+"/**/"+apt.MARKER, recursive=True)
            #from each lego file, create a Block object
            #print(lego_files)
            for x in lego_files:
                path = apt.fs(x.replace(apt.MARKER,""))
                cap = Block(path=path, excludeGit=True)
                L,N = Block.split(cap.getTitle())
                if(L not in self._remote_prjs.keys()):
                    self._remote_prjs[L] = dict()
                if(N not in self._remote_prjs[L].keys()):
                    self._remote_prjs[L][N] = cap
        #print(self._remote_prjs)
        return self._remote_prjs
        pass

    #check if any changes were made to market remotes for current workspace
    def sync(self):
        for mrk in self.getGalaxy():
            rep = git.Repo(mrk.getPath())
            if(mrk.isRemote()):
                rep.remotes.origin.pull(rep.head.reference)
        pass

    def getGalaxy(self):
        return self.__galaxy

    def availableLibs(self):
        return list(self.getCaps("local","cache","market").keys())

    #use title="lib.*" to check if library exists
    def capExists(self, title, place, updt=False):
        folder = None
        l,n = Block.split(title)
        if(place == "local"):
            folder = self.getProjectsLocal(updt)
        elif(place == "cache"):
            folder = self.getProjectsCache(updt)
        elif(place == "market"): #TO-DO-> get projects from remote
            folder = self.getProjectsMarket(updt)
        return (l in folder.keys() and (n in folder[l].keys() or n == '*'))
        pass
    
    #TO-DO > work with APIs to be able to allow a user to automatically create a new remote repo if DNE
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

    def encrypt(self, token, file):
        log.info("Encrypting access token... ",end='')
        random.seed()
        with open(apt.HIDDEN+file+".bin", 'w') as file:
            for letter in token:
                secret = bin(ord(letter))[2:]
                secret = ((8-len(secret))*"0")+secret #pad to make fixed 8-bits
                for x in range(len(secret)):
                    file.write(str(random.randint(0, 1)) + secret[x])
                pass
            file.close()
        print("success")
        pass

    def decrypt(self, file):
        token = ''
        with open(apt.HIDDEN+file+".bin", 'r') as file:
            binary_str = file.read()
            while len(binary_str):
                tmp = ''
                for x in range(8*2):
                    if x % 2 == 0:
                        binary_str = binary_str[1:]
                        continue
                    tmp += binary_str[0]
                    binary_str = binary_str[1:]
                token += chr((int('0b'+tmp, base=2)))
            file.close()
        return token

    @DeprecationWarning
    def assignRandomID(self):
        MIN_ID = 10000000
        MAX_ID = 99999999
        id = random.randint(MIN_ID, MAX_ID)
        while id in self.__local_reg.keys():
            id = random.randint(MIN_ID, MAX_ID)
        return id

    @DeprecationWarning
    def accessGitlabAPI(self, base, tail, api_ext='', multi=False):
        sect = 'groups/hdldb/projects?name='
        if(not multi):
            sect = 'projects?name='
            print(tail[1:])
        print("Trying to access remote...",end=' ')
        link = base+"/api/v4/"+sect+tail[1:]
        tk = self.decrypt('gl-token')
        #try to create new project
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        if(z.status_code == 200):
            print("success")
        else:
            print("error")
        return json.loads(z.text)

    @DeprecationWarning
    def createSubgroup(self, name, parent):
        print("Trying to create remote library "+name+"...",end=' ')
        link = self.__base_url+"/api/v4/groups/?name="+name+"&path="+name+"&visibility=private&parent_id="+str(parent['id'])
        tk = self.decrypt('gl-token')
        z = requests.post(link, headers={'PRIVATE-TOKEN': tk})
        if(z.status_code == 201):
            print("success")
        else:
            print("error")
    pass