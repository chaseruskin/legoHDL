Commands
========

This section lists and explains the available commands. 
Commands are set up to run in similar fashion across all commands. 
The command usage is `legohdl <command> [argument] [flags]`.

- `command` must be supplied with every call to `legohdl`. It must be one of the supported commands listed.
- `argument` is the value to be used with the command. This is typically a block's title, but can also be a market's name or a settings value. There are only a few times when an argument is not needed.
- `flags` are optional ways to customize the command. Each command may have its own custom supported flags. A common flag found across commands is `-v0.0.0` where the `0`'s indicate a version number following semantic versioning. This flag will indicate what version of the specified block to use.

> **Note**: Windows users may experience issues using the version flag. The version flag can be written as `-v0.0.0` or `-v0_0_0` for convenience.
> 

How to understand these commands:

- Anything in `[ ]` is optional
- Anything in `< >` has an actual value needing to be filled there, respective of what is said within the angular brackets
- A `|` between flags means only one of the flags can be raised/used at a time.
- `( )` are used to group related flags together

> Note: A `<block>` is in the format `<library>.<name>`
> 

## Commands

```
USAGE:             
        legohdl <command> [argument] [flags]            

COMMANDS:

Development
   init         initialize the current folder into a valid block format
   new          create a templated empty block into workspace
   open         opens the downloaded block with the configured text-editor
   port         print ports list of specified entity
   graph        visualize dependency graph for reference
   export       generate a blueprint file from labels
   build        execute a custom configured script
   run          export and build in a single step
   release      release a new version of the current block
   del          deletes a configured setting or a block from local workspace

Management
   list         print list of all blocks available
   refresh      sync local markets with their remotes
   install      grab block from its market for dependency use
   uninstall    remove block from cache
   download     grab block from its market for development
   update       update installed block to be to the latest version
   show         read further detail about a specified block
   config       set package manager settings
	 profile      import configurations for scripts, settings, and template

Type 'legohdl help <command>' to read more on entered command.
```

### init

```
legohdl init <block> [-<market> -<remote>]

legohdl init <value> [-market | -remote | -summary]
```

### new

```
legohdl new <block> [-<market> -<remote> -open]

legohdl new <file-name> -<template-file-name> -file
```

### open

```
legohdl open <block>

legohdl open [<script-name>] -script

legohdl open (-settings | -template)
```

### release

```
legohdl release [<message>] (-maj | -min | -fix | -v0.0.0) [-strict -soft]
```

### list

```
legohdl list [<block>] [-alpha -install]

legohdl list -script

legohdl list -workspace

legohdl list -label

legohdl list -market
```

### install

```
legohdl install (<block> [-v0.0.0]) | -requirements
```

### uninstall

```
legohdl uninstall <block> [-v0.0.0]
```

### download

```
legohdl download <block> [-open]
```

### update

```
legohdl update <block>
```

### export

```
legohdl export [<toplevel>]
```

### build

```
legohdl build +<script-name> [<arguments-for-script>...]
```

### run

```
legohdl run +<script-name> [<arguments-for-script>...]
```

### del

```
legohdl del <block> -uninstall

legohdl del <market> -market

legohdl del <workspace> -workspace

legohdl del <label> -label
```

### refresh

```
legohdl refresh [<market>]
```

### port

```
legohdl port <block>[:<entity>] [-map -instance]
```

### show

```
legohdl show <block> [-v0.0.0]

legohdl show <block> [-version -v0.0.0]

legohdl show <block> [-changelog]
```

### config

```
legohdl config <value> (-author | -editor | -active-workspace | -market (-add | -remove))

legohdl config <key>="<value>" (-label [-recursive] | -market [-add | -remove] | -workspace | -script [-link])
```