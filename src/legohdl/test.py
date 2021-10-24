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
from .label import Label
from .language import Language
from .vhdl import Vhdl
from .verilog import Verilog
from .unit import Unit


def main():
    'Run tests (flip to false to deactivate).'

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
        
        apt.execute('legohdl','new', tmp_lib+'.'+tmp_name)
        
        #enter block's directory
        os.chdir(tmp_dir)

        grepo = Git(os.getcwd())
        print(grepo)
        open('myfile.txt','w').close()
        open('myfile.txt2','w').close()
        grepo.commit('myfile.txt')
        grepo.add('myfile.txt', 'myfile.txt2')
        grepo.commit('hello!')
        print("bad repo:")
        print(grepo.isValidRepo('https://myplace.git', remote=True))
        print("pong repo ssh:")
        print(Git.isValidRepo('git@gitlab.com:chase800/pong.git', remote=True))
        print('pong repo https:')
        print(Git.isValidRepo('https://gitlab.com/chase800/pong.git', remote=True))
        print(Git.isBlankRepo('https://gitlab.com/chase800/pong.git', remote=True))
        print('blank repo:')
        print(Git.isValidRepo('https://gitlab.com/chase800/blank.git', remote=True))
        print(Git.isBlankRepo('https://gitlab.com/chase800/blank.git', remote=True))
        print('real repo:')
        print(Git.isBlankRepo('/users/chase/desktop/tmp/'))

        print('cloning tests:')
        rep1 = Git('/users/chase/desktop/myBlock', clone='https://gitlab.com/chase800/blank.git')


        print('remote url tests:')
        print(rep1.getRemoteName())
        print(rep1.getRemoteURL())
        print(grepo.getRemoteName())
        print(grepo.getRemoteURL())

        print(grepo)

        print(rep1)
        grepo.setRemoteURL('https://myplace.git')
        print(grepo)
        grepo.setRemoteURL('https://gitlab.com/chase800/blank.git')
        print(grepo)
        #clean up block
        shutil.rmtree(tmp_dir, onerror=apt.rmReadOnly)
        pass

    if(False):
        print('\n---MARKET CLASS---')
        print(Market.Jar)

    if(False):
        print('\n---WORKSPACE CLASS---')
        #create workspaces
        tmp_ws = "super_WS"
        other_ws = "wsII"
        Workspace(tmp_ws, "~/develop/temporal/", ['uf-ece'])
        Workspace(other_ws, "~/develop/wsII", ['OPEN-IP'])
        for nm,ws in apt.SETTINGS['workspace'].items():
            Workspace(nm, apt.SETTINGS['workspace'][nm]['path'], apt.SETTINGS['workspace'][nm]['market'])
        Workspace.tidy()
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
        Workspace.getActive().autoRefresh(rate=-1)
        print(Workspace.getActive())
        print(tmp)
        print(other)
        #remove workspace
        tmp.remove()
        other.remove()

    if(False):
        print('\n---PROFILE CLASS---')

        tmp = Profile("Loadout_I")
        print(Profile.Jar)
        print(tmp)

        Profile("eel4712c")
        Profile("DEFAULT")
        print(Profile.Jar)

        Profile("loadout_XI", url='https://github.com/uf-eel4712c/profile.git')
        l_x = Profile("something", url='/users/chase/desktop/myprofile/')

        print(Profile.Jar["loadout_10"])
        print(Profile.Jar['default'])
        print(Profile.Jar['EEL4712C'])
        tmp.setName("Loadout_II")
        print(tmp)
        print(Profile.Jar)
        print("Last import:",Profile.ReadLastImport())

        l_x.importLoadout()
        #Profile.Jar['EEL4712C'].importLoadout(ask=True)

        tmp.remove()
        
    if(False):
        print('\n---LABEL CLASS---')

        t = Label("PY-MODEL", ['*.py'], False)
        Label("BDF", ['*.bdf'], False)
        Label("MATLAB", ['*.m, *.matlab'], False)
    
        print(t)

        t.setExtensions(['*.pyc', '*.python'])

        print(Label.Jar)

        print(Label.Jar[t.getName()])

        t.setName("PYTHON-CODE")

        print(Label.Jar[t.getName()])

    if(False):
        print('\n---MARKET CLASS---')

        Market("open-ip")

        Market("soc-blocks", "https://gitlab.com/chase800/mymarket.git")

        Market('uf-ece', "https://gitlab.com/uf-eel4712c/uf-ece.git")

        #Market2("marketIII", "https://gitlab.com/chase800/mymarket.git")

        Market.printAll()

        Market.Jar['UF-ECE'].refresh()

        Market.tidy()

        #shutil.rmtree(Market.Jar['soc-blocks'].getMarketDir(), onerror=apt.rmReadOnly)
    
    if(True):
        print('\n---ENTITY CLASS---')
        fp1 = '/Users/chase/Develop/eel4712c/lab1/src/fa.vhd'
        fp4 = '/Users/chase/Develop/eel4712c/lab1/src/adder.vhd'
        fp2 = '/Users/chase/Develop/eel4712c/lab3/src/adder.vhd'
        fp3 = '/Users/chase/Develop/eel4712c/lab4/src/top_level.vhd'
        fp5 = '/Users/chase/Develop/eel4712c/demo/led_animation/src/led_animation.vhd'

        v1 = Vhdl(fp4, L='eel4712c', N='lab1')
        #v2= Vhdl(fp2, L='eel4712c', N='lab3')
        v3 = Vhdl(fp3, M='uf-ece', L='eel4712c', N='lab2')

        v5 = Vhdl(fp5, M='',L='projects',N='LED_animation')
        print(v1)
        #print(v3)

        v1.decipher()
        v5.decipher()

        #print(Unit.Jar['']['EEL4712C']['LAB1']['fA'])
        print("__Processed__")
        print(Language._ProcessedFiles)

        #print(Unit.allL())

        #print(Unit.FlippedJar)

        #print(Unit.shortcut(e='fa', n='lab1'))

    pass