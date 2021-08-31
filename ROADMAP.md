## Roadmap to Release v1.0.0

- [ ] add run command to peform both 'export' and then 'build'

- [ ] make market names case insensitive (duplicate names will clash on folder namespace within registry/)

- [ ] move unique tag id to end like 'v1.0.0-legohdl' (currently is 'legohdl-v1.0.0')

- [ ] vhdl component declarations avoid library usage calls ? -> investigate

- [ ] implement additional "help" command documentation

- [?] recursive labels in cached versions...track what labels have already been added and overwrite them with the highest version used if applicable -> is this desired? (avoids duplicate files)

- [-] add verilog/systemverilog file support (parse verilog for module dependencies/instances) -> mostly there

- [ ] implement code for 'port' command to provide prints for verilog instantiations + cross-over for vhdl to verilog and verilog to vhdl using '-vhdl' flag or '-verilog' flag

### Future Roadmap

- [x] test creating a new block from an existing git repository (clone, then run stuff to configure Block.lock)

- [-] add additional safety measures to all Block.lock files and settings.yml to ensure all pieces are available

- [ ] add ability to see what market a block belongs too on list command

- [ ] add ability to search by market

- [ ] allow option to print a .log file on export so a record of graph can be kept?

- [ ] graph command but -upstream option (returns all blocks that are effected/use this block)

- [ ] produce log.warning when trying to make 'new' with a remote repo that isn't empty (doesnt link remote)

- [-] have some way of notifying user that a block is missing from installations when trying to export -> is somewhat implemented as a warning in some cases if it has the library available but can't find the unit name

- [ ] better commands/parsing? examples: --flag=value --market=open-market --git=url.git --open --soft 	--label="PINS=*.pins" --recursive
- [ ] use argparse package to create better CLI?

- [ ] 'update' command idea; (have -all flag to update all installs, otherwise update by block name?)

- [ ] '-all' option on graph/export to grab all project-level code

- [ ] add cool logging

- [-] see if improvements can be made to "set settings" code (config command) -> users can now directly interact with the settings.yml

__Completed__
- [x] add -install (implemented), -download (implemented) to list command
- [x] allow ability to open a script by specifying script 'alias' name `legohdl open master -script`
- [x] assess tradeoff: delete any git version tags that aren't valid but were identified? -> only really concerned with using existing repos -> the unique ID handles if existing repos already have version tags
- [x] add series of prompts to release command before actually doing anything
- [x] have a way to see what version was used when using a block's 'latest' (no version specified) -> (show a directory?) -> (OR transform the base installation -> leaning yes) or block's major ver (_v1, _v2, etc.) -> useful to know in case an update ends up breaking the code, allows dev to know what the last working version was
- [x] bypass -soft option if the market does not have a remote (there is no point to make a branch)
- [x] adds hidden folder "version" 
- [x] safety measure on 'version' meta by dynamically setting it every time legohdl is called by looking at highest valid git tag -> prevents user from overwriting it and messing it up -> solution is to store that `version.log` file no matter if a market is tied to the block.
- [x] auto upload (on release) a changelog file to market as well if found in the block? -> leaning yes. will look for CHANGELOG.md, if a changelog exists then open code-editor to write new addition updates? -> yes -> will upload and display changelog if found at root of block directory and use flag '-changelog' with show command
- [x] uninstall a whole entire major version from cache
- [x] add prompt to uninstall command, will notify user of all uninstallations and then ask to proceed
- [x] uninstalling a leading version will then try to replace the parent version with a new leading version if already available in the cache
- [x] implement behavior to change module name's when installing a specific version for verilog files
- [x] update default labels to include verilog
- [x] allow user to add a comment to release -> goes to git commit and also goes to version.log file
example: `legohdl release "Fixes clock sync bug" -fix`
- [x] when installing or downloading a block, auto-install dependencies if found in remote or block is in cache (and required version is not created)
- [x] test auto-install of dependencies (if a dependency has (v1.0.0), then break it off in install command and pass in the version as arg and use block name thats left from break)
- [x] solve cache recursive label issue take off version cast of name and then write off labels found at this version, 
- [x] install a level for majors (gets rewritten when a new install comes that fulfills this level)
	ex: /v0
		/v1
		/v2
	-> allows user to just use halfadder_v1 without long specific version (form of dependency resolution)
		u0 : entity common.halfadder_v1
		uX : entity common.halfadder_v1_1_0
	-> referencing an entity without version will refer to 'latest', (the actual full branch kept in install)
- [x] auto install "major" vers (v0, v1, etc..) when an install occurs within its respective bin and check the meta 'version' to see if it needs to be overridden by new larger version
- [o] when running export/graph command, auto-install dependencies if DNE and found in remote or block is in cache (and required version is not created) -> not implemented, think python/pip, user must install the package before using it! (can't just magically install right on run-time)
- [x] create a version.log file and keep markets to only one folder per block (not span over folders for every release) -> don't need folder for every release because legohdl uses git-tags to grab release-points
- [x] rewrite labels to must include * to fully say its glob style
- [x] when installing a version, go through all vhdl code and append the version to the entity name's for that block
- [o] perform git pull on release command before releasing? -> leaning no -> don't think its needed
- [x] implement update/upgrade command
- [x] implement refresh command -> specify market or specify none to refresh all markets tied to workspace
- [x] investigate whether to use `git checkout tag` then moving files OR continue using `git clone --single-branch` of tag for installation -> would allow for checking if valid legohdl release point and save space in the long run of having many installations -> moves files option
- [x] implement versioning (folders for each version created on-demand) (installing spec. versions)
- [x] legohdl will now try to release all versions with valid tag if a Block.lock file exists there to a market, only tries once as a folder will be created for that tag # but may not have a Block.lock for it if invalid
- [o] test installing a block, then auto-installs requirements to cache if DNE in cache and if the requirement is found in local path or in market -> already covered by a roadmap mission
- [o] auto-install to cache when creating a workspace and blocks already exist in that local path (occurs in config/initialize workspace) (does it work when doing it on just a regular block?) (say install block from market and gets requirements installs automatically?)
- [x] investigate rmdir errors on windows when releasing -> added error catch function for windows permission issues
- [x] allow renaming of block and/or library name? -> yes
- [x] allow users to touch Block.lock file? (it gets auto-updated anyway when performing things like release) -> 	   leaning yes
- [x] let the % % be used on all files in the template, even READMEs
- [x] change .lego.lock to Block.lock
- [x] ensure init command is up to par
- [x] test having a remote project already (non-block), then running init
- [x] test init adding a remote already to git repo and then doing legohdl command
- [x] remotes that are not empty can be initialized using "legohdl init library.block -url.git"
- [x] test init on blank git url
- [x] must remove a git remote url from a block by doing "git remote remove 'name'"
- [x] ensure download will download the entire remote ("clone") (unless no remote is configured and block is in cache)
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
- [x] rename `capsule.py` to `block.py`
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