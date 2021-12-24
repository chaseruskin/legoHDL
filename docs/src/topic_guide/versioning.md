# Versioning

This page explains how legoHDL handles different block versions.

Versions contain 3 distinct integer values under the [semantic versioning](./../glossary.md#semantic-versioning) scheme.

Here is a quick example:

`v1.0.3`

The first digit is the major version (`1`).

The second digit is the minor version (`0`).

The third digit is the patch version (`3`).

> __Tip:__ Throughout this page, a `*` will indicate an arbitrary integer value in a version.

legoHDL identifies a block's different versions by checking its git repository for all the commits tagged with `v*.*.*-legohdl`. This tag is automatically created during the `release` command.

There are two different types of versions: [partial versions](./../glossary.md#partial-version) and [full-versions](./../glossary.md#full-version). These two version types are created to help the user determine what degree of restriction is necessary for the dependent design.

Whenever a version is installed (except for when being installed as `latest`), all references to designs internal to that block are renamed with `_v*_*_*`.

## Full Versions

A user can install full versions. These are the exact versions spelled out to 3 integer values (`v1.0.3`). When a full version is ins


## Partial Versions

Partial versions are automatically handled and updated by legoHDL as a user installs/uninstalls full versions.


## Installation Example

Scenario: 

A block called `tutorials.gates` with version `v1.0.3` is to be installed so it can be used in creating new blocks. It has designs `and_gate` (VHDL entity), `nor_gate` (VHDL entity), and `gates` (VHDL package). No other installations exist for this block in this workspace.

Every reference to `and_gate`, `nor_gate` and `gates` for all HDL files within the `tutorials.gates` block will be renamed to `and_gate_v1_0_3`, `nor_gate_v1_0_3` and `gates_v1_0_3`, respectively.

Design transformations in the workspace's cache for `tutorials.gates(v1.0.3@v1.0.3)`:

- `and_gate` -> `and_gate_v1_0_3`
- `nor_gate` -> `nor_gate_v1_0_3`
- `gates` -> `gates_v1_0_3`

A partial version will be created under `v1`. To minimize the amount of space used, partials only keep their own HDL files and will reference all other supporting files in the block's full version.

A partial version `v1` will be installed.

Design transformations in the workspace's cache for `tutorials.gates(v1@v1.0.3)`:

- `and_gate` -> `and_gate_v1`
- `nor_gate` -> `nor_gate_v1`
- `gates` -> `gates_v1`

A partial version will also be created under `v1.0`.

A partial version `v1.0` will be installed.

Design transformations in the workspace's cache for `tutorials.gates(v1.0@v1.0.3)`:

- `and_gate` -> `and_gate_v1_0`
- `nor_gate` -> `nor_gate_v1_0`
- `gates` -> `gates_v1_0`

## Why Partials?

Partial versions exist to give a dependency _flexibility_. If a developer chooses to say use a partial `v1`, then they assume as this design improves while holding the major version constant (`1`), this block can use any changes/improvements that may occur over time.

## Latest Versions

You can also reference the `latest` version that's installed in the cache (and also giving a dependency maximum flexibility) by using no identifier modifier when instantiating a dependent design (no design name transformations occur in the `latest` version installation).