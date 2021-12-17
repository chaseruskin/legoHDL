# ------------------------------------------------------------------------------
# File: demo.py
# Author: Chase Ruskin
# Modified: 12/15/2021
# Created: 09/19/2021
# Plugin: demo
# Usage:
#   legohdl build +demo (-lint | -synth | -route | -sim)
#
# Description:
#   A fake EDA tool script to be a plugin for legoHDL.
#
#   This script is used in the tutorials for legoHDL and can be an outline
#   for how a developer can structure a plugin. In this plugin, workflows 
#   are executed that only print related information to the console. Supports
#   custom label PIN-MAP for reading .csv files during route stage.
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
  legohdl build +demo (-lint | -synth | -route | -sim)

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

# === Collect data from the blueprint file =====================================
#   Gather the data available from the blueprint to be able to use it for some
#   desirable task.
# ==============================================================================

#enter the 'build' directory; this is where the blueprint file is located
if(os.path.exists('build') == False or os.path.exists('build/blueprint') == False):
    exit("Error: Export a blueprint file before running this plugin.")

os.chdir('build')

#set up variables to store data from blueprint
src_files = {'VHDL' : [], 'VLOG' : []}
sim_files = {'VHDL' : [], 'VLOG' : []}
lib_files = {'VHDL' : {}, 'VLOG' : {}}
top_design = top_testbench = None
pin_file = None

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

        #add support for custom pin-assignment file using .csv
        elif(label == "@PIN-MAP"):
            pin_file = filepath

    pass


# === Act on the collected data ================================================
#   Now that we have the data, call your tool to perform a specific task with
#   this data.
# ==============================================================================

#[!] perform syntax checking
if(lint):
    execute(TOOL_PATH,"PSEUDO SYNTAX CHECKER")
    print("Analyzing files...")
    #print souce files being analyzed
    for l in src_files.keys():
        for f in src_files[l]:
            print(l,f)
    #print simulation fies being analyzed
    for l in sim_files.keys():
        for f in sim_files[l]:
            print(l,f)
    print('Analysis complete.')
    pass

#[!] perform simulation
elif(simulate):    
    if(top_testbench == None):
        exit("Error: No toplevel testbench found.")

    #call our pseudo-tool
    execute(TOOL_PATH,"PSEUDO SIMULATOR")

    print('Compiling files...')
    #print souce files being compiled
    for l in src_files.keys():
        for f in src_files[l]:
            print(l,f)
    #print simulation fies being compiled
    for l in sim_files.keys():
        for f in sim_files[l]:
            print(l,f)
    print('Running simulation using testbench '+top_testbench+'...')
    print('Simulation complete.')
    pass

#[!] perform synthesis
elif(synthesize):
    if(top_design == None):
        exit("Error: No toplevel design found.")

    #call our pseudo-tool
    execute(TOOL_PATH,"PSEUDO SYNTHESIZER")

    print('Synthesizing design for toplevel '+top_design+'...')
    #print all files being synthesized
    for l in src_files.keys():
        for f in src_files[l]:
            print(l,f)
    #print all files from libraries (external from project)
    for f_type in lib_files.keys():
        for lib in lib_files[f_type].keys():
            for f in lib_files[f_type][lib]:
                print(f_type,lib,f)
    print('Synthesis complete.')
    pass

#[!] perform routing/fitting
elif(route):
    if(pin_file == None):
        exit("Error: no routing file (.csv) was found for label @PIN-MAP.")

    pin_assignments = []
    #open and read data from pin mapping file
    with open(pin_file, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            #skip empty lines
            if(len(line) == 0):
                continue
            #split by comma
            parts = line.split(',')
            #add to pin assignments
            if(len(parts) > 1):
                pin_assignments += [(parts[0], parts[1])]
            pass

    #call our pseudo-tool
    execute(TOOL_PATH,"PSEUDO PIN MAPPER")

    print("Routing pins for device "+DEVICE+"...")
    for grps in pin_assignments:
        print(grps[0],'-->',grps[1])
    print("Pin assignments complete.")
    pass

#[!] Perform no action
else:
    exit(HELP_TXT)