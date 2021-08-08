## Roadmap to Release v0.1.0

- [ ] implement versioning (folders for each version created on-demand)
- [ ] auto-install dependencies if found in remote (occurs on export command)
- [ ] auto-install to cache when creating a workspace and blocks already exist in that local path (occurs in config/initialize workspace)

- [ ] change .lego.lock to Block.lock
- [ ] add additional safety measures to all Block.lock files and settings.yml to ensure all legal pieces are available

- [ ] improve list by adding an option to search (legohdl list util.m, legohdl list gfx)

- [ ] provide meaningful feedback if a desired version for release is invalid (what's the next possible version?)
- [ ] rewrite how config command deletes (maybe use del command with flags?)
- [ ] see if improvements can be made to "set settings" code (config command)


- [ ] implement additional "help" command documentation


- [ ] only do single git push and single git pull when working with a block

- [ ] '-all' option on graph/export to grab all project-level code


__Completed__
- [x] rename "cap" functions to "block"
- [x] investigate using "work." on one instance in a library when in a different block using that other block
- [x] test using in-line external package calls within another package in a project (within package body)
- [x] allow .all from pkgs with instantiations in entities
- [x] investigate if necessary to include the component files from declarations in a package even if it wasn't instantiated
- [x] prompt user if multiple top-level testbenches are found
- [o] investigate adding entity from pkg and pkg order getting swapped up
- [x] fix how export selects testbench unit when user choosing a top without a testbench (aid.helper block)
- [x] be sure to scan every inner-project component for its dependencies
- [x] allow codestream to support case sensitivity
- [x] use recursion within decipher function to fill out design book (also prevent overlap)
- [x] use recursion between block chain (dependency tree of blocks) to get all recursive label discoveries
- [x] verify both double/single quotes are okay for config command strings/values
- [x] add template reference option
- [x] search all design VHD files to determine which is top-level design then find which testbench instantiates that design
- [x] rename capsule.py to block.py
- [x] allow user to open template folder
- [x] allow user to open settings file
- [x] allow remote to be null