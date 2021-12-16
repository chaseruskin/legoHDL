# ------------------------------------------------------------------------------
# File: demo.py
# Author: Chase Ruskin
# Modified: 12/15/2021
# Created: 09/19/2021
# Plugin: demo
# Usage:
#   legohdl +demo (-lint | -synth | -route | -sim) [-gen <g1>=<val1> 
#   <g2>=<val2> ...]
#
# Description:
#   A fake EDA tool script to be a plugin for legoHDL.
#
#   This script is used in the tutorials for legoHDL and can be an outline
#   for how a developer can structure a plugin. In this plugin, workflows 
#   are executed that only print related information to the console.
#
# Options:
#   -lint
#       Simulate checking the syntax of HDL files.
#   -synth
#       Simulate synthesising the design.
#   -route
#       Simulate routing/assigning pins for the design.
#   -sim
#       Simulate a simulation is being performed with an HDL testbench.
#   -gen <generic1>=<value1> <generic2>=<value2> ...       
#       Any arguments proceeding '-gen' are VHDL generics or verilog 
#       parameters passed to the top-level design.
#
# Help:
#   https://c-rus.github.io/legoHDL/
# ------------------------------------------------------------------------------

import sys,os

# === Define constants, important variables, helper methods ====================
#   Identify any variables necessary for this plugin to work. Some examples
#   include tool path, device name, project name, device family name. 
# ==============================================================================

def execute(*code):
    '''
    Prints out the command before executing it. Exits script on bad return code.
    
    Parameters:
        code (*str): parts of a command to call
    Returns:
        None
    '''
    #format the command with spaces between each passed-in string
    code_line = ''
    for c in code:
        code_line = code_line + c + ' '
    #print command to console
    print(code_line)
    #execute the command
    rc = os.system(code_line)
    #immediately stop script upon a bad return code
    if(rc):
        exit(rc)

#path to the tool's executable (can be blank if the tool is already in the PATH)
TOOL_PATH = "echo"

#fake device name, but can be useful to be defined or to be set in command-line
DEVICE = "A2CG1099-1"

#the project will reside in a folder the same name as the current block's folder
PROJECT = os.path.basename(os.getcwd())


HELP_TXT = '''\
Plugin: demo
Usage:
  legohdl +demo (-lint | -synth | -route | -sim) [-gen <g1>=<val1> 
  <g2>=<val2> ...]

Description:
  A fake EDA tool script to be a plugin for legoHDL.

  This script is used in the tutorials for legoHDL and can be an outline
  for how a developer can structure a plugin. In this plugin, workflows 
  are executed that only print related information to the console.

Options:
  -lint
      Simulate checking the syntax of HDL files.
  -synth
      Simulate synthesising the design.
  -route
      Simulate routing/assigning pins for the design.
  -sim
      Simulate a simulation is being performed with an HDL testbench.
  -gen <generic1>=<value1> <generic2>=<value2> ...       
      Any arguments proceeding '-gen' are VHDL generics or verilog 
      parameters passed to the top-level design.
'''

# === Handle command-line arguments ============================================
#   Create custom command-line arguments to handle specific workflows and common
#   usage cases.
# ==============================================================================

#keep all arguments except the first one (the filepath is not needed)
args = sys.argv[1:]

#detect what workflow to perform
lint       = args.count('-lint')
synthesize = args.count('-synth')
simulate   = args.count('-sim')
route      = args.count('-route')

#identify if there are any generics set on command-line
generics = {}
if(args.count('-gen')):
    start_i = args.index('-gen')
    #iterate through remaining arguments to capture generic value sets
    for i in range(start_i+1, len(args)):
        #split by '=' sign
        if(args[i].count('=') == 1):
            name,value = args[i].split('=')
            generics[name] = value


# === Collect data from the blueprint file =====================================
#   Gather the data available from the blueprint to be able to use it for some
#   desirable task.
# ==============================================================================

#enter the 'build' directory; this is where the blueprint file is located
if(os.path.exists('build') == False):
    exit("Export a blueprint file before running this plugin!")

os.chdir('build')

