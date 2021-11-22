# Blocks

## Hardware Designing

At the most fundamental level, an HDL developer describes a piece hardware based on given specifications and contraints on how it is to behave. These "pieces of hardware" are defined as _entities_ in VHDL and _modules_ in Verilog. For the sake of consistency, we will define a _unit_ to represent both an _entity_ or _module_.

    Graphic of gates stringed together to perform a logical function.

Hardware designs can be represented with "black boxes", meaning the internal behaviors of sub-units can become abstracted away as designs become more complex.

    Graphic of simple black box digital circuit design. A second graphic of a bigger box encapsulating the simpler circuit.

A complete hardware design can be called a project, where one or more units are coupled together to achieve some specific behavior. You have most likely already been creating hardware projects, and you have come here seeking a better solution to managing your projects.

<br/>

## A Whirlwind Tour through an Example Block- uf.math.adder

Consider the following directory.

    adder/
        Block.cfg
        src/
            adder.vhd
            full_adder.vhd 
        inputs.txt
        zybo-z10.xdc
        adder_tb.vhd

legoHDL defines a __block__ as an HDL project with a special __Block.cfg__ metadata file at the root of its directory.

        Block.cfg

 Each block most consist of a unique case-insensitive __identifier__. An identifier is composed of 3 parts: __vendor__, __library__, and __name__. This identifier is defined within the Block.cfg file.

```uf.math.adder```

A block consists of __source files__, which are the relevant HDL files that may describe some set of related units.

        src/
            adder.vhd
            full_adder.vhd
        adder_tb.vhd

A block can also consist of __supporting files__, which are files that accompany HDL files, such as a constraint file, a pin assignment file, or some test vector scripts.

        zybo-z10.xdc
        inputs.txt