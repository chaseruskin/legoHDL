# ![](./docs/src/images/title_3x.png)

# legoHDL
![ci-build](https://github.com/c-rus/legohdl/actions/workflows/build.yml/badge.svg)
### The package manager and development tool for Hardware Description Languages (HDL).
  
<br />  

legoHDL is a complete, robust, and flexible HDL package manager and development tool used through the command-line interface. It provides full package management capabilities and incorporates special functionality specific to HDL designs to rapidly improve development workflow.

__VHDL__ and __Verilog__ are supported and also as mixed-language.

Cross-platform compatibility with __macos__, __ubuntu__, and __windows__.

Requires only python 3.5+, git, and your favorite text-editor.


## __Better IP management. For all.__

legoHDL approaches IP management by allowing the developer to soley focus on designing new hardware, not wasting time fighting with tools and rewriting code. Developers take advantage of structural modeling styles to reuse IP, and legoHDL analyzes HDL source files to determine what external designs are required based on instantiations within the source code.
```
INFO:   Identified top-level unit: synthesizer
INFO:   Identified top-level testbench: tb_synthesizer
INFO:   Generating dependency tree...
--- DEPENDENCY TREE ---
\- audio.tb_synthesizer 
   +- audio.synthesizer 
   |  +- audio.wave_gen 
   |  +- audio.multi_port_adder 
   |  |  \- audio.adder 
   |  +- audio.audio_ctrl 
   |  \- audio.piano 
   \- audio.audio_codec_model 


--- BLOCK ORDER ---
[1]^-   audio.synthesizer(v2.0.2)
```

When a developer is ready to build their project, whether it's for linting, simulation, synthesis, or generating a bitstream, legoHDL exports a simple text file called a __blueprint__ that lists the necessary HDL files in a topologically sorted order to be read and plugged into _any_ backend tool for a completely custom workflow.

```
@BOARD-DESIGN /Users/chase/develop/eel4712c/synth/quartus/system_top_level.bdf
@VHDL-SRC /Users/chase/develop/eel4712c/synth/vhd/wave_gen.vhd
@VHDL-SRC /Users/chase/develop/eel4712c/synth/vhd/adder.vhd
@VHDL-SRC /Users/chase/develop/eel4712c/synth/vhd/audio_ctrl.vhd
@VHDL-SRC /Users/chase/develop/eel4712c/synth/vhd/piano.vhd
@VHDL-SRC /Users/chase/develop/eel4712c/synth/vhd/audio_codec_model.vhd
@VHDL-SRC /Users/chase/develop/eel4712c/synth/vhd/multi_port_adder.vhd
@VHDL-SRC /Users/chase/develop/eel4712c/synth/vhd/synthesizer.vhd
@VHDL-SIM /Users/chase/develop/eel4712c/synth/tb/tb_synthesizer.vhd
@VHDL-SIM-TOP tb_synthesizer /Users/chase/develop/eel4712c/synth/tb/tb_synthesizer.vhd
@VHDL-SRC-TOP synthesizer /Users/chase/develop/eel4712c/synth/vhd/synthesizer.vhd
```
Developers set up custom workflows by writing a build __script__ as simple or complex only once for their backend tool to be reused with all projects. No more copying makefiles or tcl scripts into every project. Easily share scripts, settings, and templates across your team by setting up __profiles__.

``` python
import os
#blueprint file is located in 'build/' directory
os.chdir('build') 

tb_entity = None
#list of tuples storing the (library,filepath) to be analyzed in order
src_list = [] 
#[!] read blueprint file to collect the necessary data to build the design
with open('blueprint', 'r') as blueprint:
    for rule in blueprint.readlines():
        #break up line into list of words
        rule = rule.split()
        #label is always first item, filepath is always last item
        label,filepath = rule[0],rule[-1]
        #collect data on non-work VHDL files and their libraries
        if('@VHDL-LIB' == label): 
            lib = rule[1] #second item is library name
            src_list += [(lib, filepath)]
        #collect data on VHDL work files
        elif('@VHDL-SRC' == label or '@VHDL-SIM' == label): 
            src_list += [('work', filepath)]
        #collect data on VHDL testbench entity
        elif('@VHDL-SIM-TOP' == label): 
            tb_entity = rule[1] #second item is entity name

#[!] analyze all collected VHDL files
for src in src_list:
    os.system('ghdl -a --std=08 --ieee=synopsys --work='+src[0]+' '+src[1])

#[!] run simulation if a testbench entity is provided
if(tb_entity != None):
    os.system('ghdl -r --std=08 --ieee=synopsys '+tb_entity)
```

legoHDL has multiple configurable settings that can be easily changed through its integrated GUI.

![legohdl settings label](./docs/src/images/settings_gui_label.png)

<br /> 

### __Documentation__
Documentation can be found [here](https://c-rus.github.io/legoHDL/). 

### __Roadmap__
This project is under active development, and the [roadmap](https://github.com/c-rus/legoHDL/projects/1) gives a glimpse into what features and enhancements are being worked on. Documentation and features are constantly being added/changed.

### __Trying it out__

1. Make sure a version of python >=3.5 and git are installed.

`python --version`

`git --version`

2. clone this repository

`git clone https://github.com/c-rus/legoHDL.git`

3. Install the python program via pip

`pip install .`

4. Verify it is properly installed.

`legohdl --version`

5. See the documentation website for further details on [getting started](https://c-rus.github.io/legoHDL/1_0_starting.html).

> __Note__: Once the roadmap is complete for __v1.0.0__, users will be able to install legoHDL directly through pip from PYPI.

### __Quick Start__
1. Upon first time calling legohdl, run `legohdl` from the command line.

2. When prompted to import a profile, return `y`.

3. Next, return nothing to get going with the default profile.

4. Enter other prompted information such as your name, text-editor, and workspace path.

5. legoHDL is now ready. Create a block from the imported default template and automatically open it in the configured text-editor
`legohdl new MyLib.MyBlock -open`

Refer to the [documentation](https://c-rus.github.io/legoHDL/) for more details.

### __Commands__
Refer to the [manual](https://github.com/c-rus/legoHDL/blob/master/src/legohdl/data/manual.txt) for complete overview and explanations on every command and their relevant flags.

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

</br>
Inspired by the modular and fun building approach of LEGO® bricks, legoHDL brings modularity and management to the HDL world by enabling designs to be built as if they are LEGO® bricks. LEGO® is a trademark of the LEGO Group of companies which does not sponsor, authorize or endorse this site or this project.