#set up variables to store data from blueprint
src_files = {'VHDL' : [], 'VLOG' : []}
sim_files = {'VHDL' : [], 'VLOG' : []}
lib_files = {'VHDL' : {}, 'VLOG' : {}}
top_design = top_testbench = None

#read the contents of the blueprint file
with open('blueprint', 'r') as blueprint:
    lines = blueprint.readlines()
    for rule in lines:
        parsed = rule.split()
        #label is always first item
        label = parsed[0]
        #filepath is always last item
        filepath = parsed[-1]

        #add VHDL source files
        if(label == "@VHDL-SRC"):
            src_files['VHDL'].append(filepath)

        #add VHDL simulation files
        elif(label == "@VHDL-SIM"):
            sim_files['VHDL'].append(filepath)

        #add VHDL files from libraries
        elif(label == "@VHDL-LIB"):
            lib = parsed[1]
            #create new list to track all files belonging to this library
            if(lib not in lib_files['VHDL'].keys()):
                lib_files['VHDL'][lib] = []

            lib_files['VHDL'][lib].append(filepath)

        #capture the top-level design unit
        elif(label == "@VHDL-SRC-TOP" or label == "@VLOG-SRC-TOP"):
            top_design = parsed[1]

        #capture the top-level testbench unit
        elif(label == "@VHDL-SIM-TOP" or label == "@VLOG-SIM-TOP"):
            top_testbench = parsed[1]

        #add Verilog source files
        elif(label == "@VLOG-SRC"):
            src_files['VLOG'].append(filepath)

        #add Verilog library files
        elif(label == "@VLOG-LIB"):
            lib = parsed[1]
            #create new list to track all files belonging to this library
            if(lib not in lib_files['VLOG'].keys()):
                lib_files['VLOG'][lib] = []

            lib_files['VLOG'][lib].append(filepath)

        #add Verilog simulation files
        elif(label == "@VLOG-SIM"):
            sim_files['VLOG'].append(filepath)

    pass


# === Act on the collected data ================================================
#   Now that we have the data, call your tool to perform a specific task with
#   this data.
# ==============================================================================

#[!] perform syntax checking
if(lint):
    execute(TOOL_PATH,"Checking design syntax...")
    print("---FILES ANALYZED----")
    #print souce files being analyzed
    for l in src_files.keys():
        for f in src_files[l]:
            print(l,f)
    #print simulation fies being analyzed
    for l in sim_files.keys():
        for f in sim_files[l]:
            print(l,f)
    pass

#[!] perform simulation
elif(simulate):    
    if(top_testbench == None):
        exit("Error: No top level testbench found.")
    #format generics for as a command-line argument for test vector script
    generics_command = ''
    for g,v in generics.items():
        generics_command += '-'+g+'='+v+' '

    execute(TOOL_PATH,"Simulating design with tesbench...")
    print('---RUNNING SIMULATION---')
    print('TOP:',top_testbench)
    #print out any generics we set on command-line
    if(len(generics)):
        print('GENERICS SET:',)
        for g,v in generics.items():
            print(g,'=',v)
    pass

#[!] perform synthesis
elif(synthesize):
    if(top_design == None):
        exit("Error: No top level design found.")
    execute(TOOL_PATH,"Synthesizing design...")
    print('---FILES SYNTHESIZED---')
    print("TOP:",top_design)
    #print out any generics we set on command-line
    if(len(generics)):
        print('GENERICS SET:',)
        for g,v in generics.items():
            print(g,'=',v)
    #print all files being synthesized
    for l in src_files.keys():
        for f in src_files[l]:
            print(l,f)
    #print all files from libraries (external from project)
    for f_type in lib_files.keys():
        for lib in lib_files[f_type].keys():
            for f in lib_files[f_type][lib]:
                print(f_type,lib,f)
    pass

#[!] perform routing/fitting
elif(route):
    execute(TOOL_PATH,"Routing design to pins...")
    print("----PINS ALLOCATED-----")
    pin_assignments = []
    for pin,port in pin_assignments.items():
        print(pin,'-->',port)
    pass

#[!] Perform no action
else:
    exit(HELP_TXT)