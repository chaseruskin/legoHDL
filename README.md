# _lego_**HDL** Documentation
### The simple, lightweight, powerful package manager for HDL design modules.
  
<br />  

_lego_**HDL** is a simple, powerful, and flexible package manager for VHDL designs. It provides full package management capabilities as one would expect from premiere software package managers like Cargo, APT, PIP, and RubyGems. Inspiration has been taken from all of these to build this tool for HDL development.

<br />

LegoHDL is available to work completely local or along with remote locations to collaborate and share modules with others. It is designed to give the developer maximum freedom in their workflow. At a minimum, no git knowledge is required as legoHDL will automate basic git commands that are required.

<br />

## Introduction

Let's go over some important terminology regarding legoHDL.

__Lego.lock__ : The metadata file that signifies if a project is a block. This file is automatically maintained by the legoHDL. It contains information such as the version number, remote url repository, and dependencies. It is highly recommended to not modify this file.

__project__ : A group of VHDL files grouped together to create a design. A project is a block if it has a "Lego.lock" file at the root of the its directory.

__block__ : This is a self-contained project that contains a Lego.lock file. A block's title must consist of a library and a name. An example block title is "util.fifo". It is good practice to have the block's name match the top-level entity.

__workspace__ : This is your working environment. Only one can be active on your local machine at a time. It consists of a local path and optionally any markets. The local path is where all blocks can freely live when downloaded.

__market__ : This is a repository that hosts a "collection" of released blocks. This can be a local repository or remote repository. In order for a block to be added to the collection it must have its own remote repository. Markets are self-maintained by legoHDL.

__script__ : A user created file. These can be stored within legoHDL or linked to if say the script belongs to some repository where users are actively developing it. Scripts can be used to build/run a block, but also to more generally store common files across all blocks, like a constraint file.

__label__ : A identifier that can be used to gather dependencies to be written to the recipe. Default labels are @LIB, @SRC, @SIM, @SRC-TOP, @SIM-TOP. Developers can can create labels and provide their own extensions, like creating an @IP for .xci files.

__recipe__ : A list of all required files for a given block to be built from, in the  correct order needed. It is a file with identifying labels regarding the block and its dependencies. This is intended to be the "golden link" between the package management process and building a design.



<br />

## Download and Installation

Ensure you have a version of python >=3.0 and git installed and run:

```pip install legohdl```

To ensure it is installed properly run:

```legohdl --version```

A version number should appear in the output. We are ready to go!

## Getting Started

1. __Configure a workspace and settings__

A workspace's main job is to specify the local path where blocks are to be stored when downloaded. Any block outside of this path will not be seen by this workspace.

```legohdl config home="~/develop/hdl/" -workspace```

Easy! Every workspace has its own library and cache, but can share markets. Let's look at our new workspace.

```legohdl list -workspace```

As you can see, we have no markets linked to this workspace. If we did, all released blocks in that market would be available to us to install or download.

Now we will configure other important settings.

```legohdl config "chase" -author```<br/>
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

2. __Make a new project__

A project can be made directly from legohdl CLI. This provides the benefit of adding key information and automatically setting up a developer's preferred project structure through the use of a template.

The template can be opened and freely edited.

```legohdl open -template```

> __Note__: Any where the word 'template' appears, it will be replaced by the name of the created project. %AUTHOR% will be replaced by our configured author setting, %DATE% will be replaced by that day's date, and %PROJECT% will be replaced by the project's name as well.

Let's add some folders and files that may be needed for every project.

    template/
        bench/
            testbench.py
            template_tb.vhd
        src/
            template.vhd
        README.md

An example of how to set up a template VHDL file may look like this:

``` vhdl
--  Project: %PROJECT%
--  Author: %AUTHOR%
--  Date: %DATE%
--  Description:
--

library ieee;
use ieee.std_logic_1164.all;

entity template is
    generic(
        
    );
    port(
        clk     :   IN  std_logic;
        reset   :   IN  std_logic;

    );
end entity;


architecture bhv of template is

begin


end architecture;
```

I've added a python file into the template for generating inputs/outputs for simulation as well as a templated testbench file similiar to the above code.

