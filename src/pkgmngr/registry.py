#registry.py is in charge of seeing what packages are hosted remotely and syncing
#packages between user and remote
from enum import Enum
import os, random, requests, json, glob
import yaml
from bs4 import BeautifulSoup
from collections import OrderedDict
from capsule import Capsule
from repo import Repo
from apparatus import Apparatus as apt

class Registry:
    class Mode(Enum):
        GITLAB = 1,
        GITHUB = 2,
        NONE = 3,
        GIT = 4,
        OTHER = 5
        pass

    GL_PRJ_EXT = "/projects?include_subgroups=True&simple=True"

    def __init__(self, url):
        self.__url = url
        self.__base_url = url
        self.__tail_url = url
        self.__local_path = apt.HIDDEN+"registry/"
        
        self.__local_reg = dict()
        self.__remote_reg = dict()
        self.__cur_reg = dict()
        self.__cache_reg = dict()

        self.localLoad()
        #print(url)
        #determine what remote website is being used
        self.__mode = None
        if(not apt.linkedRemote()):
            self.__mode = self.Mode.NONE
        elif(self.__url.count('.git') > 0):
            self.__mode = self.Mode.GIT
        elif(self.__url.count('gitlab') > 0):
            self.__mode = self.Mode.GITLAB
            self.parseURL('gitlab')
        elif(self.__url.count('github') > 0):
            self.__mode = self.Mode.GITHUB
            self.parseURL('github')
        else:
            self.__mode = self.Mode.OTHER
            self.parseURL('https://')

    def localLoad(self):
        with open(self.__local_path+"db.txt", 'r') as file:
            for line in file.readlines():
                if(len(line) <= 1):
                    continue
                #parse unique delimiters
                dot = line.find('.')
                eq = line.find('=')
                spce = line.find(' ')
                Rspce = line.rfind(' ')
                spk = line.find('*')
                at = line.find('@')
                iden = line[:spce]
                self.__local_reg[int(iden)] = Repo(l_a=line[Rspce+1:spk], lib=line[spce+1:dot], g_url=line[at+1:], name=line[dot+1:eq], l_v=line[eq+1:Rspce], m_b=line[spk+1:at], l_path='')
            file.close()

    def listCaps(self, options):
        reg = self.__remote_reg #grab all remotes
        sorted_reg = OrderedDict()
        if(not apt.linkedRemote()):
            reg = self.__local_reg
        if(options.count('alpha')):
            for key,repo in reg.items():
                sorted_reg[repo.library+repo.name] = repo
            reg = sorted_reg

        if(not apt.linkedRemote()):
            reg = self.getCaps("local","cache")
        #print(self.getCaps("cache","local"))
        #for lib,prjs in reg.items():
            #sorted_reg[lib] = OrderedDict(prjs)
        print("\nList of available modules:")
        print("  ",'{:<24}'.format("Module"),'{:<16}'.format("Status"),'{:<10}'.format("Version"))
        print("-"*80)
        for lib,prjs in reg.items():
            for name,cp in prjs.items():
                status = '-'
                ver = cp.getVersion()
                info = ''
                l,n = Capsule.split(cp.getTitle())
                if(self.capExists(cp.getTitle(), "local")):
                    status = 'dnld'
                    ver = self.getProjectsLocal()[l][n].getMeta("version")
                elif(self.capExists(cp.getTitle(), "cache")):
                    status = 'instl' 
                    ver = self.getProjectsCache()[l][n].getMeta("version")

                if (cp.isValid() and False): #check for downloads
                    status = 'dnld'
                    loc_ver = ''
                    loc_ver = cp.getVersion()
                    if((ver != '' and loc_ver == '') or (ver != '' and ver > loc_ver)):
                        info = '(update)-> '+ver
                        ver = loc_ver

                ver = '' if (ver == '0.0.0') else ver
                if((options.count('local') and cp.isValid()) or not options.count('local')):
                    print("  ",'{:<24}'.format(cp.getTitle()),'{:<16}'.format(status),'{:<10}'.format(ver),info)
        pass

    def parseURL(self, website):
        i =  self.__url.find(website)
        i_2 = (self.__url[i:]).find('/')

        self.__tail_url = self.__url[i+i_2:]
        self.__base_url = self.__url[:i+i_2]
        pass

    def localSync(self):
        oldKeys = self.__local_reg.copy().keys()
        curKeys = self.__cur_reg.copy().keys()
        #remove any projects not found remotely and not found locally
        for k in oldKeys:
            if(apt.linkedRemote()):
                if not k in curKeys and not k in self.__remote_reg.keys():
                    del self.__local_reg[k]
            elif not k in curKeys:
                del self.__local_reg[k]
        
        #add any found projects that are not currently in local reg
        for k in curKeys:
            self.__local_reg[k] = self.__cur_reg[k] 

        for key,repo in self.__remote_reg.items():
                #update information and add to local if not registered
                lp = repo.local_path
                if(key in self.__local_reg.keys()):
                    lp = self.__local_reg[key].local_path #must preserve local_path identified by localLoad
                self.__local_reg[key] = repo
                self.__local_reg[key].local_path = lp

        with open(self.__local_path+"db.txt", 'w') as file:
            for key,repo in self.__local_reg.items():
                line = str(key)+" "+repo.library+"."+repo.name+"="+repo.last_version+" "+repo.last_activity+"*"+repo.m_branch+"@"+repo.git_url
                file.write(line+"\n")
            file.close()
        pass

    def sync(self):
        self.localSync()
        if(apt.linkedRemote()):
            self.remoteSync()

    def remoteSync(self):
        subs = list()
        prjs = list()
        for key,r  in self.__remote_reg.items():
            subs.append(r.library)
            prjs.append(r.name)
        for key,r  in self.__local_reg.items():
            #create any unestablished libraries
            if(not r.library in subs):
                self.createSubgroup(r.library, self.accessGitlabAPI())
                subs.append(r.library)

            if(not r.name in prjs):
                c = Capsule(rp=r)
                c.genRemote()
                c.saveID(self.fetchProjectShallow(r.library,r.name)['id'])
                prjs.append(r.name)
        pass

    def getProjectsCache(self, updt=False):
        if hasattr(self,"_cache_prjs") and not updt:
            return self._cache_prjs
        path = apt.HIDDEN+"cache/"
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
                self._cache_prjs[l][p] = Capsule(path=path+l+"/"+p+"/")
        return self._cache_prjs

    def getCaps(self, *args, updt=False):
        folders = None
        if(args.count("remote")):
            if(folders == None):
                folders = self.getProjectsRemote(updt)
            else:
                folders = folders + self.getProjectsRemote(updt)
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
        for lib,prjs in place1.items(): #go through each current lib
            if lib in place2.keys(): #is this lib already in merging lib?
                for prj in place2[lib]:
                    place1[lib][prj] = place2[lib][prj]
        
        for lib,prjs in place2.items(): #go through all libs not in current lib
            if not lib in place1.keys():
                place1[lib] = dict()
                for prj in place2[lib]:
                    place1[lib][prj] = place2[lib][prj]
        return place1

    def getProjectsLocal(self, updt=False):
        if hasattr(self,"_local_prjs") and not updt:
            return self._local_prjs
        self._local_prjs = dict()
        folders = glob.glob(apt.SETTINGS['local']+"/**/.lego.lock", recursive=True)
        folders = folders + glob.glob(apt.SETTINGS['local']+"/*/.lego.lock", recursive=False)
        for file in folders:
            #read .lock to get information
            with open(file, 'r') as f:
                tmp = yaml.load(f, Loader=yaml.FullLoader)
                #print(tmp)
            s = file.rfind('/')
            c = Capsule(path=file[:s+1])
            if(c.getLib() not in self._local_prjs.keys()):
                self._local_prjs[c.getLib()] = dict()
            self._local_prjs[c.getLib()][c.getName()] = c
        #print(self._local_prjs)
        return self._local_prjs
        pass

    #TO-DO
    def getProjectsRemote(self, updt=False):
        if(self.__mode == Registry.Mode.GITLAB):
            pass
        elif(self.__mode == Registry.Mode.GITHUB):
            pass
        elif(self.__mode == Registry.Mode.GIT):
            pass
        elif(self.__mode == Registry.Mode.NONE):
            pass
        elif(self.__mode == Registry.Mode.OTHER):
            pass
        pass

    #use title="lib.*" to check if library exists
    def capExists(self, title, place, updt=False):
        folder = None
        l,n = Capsule.split(title)
        if(place == "local"):
            folder = self.getProjectsLocal(updt)
        elif(place == "cache"):
            folder = self.getProjectsCache(updt)
        elif(place == "remote"): #TO-DO-> get projects from remote
            return False
            pass

        return (l in folder.keys() and (n in folder[l].keys() or n == '*'))

    def prjLocation(self, title):
        pass

    @DeprecationWarning
    def findProjectsLocal(self, path, cached=False):
        branches = list(os.listdir(path))
        for leaf in branches:
            if(os.path.isdir(path+leaf) and leaf[0] != '.'):
                    self.findProjectsLocal(path+leaf+'/')
            if(leaf.count(".yml") > 0):
                #print("valid project!") #print(path[l+1:])
                l = path.rfind('/')
                with open (path+leaf, 'r') as f:
                    tmp = yaml.load(f, Loader=yaml.FullLoader)
                    f.close()
                    #print(leaf)#print(tmp['id'])#print(path)
                    if(cached):
                        self.__cache_reg[int(tmp['id'])] = Repo(l_a='', lib=tmp['library'], name=tmp['name'], l_v=tmp['version'], g_url='', m_b='', l_path=path)
                    else:
                        self.__cur_reg[int(tmp['id'])] = Repo(l_a='', lib=tmp['library'], name=tmp['name'], l_v=tmp['version'], g_url='', m_b='', l_path=path)
        pass

    def findPrj(self, lib, name):
        for key,r in self.getLocalPrjs().items(): #LOCAL = ALL, #REMOTE = REMOTE, #CUR = ONLY LOCAL
            if(r.library == lib and r.name == name):
                return key,r
        return -1,None

    #TO-DO: rename all reg dictionaries to better reflect which they are for future thanking
    def getCurPrjs(self):
        return self.__cur_reg

    def getRemotePrjs(self):
        return self.__remote_reg

    def getLocalPrjs(self):
        return self.__local_reg

    def getCachePrjs(self):
        return self.__cache_reg

    def assignRandomID(self):
        MIN_ID = 10000000
        MAX_ID = 99999999
        id = random.randint(MIN_ID, MAX_ID)
        while id in self.__local_reg.keys():
            id = random.randint(MIN_ID, MAX_ID)
        return id

    def installedPkgs(self):
        meta_dir = glob.glob(apt.HIDDEN+"/cache/**/.*.yml", recursive=True)
        id_dict = dict()
        for md in meta_dir:
            with open(md, 'r') as f:
                tmp = yaml.load(f, Loader=yaml.FullLoader)
                id_dict[tmp['id']] = tmp['version']
                f.close()
        return id_dict

    def createSubgroup(self, name, parent):
        print("Trying to create remote library "+name+"...",end=' ')
        link = self.__base_url+"/api/v4/groups/?name="+name+"&path="+name+"&visibility=private&parent_id="+str(parent['id'])
        tk = self.decrypt('gl-token')
        z = requests.post(link, headers={'PRIVATE-TOKEN': tk})
        if(z.status_code == 201):
            print("success")
        else:
            print("error")

    def accessGitlabAPI(self, api_ext=''):
        print("Trying to access remote...",end=' ')
        link = self.__base_url+"/api/v4/groups/"+self.__tail_url+"/"+api_ext
        tk = self.decrypt('gl-token')
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        if(z.status_code == 200):
            print("success")
        else:
            print("error")
        return json.loads(z.text)

    def fetchProjectShallow(self, library, name):
        plist = self.accessGitlabAPI(self.GL_PRJ_EXT)

        if('error' in plist and plist['error'] == 'invalid_token'):
            print("ERROR- Please configure an access token for authorization")
            return None

        for prj in plist:
            lib = prj['name_with_namespace']
            last_i = lib.rfind('/')
            first_i = (lib[:last_i-1]).rfind('/')
            lib = lib[first_i+2:last_i-1]
            if(first_i == -1):
                lib = ''
            if(library == lib and name == prj['name']):
                return prj

    def fetch(self):
        projectList = self.accessGitlabAPI(self.GL_PRJ_EXT)

        if('error' in projectList and projectList['error'] == 'invalid_token'):
            print("ERROR- Please configure an access token for authorization")
            return None
        
        for x in projectList:
            #print(x['name']) #print(x['name_with_namespace'])
            lib = x['name_with_namespace']
            last_i = lib.rfind('/')
            first_i = (lib[:last_i-1]).rfind('/')
            lib = lib[first_i+2:last_i-1]
            if(first_i == -1):
                lib = ''
            #print(lib)#print(x['web_url'])#print(x['id'])#check if there has been new activity#print(x['last_activity_at'])#print(x['default_branch'])
            last_ver = '0.0.0'
            #local registry already has a tab on this remote repo
            if((x['id'] in self.__local_reg)):
                last_ver = self.__local_reg[x['id']].last_version
                #print(x.keys())
                #print(x['name'],x['last_activity_at'], self.__local_reg[x['id']].last_activity)
                if(x['last_activity_at'] > self.__local_reg[x['id']].last_activity):
                    #fetch version number to see if there is an update available
                    last_ver = self.grabTags(x)
                
                if(x['id'] in self.__cur_reg):
                    tmp_ver = self.__cur_reg[x['id']].last_version
                    last_ver = Capsule.biggerVer(tmp_ver,last_ver)
                pass
            else: #local registry needs all info on this repo
                last_ver = self.grabTags(x)

            self.__remote_reg[x['id']] = Repo(l_a=x['last_activity_at'], lib=lib, g_url=x['web_url']+'.git', name=x['name'], l_v=last_ver, m_b=x['default_branch'], l_path='')
        
        self.localSync()
        pass

    def grabTags(self, prj):
        print("Accessing remote project "+prj['name']+"... ",end='')
        tk = self.decrypt('gl-token')
        link = self.__base_url+"/api/v4/projects/"+str(prj['id'])+"/repository/tags"
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        if(z.status_code == 200):
            print("success")
        else:
            print("error")
            return '0.0.0'
        tags = json.loads(z.text)
        if(len(tags) == 0):
            return '0.0.0'
        else:
            for t in tags:
                if(t['name'][0] == 'v' and t['name'].count('.') > 1):
                    return t['name'][1:]
        return '0.0.0'

    def encrypt(self, token, file):
        print("Encrypting access token... ",end='')
        random.seed()
        with open(apt.HIDDEN+"registry/"+file+".bin", 'w') as file:
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
        with open(apt.HIDDEN+"registry/"+file+".bin", 'r') as file:
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
            pass
        return token
    pass