# _lego_**HDL** Documentation
### The simple, lightweight, powerful package manager for HDL design modules.
  
<br />  

_lego_**HDL** is a simple, powerful, and flexible package manager for VHDL designs. It provides full package management capabilities as one would expect from premiere software package managers like Cargo, APT, PIP, and RubyGems. Inspiration has been taken from all of these to build this tool for HDL development.

<br />

LegoHDL is available to work completely local or along with remote locations to collaborate and share modules with others. It is designed to give the developer maximum freedom in their workflow. At a minimum, no git knowledge is required as legoHDL will automate basic git commands that are required.

<br />

## Introduction

Let's go over some important terminology regarding legoHDL.

__Block.lock__ : The metadata file that signifies if a project is a block. This file is automatically maintained by the legoHDL. It contains information such as the version number, remote url repository, and dependencies. It is highly recommended to not modify this file.

__project__ : A group of HDL files grouped together to create a design. A project is a block if it has a "Block.lock" file at the root of the its directory.

__block__ : This is a self-contained project that contains a Block.lock file. A block's title must consist of a library and a name. An example block title is "util.fifo". It is good practice to have the block's name match the top-level entity.

__workspace__ : This is your working environment. Only one can be active on your local machine at a time. It consists of a local path and optionally any markets. The local path is where all blocks can freely live when downloaded.

__market__ : This is a repository that hosts a "collection" of released blocks. This can be a local repository or remote repository. In order for a block to be added to the collection it must have its own remote repository. Markets are self-maintained by legoHDL.

__script__ : A user created file. These can be stored within legoHDL or linked to if say the script belongs to some repository where users are actively developing it. Scripts can be used to build/run a block. A script in legoHDL is essentially an alias to a execute a file.

__label__ : An identifier that can be used to gather dependencies to be written to the recipe. Default labels are @LIB, @SRC, @SIM, @SRC-TOP, @SIM-TOP. Developers can can create labels and provide their own extensions, like creating an @IP for .xci files. Extensions are glob-style patterns.

__recipe__ : A list of all required files for a given block to be built from, in the  correct order needed. It is a file with identifying labels regarding the block and its dependencies. This is intended to be the link between the package management process and building a design.



<br />

## Download and Installation

Ensure you have a version of python >=3.0 and git installed and run:

```pip install legohdl```

To ensure it is installed properly run:

```legohdl --version```

A version number should appear in the output. We are ready to go!

# Getting Started

## 1. __Configure a workspace and settings__

A workspace's main job is to specify the local path where blocks are to be stored when downloaded. Any block outside of this path will not be seen by this workspace. My workspace name will be `lab` and my local path for it will be `"~/develop/hdl/"`

```legohdl config lab="~/develop/hdl/" -workspace```

Easy! Every workspace has its own library and cache, but can share markets. Let's look at our new workspace.

```legohdl list -workspace```

As you can see, we have no markets linked to this workspace. If we did, all released blocks in that market would be available to us to install or download.

Now we will configure other important settings.

```legohdl config "Luke Skywalker, Jedi, One with the Force" -author```<br/>
```legohdl config "code" -editor```

Configuring an editor allows you to automatically open projects with the `-o` flag.

Settings flags for config command are:

-   -editor [string]
-   -author [string]
-   -script [key/value pair]
-   -label [key/value pair]
-   -workspace [key/value pair]
-   -active-workspace [string]
-   -market [key/value pair]
-   -template [string]

_string_ is accepted with `" "` or `' '`.

_key/value pair_ is accepted with `key="value"` or `key='value'`.

See section __Managing Settings__ to get more in-depth overview of setting configurations.

## 2. __Make a new Block__

A block can be made directly from legohdl CLI. This provides the benefit of adding key information and automatically setting up a developer's preferred project structure through the use of a template.

The template can be opened and freely edited LegoHDL has a built-in folder where it can store a template structure, but also can reference a folder from elsewhere. 

Now let's open our template and populate with basic files that all our projects will need:

```legohdl open -template```

Let's add some folders and files that may be needed for every project.

    template/
        src/
            template.vhd
        test/
            testbench.py
            template_tb.vhd
        README.md

An example of how to set up a template VHDL design file may look like this:

``` vhdl
----------------------------------------
--  Project: %BLOCK%
--  Author: %AUTHOR%
--  Date: %DATE%
--  Description:
--
----------------------------------------

library ieee;
use ieee.std_logic_1164.all;

entity template is
    port(
        Clock     :   IN  std_logic;
        Reset     :   IN  std_logic

    );
end entity;


architecture rtl of template is

begin


end architecture;
```

