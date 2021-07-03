#registry.py is in charge of seeing what packages are hosted remotely and syncing
#packages between user and remote

from enum import Enum
import random
import requests
import json
from bs4 import BeautifulSoup

class Registry:
    class Mode(Enum):
        GITLAB = 1,
        GITHUB = 2
        pass

    def __init__(self, url):
        self.__url = url
        self.__base_url = url
        self.__tail_url = url
        print(url)
        #determine what remote website is being used
        self.__mode = None
        if(self.__url.count('gitlab') > 0):
            self.__mode = self.Mode.GITLAB
            i =  self.__url.find('gitlab')
            i_2 = (self.__url[i:]).find('/')

            self.__tail_url = self.__url[i+i_2:]
            self.__base_url = self.__url[:i+i_2]
        elif(self.__url.count('github') > 0):
            self.__mode = self.Mode.GITHUB

    
    def fetch(self):
        #using only requests module to print out project list
        link = self.__base_url+"/api/v4/groups/"+self.__tail_url+"/projects?include_subgroups=True"
        print(link)
        #z = requests.get(link, headers={'PRIVATE-TOKEN': tk}))
        tk = 'jaMFRQmnKx1v1szM6e47'
        z = requests.get(link, headers={'PRIVATE-TOKEN': tk})
        print("status: ",z)
        projectList = json.loads(z.text)
        for x in projectList:
           print(x['name'])
           print(x['name_with_namespace'])
           print(x['topics'])
        pass

    def setTokenKey(self, token):

        pass

    def encrypt(self, token, filename="token"):
        random.seed()
        with open(self.hidden+filename+".bin", 'w') as file:
            for letter in token:
                secret = bin(ord(letter))[2:]
                secret = ((8-len(secret))*"0")+secret #pad to make fixed 8-bits
                for x in range(len(secret)):
                    file.write(str(random.randint(0, 1)) + secret[x])
                pass
        pass

    def decrypt(self, filename="token"):
        token = ''
        with open(self.pkgmngPath+filename+".bin", 'r') as file:
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