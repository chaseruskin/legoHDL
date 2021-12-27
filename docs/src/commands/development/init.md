# init

## Name

        init - Initialize a legoHDL block from existing code and block metadata.

## Synopsis

        legohdl init <block> [-remote=<url> [-fork]] [-vendor=<mkrt>] 
                [-summary=<summary>]

## Description

        When the current directory or provided remote repository already is a 
        valid legoHDL block, the <block> is ignored.

        When a remote repository is given and it already is a valid block (i.e. 
        the root directory contains a Block.cfg file), the <block> will be 
        ignored and the actual title will be used. This becomes an equivalent to
        using the 'download' command.

## Options

        <block>
                :ref:

        -remote=<url>
                :ref:

        -fork
                Do not link to the remote repository and try to push any changes
                to the provided <url>.

        -vendor=<vndr>
                Set the block's vendor. <vendor> must be a valid vendor 
                available in the current workspace.

        -summary=<summary>
                Fill in the summary for the block's metadata. <summary> is a 
                string that describes the current block.