> __Note__: Any where the word 'template' appears, it will be replaced by the name of the created block. %AUTHOR% will be replaced by our configured author setting, %DATE% will be replaced by that day's date, and %BLOCK% will be replaced by the block's library and name.

Here is an example VHDL template testbench file:
``` vhdl
----------------------------------------
--  Project: %BLOCK%
--  Author: %AUTHOR%
--  Date: %DATE%
--  Description:
--
----------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use std.textio.all;
use std.env.finish;

entity template_tb is
end entity;


architecture rtl of template_tb is
    --drives testbench
    signal Clock : std_logic := '0';
    signal Reset : std_logic;

    --clock period definition
    constant ClockPeriod : time := 10 ns;

begin
    --generate clock with 50% duty cycle
    Clock <= not Clock after ClockPeriod/2;

    --initially reset the DUT if applicable
    bootup : process
    begin
        Reset <= '1';
        wait for ClockPeriod*2;
        Reset <= '0';
        wait;
    end process;

    --instantiate the DUT


    --read in inputs and feed into DUT
    inputs : process
        file InFile         : text open read_mode is "inputs.txt";
        variable DataLine   : line;
    begin
        while not endfile(InFile) loop
            readline(InFile, DataLine);


        end loop;
        wait;
    end process;

    --read in expected outputs and assert from DUT
    outputs : process
        file OutFile        : text open read_mode is "outputs.txt";
        variable DataLine   : line;
    begin
        while not endfile(OutFile) loop
            readline(OutFile, DataLine);
            

        end loop;
        --simulation is complete
        finish;
    end process;

end architecture;
```

I've also added a blank python file into the template for generating inputs/outputs for simulation as well as the templated VHDL testbench file.

> __Note__: Opening the template through legoHDL opens a built-in folder named template within legoHDL. If we have a template project structure living elsewhere, we can reference that instead when creating projects with: ```legohdl config "/users/chase/develop/hdl/template" -template```. This would be handy if a group has a dedicated repository for an initial template project. Setting this option to an empty string will refer back to the template folder found within legoHDL.

Now that the template is fit for our preferences, let's use it. Close the template folder now once you are done with setting up the base files. It is time to make a new block! For this tutorial will make a half adder to be used in a later design. We will design this half adder to belong to our new library called "common".

It is required to specify a library for every created block.

```legohdl new common.halfadder -o```

> __Note__: When creating new block or downloading a block that does not exist in the workspace's local path, the block will be stored to: "WORKSPACE-LOCAL-PATH/BLOCK-LIBRARY/BLOCK-NAME"

Okay and it is open in our text-editor ready to work!

## 3. __Developing a Block__

At this point, our project's structure now looks like this:

    halfadder/
        src/
            halfadder.vhd
        test/
            testbench.py
            halfadder_tb.vhd
        README.md
        Block.lock

Our template auto-populated the project with files ready to go, there is an metadata file titled "Block.lock" inside our project, and the project is already initialized with git with an initial commit. This project is now considered to the upgraded status of a "block" because it has a Block.lock file.

Now the user can begin designing the hardware to meet the specifications of the design.

Here is the code for the half adder design.

``` vhdl 
----------------------------------------
--  Project: common.halfadder
--  Author: Luke Skywalker, Jedi, One with the Force
--  Date: August 14, 2021
--  Description:
--
----------------------------------------

library ieee;
use ieee.std_logic_1164.all;

entity halfadder is
    port(
        A     :   IN  std_logic;
        B     :   IN  std_logic;
        S     :   OUT std_logic;
        C     :   OUT std_logic
    );
end entity;

architecture rtl of halfadder is
begin
    --sum is '1' when only one input is '1'
    S <= A xor B;
    --carry output when both inputs are '1'
    C <= A and B;

end architecture;
```


### __Faster Instantiation__

LegoHDL offers some commands to help improve the workflow while designing. The `port` command is one of them.

Say we are now ready to move onto our VHDL testbench file. Inside this file we must instantiate our design as the Design Under Test (DUT). Our halfadder only has 4 ports, but imagine trying to instantiate a more complex design with many ports. It becomes very tedious and time-consuming to write out all the ports. With legoHDL, this mundane task gets a productivity boost. When we have an entity declared and written within a block, we can view it as a component with:

```legohdl port common.halfadder.halfadder```

> __Note:__ The split is "LIBRARY.BLOCK.ENTITY". If you left of the "ENTITY" then the entity returned is the toplevel one for that block. Since halfadder is also our toplevel entity (auto-detected by legoHDL), the command `legohdl port common.halfadder` yields the same result.

This will print out the entity as a component declaration, available to be easily copied and pasted into any VHDL source file.
``` vhdl
component halfadder is
    port(
        A     :   IN  std_logic;
        B     :   IN  std_logic;
        S     :   OUT std_logic;
        C     :   OUT std_logic
    );
end component;
```

