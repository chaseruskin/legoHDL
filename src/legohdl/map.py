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

    
    def _keytransform(self, k):
        '''
        Converts key to lower-case if it is type string.
        '''
        if(isinstance(k, str)):
            k = k.lower()
        return k


    def __getitem__(self, k):
        return self._inventory[self._keytransform(k)]


    def __setitem__(self, k, v):
        self._inventory[self._keytransform(k)] = v


    def __delitem__(self, k):
        del self._inventory[self._keytransform(k)]


    def __iter__(self):
        return iter(self._inventory)


    def __len__(self):
        return len(self._inventory)


    def __instancecheck__(self, instance):
        return instance == dict or instance == Map


    def __str__(self):
        return self._inventory.__str__()


    def __repr__(self):
        return self._inventory.__repr__()


    def keys(self):
        return self._inventory.keys()


    def items(self):
        return self._inventory.items()


    def values(self):
        return self._inventory.values()

    pass