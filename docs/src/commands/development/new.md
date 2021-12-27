# new

## Name

        new - Create a new legoHDL block (project)

## Synopsis

        legohdl new <block> [-open] [-remote=<url> [-fork]] [-path=<path>] 
                [-no-template]
        legohdl new <file> -file[=<template-file>] [-force] [-no-open]

## Description

        Create a new HDL project recognized by legoHDL as a "block". The block
        will be created under a new folder at the workspace's local path such
        as <workspace-path>/<block-library>/<block-name>. A git repository will 
        be automatically created, and a bare git remote repository URL can be 
        passed for automatic configuration. If a non-bare remote repository is 
        passed, the block will be created and can be optionally forked using 
        -fork.

        When copying in the template, files hidden within a hidden directory 
        will not be copied. The files a designer would place inside a hidden 
        directory may be extra files that could be initialized later on a 
        per-block basis.

        If trying to create a new file and that path already exists, the
        existing file will not be overwritten unless -force is used. Creating 
        new files by default will auto-open in the configured text editor.

## Options

        <block>
            The project's title. A library and a name must be included, and 
            optionally a vendor can be prepended to the title.

        -open
            Upon creating the block, open it in the configured text-editor.

        -remote=<url>
            A bare remote git repository to be attached to the created block's
            git repository.

        -fork
            Separate the remote repository from the local repository. Do not
            push changes to the original remote.

        -path=<path>
            Overrides the default download path and instead creates block at
            <path> relative to the workspace's local path.

        -no-template
            Do not copy in the configured template folder. The created block
            folder will only contain the necessary Block.cfg file.

        <file>
            The filepath to intialize a new file.

        -file[=<template-file>]
            Initialize a new file within the current block. Specifying 
            <template-file> will copy the template file to the desired directory
            with placeholders correctly replaced. Omitting <template-file> will 
            create a blank file.

        -force
            Overwrite the filepath even if it already exists when initializing a
            file.

        -no-open
            Do not open the newly created file in the configured editor.