The `-map` flag will print the format for the component's instantiation as well as the necessary signals and constants. 

The `-inst` flag will print the direct entity instantiation along with the necessary signals and constants. Here is the return from using the `-inst` flag.
``` vhdl
signal A : std_logic;
signal B : std_logic;
signal S : std_logic;
signal C : std_logic;

uX : entity work.halfadder
port map(
    A=>A,
    B=>B,
    S=>S,
    C=>C
);
```
If you ran this same command from outside this block project, the library would not be "work" but "common". We will see this later in the tutorial.

After copying and pasting the instantiation into the testbench and writing the code to simulate it, here is the testbench file:

``` vhdl
----------------------------------------
--  Project: common.halfadder
--  Author: Luke Skywalker, Jedi, One with the Force
--  Date: August 14, 2021
--  Description:
--
----------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.finish;

entity halfadder_tb is
end entity;

architecture rtl of halfadder_tb is
    --drives testbench
    signal Clock : std_logic := '0';
    signal Reset : std_logic;

    --clock period definition
    constant ClockPeriod : time := 10 ns;

    --signals related to DUT
    signal A : std_logic;
    signal B : std_logic;
    signal S : std_logic;
    signal C : std_logic;

begin
    --generate clock with 50% duty cycle
    Clock <= not Clock after ClockPeriod/2;

    --instantiate the DUT
    uX : entity work.halfadder
    port map(
        A=>A,
        B=>B,
        S=>S,
        C=>C
    );

    --read in inputs and feed into DUT
    inputs : process
        file InFile         : text open read_mode is "inputs.txt";
        variable DataLine   : line;
        variable InInt      : integer;
        variable InVec      : std_logic_vector(1 downto 0);
    begin
        while not endfile(InFile) loop
            --read in inputs for A and B as vector (A, B)
            readline(InFile, DataLine);
            read(DataLine, InInt);
            --cast from integer to logic vector
            InVec := std_logic_vector(to_unsigned(InInt,2));
            --Leftmost bit is A input
            A <= InVec(1);
            --Rightmost bit is B input
            B <= InVec(0);
            --give time until moving on
            wait until rising_edge(Clock);
        end loop;
        wait;
    end process;

    --read in expected outputs and assert from DUT
    outputs : process
        file OutFile        : text open read_mode is "outputs.txt";
        variable DataLine   : line;
        variable OutInt     : integer;
        variable OutSC      : std_logic_vector(1 downto 0);
    begin
        while not endfile(OutFile) loop
            --capture expected S and C value as vector (S, C)
            readline(OutFile, DataLine);
            read(DataLine, OutInt);
            --cast from integer to logic vector
            OutSC := std_logic_vector(to_unsigned(OutInt,2));
            --wait a little to let DUT compute
            wait for 1 ns;
            --print info to console
            report "Asserting " & integer'image(to_integer(unsigned(OutSC))) &
            " = " & std_logic'image(S) & std_logic'image(C);
            --confirm that the ouputs match as expected
            assert S = OutSC(1) severity failure;
            assert C = OutSC(0) severity failure;
            --give time until moving on
            wait until rising_edge(Clock);
        end loop;
        --simulation is complete
        finish;
    end process;

end architecture;
```

Although writing a software model for a half adder is completely overkill, it will be used here because most practical designs may have a software model.

Here is the code for the testbench python file:

``` python
import random
random.seed(9)
#create inputs and expected outputs files for DUT
inputs = open("inputs.txt",'w')
outputs = open("outputs.txt",'w')

count = 10
for i in range(count):
    #generate random inputs (0 to 3 is 00, 01, 10, and 11)
    ab = random.randint(0,3)
    inputs.write(str(ab)+"\n")
    #compute the expected outputs
    s = 1 if(ab == 1 or ab == 2) else 0;
    c = 1 if(ab == 3) else 0;
    #convert from binary digits to a integer value
    sc = 2*s + c
    outputs.write(str(sc)+"\n")
```

We are now almost ready to `build` our block.


## 4. __Building a Block__

legoHDL is a package manager. It has no means to build a design, as HDL tools are complex and are not a one-size-fits-all. Despite this, legoHDL provides capability through the use of its labels, recipes, and scripts to enable the developer to run with their own build tools exactly how they want. Got an awesome makefile calling GHDL? Use it. Got TCL scripts for the entire Vivado design suite? Sweet!

### __Exporting__

First, we need the recipe file.

To create the recipe file with the auto-determined toplevel design for the current project, run:

`legohdl export`

The command will not run unless you are inside the directory of the block you want to export.

