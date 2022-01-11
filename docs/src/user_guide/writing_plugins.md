# Writing Plugins

This page walks through a general procedure for how a plugin could be written within the scope of legoHDL.

A [plugin](./../glossary.md#plugin) is loosely defined as a command. However, to be beneficial to HDL designing, these commands will typically be a wrapper of a FPGA-tool, such as quartus, GHDL, verilator, etc.

Plugins are defined in the legohdl.cfg file.

```ini
[plugin]
backend1 = echo "hello world!"
backend2 = python c:/users/chase/hdl/plugins/ghdl.py
```

Here, `ghdl.py` is a custom user-defined script that wraps the GHDL command-line tool.

The general series of steps a plugin should follow are:

1. Collect data from the [blueprint](./../glossary.md#blueprint) file
2. Perform an action with the collected data

> __Note:__ Remember, you can extend your plugin to handle its own command-line arguments for an even more customized experiences/shortcuts.

The blueprint file, if created, can be guaranteed to located from the block's base directory at `/build/blueprint` after a successful export.