> __Note__: Opening the template through legoHDL opens a folder named template within legoHDL. If we have a template project structure living elsewhere, we can reference that instead when creating projects with: ```legohdl config "/users/chase/develop/hdl/template" -template```

Setting this option to an empty string will refer back to the template folder found within legohdl.

Now that the template is fit for our preferences, let's use it. It is time to make a new project! For this tutorial will make a simple mux to be used in a later design. We will design this mux to belong to our new library called "common".

```legohdl new common.mux -o```

Okay and it is open in our text-editor ready to work!

3. __Developing a Block__

At this point, a lot has happened. There is an metadata file titled "Lego.lock" inside our project, the project is already initialized with git, and our template auto-populated the project with files ready to go. This project is now considered a "block" because it has a Lego.lock file.

The development process is now no different than before. We will create our design, and then our testbench, making git commits along the way if desired. When we have our entity declared and written, we can view it with:

```legohdl port common.mux -map```

This will print out this block's toplevel entity as a component, available to be easily copied and pasted into another source file in this project, like the testbench. The -map option will give us the format for the component's instantiation as well as the necessary signals for the architecture declaration section. Pretty handy.

> __Note:__ To reference any internal entities within the block, append the entity's name to the block's title. If the block 'common.mux' had a internal entity called 'and_gate', we could view that component and its port map with: ```legohdl port common.mux.and_gate -map```

4. __Building a Block__

legoHDL is a package manager. It has no means to build a design, as HDL tools are complex and are not a one-size-fits-all. Despite this, legoHDL provides capability through the use of its labels, recipes, and scripts to enable the developer to run with their own build tools exactly how they want. Got an awesome makefile calling GHDL? Use it. Got TCL scripts for the entire Vivado design suite? Bring them on! 

First, we need the recipe file.

``legohdl export``

This creates the recipe file with the auto-determined toplevel design for the current project. 

You can explicitly set the block's toplevel design by adding the entity name to the export command.

```legohdl export mux```

Now to use the recipe file we need a script. From here, it is completely up to the developer to how they go about building; legoHDL is essentially passing off all the needed information for a build with the export command.

We could copy/paste our build scripts into every project's folder, but this problematic. First, with multiple copies it becomes difficult to update across the board. Second, we actually must include it in the project, and sometime we have more than one script to do different jobs. The solution is legoHDL's __scripts__.

<br />

> Scripts: A script is simply any user created file. legohdl can store scripts or store their file path to call for later use. It is practically using built-in aliases. Calling a script can be done like so:
```legohdl build @<script-name> [args passed to script..]```
    
Scripts can be linked from where they currently reside, in case they are hosted in a repository where users are updating them.

This was designed to keep track of handy build scripts that you as the developer use to analyze, synthesize, simulate, or program your design. Allowing legoHDL to store/point to these files gives the developer power and freedom to completely customize and bind their workflow together.

<br/>

__Recipes and Labels__

So, how will my build script know what files to analyze? Here's where recipes come into play. A recipe takes all labeled files and writes them to a file. All VHDL files and libraries will be in order to correctly be anaylzed. Default labels are:
-   @LIB for library VHDL code
-   @SRC for project-level VHDL design code,
-   @SIM for project-level  VHDL simulation code
-   @SRC-TOP for top-level design entity
-   @SIM-TOP for top-level simulation entity

Labels are what the export command throws into the recipe file.

Labels can be user-defined for the export command to additionally throw into the recipe file. These custom labels, if legoHDL finds any in the current block, will be inserted before the default labels.

Example:

You have a test generation python file that would like to be added to the recipe. Why? Answer: If you set up the stored build script to check for this new label, then the build script could run the test generation at the right stage in your build process.

Here's a sample recipe file:

``` 
@BENCH /Users/chase/Develop/hdl-dev/mem/flipflop/bench/testbench.py
@SRC /Users/chase/Develop/hdl-dev/mem/flipflop/design/sidecar.vhd
@SRC /Users/chase/Develop/hdl-dev/mem/flipflop/design/flipflop.vhd
@LIB verif /Users/chase/.legohdl/workspaces/lab/cache/verif/fileio/design/fileio.vhd
@SIM /Users/chase/Develop/hdl-dev/mem/flipflop/bench/flipflop_tb.vhd
@SIM-TOP flipflop_tb
@SRC-TOP flipflop
```

