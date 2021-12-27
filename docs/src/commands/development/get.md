# get

## Name

        get - Print the compatible code for the ports list of a specified unit

## Synopsis

        legohdl get [<block>:]<unit> [-comp[=<lang>]] [-inst[=<lang>]] [-arch]
                [-edges] [-D | -I] [-no-about]

## Description

        When trying to access current block-level entities, the <block>
        can be omitted (a form of shortcutting). To reference a unit,
        <vendor>.<library>.<project>:<unit>.

        By default, it will print the 'about' section and the component 
        declaration for VHDL entities or the module interface for Verilog 
        modules. This is the comment header block found at the beginning of this
        unit's file (if exists). Helpful to read more information about an unit 
        and how it behaves (if a developer wrote one).

        If -comp is present when -inst is also present and the language 
        outputted is VHDL, the returned VHDL instantiation code will be a 
        component instantiation. If -comp is omitted in this scenario, 
        the returned VHDL instantiation code will be a direct entity 
        instantiation.

        The <lang> assignment from -inst has higher precedence of the <lang>
        assignemnt from -comp when both are present.

## Options

        <block>
                The block's title. If omitted, the <entity> is searched for only
                within the current block's scope.

        <unit>
                The design unit name. For VHDL this is a package or entity, and
                for Verilog this is a module.

        -comp[=<lang>]
                Print the component declaration. For Verilog language, the 
                module interface is printed instead of a component declaration.

                <lang> specifies what HDL language to use to print the formatted
                code. Accepted values are vlog and vhdl. Omitting <lang> prints 
                the code in the entity's original language.

        -inst[=<lang>]
                Print the direct entity instantiation (VHDL-93 feature) or 
                component instantiation. This includes relevant constants for 
                each generic, relevant signals for each port, and the 
                instantiation code. 

                <lang> specifies what HDL language to use to print the formatted
                code. Accepted values are vlog and vhdl. Omitting <lang> prints 
                the code in the unit's original language.

        -arch
                List the available architectures. If the unit is a Verilog
                module, only "rtl" will be listed.

        -edges
                Print the units are required by this unit and print the units 
                that integrate this unit into their design. Gets the edges from
                the hierarchical graph.

        -D
                Search the downloaded blocks to get this unit, regardless of
                the status of 'multi-develop'.

        -I
                Search the installed blocks to get this unit, regardless of 
                the status of 'multi-develop'.

        -no-about
                Do not print the 'about' section for the given design unit.


