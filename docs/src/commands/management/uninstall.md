# uninstall

## Name

        uninstall - Remove a block from the workspace's cache

## Synopsis

        legohdl uninstall <block> [-<version>]

## Description

        Removes installed block versions from the workspace cache. 

        If -<version> is omitted, then ALL versions for the specified block will
        be removed. Specifying -<version> will only remove it and no others, 
        given it is installed. 

        Can also remove groups of versions by passing a partial version to
        -<version>.

## Options

        <block>
                :ref:

        -<version>
                Specific version to uninstall.


