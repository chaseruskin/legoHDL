# Writing Plugins

This page walks through a general procedure for how a plugin could be written within the scope of legoHDL.

A [plugin](./../glossary.md#plugin) is loosely defined as a command. However, to be beneficial to HDL designing, these commands will typically be a wrapper of a FPGA-tool, such as quartus, GHDL, verilator, etc.

Plugins are defined under the `[plugin]` section in `legohdl.cfg` file.

```ini
[plugin]
    backend1 = echo "hello world!"
    backend2 = python c:/users/chase/hdl/plugins/ghdl.py
```

_backend2_ is a plugin that call python to run the file `ghdl.py`, which is a custom user-defined script that wraps the GHDL command-line tool.

The general series of steps a plugin should follow are:

1. Collect data from the [blueprint](./../glossary.md#blueprint) file
2. Perform an action with the collected data

> __Note:__ Remember, you can extend your plugin to handle its own command-line arguments for an even more customized experiences/shortcuts.

The blueprint file, if created, can be guaranteed to located from the block's base directory at `/build/blueprint` after a successful export.

## Pseudo-code

Here is some general pseudo-code for creating a plugin script that wraps an EDA tool's functionality.

```
Create data structures that will store commonly labeled files listed in the blueprint.

Open BLUEPRINT.

While BLUEPRINT has lines:
    Parse the line to obtain the file's LABEL.

    Determine filepath's storage based on label.
    if LABEL == @VHDL-SRC
        store filepath in collection of vhdl files
    else if LABEL == @VLOG-SRC
        store filepath in collection of verilog files
    ...

Close BLUEPRINT.

Handle command-line arguments to determine EDA tool's ACTION.

Route action based on command-line arguments.
if ACTION == CHECK SYNTAX
    Perform linting using EDA tool.
else if ACTION == SYNTHESIZE
    Perform synthesize using EDA tool.
else if ACTION == PLACE AND ROUTE
    Perform place-and-route using EDA tool.
```