from genericpath import isdir
import os,shutil,git
import logging as log
import copy
from .apparatus import Apparatus as apt
import yaml

class Market:

    def __init__(self, name, url):
        self._name = name
        self.url = url
        self._local_path = apt.HIDDEN+"registry/"+self._name
        #is there not a git repository here? if so, need to init
        if(not os.path.isdir(self._local_path+"/.git")):
            valid_remote = False
            if(url != None):
                valid_remote = apt.isValidURL(url)
                url_name = url[url.rfind('/')+1:url.rfind('.git')]
            if(valid_remote):
                git.Git(apt.HIDDEN+"registry/").clone(url)
                log.info("Found and linked remote repository to "+self._name)
            else:
                git.Repo.init(self._local_path)
                log.warning("No remote repository configured for "+self._name)
                url_name = self._name
            os.rename(apt.HIDDEN+"registry/"+url_name, self._local_path)
            
        self._repo = git.Repo(self._local_path)
        pass

    def getName(self):
        return self._name

    def delete(self):
         if(os.path.exists(self._local_path)):
                shutil.rmtree(self._local_path, onerror=apt.rmReadOnly)

    def setRemote(self, url):
        if((self.isRemote() and self._repo.remotes.origin.url != self.url) or (not self.isRemote())):
            if(url == None):
                return None
            valid_remote = apt.isValidURL(url)
            #is this a valid remote path? if it is and we have no origin, make it linked!
            if(not self.isRemote() and valid_remote):
                self._repo.create_remote('origin', self.url)
                log.info("Creating link for "+self._name+" to "+self.url+"...")
            elif(self.isRemote() and valid_remote):
            #is this a valid remote path? do we already have one? if we already have a remote path, delete folder
                log.info("Swapping link for "+self._name+" to "+self.url+"...")
                if(os.path.exists(self._local_path)):
                    shutil.rmtree(self._local_path, onerror=apt.rmReadOnly)
                git.Git(apt.HIDDEN+"registry/").clone(url) #and clone from new valid remote path
                url_name = url[url.rfind('/')+1:url.rfind('.git')]
                os.rename(apt.HIDDEN+"registry/"+url_name, self._local_path)
            else:
                log.error("Invalid link- setting could not be changed")
                if(self.isRemote() and url != None):
                    self.url = self._repo.remotes.origin.url
        return self.url

    #release a block to this market
    def publish(self, meta, options=[], all_vers=[]):
        #file kept in markets to remember all valid release points
        log_file = "version.log"

        if(self.url != None):
            #refresh remote
            if(len(self._repo.remotes)):
                log.info("Refreshing "+self.getName()+"... "+self.url)
                self._repo.git.pull()  
            #create remote origin
            else:
                if(apt.isValidURL(self.url)):
                    self._repo.git.remote("add","origin",self.url)
                else:
                    log.warning("Remote does not exist for market "+self.getName())
                    self.url = None

        active_branch = self._repo.active_branch
        #switch to side branch if '-soft' flag raised
        tmp_branch = meta['library']+"."+meta['name']+"-"+meta['version']
        if(self.url != None and options.count("soft")):
            log.info("Creating new branch ["+tmp_branch+"] to release block to: "+self.getName())
            self._repo.git.checkout("-b",tmp_branch)

        #locate block's directory within market
        block_dir = self._local_path+"/"+meta['library']+"/"+meta['name']+"/"
        os.makedirs(block_dir,exist_ok=True)
        #read in all loggin info about valid release points
        file_data = []
        if(os.path.exists(block_dir+log_file)):
            with open(block_dir+log_file,'r') as f:
                file_data = f.readlines()
                pass
        #insert any versions not found in file_data to also be valid release points to version.log
        for old_ver in all_vers:
            #skip our current version
            if(old_ver[1:] == meta['version']):
                continue
            if(old_ver+"\n" not in file_data):
                file_data.append(old_ver+"\n")

        #insert this version as a new valid release point to version.log
        with open(block_dir+log_file,'w') as f:
            f.write('v'+meta['version']+"\n")
            for line in file_data:
                f.write(line)
            pass

        #save yaml file
        with open(block_dir+apt.MARKER, 'w') as file:
            for key in apt.META:
                #pop off front key/val pair of yaml data
                single_dict = {}
                single_dict[key] = meta[key]
                yaml.dump(single_dict, file)
                pass
            pass
            file.close()
        #save changes to repository (only add and stage the file that was made)
        self._repo.index.add(block_dir+apt.MARKER)
        self._repo.index.add(block_dir+log_file)
        pass
        
        #commit all releases
        self._repo.index.commit("Adds "+meta['library']+'.'+meta['name']+" v"+meta['version'])
        #push to remote market repository
        if(self.url != None):
            self._repo.git.push("-u","origin",str(self._repo.head.reference))
            self._repo.git.checkout(active_branch)
            # delete soft/tmp branch that was created for release
            if(options.count("soft")):
                self._repo.git.branch("-d",tmp_branch)
        pass

    #return true is configured to a remote repository
    def isRemote(self):
        return len(self._repo.remotes)

    def getPath(self):
        return self._local_path

    def __str__(self):
        return f"{self._name}, {self.url}"
    pass

#legacy code for publish function that would add all unreleased release points,
# function took in all_vers=[]
#(
        # #add all releases that haven't been available here
        # for v in all_vers:
        #     #skip versions that already exist
        #     if v[1:] in released_vers:
        #         continue
        #     #create new directory (occurs ONLY ONCE with a new version tag because folder will be made)
        #     fp = block_dir+v[1:]+"/"
        #     os.makedirs(fp)

        #     #checkout the block at that tag if this is not the right meta
        #     tmp_meta = apt.getBlockFile(repo, v)
        #     #override tmp_meta with the current metadata on deck
        #     if(meta['version'] == v[1:]):
        #         tmp_meta = copy.deepcopy(meta)
        #     #must be a valid release point to upload block version
        #     if(tmp_meta != None):
        #         #ensure this yaml file has the correct "remote" and "market"
        #         tmp_meta['remote'] = meta['remote']
        #         tmp_meta['market'] = meta['market']
        #         #tmp_meta['library'] = meta['library']
        #         #tmp_meta['name'] = meta['name']
        #         #save yaml file
        #         with open(fp+apt.MARKER, 'w') as file:
        #             for key in apt.META:
        #                 #pop off front key/val pair of yaml data
        #                 single_dict = {}
        #                 single_dict[key] = tmp_meta[key]
        #                 yaml.dump(single_dict, file)
        #                 pass
        #             pass
        #             file.close()
        #         #save changes to repository (only add and stage the file that was made)
        #         self._repo.index.add(fp+apt.MARKER)
        #     pass
#   )