Notice the _@BENCH_ label is a custom label set like so:

```legohdl config BENCH="testbench.py" -label```

If IP were needed to be included for my script building, I could add a label

```legohdl config IP=".xci" -label -recur```

where the recur flag will indicate to recursively grab all .xci files found within every dependency used.

We can view our labels with

``legohdl list -label``

Here's a simple build file:
``` python
import os
#example build script demonstrating the easy handling of recipe file
#change directory to project's build folder
os.chdir("build")
#open recipe file
recipe = open("recipe", 'r')
#parse recipe file and analyze units
tb_unit = ''
top_unit = ''
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
#now analyze and run simulation from testbench file
os.system("ghdl -r --std=08 --ieee=synopsys "+tb_unit+" --vcd=./wf.vcd")
```

Now, we could add this to our legoHDL scripts, and further extend this script to do much more like take in any arguments. The sky is the limit when developer's are in control of how their scripts are to build HDL code. Let's add this file to my legohdl scripts.

Open the scripts folder.

```legohdl open -script```

Make a new build script file. However you roll, write a file in Make, python, TCL, or even a shell script, and have it run whatever tools you have, whether it be Vivado, GHDL, or Quartus. When your done, configure it for legoHDL to see:

```legohdl config master="python /Users/chase/.legohdl/scripts/builder.py" -script -lnk```

> __Note:__ The -lnk flag will prevent legoHDL from trying to copy the file into the scripts folder. Since it is already in the scripts folder, it is wise to just link it. It would also be wise to use -lnk when you would like your script to live elsewhere, allowing you to continue to improve it from its original location.


To run this newly configured script:

```legohdl build @master```

> __Note:__ If there is a script's alias being "master", it can be omitted from the build args and will run as default.
```legohdl build``` has the same effect as the previous command because they both call the script under master.

We can view our scripts with

```legohdl list -script```


5. __Releasing a Block__

Up until this point, everything has been local and the block has not yet been officially "released". It has been on version 0.0.0, which is an unreleased state. Now we are ready to release the current code's state as a version.

```legohdl release -maj```

This will set the version to the next major version for the project. It is best to follow semantic versioning for HDL design.
    
_MAJOR.MINOR.PATCH versioning suggestions:_  
-   _major_: any entity port changes or inconsistent changes to the block's intended behavior
-   _minor_: performance enhancements  
-   _patch/fix_: bug fixing and small code tweaks 

Seeing our block with ```legohdl list``` now highlights common.mux as version 1.0.0.

6. __Incorporating a Block as a Dependency__

Okay, the project is now ready to be incorporated into any other design! Upon releasing, it will install the release to the cache folder alongside generating a VHDL package file for the toplevel entity into the library folder, if a toplevel exists. The lines
``` VHDL
library common;
use common.mux_pkg.all;
```
are all that are needed for legoHDL to recognize the library and files being used and throw the required files in the recipe.

You could also instantiate the entity directly without having to use the auto-generated package file

``` VHDL
library common;

entity ...
end entity;

architecture ...
begin
    u0 : entity common.mux
    port map(
        IN_A=>IN_A,
        IN_B=>IN_B,
        SEL=>SEL,
        OUT_F=>OUT_F
    );
...
end architecture;
```

Don't remember the ports list? Run

```legohdl port common.mux -map```

to grab the format for instantation and any required signals.

<br/>

## Using Markets



<br/>

## Commands

```
USAGE:             
        legohdl <command> [block] [args]            

COMMANDS:
   init         initialize the current folder into a valid block
   new          create a templated empty block into workspace
   open         opens the downloaded block with the configured text-editor
   release      release a new version of the current block
   list         print list of all blocks available
   install      grab block from its market for dependency use
   uninstall    remove block from cache
   download     grab block from its market for development
   update       update installed block to be to the latest version
   export       generate a recipe file to build the block
   build        run a custom configured script
   del          deletes the block from the local workspace
   search       search markets or local workspace for specified block
   refresh      sync local markets with their remotes
   port         print ports list of specified block's entity
   show         read further detail about a specified block
   summ         add description to current block
   config       set package manager settings
```







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