# Blocks

This page explains how legoHDL packages projects into [blocks](./../glossary.md#block) for reusability.

## What's a block?

A _block_ is an HDL project managed by legoHDL. At its root folder exists a special file that must be exactly called "[Block.cfg](./../glossary.md#blockcfg)".

## Where do blocks live?

Blocks can exist at one or more _levels_: 
- downloaded/developing (`D`)
- installed (`I`)
- available (`A`)

### Downloaded/Developing

Blocks at the _downloaded/developing_ level are projects that are currently in-development. They exist under the workspace's local path, which is defined in the [legohdl.cfg](./../glossary.md#legohdlcfg) file. 

These blocks are considered _un-stable_ because there designs can freely change at any time.

### Installed

Blocks at the _installed_ level are installed to the workspace's cache. Their location is abstracted away from the developer because these blocks are not to be edited. These blocks have their files stored as read-only to add a extra precautious layer to prevent accidental alterations.

These blocks are considered _stable_ because they are "snapshots" of the project from the repository's version control history. A block can be installed under multiple versions.

Installed blocks are intended to be referenced as dependencies for blocks at the downloaded/developing level.

### Available

Blocks at the _available_ level are found in one of the workspace's vendors as having the potential to be installed for use or downloaded for further development.

## What's in a block?

The files in a block can be grouped into 3 categories:
- HDL source files
- Block.cfg file
- supportive files

### HDL source files

These are the project's relevant internal HDL code files written in either VHDL or verilog. External HDL code files are to be referenced and do not need to be copied into the project. External HDL files are known to be used from the Block.cfg file's `block.requires` key.

### Block.cfg file

A metadata file necessary for legoHDL to mark a folder as a _block_. Zero to minimal editing is to be done by the developer within this file.

### Supportive files

All other files relevant to the current project; whether it be tcl scripts, do files, constraint files, test vectors, etc. You can integrate any filetype into your workflow by creating labels and supporting that label in a plugin.