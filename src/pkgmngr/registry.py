#registry.py is in charge of seeing what packages are hosted remotely and syncing
#packages between user and remote

from enum import Enum
import random
import requests
import json
from bs4 import BeautifulSoup
import os
try:
    from pkgmngr import capsule as caps
except:
    import capsule as caps

class Repo:
    def __init__(self, l_a, lib, name, l_v, g_url, m_b='master'):
        self.last_activity = l_a
        self.library = lib
        self.name = name
        self.last_version = l_v
        self.m_branch = m_b
        self.downloaded = False
        self.git_url = g_url
    pass

class Registry:
    class Mode(Enum):
        GITLAB = 1,
        GITHUB = 2,
        OTHER = 3
        pass

    def listCaps(self):
        print("\nList of available modules:")
        print("\tModule\t\t    local\t    version")
        print("-"*80)
        for key,repo in self.__remote_reg.items():
            hdr = ''
            if(repo.library != ''):
                hdr = repo.library+'.'
            title = hdr+repo.name
        
            cp = caps.Capsule(repo.name)
            isDownloaded = '-'
            info = ''
            ver = repo.last_version
            if (cp.isValid()):
                isDownloaded = 'y'
                loc_ver = ''
                loc_ver = self.fetchVersion(cp, False)
                if((ver != '' and loc_ver == '') or (ver != '' and ver > loc_ver)):
                    info = '(update)-> '+ver
                    ver = loc_ver
            print("  ",'{:<26}'.format(title),'{:<14}'.format(isDownloaded),'{:<10}'.format(ver),info)
        pass

    def parseURL(self, website):
        i =  self.__url.find(website)
        i_2 = (self.__url[i:]).find('/')

        self.__tail_url = self.__url[i+i_2:]
        self.__base_url = self.__url[:i+i_2]
        pass

    def __init__(self, url):
        self.__url = url
        self.__base_url = url
        self.__tail_url = url
        self.__hidden = os.path.expanduser("~/.legoHDL/") #TO-DO: fix dupe writing
        self.__local_path = self.__hidden+"registry/"
        
        self.__local_reg = dict()
        self.__remote_reg = dict()

        self.localLoad()

        print(url)
        #determine what remote website is being used
        self.__mode = None
        if(self.__url.count('gitlab') > 0):
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
                self.__local_reg[int(iden)] = Repo(l_a=line[Rspce+1:spk], lib=line[spce+1:dot], g_url=line[at+1:], name=line[dot+1:eq], l_v=line[eq+1:Rspce], m_b=line[spk+1:at])
                #print(self.__local_reg[int(iden)].last_activity)
            file.close()

    def localSync(self):
        for key,repo in self.__remote_reg.items():
                #update information and add to local if not registered
                self.__local_reg[key] = repo

        with open(self.__local_path+"db.txt", 'w') as file:
            for key,repo in self.__local_reg.items():
                line = str(key)+" "+repo.library+"."+repo.name+"="+repo.last_version+" "+repo.last_activity+"*"+repo.m_branch+"@"+repo.git_url
                file.write(line+"\n")
            file.close()
        pass


    def findProjects(self):
        #using only requests module to print out project list
        link = self.__base_url+"/api/v4/groups/"+self.__tail_url+"/projects?include_subgroups=True&simple=True"
        print(link)
        #z = requests.get(link, headers={'PRIVATE-TOKEN': tk}))
        tk = self.decrypt('gl-token')
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        print("status: ",z)
        return json.loads(z.text)

    def fetch(self):
        projectList = self.findProjects()
        for x in projectList:
            #print(x['name'])
            #print(x['name_with_namespace'])
            lib = x['name_with_namespace']
            last_i = lib.rfind('/')
            first_i = (lib[:last_i-1]).rfind('/')
            lib = lib[first_i+2:last_i-1]
            if(first_i == -1):
                lib = ''
            #print(lib)
            #print(x['web_url'])
            #print(x['id'])
            #check if there has been new activity
            #print(x['last_activity_at'])
            #print(x['default_branch'])
            #local registry already has a tab on this remote repo
            last_ver = '0.0.0'
            if((x['id'] in self.__local_reg)):
                last_ver = self.__local_reg[x['id']].last_version
                if(x['last_activity_at'] > self.__local_reg[x['id']].last_activity):
                    #fetch version number to see if there is an update available
                    last_ver = self.grabTags(x)
                pass
            else: #local registry needs all info on this repo
                last_ver = self.grabTags(x)

            self.__remote_reg[x['id']] = Repo(l_a=x['last_activity_at'], lib=lib, g_url=x['web_url']+'.git', name=x['name'], l_v=last_ver, m_b=x['default_branch'])
        
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