# open

## Name

        open - Use a text-editor to open a variety of legoHDL-related things

## Synopsis

        legohdl open <block>
        legohdl open [<plugin-alias>] -plugin
        legohdl open <profile-name> -profile
        legohdl open (-template | -settings[=<mode>])
        legohdl open <vendor-name> -vendor

## Description

        :todo:

## Options

        <block>
                :ref:

        <plugin-alias>
            The alias for the saved custom plugin within legoHDL. It is a 
            user-defined key in settings under "plugins". If the alias's value 
            is a command that references a real existing file, that file will be
            opened.

        -plugin
            The flag to indicate a plugin is trying to be opened. If no 
            <plugin-alias> value is given with this flag, the built-in plugins 
            folder will be opened.

        <profile-name>
            The profile configuration name stored within legoHDL settings. When 
            valid, that profile directory will open.

        -profile
            The flag to indicate a profile is trying to be opened.

        -template
            The flag to indicate the template is trying to be opened. If the
            configured template value in settings is blank, the built-in 
            template folder will be opened.

        -settings[=<mode>]
            The flag to indicate the settings are trying to be opened.

            <mode> determines how to open the settings. Accepted values are gui 
            and file. When omitted, the default is to open the settings in gui 
            mode.


