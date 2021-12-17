# Referencing Blocks: Comparator

On this page, we begin to see more of the package management aspects of legoHDL as we create a second project called _comparator_. _Comparator_ will need to use external designs previously created in the block _gates_. Before we create our next block, let's learn how to edit the template.

## Editing the template



<br>

## Creating XOR gate

Our final design for the _gates_ block will be an XOR gate.

Let's review the schematic for an XOR gate from purely NOR gates.

![xor_from_nor](./../images/XOR_from_NOR.svg.png)

Notice how the upper 3 NOR gates are the equivalent to the AND gate we previously designed. Rather than using 5 instances of a NOR gate, we will save time by using 1 AND gate instance and 2 instances of the NOR gate.

Create a new file from our template called `xor_gate.vhd`.

```
$ legohdl new ./src/xor_gate.vhd -file=/src/TEMPLATE.vhd
```