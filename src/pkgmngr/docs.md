# _lego_**HDL** Documentation
  
<br />   

_lego_**HDL** is a simple, powerful, and flexible package manager for VHDL designs. It provides full package management capabilities as one would expect from premiere software package managers like Cargo, APT, PIP, and RubyGems. Inspiration has been taken from all of these to build this tool for HDL development.

<br />

LegoHDL is available to work completely local or along with remote locations to collaborate and share modules with others. It is designed to give the developer maximum freedom in their workflow.

<br />

## Introduction

Let's go over some important terminology regarding legoHDL.

__project__ : A group of VHDL files grouped together to create a design. A project is a package if it has a ".lego.lock" file at the root of the its directory.

__workspace__ : This is your working environment. Only one can be active on your local machine at a time. It consists of a local path and optionally, any linked remotes. The local path is where all projects can freely live when downloaded.

__market__ : This is a repository that hosts a "collection" of released packages. This can be a local repository or remote repository. In order for a package to be added to the collection it must have its own remote repository.

__package__ : This is a self-contained project that contains a .lego.lock file. A package's title must consist of a library and a name. An example package title is "util.fifo".

__script__ : A user created file. These can be stored within legoHDL or linked to if say the script belongs to some repository where users are actively developing it. Scripts can be used to build/run a package, but also to more generally store common files across all packages, like a constraint file.

__recipe__ : A list of all required files for a given package to be built from, in the  correct order needed. It is a file with identifying labels regarding the project and its dependencies. This is intended to be the "golden link" between the package management process and building a design.

__label__ : A identifier that can be used to gather dependencies to be written to the recipe. Default labels are @LIB for VHDL libraries, @SRC for package-level VHDL code, and @TB for package-level testbench file. Developers can can create labels and provide their own extensions, like creating an @IP for .xci files.

__.lego.lock__ : The metadata file that signifies if a project is a package. This file is automatically maintained and is hidden from the developer. It is strongly recommended to NOT try to modify this file, as it will not be needed.

<br />

## Getting Started

1. Configure a workspace and other settings

A workspace specifies what local location to store downloaded packages in for development.

```legohdl config home="~/develop/hdl/" -workspace```

Easy! Every workspace has its own library and cache, but can share markets. Let's look at our new workspace.

```legohdl list -workspace```

As you can see, we have no markets linked to this workspace. If we did, all released packages in that market would be available to us to install or download.

Now we will configure other important settings.

```legohdl config "chase" -author```<br/>
```legohdl config "code" -editor```

Configuring an editor allows me to automatically open projects with the `-o` flag.

2. Make a new project

A project can be made directly from legohdl CLI. This provides the benefit of adding key information and automatically setting up a developer's preferred project structure through the use of a template.

The template can be opened and freely edited.

```legohdl open -template```

> __Note__: Any where the word 'template' appears, it will be replaced by the name of the created project. %AUTHOR% will be replaced by our configured author setting, %DATE% will be replaced by that day's date, and %PROJECT% will be replaced by the project's name as well.

Now that the template is fit for our preferences, let's use it. It is time to make a new project! For this tutorial will make a simple mux to be used in a later design.

```legohdl new demo.mux -o```

Okay and it's open in our text-editor ready to work!

3. Develop a project

At this point, a lot has happened. There is an off-limits file called ".lego.lock" inside our project, the project is already initialized with git, and our template auto-populated the project with files ready to go.

The development process is now no different than before. We will create our design, and then our testbench, making git commits along the way. When we have our entity declared and written, we can view it with:

```legohdl port demo.mux -map```

This will print out our entity as a component, available to be easily copied and pasted into another source file in this project, like the testbench. The -map option will give us the format for the component's instantiation as well as the necessary signals for the architecture declaration section. Pretty handy.

4. Building a project

legohdl is a package manager. It has no means to build a project, as HDL tools are complex and are not a one-size-fits-all. Despite this, legohdl provides capability through the use of its labels, recipes, and scripts enable the developer to run with their own build tools exactly how they want. Got an awesome makefile calling ghdl? Use it. Got TCL scripts for the entire vivado design suite? Bring them on! 

First, we need the recipe file.

``legohdl export``

This creates the recipe file with the auto-determined toplevel design for the current project. Now to use the recipe file we need a script. From here, it is completely up to the developer to how they go about building; legohdl is essentially passing off all the needed information for a build with the export command.

We could copy/paste our build scripts into every project's folder, but this problematic. First, with multiple copies it becomes difficult to update across the board. Second, we actually must include it in the project. The solution is legohdl's __scripts__.

<br />

     >>>Scripts>>>

    A script is simply any user created file. legohdl can store scripts or store their file path to call for later use. It is practically using built-in aliases. Calling a script can be done like so:
```legohdl build @<script-name> [args passed to script..]```
    
    Scripts can be linked from where they currently reside, in case they are hosted in a repository where users are updating them.

    This was designed to keep track of handy build scripts that you as the developer use to analyze, synthesize, simulate, or program your design. Allowing legohdl to store/point to these files gives the developer power in not "copying" this file into every project for use, thus making it troublesome if that script would need to be modified.

<br/>

