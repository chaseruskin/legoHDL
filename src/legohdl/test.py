# Project: legohdl
# Script: script.py
# Author: Chase Ruskin
# Description:
#   Runs unit-tests by enabling its block of code.

from .script import Script
from .map import Map
from .git import Git
from .profile import Profile
import shutil
from .market import Market
from .apparatus import Apparatus as apt
import os
from .workspace import Workspace

def main():
    apt.load()
    #run tests (flip to false to deactivate)
    if(False):
        print("\n--- SCRIPT.PY ---")
        s = Script("superScript","make -f /Users/chase/Develop/HDL/SimpleCircuit/makefile alyze")
        print(s)
        m = Map()
        m['KEY'] = 2
        print(m.keys())

        print(Script.Jar)
        print(Script.Jar['superscript'])
        s.setAlias('scriptII')
        Script.Jar['SCRIPTII'].setCommand("echo \"hello world!\"")
        print(Script.Jar['scriptII'])
        Script.Jar['SCRIPTII'].setCommand("")
        Script("SCRIPTX", "\n")
        print(Script.Jar['scriptII'])
        print("Dictionary:")
        print(Script.Jar)
        print(Script.Jar.__instancecheck__(Map))
        print(isinstance(Script.Jar, dict))
        pass

    if(False):
        print('\n--- GIT CLASS ---')
        #create temporary new block
        tmp_lib = 'Test'
        tmp_name = 'temporal'
        tmp_dir = apt.getLocal()+tmp_lib+'/'+tmp_name+'/'

        if(os.path.exists(tmp_dir)):
            shutil.rmtree(tmp_dir, onerror=apt.rmReadOnly)
        
        apt.execute('legohdl','new',tmp_lib+'.'+tmp_name)
        
        #enter block's directory
        os.chdir(tmp_dir)

        grepo = Git(os.getcwd())
        print(grepo)
        open('myfile.txt','w').close()
        open('myfile.txt2','w').close()
        grepo.commit('myfile.txt')
        grepo.add('myfile.txt', 'myfile.txt2')
        grepo.commit('hello!')
        grepo.setRemote('https://myplace.git')
        #clean up block
        #shutil.rmtree(tmp_dir, onerror=apt.rmReadOnly)
        pass
    if(False):
        print('\n---MARKET CLASS---')
        print(Market.Jar)
    if(True):
        print('\n---WORKSPACE CLASS---')
        #create workspaces
        tmp_ws = "super_WS"
        other_ws = "wsII"
        Workspace(tmp_ws, "~/develop/temporal/", ['uf-ece'])
        Workspace(other_ws, "~/develop/wsII", ['OPEN-IP'])
        #grab workspace from Jar
        tmp = Workspace.Jar[tmp_ws]
        other =  Workspace.Jar[other_ws]
        print(Workspace.Jar)
        print(tmp)

        #assign active
        Workspace.setActiveWorkspace(other_ws)
        print("[!] CHANGING WORKSPACE NAME [!]")
        print(Workspace.Jar)
        print(other)
        other.setName("wsIV")
        print(Workspace.Jar)
        print(other)
        #link markets
        tmp.linkMarket("anotherMrkt")
        tmp.linkMarket("open-ip")
        print(tmp)
        #unlink markets
        tmp.unlinkMarket("anotherMrkt")
        tmp.unlinkMarket("open-ip")
        tmp.unlinkMarket("open-ip")
        #re assign the active workspace
        Workspace.setActiveWorkspace(tmp_ws)
        print(Workspace.getActiveWorkspace())
        print(tmp)
        print(other)
        #remove workspace
        tmp.remove()
        other.remove()
    if(True):
        print('\n---PROFILE CLASS---')

        tmp = Profile("Loadout_I")
        print(Profile.Jar)
        print(tmp)

        Profile("eel4712c")
        Profile("DEFAULT")
        print(Profile.Jar)

        print(Profile.Jar['default'])
        print(Profile.Jar['EEL4712C'])
        tmp.setName("Loadout_II")
        print(tmp)
        print(Profile.Jar)
        print("Last import:",Profile.LoadLastImport())

        tmp.remove()
        pass
    pass