The recipe file will be located within the block's folder in the folder called "build". I will add a .gitignore file to exclude the build directory from my block's git tracking.

It also prints out helpful information regarding the hierarchal structure.

 ```
INFO:   DETECTED TOP-LEVEL ENTITY: halfadder
INFO:   DETECTED TOP-LEVEL BENCH: halfadder_tb
INFO:   Generating dependency tree...
INFO:   Deciphering VHDL file...
INFO:   C:/Users/chase/develop/hdl/common/halfadder/test/halfadder_tb.vhd
INFO:   Deciphering VHDL file...
INFO:   C:/Users/chase/develop/hdl/common/halfadder/src/halfadder.vhd
---DEPENDENCY TREE---
vertex: [ common.halfadder_tb ] <-- common.halfadder
vertex: [ common.halfadder ] <--
---ENTITY ORDER---
common.halfadder -> common.halfadder_tb
---BLOCK ORDER---
common.halfadder
 ```

> __Note:__ If multiple toplevel entities are detected, legoHDL will prompt you with your choices to select one. The same is true for the VHDL testbench entity if it detects multiple testbenches that instantiate the selected toplevel.

You can also explicitly set the block's toplevel entity by adding the entity name to the export command like: ```legohdl export halfadder```

Now to use the recipe file we need a script. From here, it is completely up to the developer to how they go about building a block; legoHDL is essentially passing off all the needed information for a build from the export command.

We could copy/paste our build scripts into every project's folder, but this problematic. First, with multiple copies it becomes difficult to update across the board. Second, we actually must include it in the project, and sometime we have more than one script to do different jobs. The solution is legoHDL's __scripts__.

<br />

> Scripts: A script is simply an alias for running user created files. legoHDL can store scripts in the built-in "scripts" folder or link to them and store their file path to call for later use. It is practically using built-in aliases. Calling a script can be done like so:
```legohdl build @SCRIPT-NAME [args passed to script..]```, where SCRIPT-NAME is the name given by the user for legoHDL to remember the script.
    
Scripts can be linked from where they currently reside, in case they are hosted in a repository where a group is updating them.

The scripts concept was designed to keep track of valuable build scripts that you as the developer use to analyze, synthesize, simulate, or program your design. Allowing legoHDL to store/point to these files gives the developer power and freedom to completely customize and glue their workflow together.

<br/>

### __Recipes and Labels__

So, how will build scripts know what files to analyze or use? Here's where recipes come into play. A recipe takes all labeled files and writes them to a file. All VHDL files will be in order to correctly be anaylzed. Default labels are:
-   @LIB for library VHDL code
-   @SRC for project-level VHDL design code,
-   @SIM for project-level  VHDL simulation code
-   @SRC-TOP for top-level design entity
-   @SIM-TOP for top-level simulation entity

Labels are what the export command throws into the recipe file.

Labels can be user-defined for the export command to additionally throw into the recipe file. Custom labels can be either `shallow` or `recursive`. 

- shallow: looks for label within current block
- recursive: looks for label from lowest-level blocks to the current block

You from our last export command our recipe file looks like:

``` 
@SRC C:/Users/chase/develop/hdl/common/halfadder/src/halfadder.vhd
@SIM C:/Users/chase/develop/hdl/common/halfadder/test/halfadder_tb.vhd
@SIM-TOP halfadder_tb C:/Users/chase/develop/hdl/common/halfadder/test/halfadder_tb.vhd
@SRC-TOP halfadder C:/Users/chase/develop/hdl/common/halfadder/src/halfadder.vhd
```

We are missing our testbench python file. Let's throw into our recipe with:

`legohdl config BENCH=".py" -label`

Adding the `-recursive` flag will make that label recursive.

Let's rerun the export command to update our recipe file.

`legohdl export`

Now our recipe file looks like:

``` 
@BENCH C:/Users/chase/Develop/hdl/common/halfadder/test/testbench.py
@SRC C:/Users/chase/Develop/hdl/common/halfadder/src/halfadder.vhd
@SIM C:/Users/chase/Develop/hdl/common/halfadder/test/halfadder_tb.vhd
@SIM-TOP halfadder_tb C:/Users/chase/Develop/hdl/common/halfadder/test/halfadder_tb.vhd
@SRC-TOP halfadder C:/Users/chase/Develop/hdl/common/halfadder/src/halfadder.vhd
```


If Xilinx IP were needed to be included for my build script, I could add a label

```legohdl config IP=".xci" -label -recursive```

where the recursive flag will indicate to recursively grab all .xci files found within every dependency block used.

We can view our labels with

``legohdl list -label``

