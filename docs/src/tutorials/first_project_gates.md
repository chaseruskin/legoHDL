# First Project: Gates

legoHDL groups HDL code into [blocks](./../glossary.md#block). Blocks are essentially your projects, but identified by legoHDL due to a [Block.cfg](./../glossary.md#blockcfg) existing at the project's root folder.

<br>

Let's create our first block, under the name _gates_, which will be under the library _tutorials_. _Gates_ will be a project involving various logical gates such as NOR, AND, and XOR.

```
$ legohdl new tutorials.gates -open
```

Our text-editor should have now opened at the block's root folder and a couple of files should be automatically added to our block. This is because we used the template loaded in by the default profile during [initial setup](./../getting_started/2_initial_setup.md).


## Creating a new design: NOR Gate

Let's create our first HDL design, _nor_gate_.

```
$ legohdl new ./src/nor_gate.vhd -file
```

Here we specified we wanted to create a new file `nor_gate.vhd`. Your editor should automatically focus on this new file.

The following is the code for our first HDL design, _nor_gate_. Copy it into `nor_gate.vhd`.

```VHDL
--------------------------------------------------------------------------------
-- Block: tutorials.gates
-- Entity: nor_gate
-- Description:
--  Takes two bits and performs the NOR operation. C = ~(A | B). 
--
--  Both A and B are a singular bit and must both be '0' for C to be '1'.
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity nor_gate is
    port(
        a, b : in std_logic;
        c : out std_logic);
end entity;

architecture rtl of nor_gate is
begin
    --logic to drive 'C' output using 'NOR' keyword
    c <= a nor b;
    
end architecture;
```

<br>

Awesome, nothing too fancy going on here. Now its time to reuse our [IP](./../glossary.md#intellectual-property-ip) in other designs. 


## Reusing designs: AND Gate

Reusing designs is at the core of what legoHDL is built to be. Not reinventing the wheel saves time and resources that can be spun into designing more innovation, faster. Our next task will be to create a logical AND gate using only NOR gates.

![and_from_nor](./../images/and_from_nor.pdf)

The design requires 3 instances of a NOR gate.

<br>

Let's create another file `and_gate.vhd` using the `new` command like last time.

```
$ legohdl new ./src/and_gate.vhd -file
```

Copy the following code into `and_gate.vhd`; we will complete it shortly.

```VHDL
--------------------------------------------------------------------------------
-- Block: tutorials.gates
-- Entity: and_gate
-- Description:
--  Takes two bits and performs the AND operation. C <- A & B. 
--
--  Both A and B are a singular bit and each must be '1' for C to be '1'. Built
--  from 3 instances of logical NOR gates.
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity and_gate is
    port(
        a, b : in std_logic;
        c : out std_logic);
end entity;

architecture rtl of and_gate is

begin

    
end architecture;
```

HDL languages support the use of a structural modelling technique, which will be applied here to create 3 instances of the NOR gate. 

There is a specific syntax within HDL languages that must be followed to instantiate components within larger designs. Not only must a developer get the syntax correct, the developer must know all the I/O ports to list, which can get out of hand as designs become more complex.

We introduce the `get` command.

Let's generate the VHDL code required to create our NOR gates using our design written in `nor_gate.vhd`.

```
$ legohdl get nor_gate -inst
```

The console outputs the following:
```
--- ABOUT ---
------------------------------------------------------------------------------
 Block: tutorials.gates
 Entity: nor_gate
 Description:
  Takes two bits and performs the NOR operation. C = ~(A | B).

  Both A and B are a singular bit and must both be '0' for C to be '1'.
------------------------------------------------------------------------------

--- CODE ---
signal w_a : std_logic;
signal w_b : std_logic;
signal w_c : std_logic;

uX : entity work.nor_gate port map(
    a => w_a,
    b => w_b,
    c => w_c);

```

The `--- ABOUT ---` section returns the initial comments from the design's source file to potentially help inform the user.

The `--- CODE ---` section produces instantly-compatible code to be directly copied and pasted into the necessary design (`and_gate.vhd` in our case).

After copying and pasting the compatible code and making minor adjustments, our `and_gate.vhd` should now be complete.

```VHDL
--------------------------------------------------------------------------------
-- Block: tutorials.gates
-- Entity: and_gate
-- Description:
--  Takes two bits and performs the AND operation. C = A & B. 
--
--  Both A and B are a singular bit and each must be '1' for C to be '1'. Built
--  from only NOR gates.
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity and_gate is
    port(
        a, b : in std_logic;
        c : out std_logic);
end entity;

architecture rtl of and_gate is

    signal w_a_not : std_logic;
    signal w_b_not : std_logic;
    signal w_c : std_logic;

begin
    --negate a
    u_A_NOT : entity work.nor_gate port map(
        a => a,
        b => a,
        c => w_a_not);

    --negate b
    u_B_NOT : entity work.nor_gate port map(
        a => b,
        b => b,
        c => w_b_not);

    --perform /a nor /b
    u_A_AND_B : entity work.nor_gate port map(
        a => w_a_not,
        b => w_b_not,
        c => w_c);

    --drive output
    c <= w_c;

end architecture;
```

## Viewing a design

In our project, _and_gate_ depends on _nor_gate_. We can visualize this dependency by using the `graph` command.

```
$ legohdl graph
```

The console outputs the following:
```
INFO:   Identified top-level unit: and_gate
WARNING:        No testbench detected.
INFO:   Generating dependency tree...
--- DEPENDENCY TREE ---
\- tutorials.and_gate 
   \- tutorials.nor_gate 


--- BLOCK ORDER ---
[1]^-   tutorials.gates(@v0.0.0)

```

<br>

# Review

Nice work! We learned how to:
- create a new block 
- use legoHDL for basic interaction with your HDL code files
- see a hierarchical view of the current design

Next, we will create a testbench file from the template to test our _and_gate_ as well as export our design for use with plugins.