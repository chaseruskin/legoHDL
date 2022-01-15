# Workspaces

This page explains how legoHDL uses [workspaces](./../glossary.md#workspaces) to group and manage your [blocks](./../glossary.md#block).

Workspaces allow your blocks to be found and managed for a given context. A user can have multiple workspaces for different contexts, such as for work and for hobbyist designs.

A user configures a workspace by defining a path where all downloaded blocks should exist and which vendors to link to.

Workspaces are defined as subsections in the `[workspace]` section of the `legohdl.cfg` file. Here is an example defining two different workspaces.

```ini
[workspace]

    [.EEL4712c]
        path    = /Users/chase/develop/eel4712c/
        vendors = (uf-ece, vhd-vault)

    [.personal]
        path    = /Users/chase/develop/hdl/
        vendors = ()
```

- Workspace `EEL4712C` looks under `/Users/chase/develop/eel4712c/` for downloaded blocks, and links to vendors defined as `uf-ece` and `vhd-vault`.

- Workspace `personal` looks under `/Users/chase/develop/hdl/` for downloaded blocks, and links to no vendors.

## Levels on Levels

Workspaces manage blocks at 3 different levels: downloaded/in-development, installed, and available.

1. Downloaded blocks are found within the workspace's user-defined path, sometimes called _local path_.

2. Installed blocks are internally managed by the workspace within a hidden folder currently found at `~/.legohdl/workspaces/<workspace>/cache/`.

3. Available blocks depend on what vendors are linked to the workspace, and can be installed or downloaded.

## Active Workspace

Only 1 workspace can be active at a given time. This is defined in the `[general]` section of the `legohdl.cfg` file.

```ini
[general]
    active-workspace = EEL4712C
```

> __NOTE:__ The value for `active-workspace` must be a case-insensitive match with a workspace section defined under `[workspace]`.