Here's the code for a simple example build script file that is written in python and uses GHDL. It will parse the recipe file, analyze all VHDL files, and run a simulation if a testbench unit is found in the recipe file (indicated by @SIM-TOP label).
``` python
import os
#example build script demonstrating the easy handling of recipe file
#change directory to project's build folder
os.chdir("build")
#open recipe file
recipe = open("recipe", 'r')
#parse recipe file and analyze units
tb_unit = top_unit = ''
for rule in recipe.readlines():
    #break up line into list of strings
    parse = rule.split()
    tag = parse[0] #tag is always first item
    if(tag == '@LIB'): 
        #determine how to handle libraries
        os.system("ghdl -a --std=08 --work="+parse[1]+" "+parse[2])
    elif(tag == '@SRC' or tag == '@SIM'): 
        #determine how to handle project-level code
        os.system("ghdl -a --std=08 --ieee=synopsys "+parse[1])
    elif(tag == '@SIM-TOP'): 
        #capture testbench unit name
        tb_unit = parse[1]
    elif(tag == '@SRC-TOP'): 
        #capture top-level design unit name
        top_unit = parse[1]
    elif(tag == "@BENCH"): 
        #will run test-generation script to create input/output sim files
        os.system("python "+parse[1].strip())
if(tb_unit != ''):
    #now analyze and run simulation from testbench file
    os.system("ghdl -r --std=08 --ieee=synopsys "+tb_unit+" --vcd=./wf.vcd")
```

Now, we could add this to our legoHDL scripts, and further extend this script to do much more like take in any arguments. The sky is the limit when developer's are in control of how their scripts are to build HDL code. Let's add this file to my legoHDL scripts.

Here is another simple example build script but this time is written in TCL and uses Vivado. It will create a vivado project, parse the recipe file, add files to the correct file sets, and then passed on any tclargs will either run synthesis or simulation.

``` TCL
#grab directory name to set for vivado project name
set PRJ [file tail [pwd]]
#change directory to build
cd build
puts [pwd]

#create vivado project
create_project -part xc7a200tfbg676-2 -force $PRJ

#open the recipe file and read its contents
set fp [open "recipe" r]

set top_unit ''
set tb_unit ''
#read line by line
while {[gets $fp data] >= 0} {
    #assign label as the first element in list
    set label [lindex $data 0]
    #conditionally branch based on the label
    #set toplevel entity
    if {[string compare "@SRC-TOP" $label] == 0} {
        set top_unit [lindex $data 1]
     #set testbench entity
    } elseif {[string compare "@SIM-TOP" $label] == 0} {  
        set tb_unit [lindex $data 1]
    #add to simulation files
    } elseif {[string compare "@SIM" $label] == 0} {
        add_files -fileset sim_1 [lindex $data 1]
    #add to design files
    } elseif {[string compare "@SRC" $label] == 0} {
        add_files -fileset sources_1 [lindex $data 1]
    #add libraries
    } elseif {[string compare "@LIB" $label] == 0} {
        set_property -library [lindex $data 1] [lindex $data 2]
        add_files -fileset sources_1 [lindex $data 2]
    #run the python testbench generation script
    } elseif {[string compare "@BENCH" $label] == 0} {
        exec python [lindex $data 1]
    }
}
#set toplevel entity
set_property top $top_unit [current_fileset]

#branch based on arguments based to the TCL script
if {$arc > 0} {
    #synthesize the design
    if {[lindex $argv 0] == "synth"} {
        launch_runs synth_1
        wait_on_run synth_1
    #simulate the design
    } elseif {[lindex $argv 0] == "sim"} {
        launch_simulation
    }
}
```

Open the scripts folder.

```legohdl open -script```

Make a new build script file called `master.py` and copy the python build script code above into it.

Now let's tell legoHDL to remember this script:

```legohdl config master="python /Users/chase/.legohdl/scripts/master.py" -script -lnk```

> __Note:__ The `-lnk` flag will prevent legoHDL from trying to copy the file into the built-in scripts folder. Since it is already in the scripts folder, it is wise to just link it. It would also be wise to use `-lnk` when you would like your script to live elsewhere, allowing you to continue to improve it from its original location.

You can also go ahead and add the TCL build script into the built-in scripts folder and name it something like:

`legohdl config vivado="c:/xilinx/vivado/2019.2/bin/vivado.bat -mode batch -source c:/users/chase/.legohdl/scripts/viv.tcl -nolog -nojou" -script -lnk`

To run the newly configured master script for our halfadder block run this command at the base of the block's directory:

```legohdl build @master```

The command will not run unless you are inside the directory of the block you want to build.

> __Note:__ If there is a script's alias being "master", it can be omitted from the build args and will run as default.
```legohdl build``` has the same effect as the previous command because they both call the script under master.

