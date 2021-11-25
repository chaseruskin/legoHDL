# Installation

There are very minimal requirements to get legoHDL up and running. Even though git is a requirement, developers do not need to fully understand git nor directly run git commands. 

## Requirements

- [python](https://www.python.org/downloads/) (version 3.5+)
- [git](https://git-scm.com/downloads)
- your favorite text-editor

Some recommended text-editors:
- [visual studio code](https://code.visualstudio.com/download) (ubuntu, macos, windows)
- [atom](https://atom.io) (ubuntu, macos, windows)
- [notepad++](https://notepad-plus-plus.org/downloads/) (windows)
- [emacs](https://www.gnu.org/software/emacs/) (ubuntu, macos, windows)

> __Note:__ If you have never ran `git` before, make sure to configure your name and email address before continuing. Check out git's documentation for [first time setup](https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup) (notably the section titled "Your Identity").

Verify an acceptable python version is installed (greater than or equal to 3.5).

`$ python --version`

Verify git is installed.

`$ git --version`

</br>

There are two places to install legoHDL from: GitHub or PYPI.

## Installing from GitHub

1. Clone the project from GitHub

```$ git clone https://github.com/c-rus/legoHDL.git```

2. Install the python program using PIP

`$ pip install ./legoHDL`

3. Delete the cloned project.

ubuntu | macos: `$ rm -r ./legoHDL`

windows: `$ rmdir /S ./legoHDL`

4. Verify legoHDL is installed.

`$ legohdl --version`
</br>

## Installing from PYPI
> __Note__: This method is currently unavailable.

1. Install the python program using PIP

`$ pip install legohdl`

2. Verify legoHDL is installed.

`$ legohdl --version`
