# info

## Name

        info - Read detailed information about a block

## Synopsis

        legohdl info <block> [-D | -I | -<version> | -A] [-more] 
                [-vers[=<range>]] [-changelog]
        legohdl info <profile> -profile
        legohdl info <vendor> -vendor

## Description

        By default, will print the metadata about the given block. 

        If -vers is applied, it will list all the available versions for 
        installation, and hightlight which versions are installed under the 
        workspace cache.

        If -changelog is applied, only the changelog file will be printed to
        the console (if exists).

## Options

        <block>
                :ref:

        -D
                Return data from block at the download level, regardless of
                the status of 'multi-develop'.

        -I
                Return data from latest block at the installation level,
                regardless of the status of 'multi-develop'.

        -<version>
                Return data from the block with specified version/partial
                version.

        -A
                Return data from the block at the available level.

        -more
                Get relevant stats about the block such as the path, project 
                size, design units, and block integrations.

        -vers[=<range>]
                List all available versions for the specified block. <range>
                will constrain the list of versions. Accepted values for <range>
                are I or a version indexing.

        -changelog
                Print the associated changelog with the block.

        <profile>
                :ref:

        -profile
                Indicate that a profile is to be searched for its information.

        <vendor>
                :ref:

        -vendor
                Indicate that a vendor is to be searched for its information.


