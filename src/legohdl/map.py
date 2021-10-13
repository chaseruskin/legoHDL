# Project: legohdl
# Script: map.py
# Author: Chase Ruskin
# Description:
#   The Map class. A map object is a special modification of a python dictionary
#   where keys are converted to lower case. Inspired by: 
#   https://stackoverflow.com/questions/3387691/how-to-perfectly-override-a-dict

from collections.abc import MutableMapping

class Map(MutableMapping):

    def __init__(self, *args, **kwargs):
        self._inventory = dict()
        self.update(dict(*args, **kwargs))
        pass

    def __getitem__(self, k):
        return self._inventory[self._keytransform(k)]

    def __setitem__(self, k, v):
        self._inventory[self._keytransform(k)] = v

    def __delitem__(self, k):
        del self._inventory[self._keytransform(k)]

    def _keytransform(self, k):
        return k.lower()

    def __iter__(self):
        return iter(self._inventory)

    def __len__(self):
        return len(self._inventory)

    pass
