# Initial Setup

Follow the process below to set up required preliminary settings.

Running `legohdl` for the first time will prompt the user if they would like to set up a [profile](./../glossary.md#profile).

```
$ legohdl
INFO:	This looks like your first time running legoHDL! Would you like to use a 
profile (import settings, template, and plugins)? [y/n]
```

Returning `y` gives the user 3 choices.
```
$ y
Enter:
1) nothing for default profile
2) a path or git repository to a profile
3) 'exit' to cancel configuration
```

Unless you have a profile already that you would like to use, let's go ahead and return an empty response to use the default profile.

```
$
INFO:   Setting up default profile...
INFO:   Reloading default profile...
INFO:   Importing default profile...
INFO:   Overloading legohdl.cfg...
CREATED: plugin.hello = echo "hello world!"
CREATED: plugin.demo = python $LEGOHDL/plugins/demo.py
OBSERVE: hdl-styling.auto-fit = on
OBSERVE: hdl-styling.alignment = 1
ALTERED: hdl-styling.port-modifier = w_*
CREATED: [workspace.primary]
CREATED: workspace.primary.path = 
CREATED: workspace.primary.vendors = 
INFO:   Importing template...
INFO:   Overloading template in legohdl.cfg...
OBSERVE: general.template = 
INFO:   Importing plugins...
INFO:   Copying demo.py to built-in plugins folder...
INFO:   Overloading plugins in legohdl.cfg...
OBSERVE: plugin.hello = echo "hello world!"
OBSERVE: plugin.demo = python $LEGOHDL/plugins/demo.py
```
legoHDL then asks for your name
```
Enter your name:
$ Chase Ruskin
ALTERED: general.author = Chase Ruskin
```
and how it should call your text-editor to run.
```
Enter your text-editor:
$ code
ALTERED: general.editor = code
```
Finally, you must specify a path for the current active-workspace, which is named "primary" by default.
```
INFO:	Local path for workspace primary cannot be empty.
Enter path for workspace primary: 
$ ~/develop/hdl/primary/
```
> __Note__: If the entered path does not exist, legoHDL will notify you and ask to verify the creation of the new path.

Now the default console output from legoHDL appears. All required configurations are complete.
```
Usage:         
	legohdl <command> [entry] [<flags>] [-h]   

Commands:
Development
   new          create a new legohdl block (project)
   init         initialize existing code into a legohdl block
   open         open a block with the configured text-editor
   get          print instantiation code for an HDL unit
   graph        visualize HDL dependency graph
   export       generate a blueprint file
   build        execute a custom configured plugin
   release      set a newer version for the current block
   del          delete a block from the local workspace path

Management
   list         print list of all blocks available
   refresh      sync local vendors with their remotes
   install      bring a block to the cache for dependency use
   uninstall    remove a block from the cache
   download     bring a block to the workspace path for development
   update       update an installed block to be its latest version
   info         read further detail about a block
   config       modify legohdl settings

Type 'legohdl help <command>' to read about that command.
```

You can modify settings at any time in the GUI with
```
$ legohdl open -settings
```
See [Managing Settings](../user_guide/managing_settings.md) for more information regarding settings.