from enum import Enum

class Signal:

    class Mode(Enum):
        IN = 1,
        OUT = 2,
        INOUT = 3,
        GENERIC = 4
        pass

    def __init__(self, name, mode, s_type, default=None):
        self._name = name
        self._mode = mode
        self._type = s_type
        self._default = default

    def __repr__(self):
        return(f'''
{self._name} is {self._mode} of type {self._type} with value: {self._default}
\n''')
    pass