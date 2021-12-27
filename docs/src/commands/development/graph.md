# graph

## Name

        graph - Visualize the dependency tree for the design

## Synopsis

        legohdl graph [<entity>] [-tb=<tb> | -ignore-tb] [-expand] [-disp-full]

## Description

        Create and view the dependency tree for the current block design. This 
        command is provided as a guide to quickly help the designer see how the
        design unfolds.

        When no <entity> is given, the top-level will be auto-detected and the
        user will be prompted to select one if multiple exist. When -ignore-tb 
        and -tb=<tb> are absent, the testbench for the top-level entity will be 
        auto-detected, if one exists. The user will be prompted to select one if
        multiple exist.

        By default, the graph is in compression mode and will create reference points
        when a duplicate branch occurs. Raising -expand will explicitly display all
        branches without reference points.

## Options

        <entity>
                The design unit to request as top-level.

        -tb=<tb>
                The relevant testbench file to explicitly include in the 
                dependency tree. Has higher precedence of -ignore-tb.

        -ignore-tb
                Do not include any testbench unit in the dependency tree.

        -expand
                Decompress reference points into their duplicate branchs.

        -disp-full
                Display full block identifiers for each unit.


