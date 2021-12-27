# list

## Name

        list - View a variety of legoHDL-related things

## Synopsis

        legohdl list [<search>] [[-unit [-all] [-ignore-tb]] | [-D] [-I] [-A]] [-alpha]
        legohdl list [-plugin | -label | -vendor | -workspace | -profile | 
                -template]

## Description

        Retrieves a requested data from the catalog.

        When passing a value for <search>, each subsection of a block's
        identifier can be omitted. With each additionally provided subsection,
        the values shift left to the next subsection. See EXAMPLES for more 
        information.

## Options

        <search>
                Optional field to narrow the given list by. 

        -unit
                Instead of listing blocks, list the units.

        -alpha
                Organize the list in alphabetical order.

        -I
                Filter only installed blocks or units.

        -D
                Filter only downloaded blocks or units.    

        -A
                Filter only available blocks or units from vendors.

        -all
                Display all units, regardless if they are usable or not
                according to what 'multi-develop' is set to.

        -plugin
                Return the list of plugins. Fields are alias and command.

        -label
                Return the list of labels. Fields are label, extensions,
                and global.

        -vendor
                Return the list of vendors. Fields are vendor, remote 
                repository, block count, and active.

        -workspace
                Return the list of workspaces. Fields are workspace, active, 
                path, and vendors.

        -profile
                Return the list of profiles. Fields are profile, last import, 
                legohdl.cfg, template/, and plugins/.

        -template
                Return the list of all availble files from the current template.
                These files can be referenced exactly as listed when 
                initializing a new file with the 'init' command.

## Examples

        legohdl list lab0
                Since a vendor is omitted and a library is omitted, all blocks 
                starting with "lab0" in their name are returned.

        legohdl list eel4712c.  
                Since a vendor is omitted and a name is omitted, all blocks 
                starting with "eel4712c" in their library are returned.

        legohdl list uf-ece..
                Since a library is omitted and a name is omitted, all blocks 
                starting with "uf-ece" in their vendor are returned.

        legohdl list ..:mux_2x1 -unit
                All V.L.N subsections are blank, so the entire catalog is 
                searched to see if an unit exists with the name "mux_2x1".


