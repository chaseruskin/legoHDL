# Project: legohdl
# Script: script.py
# Author: Chase Ruskin
# Description:
#   Runs unit-tests by enabling its block of code.

from .script import Script
from .map import Map
from .git import Git
import shutil
from .apparatus import Apparatus as apt
import os

def main():
    apt.load()
    #run tests (flip to false to deactivate)
    if(False):
        print("--- SCRIPT.PY ---")
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

    if(True):
        print('--- GIT CLASS ---')
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
    pass