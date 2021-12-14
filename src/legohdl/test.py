# ------------------------------------------------------------------------------
# Project: legohdl
# Script: script.py
# Author: Chase Ruskin
# Description:
#   Runs unit-tests by enabling its block of code.
# ------------------------------------------------------------------------------

import shutil,os

from legohdl.language import Language
from .plugin import Plugin
from .map import Map
from .git import Git
from .profile import Profile
from .vendor import Vendor
from .apparatus import Apparatus as apt
from .workspace import Workspace
from .label import Label
from .vhdl import Vhdl
from .verilog import Verilog
from .unit import Unit
from .block import Block
from .cfgfile2 import Cfg, Key, Section


def main():
    'Run tests (flip to false to deactivate).'

    if(False):
        print("\n--- SCRIPT.PY ---")
        s = Plugin("superPlugin","make -f /Users/chase/Develop/HDL/SimpleCircuit/makefile alyze")
        print(s)
        m = Map()
        m['KEY'] = 2
        print(m.keys())

        print(Plugin.Jar)
        print(Plugin.Jar['superplugin'])
        s.setAlias('pluginII')
        Plugin.Jar['SCRIPTII'].setCommand("echo \"hello world!\"")
        print(Plugin.Jar['pluginII'])
        Plugin.Jar['SCRIPTII'].setCommand("")
        Plugin("SCRIPTX", "\n")
        print(Plugin.Jar['pluginII'])
        print("Dictionary:")
        print(Plugin.Jar)
        print(Plugin.Jar.__instancecheck__(Map))
        print(isinstance(Plugin.Jar, dict))
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
        print('\n---VENDOR CLASS---')
        print(Vendor.Jar)

    if(False):
        print('\n---WORKSPACE CLASS---')
        #create workspaces
        tmp_ws = "super_WS"
        other_ws = "wsII"
        Workspace(tmp_ws, "~/develop/temporal/", ['uf-ece'])
        Workspace(other_ws, "~/develop/wsII", ['OPEN-IP'])
        for nm,ws in apt.SETTINGS['workspace'].items():
            Workspace(nm, apt.SETTINGS['workspace'][nm]['path'], apt.SETTINGS['workspace'][nm]['vendor'])
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
        print('\n---VENDOR CLASS---')

        Vendor("open-ip")

        Vendor("soc-blocks", "https://gitlab.com/chase800/mymarket.git")

        Vendor('uf-ece', "https://gitlab.com/uf-eel4712c/uf-ece.git")

        #Market2("marketIII", "https://gitlab.com/chase800/mymarket.git")

        Vendor.printAll()

        Vendor.Jar['UF-ECE'].refresh()

        Vendor.tidy()

        #shutil.rmtree(Vendor.Jar['soc-blocks'].getMarketDir(), onerror=apt.rmReadOnly)
    if(False):
        print('\n---LANGUAGE CLASSES---')

        src = ['']*6
        src = ['/Users/chase/develop/eel4712c/lab1/src/fa.vhd',
            '/Users/chase/desktop/testcode/counter.v',
            '/Users/chase/desktop/testcode/fa.vhd',
            '/Users/chase/develop/eel4712c/lab1/src/adder.vhd',
            '/Users/chase/develop/eel4712c/lab2/src/alu_ns.vhd',
            '/Users/chase/develop/eel4712c/DungeonRun/main_module.vhd',
            '/Users/chase/develop/eel4712c/DungeonRun/elapsed_time.vhd']

        names = [['', 'LIB1', 'BLK1'], ['', 'LIB1', 'BLK2'], ['', 'LIB1', 'BLK1']]

        vs = Map()
        for i in range(0, 2):
            if(src[i].endswith('.vhd')):
                v = Vhdl(src[i], M=names[i][0], L=names[i][1], N=names[i][2])
                vs[v] = v.identifyDesigns()
            else:
                v = Verilog(src[i], M=names[i][0], L=names[i][1], N=names[i][2])
                vs[v] = v.identifyDesigns()

        for ul in vs.values():
            for u in ul:
                if(u.E() == 'adder'):
                    Language.ProcessedFiles[u.getFile()].decode(u)
                    print(u.getReqs())
                    Unit.Hierarchy.output(u)

        pass
    if(False):
        print('\n---ENTITY CLASS---')
        fp1 = '/Users/chase/Develop/eel4712c/lab1/src/fa.vhd'
        fp4 = '/Users/chase/Develop/eel4712c/lab1/src/adder.vhd'
        fp2 = '/Users/chase/Develop/eel4712c/lab3/src/adder.vhd'
        fp3 = '/Users/chase/Develop/eel4712c/lab4/src/top_level.vhd'
        fp5 = '/Users/chase/Develop/eel4712c/demo/led_animation/src/led_animation.vhd'

        v1 = Vhdl(fp1, L='eel4712c', N='lab1')
        v4 = Vhdl(fp4, L='eel4712c', N='lab1')
        #v2= Vhdl(fp2, L='eel4712c', N='lab3')
        v3 = Vhdl(fp3, M='uf-ece', L='eel4712c', N='lab4')

        v5 = Vhdl(fp5, M='',L='projects',N='LED_animation')
        print(v1)
        #print(v3)
        v1.decipher()
        v4.decipher()
        v5.decipher()

        # print(Unit.Jar['']['EEL4712C']['LAB1']['adder'].getInterface().writeInstance(Unit.Language.VHDL))
        # print(Unit.Jar['']['EEL4712C']['LAB1']['adder'].getInterface().writeConnections(Unit.Language.VHDL))
        # print("__Processed__")
        # print(Language._ProcessedFiles)
        # print(Unit.Jar['']['projects']['LED_animation']['led_animation'].getInterface().writeInstance(entity_inst=True, align=True, inst_name='DUT'))
        # print(Unit.Jar['']['projects']['LED_animation']['led_animation'].getInterface().writeConnections(align=True))
        #print(Unit.allL())
        # print(Unit.Jar['uf-ece']['eel4712c']['lab4']['top_level'].readAbout())
        # print(Unit.Jar['']['eel4712c']['lab1']['adder'].readAbout())
        #print(Unit.FlippedJar)

        #print(Unit.shortcut(e='fa', n='lab1'))
        print(Unit.Jar['']['EEL4712C']['LAB1']['adder'])
        

        fp01 = '/Users/chase/Develop/eel4712c/experimental/testv/src/andgate.v'
        fp02 = '/Users/chase/Develop/eel4712c/experimental/testv/src/OtherC.v'
        fp03 = '/Users/chase/Develop/eel4712c/experimental/testv/src/TestV.v'

        vl1 = Verilog(fp01, M='', L='Sample', N='Test')
        vl2 = Verilog(fp02, M='', L='Sample', N='Test')
       

        #vl1.decipher()
        #vl2.decipher()
        #Unit.printList()
        #print(Unit.Jar['']['sample']['test']['andEX'].getInterface().writeConnections())
        #print(Unit.Jar['']['sample']['test']['andEX'].getInterface().writeInstance(form=Unit.Language.VHDL))
        #print(Unit.Jar['']['sample']['test']['andEX'].getInterface().writeInstance(form=Unit.Language.VERILOG))
    
    if(False):
        print('\n---BLOCK CLASS---')
        b1 = Block(path='/Users/chase/Develop/eel4712c/lab1/')
        print(b1.init2('/Users/chase/Develop/eel4712c/lab1/'))

        b1.loadHDL()
        b1.getUnits()

        test_path = '/Users/chase/Develop/eel4712c/library1/labX/'
        b2 = Block(test_path)
        success = b2.create("open-ip2.sample.myblock", remote='https://gitlab.com/chase800/block.git')

        #clean up test block
        if(success):
            shutil.rmtree(test_path, onerror=apt.rmReadOnly)
    if(True):
        comments = {}

        #open the info.txt
        with open(apt.getProgramPath()+'./data/info.txt', 'r') as info:
            txt = info.readlines()
            disp = False
            key = ''
            for line in txt:
                sep = line.split()
                #skip comments and empty lines
                if(len(sep) == 0):
                    if(disp == True):
                        print()
                    continue
                if(sep[0].startswith(';')):
                    continue
                #find where to start
                if(len(sep) > 1 and sep[0] == '*'):
                    key = sep[1].lower()
                    if(key == 'settings-header'):
                        key = ''
                    comments[key] = ''
                    disp = True
                elif(disp == True):
                    if(sep[0] == '*'):
                        break
                    else:
                        end = line.rfind('\\')
                        if(end > -1):
                            line = line[:end]
                        comments[key] = comments[key] + line
            pass
        c = Cfg('./input.cfg', comments=comments)
        c.read()
        print(c.get('general.key2', dtype=str))

        print(Cfg.castStr(c.get('BLOCK.requires', dtype=list), frmt_list=True))

        print(c.get('block.REQUIRES', dtype=list))

        b = c.get('block', dtype=dict)

        b['VENDOR'] = 'uf-ece'

        c.set('block', b)
        c.set('block.VeRSIONS', 11)
        #c.set('block', b)

        print(c.get('general', dtype=dict))

        c.set('block.requires', Cfg.castStr(c.get('BLOCK.requires', dtype=list), tab_cnt=1, frmt_list=True))

        c.write(auto_indent=True, neat_keys=True)

        k = Key("KEY0", "0x3234ab")
        k._val = k._val + "ce"
        print(k)
        print(k._name)

        levels = c.get('general.level2c', dtype=dict, returnkey=True)
        print(levels._name)
        for i in levels.keys():
            print(levels[i]._name)


        d = Section(name="Block")

        d['name'] = 'lab1'
        print(d._name)
        print(str(d))

        ws = c.get('workspace', dtype=dict)
        print(ws['eel4712c']._name)
        print(ws)
        ws['eel4712c']['path'] = '/other/way/'
        print(ws)
        print(c.get('workspace', dtype=dict))

        #case-insensitive on accessing
        print(c.get('BLOCK.VENDOR'))
        print(c.get('BLoCK.veNdoR'))

        c.set('workspace', ws, override=True)
        print(c.get('workspace', dtype=dict))

        print(c.get('general.key', dtype=int) == 10)
        newfile = {'Block': {'NAME' : '', 'library' : '', 'vendor' : '', 'version' : '0.0.0'}}
        meta = Cfg('./output2.cfg', data=Section(newfile))
        meta.read()
        #meta.write(auto_indent=False)

        cfgsettings = Cfg('./output3.cfg', data=Section(), comments=comments)
        #load settings
        cfgsettings.read()
        print(cfgsettings._filepath)
        print(cfgsettings._data)
        #reload any missing settings

        print(Section(apt.LAYOUT))
        cfgsettings.set('', Section(apt.LAYOUT), override=False)
        print(cfgsettings._data)
        #print(cfgsettings.get('', dtype=dict))
        cfgsettings.write()
    pass