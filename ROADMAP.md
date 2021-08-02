## Roadmap to Release v0.1.0

- [ ] implement versioning (folders for each version created on-demand)
- [ ] auto-install dependencies if found in remote
- [ ] auto-install to cache when creating a workspace and blocks already exist in that path

- [ ] test using in-line external package calls within another package in a project (within package body)
- [ ] be sure to scan every inner-project component for its dependencies

- [ ] add additional safety measures to all Lego.lock files and settings.yml to ensure all legal pieces are available

- [ ] rewrite how config command deletes
- [ ] see if improvements can be made to "set settings" code (config command)

- [ ] prompt user if multiple top-level testbenches are found
- [ ] implement additional "help" command documentation



__Completed__
- [x] verify both double/single quotes are okay for config command strings/values
- [x] add template reference option
- [x] search all design VHD files to determine which is top-level design then find which testbench instantiates that design
- [x] rename capsule.py to block.py
- [x] allow user to open template folder
- [x] allow user to open settings file
- [x] allow remote to be null