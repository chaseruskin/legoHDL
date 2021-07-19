from collections import abc
from . import apparatus as apt


class Entity:

    def __init__(self):
        self._req_files = list() #list of required files by this entity
        self._name
        self._dependencies = list() #list of other entities that it needs
    pass


class Source(abc):

    entity_bank = list() #class var of a list of entities

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        pass

    @abstractmethod
    def decipher(self):
        pass

    pass



class Vhdl(Source):

    def decipher(self):
        print("test")
        return super().decipher()

    pass


class Verilog(Source):

    pass