So, how will my build script know what files to anaylze? Here's where recipes come into play. A recipe takes all labeled files and writes them to a file. All VHDL files and libraries will be in order to correctly be anaylzed. Default labels are @LIB for user libraries, @SRC for project-level source code, and @TB for the top-level testbench.

Here's a sample recipe file:

``` 
@TEST-GEN /Users/Chase/Develop/hdl/util/alu/bench/testbench.py  
@LIB util /Users/Chase/.legohdl/cache/util/flipflop/design/*.vhd  
@LIB util /Users/Chase/.legohdl/lib/util/flipflop_pkg.vhd  
@SRC /Users/Chase/Develop/hdl/util/alu/design/*.vhd  
@TB /Users/Chase/Develop/hdl-dev/util/alu/bench/alu_tb.vhd
```

Notice the _@TEST-GEN_ label is a custom label set like so:

```legohdl config TEST-GEN="testbench.py" -label```

If IP were needed to be included for my script building, I could add a label

```legohdl config IP=".xci" -label -recur```

where the recur flag will indicate to recursively grab all .xci files found within every dependency used.

We can view our labels with

``legohdl list -label``s

Here's a simple build file:
``` python
import os
#example build script demonstrating the easy handling of recipe file
#open recipe file
recipe = open("./build/recipe", 'r')
#parse recipe file and analyze units
tb_path = ''
for x in recipe.readlines():
    #break up line into list of strings
    parsed_list = x.split(' ')
    tag = parsed_list[0] #tag is always first item
    if(tag == '@LIB'): 
        #determine how to handle libraries
        os.system("ghdl -a --std=08 --work="+parsed_list[1]+" "+parsed_list[2])
    elif(tag == '@SRC'): 
        #determine how to handle source code
        os.system("ghdl -a --std=08 "+parsed_list[1])
    elif(tag == '@TB'): 
        #determine how to handle testbench file
        tb_path = parsed_list[1]
        #parse unit name from file path
        unit_name = tb_path[tb_path.rfind('/')+1:tb_path.rfind('.')]
    elif(tag == "@TEST-GEN"): 
        #will run test-generation script to create files for tb
        os.system("python3 "+parsed_list[1].strip())
#now analyxe and run simulation from testbench file
os.system("ghdl -a -g --std=08 -fsynopsys "+tb_path) 
os.system("ghdl -r --std=08 -fsynopsys "+unit_name+" --vcd=./wf.vcd")
```

Now, I could add this to my legohdl scripts, and further extend this script to do much more like take in arguments. The sky is the limit when developer's are in the driver seat for how their scripts are to build HDL code. Let's add this file to my legohdl scripts.

```legohdl config quick-build="python3 users/chase/develop/hdl/demo/mux/builder.py" -script```

To run this newly configured script:

```legohdl build @quick-build```

We can view our scripts with

```legohdl list -script```

We can edit our copied scripts with

```legohdl open -script```

5. Releasing a project as package

Up until this point, everything has been local and the project has not yet been officially "released". It has been on version #0.0.0. Now we are ready to release the current code's state as a version. 

```legohdl release -maj```

This will set the version to the next major version for the project. It is best to follow semantic versioning for HDL design.
    
> _MAJOR.MINOR.PATCH versioning_  
_major_: any entity port changes or inconsistent changes to the module's intended behavior  
_minor_: performance enhancements  
_patch/fix_: bug fixing and small code tweaks 

Okay, the project is now ready to be incorporated into any other design! Upon releasing, it will install the release to the cache folder alongside generating a VHDL package file for the toplevel entity into the library folder. The lines
``` VHDL
library demo;
use demo.mux_pkg.all;
```
are all that are needed for legohdl to say yup, I'll throw the required files in the recipe for you! And don't forget, since its a package, you can go straight to instantiating the component in your design. Don't remember the ports list? Run

```legohdl port demo.mux -map```

to grab the format for instantation and any required signals.

<br/>

## Using Markets
<br/>
<br/>
<br/>

Developers can also store other common files in the scripts section, such as constraint files. It can then become very powerful to enable a build script to reference/use these files by passing an certain arg through a build command.

Example:

Developer creates a python script used to build designs with quartus command line tools. The developer designed the python script to accept the first argument as the target device.

```legohdl build @quartus x47c133g2```

<br />

## Labels

Labels are what the export command throws into the recipe file. Default labels are @LIB for libraries/dependencies, @SRC for current project's source code, and @TB for top-level module's respective testbench.

Labels can be user-defined for the export command to additionally throw into the recipe file. These custom labels, if legohdl finds any in the current project, will be inserted before the default labels.

Example:

Developer has a test-gen python file that would like to be added to the recipe. Why? Answer: If the developer set up the stored build script to check for this new label, then the build script could run the test-gen at the right point in the build process.

```legohdl config TEST-GEN=".py" -label```

or, more explicitly could have lots of files with .py ext in the project that do different things

```legohdl config TEST-GEN="test_gen.py" -label```

```legohdl config TEST-VER="test_ver.py" -label```

Now the developer has set up the build script to handle these two labels and run their files at the user-defined time.

Assigning a -label or -build to "" or '' will effectively remove it from legohdl's settings and delete it if it was a script and had made a copy (configured without -lnk option).

    NOTE: A user-defined label can be recursively searched through dependencies, as would an @LIB label with the -recur flag.