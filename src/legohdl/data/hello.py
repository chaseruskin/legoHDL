# Script: hello.py
# Author: Chase Ruskin
# Creation Date: 09.19.2021
# Description:
#   Backend script that uses no EDA tool but provides an outline for one way
#   how to structure a script. A workflow is ran here by only printing related
#   information to the console.
# Default:
#   Do nothing.
# Options:
#   -lint        : lint the design
#   -synth       : synthesis the design
#   -route       : route/implement/fit the design (assign pins)
#   -sim         : simulate the design
#   -gen         : any arguments after this one are VHDL generics or verilog 
#                  parameters and will be passed to the top-level design and to 
#                  the test vector script, if available. An example of setting 
#                  generics: -gen width=10 addr=32 trunc=2
#   
# To learn more about writing your own backend scripts for legohdl, visit:
# https://hdl.notion.site/Writing-Scripts-f7fc7f75be104c4fa1640d2316f5d6ef

import sys,os

# === Define constants, important variables, helper methods ====================
#   Identify any variables necessary for this script to work. Some examples
#   include tool path, device name, project name, device family name. 
# ==============================================================================

def execute(*code):
    '''
    This method prints out the inputted command before executing it. The
    parameter is a variable list of strings that will be separated by spaces
    within the method. If a bad return code is seen on execution, this entire
    script will exit with that error code.
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
TOOL_PATH = ""

#fake device name, but can be useful to be defined or to be set in command-line
DEVICE = "A2CG1099-1"

#the project will reside in a folder the same name as this block's folder
PROJECT = os.path.basename(os.getcwd())

# === Handle command-line arguments ============================================
#   Create custom command-line arguments to handle specific workflows and common
#   usage cases.
# ==============================================================================

#keep all arguments except the first one (the filepath is not needed)
args = sys.argv[1:]

#detect what workflow to perform
lint = args.count('-lint')
synthesize = args.count('-synth')
simulate = args.count('-sim')
route = args.count('-route')

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

# === Collect data from the blueprint file ========================================
#   This part will gather the necessary data we want for our workflow so that
#   we can act accordingly on that data to get the ouptut we want.
# ==============================================================================

#enter the 'build' directory for this is where the blueprint file is located
os.chdir('build')

src_files = {'VHDL' : [], 'VLOG' : []}
sim_files = {'VHDL' : [], 'VLOG' : []}
lib_files = {'VHDL' : {}, 'VLOG' : {}}
top_design = top_testbench = None
python_vector_script = None
pin_assignments = {}

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

        #custom label: capture information regarding pin assignments
        elif(label == "@PIN-PLAN"):
            #write a custom file parser for these special files we designed to
            # extract pin information
            with open(filepath) as pin_file:
                locations = pin_file.readlines()
                for spot in locations:
                    #skip any comment lines indicated by '#'
                    comment_index = spot.find('#')
                    if(comment_index > -1):
                        spot = spot[:comment_index]
                    #separate by the comma
                    if(spot.count(',') != 1):
                        continue
                    #organize into fpga pin and port name
                    pin,name = spot.split(',')
                    pin_assignments[pin.strip()] = name.strip()

        #custom label: capture the python test vector script if avaialable
        elif(label == "@PY-MODEL"):
            python_vector_script = filepath.strip()

    #done collecting data for our workflow
    blueprint.close()

# === Act on the collected data ================================================
#   Now that we have the 'ingredients', write some logic to call your tool
#   based on the data we collected. One example could be to use the collected
#   data to write a TCL script, and then call your EDA tool to use that TCL
#   script.
# ==============================================================================

#simulation
if(simulate):    
    if(top_testbench == None):
        exit("Error: No top level testbench found.")
    #format generics for as a command-line argument for test vector script
    generics_command = ''
    for g,v in generics.items():
        generics_command += '-'+g+'='+v+' '
    #call test vector generator first with passing generics into script
    if(python_vector_script):
        execute('python',python_vector_script,generics_command)

    execute(TOOL_PATH+"echo","Simulating design with tesbench...")
    print('---RUNNING SIMULATION---')
    print('TOP:',top_testbench)
    #print out any generics we set on command-line
    if(len(generics)):
        print('GENERICS SET:',)
        for g,v in generics.items():
            print(g,'=',v)
    pass
#routing/fit/implementation
elif(route):
    execute(TOOL_PATH+"echo","Routing design to pins...")
    print("----PINS ALLOCATED-----")
    for pin,port in pin_assignments.items():
        print(pin,'-->',port)
    pass
#synthesis
elif(synthesize):
    if(top_design == None):
        exit("Error: No top level design found.")
    execute(TOOL_PATH+"echo","Synthesizing design...")
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
#syntax checking
elif(lint):
    execute(TOOL_PATH+"echo","Checking design syntax...")
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
#no action
else:
    exit("Error: No flow was recognized! Try one of the following: -lint, \
-synth, -route, -sim.")