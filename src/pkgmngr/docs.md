# _lego_**HDL** Documentation
  
<br />   

_lego_**HDL** is a simple, powerful, and flexible package manager for VHDL designs. It provides full package management capabilities as one would expect from premiere software package managers like Cargo, APT, PIP, and RubyGems. Inspiration has been taken from all of these to build this tool for HDL development.

<br />

LegoHDL is available to work completely local or along with remote locations to collaborate and share modules with others.

<br />

## Scripts

A script is simply any user created file. legohdl can store scripts or store their file path to call for later use. It is almost like using built-in aliases. 
Calling a script can be done with the "build" command and using @name of configured script. 

This was designed to keep track of possibly handy build scripts that you as the developer use to analyze, synthesize, simulate, or program your design. Allowing legohdl to store/point to these files gives the developer power in not "copying" this file into every project for use, thus making it troublesome if that script would need to be modified.

Developers can also store other common files in the scripts section, such as constraint files. It can then become very powerful to enable a build script to reference/use these files by passing an certain arg through a build command.

Example:

Devloper creates a python script used to build designs with quartus command line tools. The developer designed the python script to accept the first argument as the target device.

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

    NOTE: A user-defined label will not be recursively searched through dependencies, as would an @LIB label.