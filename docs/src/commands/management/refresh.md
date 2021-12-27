# refresh

## Name

        refresh - Synchronize local vendor repositories with their remotes

## Synopsis

        legohdl refresh [<vendor> | -all]
        legohdl refresh [<profile> | -all] -profile

## Description

        Checks for updates from vendor remote repositories and pulls them down
        to stay up-to-date.

        If no arguments are given, by default all vendors available to the
        current workspace will try to refresh. If -all is given, every possible
        vendor, even outside workspace availability, will sync with its remote 
        (if exists).

## Options

        <vendor>
                The name of the known vendor to synchronize.

        -all
                Synchronize all profiles or vendors across all workspaces.

        <profile>
                The name of the profile to syncrhonize.

        -profile
                Flag to indicate that a profile is trying to be refreshed.