To run the TCL build script, if it's name is "viv", run:

`legohdl build @vivado`

Since we designed this script to take in arguments, we can pass them into the script like we wanted. So to do perform synthesis run:

`legohdl build @vivado -tclargs synth`

To run simulation:

`legohdl build @vivado -tclargs sim`

The `-tclargs` is specific to allowing vivado to pass in arguments to the TCL script. Remember, the `build` command is essentially the alias for the value of `vivado` that we configured.

Nice! We have just tested our design.

We can view our scripts with: `legohdl list -script`


## 5. __Releasing a Block__

Up until this point, everything has been local and the block has not yet been officially "released". It has been on version 0.0.0, which is an unreleased state. Now we are ready to release the current code's state as a version.

If we have not made any git commits yet, that is okay. The release command will automatically add and commit altered files. If this is undesirable, you can use the `-strict` flag to only let legoHDL commit the changes it makes to the `Block.lock` file for that specific release.

```legohdl release -maj```

This will set the version to the next major version for the project. It is best to follow semantic versioning for HDL design.

You must select one of these flag options for release: `-maj`, `-min`, `-fix`, or `-v*.*.*`. the `-v*.*.*` flag allows the user to explicitly set the next version to release, where `*` are the version numbers.
    
_MAJOR.MINOR.PATCH versioning suggestions:_  
-   _major_: any entity port changes or inconsistent changes to the block's intended behavior
-   _minor_: performance enhancements  
-   _patch/fix_: bug fixing and small code tweaks 

Seeing our block with ```legohdl list``` now highlights common.halfadder as version 1.0.0.

## 6. __Incorporating a Block as a Dependency__

Okay, the project is now ready to be incorporated into any other design! Upon releasing, it will install the release to the cache folder alongside generating a VHDL package file for the toplevel entity into the library folder, if a toplevel exists. Legohdl provides a lot of flexibility in how the designer wants to incorporate a block into another design. Here are some common ways:

1. Include library and use keywords and then instantiate the dependent block's toplevel entity in the architecture.
``` VHDL
library common;
use common.mux_pkg.all;
```

2. You could also instantiate the entity directly without having to use the auto-generated package file. Running `legohdl port common.mux -inst` will give the instantiation form shown below along with any required signals.
``` VHDL
library common;

entity ALU is
...
end entity;

architecture bhv of ALU is
...
begin

    u0 : entity common.mux
    port map(
        ...
    );
end architecture
```

3.
``` VHDL
library common;

entity ALU is
...
end entity;

architecture bhv of ALU is
...
    component common.mux is
    ...
    end component;
begin

    u0 : common.mux
    port map(
        ...
    );
end architecture
```

legoHDL will recognize the library and files being used and throw the required files in the recipe. If a library is called in the VHDL file that does not exist as a custom created library, such as ieee or std, it will be ignored as it assumes the tool will automatically have these libraries.

Don't remember the ports list? Run

```legohdl port common.mux -map```

to grab the format for instantation and any required signals.

<br/>

## __Using Markets__

### __Block Layers__

There are 3 main layers to how a block exists. A block can coexist and usually will within any or all of the 3 layers. The 3 layers are:

1. Downloaded to the local path
2. Installed to the cache
3. Released to a market

Blocks to be developed must be downloaded to the local path.

Blocks to be used as dependencies are installed to the cache.

Blocks to be available are released to a market. When running the `release` command, the new released version will be automatically installed to the cache, regardless of market status.

_Some important concepts to understand:_

If a block is downloaded or installed (via market) and it has dependencies, legoHDL will search the workspace's available markets to auto-install the dependencies to the cache.

If a block is downloaded and it has a remote repository, legoHDL will git clone the block to the local path.

If a block is downloaded and does not have a remote repository (and therefore does not exist in any market), legoHDL will clone the block's master branch to the local path from the cache.

### __Markets__

A market can be either configured to a remote repository or not. Markets are special git repositories that store the information for a released block. Markets are self-maintained by legoHDL. 

The benefit of a market having a remote repository is that multiple users can use that market and therefore share blocks.

A market contains the Block.lock files for its released blocks. These now act as essentially "pointers" to the actual block and version, indicated by the Block.lock's `version` and `remote`.

### __Developing Related Blocks Together__

As noted, a block will by default use the dependency located within the cache. This allows developing to be consistent so that when it is ready for release, anyone else to download the new released block can also replicate the results and behavior using the other released dependencies.

However, there may instances when multiple blocks must be developed together simultaneously. This can be achieved by setting the `multi-develop` setting to `true` through the command line with `legohdl config true -multi-develop` or by opening up the settings.yml file.

