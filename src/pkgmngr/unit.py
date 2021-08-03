from enum import Enum

class Unit:
    class Type(Enum):
        ENTITY = 1,
        PACKAGE = 2
        pass

    def __init__(self, filepath, dtype, lib):
        self._filepath = filepath
        self._dtype = dtype
        self._lib = lib
        pass
    pass