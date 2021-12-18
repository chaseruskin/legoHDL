# Why does legoHDL exist?

Design reuse is of importance in any development environment. For hardware designing in HDL, this is even more important as more complex designs follow a hierarchal approach. The benefits to resuing designs are identified as saving time and resources while increasing productivity.

From a [VLSI Technology paper](https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.610.9071&rep=rep1&type=pdf) about VHDL coding techniques, design reusability means that the design is:

- able to solve a general problem
- well coded, documented, and commented
- rigorously verified
- technology independent
- synthesis tool independent
- simulator independent
- application independent

## legoHDL is the solution to the design resusability challenge.

<br> 

legoHDL:

- enables developers to write code once and have it maintained in its single location; enforcing the DRY principle.

- decouples your HDL code from EDA tools, producing highly portable designs.

- provides quick access to previous designs for instant integration. legoHDL can return the required code to instantiate any of your designs in VHDL or Verilog.

- empowers developers through its management commands to effortlessly install HDL code for usability, reference specific versions of a design, and release new versions.

- sets up an environment to take advantage of natural language constructs, such as VHDL libraries and packages, that target resuability.

- places zero to little additional work on the developer to get existing code compatible with legoHDL