Multi-develop will instead first check the local path for a block's dependencies before checking the cache. This means it will use the downloaded blocks over the installed blocks, if it found it in the local path.

<br/>

## __Block.lock__

Block.lock is a metadata file managed by legoHDL. It contains the important information used by legoHDL and itself acts as the indicator if a folder/project is a block. This section is for increased understanding and does not instruct the developer to do anything with Block.lock files.

Here is a sample Block.lock file:

``` yml
name: ALU
library: util
version: 1.2.0
summary: Generic arthimetic logic unit
toplevel: ALU
bench: ALU_tb
remote: https://github.com/c-rus/alu.git
market: SuperMarket
derives: 
    - common.fulladder
    - util.flipflop
```

Block.lock files are actually YAML-structured. The sections explained:

- _name_: the block's name (can be different than the toplevel entity's name)
- _library_: the block's library (this is also the VHDL library for this block's source code)
- _version_: the block's current state's version. If a version is `0.0.0`, then it has not ever been released.
- _summary_: short description about the block
- _toplevel_: the toplevel entity name
- _bench_: the testbench entity that instantiates the toplevel entity
- _remote_: a git url, if no remote then the value is `null`
- _market_: the market to where this block will be released to, if no market then the value is `null`
- _derives_: a list of the block's dependent blocks (TODO- also contains the version number used or states `latest` to use the latest). Note that these names listed are the library name and block name.

<br/>

## Software Verification Chaining (SWVC)

Take this example workflow. Testbenches are verified by having a software model written in a scripting language (maybe python) that generates an input file and expected outputs file. The user would make a label to get this sw model script added into the recipe, maybe like `BENCH=".py"`. It would be a shallow label so only the current block's script gets added to the recipe.

Now imagine the system being designed requires multiple blocks, and they are configured in a sequential order. A common example would be a communications system, where data is passed from one block to the next. We design a top-level block where all lower-level blocks are instantiated and wired in the sequential manner, but now the task of verifying this top-level block becomes cumbersome. Must we rewrite the sw models of each lower-level block into a new script to generate inputs and expected outputs files? What if one lower-level model gets updated? Now the top-level sw model must also be updated. This is problematic.

Enter Software Verification Chaining (SWVC). The idea is to use the already designed sw model scripts and build up the input and expected output files, one script after another. Here's how it's done:

Create the label to be recursive, so that all sw model scripts found in each of the required blocks as well as the current block's sw model will be added to the recipe list. Now, inside your build script, you can execute each sw model script identified by its label. For every stage after the initial one, the next sw model will read in the previous stage's expected outputs file and manipulate that data to generate a new expected outputs file. By the end you will have the correct initial inputs and correct expected outputs.

    TODO: insert diagram of SWVC.


<br/>

## Commands

```
USAGE:             
	legohdl <command> [block] [flags]            

COMMANDS:
   init         initialize the current folder into a valid block format
   new          create a templated empty block into workspace
   open         opens the downloaded block with the configured text-editor
   release      release a new version of the current block
   list         print list of all blocks available
   install      grab block from its market for dependency use
   uninstall    remove block from cache
   download     grab block from its market for development
   update       update installed block to be to the latest version

   graph        visualize dependency graph for reference
   export       generate a recipe file to build the block
   build        run a custom configured script
   del          deletes a block from local workspace or a configured setting
   refresh      sync local markets with their remotes
   port         print ports list of specified entity
   show         read further detail about a specified block
   config       set package manager settings

Type 'legohdl help <command>' to read more on entered command.
```

> __Note:__ A block is in the format _library.block-name_

### init

    legohdl init <value> [-market | -remote]

    legohdl init <block> [-<market-name> -<remote-url>]

### new

    legohdl new <block> [-<market-name> -<remote-url> -o]

    legohdl new <new-file> -<template-file> -file

### open

    legohdl open <block>

    legohdl open <-settings | -template | -script>

### release

    legohdl release [-maj | -min | -fix | -v0.0.0] [-strict -soft]

### list

    legohdl list [<block>]

    legohdl list -script

    legohdl list -workspace

    legohdl list -label

    legohdl list -market

### install

    legohdl install <block> [-v0.0.0]

### uninstall

    legohdl uninstall <block> [-v0.0.0]

### download

    legohdl download <block> [-o]

### update

    legohdl update <block>

### export

    legohdl export [<toplevel-entity>] [-<testbench-entity>]

### build

    legohdl build @<script-name> [arguments to script file]

### del

    legohdl del <block> -u

    legohdl del <market> -market

    legohdl del <workspace> -workspace

    legohdl del <label> -label

### refresh

    legohdl refresh [-market1 | -market2 | ...]

### port

    legohdl port <block> [-map -inst]
    
    legohdl port <block>.<entity> [-map -inst]

