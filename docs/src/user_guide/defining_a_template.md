# Defining a Template

A template is helpful in that it can encourage a team to use a particular coding practice and removes the need to continually write boilerplate code.

A template can exist anywhere on a user's machine. 

To set a folder as the defined template, edit the `template` key under the `[general]` section in the `legohdl.cfg` file.

```ini
[general]
    template = /users/chase/develop/template/
```

Organize the folder's directory as fit. A block is created using the defined template by default. This means the folder is copied into a new location under the workspace's local path.

## Viewing templated files

```
$ legohdl list -template
Relative Path                                                Hidden  
------------------------------------------------------------ --------
/.hidden/tb/TEMPLATE.vhd                                     yes     
/.gitignore                                                  -       
/src/TEMPLATE.vhd                                            -       
```

## Editing the template

To open the template folder in your configured text-editor run the following command:
```
$ legohdl open -template
```

## Importing a templated file into an existing block

An existing block can have a new file based off a templated file with the following command:

```
$ legohdl new <file> -file=<template-file>
```

where `<file>` is a relative non-existent path and `<template-file>` is a value listed under the template's "Relative Path" column.

Use `-force` to overwrite a file that already exists.

## Hiding files for particular scenarios

Templates will not copy in hidden directories when creating a block.

To hide a file for availability when only needed on a case-by-case basis, nest it inside a hidden directory.

An example defining a folder named `.hidden` located at the root of our template's path.
```
/.hidden/tb/TEMPLATE.vhd 
```