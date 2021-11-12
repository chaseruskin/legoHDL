# ![](./docs/assets/title_3x.png)

# legoHDL
![ci-build](https://github.com/c-rus/legohdl/actions/workflows/build.yml/badge.svg)
### The custom, lightweight, and powerful HDL package manager and development tool.
  
<br />  

legoHDL is a simple, powerful, and flexible HDL package manager and development tool used through the command-line interface. It provides full package management capabilities as one would expect from premiere software package managers like Cargo, APT, PIP, and RubyGems and incorporates special functionality specific to HDL designing to rapidly improve development workflow.

Inspired by the modular and fun building approach of LEGO® bricks, legoHDL brings modularity and management to the HDL world by enabling designs to be built as if they are LEGO® bricks. LEGO® is a trademark of the LEGO Group of companies which does not sponsor, authorize or endorse this site or this project.

Supports Linux, macOS, and Windows.

Supports VHDL and Verilog with mixed language support.

<br />

legoHDL is available to work completely local or along with remote locations to collaborate and share blocks with others. It is designed to give the developer complete customization and increased productivity in their workflow. Settings can be modified via an integrated GUI.
<br /> 

### __Documentation__

Documentation can be found [here](https://legohdl.readthedocs.io/en/latest/index.html). 


### __Roadmap__
The project is currently under development, and the [roadmap](https://github.com/c-rus/legoHDL/projects/1) gives a glimpse into what is being developed with new things always being added.

### __Trying it out__
Being under active development, some things are out-of-date in the documentation and features are constantly being changed. If you still want to try some things out, you currently can:
1. clone this repository
2. run `pip install .` from within the repository's root directory.
3. have fun! See the documentation website for further info on getting started.

Once the roadmap is complete for v1.0.0, users will be able to install legoHDL directly through pip from PYPI.

### __Quick Start__

1. Upon first time calling legohdl, run `legohdl` from the command line.

2. When prompted to import a profile, return `y`.

3. Next, return nothing to get going with the default profile.

4. Enter other prompted information such as your name, text-editor, and workspace path.

5. Ready to design! Create a block from the imported default template and automatically open it in the configured text-editor: `legohdl new MyLib.MyBlock -open`. Refer
to the [documentation](https://hdl.notion.site/legoHDL-f798525eee2f4378bcf5e970ae6373cf) for more details.

### Commands

Refer to the [manual](https://github.com/c-rus/legoHDL/blob/master/src/legohdl/data/manual.txt) for documentation on every command and their relevant flags.

```
USAGE:             
        legohdl <command> [argument] [flags]            

COMMANDS:

Development
   new          create a new legohdl block (project)
   init         initialize existing code into a legohdl block
   open         open a block with the configured text-editor
   get          print instantiation code for an HDL entity
   graph        visualize HDL dependency graph
   export       generate a blueprint file
   build        execute a custom configured script
   release      set a newer version for the current block
   del          delete a block from the local workspace path

Management
   list         print list of all blocks available
   refresh      sync local markets with their remotes
   install      bring a block to the cache for dependency use
   uninstall    remove a block from the cache
   download     bring a block to the workspace path for development
   update       update an installed block to be its latest version
   show         read further detail about a block
   config       modify legohdl settings

Type 'legohdl help <command>' to read about the entered command.

```
