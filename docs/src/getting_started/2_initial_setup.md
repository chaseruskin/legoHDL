# Initial Setup

Follow the process below to set up required preliminary settings.

Running `legohdl` for the first time will prompt the user if they would like to set up a [profile](./../glossary.md#profile).

```
$ legohdl
INFO:	This looks like your first time running legoHDL!
Would you like to use a profile (import settings, template,
and scripts)? [y/n]
```

Returning `y` gives the user 3 choices.
```
$ y
Enter:
1) nothing for default profile
2) a path or git repository to a profile
3) 'exit' to cancel configuration
```

Unless you have a profile already that you would like to use, let's go ahead and return an empty string to use the default profile.

```
$
INFO:	Setting up default profile...
INFO:	Reloading default profile...
INFO:	Importing profile default...
INFO:	Overloading legohdl.cfg...
INFO:	[workspace] [primary] path = 
INFO:	[workspace] [primary] vendors = 
INFO:	Importing template...
INFO:	Importing scripts...
INFO:	Copying hello.py to built-in scripts folder...
INFO:	Overloading scripts in legohdl.cfg...
INFO:	[script] hello = python /Users/chase/.legohdl/scripts/hello_world.py
```
legoHDL then asks for your name
```
Enter your name:
```
and how it should call your text-editor to run.
```
Enter your text-editor:
```
Finally, you must specify a path for the current active-workspace, which is named "primary" by default.
```
INFO:	Local path for workspace primary cannot be empty.
Enter path for workspace primary: 
```
> __Note__: If the entered path does not exist, legoHDL will notify you and ask to verify the creation of the new path.

Now you should see the regular output from legoHDL. This means all required configurations are complete.
```
Usage:         
	legohdl <command> [argument] [flags]        

Commands:
Development
   new          create a new legohdl block (project)
   init         initialize existing code into a legohdl block
   open         open a block with the configured text-editor
   get          print instantiation code for an HDL unit
   graph        visualize HDL dependency graph
   export       generate a blueprint file
   build        execute a custom configured script
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

Type 'legohdl help <command>' to read about the entered command.
```
You can change any settings at anytime in the GUI with

`$ legohdl open -settings`