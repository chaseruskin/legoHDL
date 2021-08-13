## Roadmap to Release v0.1.0

- [ ] implement versioning (folders for each version created on-demand) (installing spec. versions)
- [ ] auto-install dependencies if found in remote (occurs on export command)

- [-] auto-install to cache when creating a workspace and blocks already exist in that local path (occurs in config/initialize workspace) (does it work when doing it on just a regular block?) (say install block from market and gets requirements installs automatically?)

- [!] implement update command (have -all flag to update all installs, otherwise update by block name?) (could occur on refresh command?)

- [ ] ensure init command is up to par
- [ ] test init adding a remote already to git repo and then doing legohdl command
- [ ] remotes that are not empty (already have branches) can not be initialized using legohdl command
- [ ] test init on blank git url

- [!] change .lego.lock to Block.lock

- [ ] ensure download will download the entire remote ("clone") (unless no remote is configured and block is in cache)

- [ ] test installing a block, then auto-installs requirements to cache if DNE in cache and if the requirement is found in local path or in market

- [ ] implement additional "help" command documentation


### Future Roadmap

- [ ] add verilog/systemverilog file support (parse verilog for module dependencies/instances)

- [ ] test creating a new block from an existing git repository (clone, then run stuff to configure Block.lock)
- [ ] add additional safety measures to all Block.lock files and settings.yml to ensure all pieces are available
- [ ] add -instl, -dnld, -mrkt as flags for list command (not mutually exclusive flags)
- [ ] add ability to search by market

- [ ] have some way of notifying user that a block is missing from installations when trying to export

- [ ] '-all' option on graph/export to grab all project-level code

- [ ] add cool logging
- [ ] see if improvements can be made to "set settings" code (config command)


__Completed__
- [x] test making market from local to remote
- [x] dynamically manage workspaces if created/deleted within settings.yml
- [x] dynamically manage markets if deleted/added within settings.yml
- [x] issue warning if market is removed from registries but a block still is tied to that market?
- [x] multi-block setting: allow for designs to prioritize blocks found locally over released blocks in cache (if version number is not appended to the entity name)
    the trade off: 
        -some designs may only work with unreleased versions if that intertwined block is not released again
        -allow working on blocks together to make sure they work seamlessly
- [x] dynamically determine scripts and update settings if one has been deleted from outside legohdl
- [x] remove extra arrows on compile order prints
- [x] wrap "summ" command into init for specifying block summary -> -summary flag for init command
- [x] if a block belongs to a remote market, perform a -soft release to checkout a new branch and push that to remote
- [x] add -soft release option
- [x] verify that the workspaces folder gets deleted when deleting workspace
- [x] test using templated repo (don't copy over .git)
- [x] test using templated repo (don't copy over .git)
- [-] see if improvements can be made to "set settings" code (config command)
- [x] rewrite how config command deletes (maybe use del command with flags?) -> uses "del" command w/ flags
- [x] provide meaningful feedback if a desired version for release is invalid (what's the next possible version?)
- [x] improve list by adding an option to search (legohdl list util.m, legohdl list gfx, legohdl list .j)
- [x] rename "cap" functions to "block"
- [o] only do single git push and single git pull when working with a block -> this no longer occurs unless its a release or a new project being made with a remote
- [x] investigate using "work." on one instance in a library when in a different block using that other block
- [x] test using in-line external package calls within another package in a project (within package body)
- [x] allow .all from pkgs with instantiations in entities
- [x] investigate if necessary to include the component files from declarations in a package even if it wasn't instantiated
- [x] don't set * to src dir of top level, individually add every current level vhd file from glob.glob
- [x] be sure to scan every inner-project component for its dependencies
- [x] any package file made will be visible by outer-pkg alongside auto-generated pkg
- [x] prompt user if multiple top-level testbenches are found
- [o] investigate adding entity from pkg and pkg order getting swapped up
- [x] fix how export selects testbench unit when user choosing a top without a testbench (aid.helper block)
- [x] be sure to scan every inner-project component for its dependencies
- [x] allow codestream to support case sensitivity
- [x] use recursion within decipher function to fill out design book (also prevent overlap)
- [x] use recursion between block chain (dependency tree of blocks) to get all recursive label discoveries
- [x] verify both double/single quotes are okay for config command strings/values
- [o] ability to set mulitple remotes to 1 local path -> no
- [x] add template reference option
- [x] search all design VHD files to determine which is top-level design then find which testbench instantiates that design
- [x] prompt user if multiple top-level testbenches are found
- [x] rename capsule.py to block.py
- [x] allow user to open template folder
- [x] allow user to open settings file
- [x] allow remote to be null
- [x] update dependencies upon release
- [x] test using in-line external package calls within another package in a project (within package body)
- [x] scans for in-line package use (only within entities/architectures)
- [x] add extra folder layer to house cache,lib,map.toml,registry for a given workspace
- [x] implement -strict option to "release" command
- [x] revisit using makefile as script
- [x] auto-update if scripts DNE -> Yes
- [x] give option to update and commit all changes with next "release" -ac (already was!)
- [x] fix "-alpha" option for list command to correctly display modules' status
- [x] implement uninstall command       
- [x] user is able to open and edite the build scripts through legohdl
- [x] need ability to set custom parameters from command line, like make (args can be passed to build file)
- [x] try moving source files around and then releasing  
- [x] fix when releasing a module to update cache and lib
- [x] implement recursive nature on install for other dependencies
- [x] implement cache folder
- [x] set up remote using registry design and git repo (ex: winget)
- [o] organize recur labels to print with associated project -> No, not necessary
- [x] add way to add a recursive label (useful for labelling IP files that are needed inside dependencies)
- [x] users specify external ext. and what the tag is to search for adding to recipe	("tags" option)	
		ex: you can set:
			@XILINX_CONSTR -> .XDC
			@QUARTUS_ROUTE -> .qpr
			@PYTHON 	   -> .py
			-when these are set (at user level), the export command will build the recipe and include these
			first
- [x] when setting a build script, you specify how to call it (python3, sh, make) and the file
- [x] entering blank path to build script in config will delete it or unlink it
- [x] ability to set a build script file, (can be any file (TCL, make, py)) to house in 1 place
- [x] master build script will try to run by default when running build option and no file specified
- [x] organize workspaces
- [x] ability to set multiple local path places
		-> achieved with 'workspaces'
- [x] print neater lists
- [x] map.toml files are used and placed as ~/.vhdl_ls.toml
- [x] allow for opening settings to directly write into them
- [x] regroup settings labels into labels/recursive, labels/shallow
- [x] remove "template_pkg" and convert lines of vhdl embedded directly into legohdl code to write to file
- [x] start transition to running/developing legohdl as its PYPI package (use pip install -e .)
			-this means on install, template folder is created, settings.yml exists,
			-folders are set up on fresh install