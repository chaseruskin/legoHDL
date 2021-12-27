# export

## Name

        export - Generate a blueprint file or VHDL package file

## Synopsis

        legohdl export [<unit>] [-tb=<tb> | -ignore-tb] [-quiet] [-no-clean]
                [-all]
        legohdl export -pack[=<file>] [-omit=<units>] [-inc=<units>]

## Description

        -ignore-tb has higher precedence than when a <tb> is stated.

        For generating a VHDL package file, passing -inc will ignore -omit if it
        is passed to the command-line as well. -inc has higher precedence than 
        -omit.

        The default VHDL package file name is the block's project name appended
        with '_pkg', and its path will be located at the same directory of the
        Block.cfg file. Override its location and name by entering a <file>.
        Testbench units (design units with no port interfaces) are always
        omitted.

## Options

        <unit>
                The design unit to request as top-level. All relevant HDL files
                will stem from this unit's file.

        -tb=<tb>
                Explicitly request what top-level simulation file to include in
                the blueprint.

        -ignore-tb
                Do not include a testbench file in the blueprint.

        -quiet
                Do not print intermediate information while the blueprint file 
                is being created.

        -no-clean
                Do not delete the build/ directory when writing the blueprint.

        -all
                Add all block-level source files and their dependencies.

        -pack[=<file>]
                Create a VHDL package file with component declarations for the 
                current block. Optionally add a relative path and file name for
                <file>.

        -omit=<units>
                Specific list of units to exclude when generating the package 
                file. <units> is a list separated by ','.

        -inc=<units>
                When given, it will only allow these explicit units to be
                included in the VHDL package file. <units> is a list separated
                by ','.