### show

    legohdl show <block>

### summ

    legohdl summ <description>

### config

    legohdl config <"value"> [-author | -editor | -active-workspace]

    legohdl config <key="value"> [-label [-recursive] | -market | -workspace | -script [-lnk]]




# __Managing Settings__

First, make sure you set up our preferred text-editor. This will be used to help us open various files related to legoHDL and our workspace.

The general usage for setting the text-editor is:

`legohdl config VALUE -editor`

where VALUE is replaced by your actual editor (code, atom, nano, ...).

I will be using VSCode so I run:

`legohdl config code -editor`

Now we will use the faster and more visual way to get set up, rather than use the config command. Let's open the settings file.

`legohdl open -settings`

The settings file is a YAML file type that is configured for the user-installed version of legoHDL. Here is a layout with example values and extra spacing to help illustrate the sections:

``` yaml
active-workspace: lab
author: Luke Skywalker, Jedi, One with the Force
editor: code

label:
  recursive:
    IP: .xci
  shallow:
    BENCH: .py
    XDC: .xdc

market:
  SuperMarket: https://gitlab.com/chase800/supermarket.git
  open-market: https://gitlab.com/chase800/open-market.git
  hdl-base: null

multi-develop: false

script:
  master: '"python /Users/chase/.legohdl/scripts/master.py"'
  simple: '"make -f /Users/chase/Develop/HDL/scripts/simplemake"'

template: null

workspace:
  lab:
    local: /Users/chase/develop/hdl/
    market:
    - open-market
    - hdl-base
  home:
    local: /Users/chase/develop/home-space/
    market: []

```

Lets discuss each setting in detail:

- active-workspace:

- author:

- editor:

- label:

- market:

- multi-develop:

- script:

- template:

- workspace:



<br/>
<br/>
<br/>
<br/>
<br/>
<br/>

_Cuts_

Developers can also store other common files in the scripts section, such as constraint files. It can then become very powerful to enable a build script to reference/use these files by passing an certain arg through a build command.

Example:

Developer creates a python script used to build designs with quartus command line tools. The developer designed the python script to accept the first argument as the target device.

```legohdl build @quartus x47c133g2```

<br />

## Labels

Labels are what the export command throws into the recipe file.

Labels can be user-defined for the export command to additionally throw into the recipe file. These custom labels, if legoHDL finds any in the current block, will be inserted before the default labels.

Example:

You have a test generation python file that would like to be added to the recipe. Why? Answer: If you set up the stored build script to check for this new label, then the build script could run the test generation at the right stage in your build process.

```legohdl config BENCH=".py" -label```

or, more explicitly could have lots of files with .py ext in the project that do different things

```legohdl config POST-CHECK="test_gen.py" -label```

```legohdl config TEST-VER="test_ver.py" -label```

Now the developer has set up the build script to handle these two labels and run their files at the user-defined time.

Assigning a -label or -build to "" or '' will effectively remove it from legohdl's settings and delete it if it was a script and had made a copy (configured without -lnk option).

    NOTE: A user-defined label can be recursively searched through dependencies, as would an @LIB label with the -recur flag.


    > __Note__: Use `legohdl config "PATH" -template`, where PATH is the path to template folder, to specify where legoHDL should copy files from. This would be handy if a group has a dedicated repository for an inital template project.

> __Note:__ To reference any internal entities within the block, append the entity's name to the block's title. If the block 'common.mux' had a internal entity called 'and_gate', we could view that component and its port map with: ```legohdl port common.mux.and_gate -map```


Example:

You have a test generation python file that would like to be added to the recipe. Why? Answer: If you set up the stored build script to check for this new label, then the build script could run the test generation at the right stage in your build process.

Here's a sample recipe file:

``` 
@BENCH /Users/chase/Develop/hdl-dev/mem/flipflop/bench/testbench.py
@SRC /Users/chase/Develop/hdl-dev/mem/flipflop/design/sidecar.vhd
@SRC /Users/chase/Develop/hdl-dev/mem/flipflop/design/flipflop.vhd
@LIB verif /Users/chase/.legohdl/workspaces/lab/cache/verif/fileio/design/fileio.vhd
@SIM /Users/chase/Develop/hdl-dev/mem/flipflop/bench/flipflop_tb.vhd
@SIM-TOP flipflop_tb /Users/chase/Develop/hdl-dev/mem/flipflop/bench/flipflop_tb.vhd
@SRC-TOP flipflop /Users/chase/Develop/hdl-dev/mem/flipflop/design/flipflop.vhd
```

Notice the _@BENCH_ label is a custom label set like so:

```legohdl config BENCH="testbench.py" -label```
