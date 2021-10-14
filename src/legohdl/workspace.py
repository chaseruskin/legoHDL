# Project: legohdl
# Script: workspace.py
# Author: Chase Ruskin
# Description:
#   The Workspace class. A Workspace object has a path and a list of available
#   markets. This is what the user keeps their work's scope within for a given
#   "organization".

import os
from .map import Map

class Workspace:
    #store all workspaces in dictionary
    Jar = Map()

    def __init__(self, path, markets):

        pass