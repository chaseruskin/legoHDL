#registry.py is in charge of seeing what packages are hosted remotely and syncing
#packages between user and remote

from enum import Enum
import random
import requests
import json
import yaml
from bs4 import BeautifulSoup
import os
from collections import OrderedDict
try:
    from pkgmngr import capsule as caps
    from pkgmngr import repo
except:
    import capsule as caps
    import repo

class Registry:
    class Mode(Enum):
        GITLAB = 1,
        GITHUB = 2,
        LOCAL = 3,
        OTHER = 4
        pass

    def __init__(self, url):
        self.__url = url
        self.__base_url = url
        self.__tail_url = url
        self.__hidden = os.path.expanduser("~/.legoHDL/") #TO-DO: fix dupe writing
        self.__local_path = self.__hidden+"registry/"
        
        self.__local_reg = dict()
        self.__remote_reg = dict()
        self.__cur_reg = dict()

        self.localLoad()

        print(url)
        #determine what remote website is being used
        self.__mode = None
        if(not caps.Capsule.linkedRemote()):
            self.__mode = self.Mode.LOCAL
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
                self.__local_reg[int(iden)] = repo.Repo(l_a=line[Rspce+1:spk], lib=line[spce+1:dot], g_url=line[at+1:], name=line[dot+1:eq], l_v=line[eq+1:Rspce], m_b=line[spk+1:at], l_path='')
            file.close()

    def listCaps(self, options):
        reg = self.__remote_reg
        sorted_reg = OrderedDict()
        if(not caps.Capsule.linkedRemote()):
            reg = self.__local_reg
        if(options.count('alpha')):
            for key,repo in reg.items():
                sorted_reg[repo.library+repo.name] = repo
            reg = sorted_reg

        print("\nList of available modules:")
        print("\tModule\t\t    local\t    version")
        print("-"*80)
        for key,repo in reg.items():
            hdr = ''
            if(repo.library != ''):
                hdr = repo.library+'.'
            title = hdr+repo.name
            
            cp = caps.Capsule(rp=repo)
            isDownloaded = '-'
            info = ''
            ver = repo.last_version
            if (cp.isValid()):
                isDownloaded = 'y'
                loc_ver = ''
                loc_ver = cp.getVersion()
                if((ver != '' and loc_ver == '') or (ver != '' and ver > loc_ver)):
                    info = '(update)-> '+ver
                    ver = loc_ver
            
            if((options.count('local') and cp.isValid()) or not options.count('local')):
                print("  ",'{:<26}'.format(title),'{:<14}'.format(isDownloaded),'{:<10}'.format(ver),info)
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
        #print("LOCAL",self.__local_reg)
        #remove any projects not found remotely and not found locally
        for k in oldKeys:
            if(caps.Capsule.linkedRemote()):
                if not k in curKeys and not k in self.__remote_reg.keys():
                    del self.__local_reg[k]
            elif not k in curKeys:
                del self.__local_reg[k]
        
        #add any found projects that are not currently in local reg
        for k in curKeys:
            self.__local_reg[k] = self.__cur_reg[k] 

        for key,repo in self.__remote_reg.items():
                #update information and add to local if not registered
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
        if(caps.Capsule.linkedRemote()):
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
                self.createSubgroup(r.library, self.getGroup())
                subs.append(r.library)

            if(not r.name in prjs):
                c = caps.Capsule(rp=r)
                c.genRemote()
                c.saveID(self.fetchProject(r.library,r.name)['id'])
                prjs.append(r.name)
        pass

    def findProjectsLocal(self, path):
        branches = list(os.listdir(path))
        for leaf in branches:
            if(os.path.isdir(path+leaf) and leaf[0] != '.'):
                    self.findProjectsLocal(path+leaf+'/')
            if(leaf.count(".yml") > 0):
                #print("valid project!")  
                l = path.rfind('/')
                #print(path[l+1:])
                with open (path+leaf, 'r') as f:
                    tmp = yaml.load(f, Loader=yaml.FullLoader)
                    f.close()
                    #print(leaf)
                    #print(tmp['id'])
                    #print(path)
                    self.__cur_reg[int(tmp['id'])] = repo.Repo(l_a='', lib=tmp['library'], name=tmp['name'], l_v=tmp['version'], g_url='', m_b='', l_path=path)
        pass

    def findPrj(self, lib, name):
        for key,r in self.getLocalPrjs().items(): #LOCAL = ALL, #REMOTE = REMOTE, #CUR = ONLY LOCAL
            if(r.library == lib and r.name == name):
                return key,r
        return -1,None

    def getCurPrjs(self):
        return self.__cur_reg

    def getRemotePrjs(self):
        return self.__remote_reg

    def getLocalPrjs(self):
        return self.__local_reg

    def assignRandomID(self):
        id = random.randint(10000000, 99999999)
        while id in self.__local_reg.keys():
            id = random.randint(10000000, 99999999)
        return id

    def createSubgroup(self, name, parent):
        link = self.__base_url+"/api/v4/groups/?name="+name+"&path="+name+"&visibility=private&parent_id="+str(parent['id'])
        tk = self.decrypt('gl-token')
        z = requests.post(link, headers={'PRIVATE-TOKEN': tk})
        print("status: ",z)

    def getGroup(self, web_path_ext=''):
        link = self.__base_url+"/api/v4/groups/"+self.__tail_url+"/"+web_path_ext
        tk = self.decrypt('gl-token')
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        print("status: ",z)
        return json.loads(z.text)

    def findProjectsRemote(self):
        #using only requests module to print out project list
        link = self.__base_url+"/api/v4/groups/"+self.__tail_url+"/projects?include_subgroups=True&simple=True"
        print(link)
        tk = self.decrypt('gl-token')
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        print("status: ",z)
        return json.loads(z.text)

    def fetchProject(self, library, name):
        plist = self.findProjectsRemote()

        if('error' in plist):
            print("ERROR- "+plist['error'])
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
        projectList = self.findProjectsRemote()

        if('error' in projectList):
            print("ERROR- "+projectList['error'])
            return
        
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
                #print(x['last_activity_at'])
                if(x['last_activity_at'] > self.__local_reg[x['id']].last_activity):
                    #fetch version number to see if there is an update available
                    last_ver = self.grabTags(x)
                pass
            else: #local registry needs all info on this repo
                last_ver = self.grabTags(x)

            self.__remote_reg[x['id']] = repo.Repo(l_a=x['last_activity_at'], lib=lib, g_url=x['web_url']+'.git', name=x['name'], l_v=last_ver, m_b=x['default_branch'], l_path='')
        
        self.localSync()
        pass

    def grabTags(self, prj):
        print("GRABBING TAGS")
        tk = self.decrypt('gl-token')
        link = self.__base_url+"/api/v4/projects/"+str(prj['id'])+"/repository/tags"
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        tags = json.loads(z.text)
        if(len(tags) == 0):
            return '0.0.0'
        else:
            return tags[0]['name'][1:]

    def encrypt(self, token, file):
        random.seed()
        with open(self.__hidden+file+".bin", 'w') as file:
            for letter in token:
                secret = bin(ord(letter))[2:]
                secret = ((8-len(secret))*"0")+secret #pad to make fixed 8-bits
                for x in range(len(secret)):
                    file.write(str(random.randint(0, 1)) + secret[x])
                pass
        print("Successfully encrypted access token")
        pass

    def decrypt(self, file):
        token = ''
        with open(self.__hidden+file+".bin", 'r') as file:
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