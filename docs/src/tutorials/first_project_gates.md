# First Project: Gates

On this page, we will go through the entire process for creating, building, and releasing a [block](./../glossary.md#block).
1. [Creating](./first_project_gates.md#1-creating-the-block)
2. [Building](./first_project_gates.md#2-building-the-block)
3. [Releasing](./first_project_gates.md#3-releasing-the-block)

<br>

# 1. Creating the Block

Let's create our first block, under the name _gates_, which will be under the [library](./../glossary.md#library) _tutorials_. _Gates_ will be a project involving two logical gates: NOR and AND.
```
$ legohdl new tutorials.gates
```

Open the block using your configued text-editor.
```
$ legohdl open tutorials.gates
```

Your text-editor should have opened the block's root folder and a couple of files should be automatically added in the block. This is because a template was used, which we loaded during [initial setup](./../getting_started/2_initial_setup.md).

> __Note:__ The commands presented throughout the remainder of this page assume they are ran from the block's root folder.


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
--  Takes two bits and performs the NOR operation. Q = ~(A | B). 
--
--  Both A and B are a singular bit and must both be '0' for Q to be '1'.
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity nor_gate is
    port(
        a, b : in std_logic;
        q : out std_logic);
end entity;

architecture rtl of nor_gate is
begin
    --logic to drive 'Q' output using 'NOR' keyword
    q <= a nor b;
    
end architecture;
```

<br>

Awesome, nothing too fancy going on here. Now its time to reuse our [IP](./../glossary.md#intellectual-property-ip) in other designs. 


## Reusing designs: AND Gate

Reusing designs is at the core of what legoHDL is built to be. Not reinventing the wheel saves time and resources that can be spun into designing more innovation, faster. Our next task will be to create a logical AND gate using only NOR gates.

Let's review the schematic for creating an AND gate from purely NOR gates.

![and_from_nor](./../images/AND_from_NOR.svg.png)

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
--  Takes two bits and performs the AND operation. Q <- A & B. 
--
--  Both A and B are a singular bit and each must be '1' for Q to be '1'. Built
--  from 3 instances of logical NOR gates.
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity and_gate is
    port(
        a, b : in std_logic;
        q : out std_logic);
end entity;

architecture rtl of and_gate is

begin

    
end architecture;
```

HDL languages support the use of a structural modelling technique, which will be applied here to create 3 instances of the NOR gate. 

### Getting NOR gate

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
  Takes two bits and performs the NOR operation. Q = ~(A | B).

  Both A and B are a singular bit and must both be '0' for Q to be '1'.
------------------------------------------------------------------------------

--- CODE ---
signal w_a : std_logic;
signal w_b : std_logic;
signal w_q : std_logic;

uX : entity work.nor_gate port map(
    a => w_a,
    b => w_b,
    q => w_q);

```

The `--- ABOUT ---` section returns the initial comments from the design's source file to potentially help inform the user.

The `--- CODE ---` section produces instantly-compatible code to be directly copied and pasted into the necessary design (`and_gate.vhd` in our case).

After copying and pasting the compatible code and making minor adjustments, our `and_gate.vhd` should now be complete.

```VHDL
--------------------------------------------------------------------------------
-- Block: tutorials.gates
-- Entity: and_gate
-- Description:
--  Takes two bits and performs the AND operation. Q = A & B. 
--
--  Both A and B are a singular bit and each must be '1' for Q to be '1'. Built
--  from only NOR gates.
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity and_gate is
    port(
        a, b : in std_logic;
        q : out std_logic);
end entity;

architecture rtl of and_gate is

    signal w_a_not : std_logic;
    signal w_b_not : std_logic;
    signal w_q : std_logic;

begin
    --negate a
    u_A_NOT : entity work.nor_gate port map(
        a => a,
        b => a,
        q => w_a_not);

    --negate b
    u_B_NOT : entity work.nor_gate port map(
        a => b,
        b => b,
        q => w_b_not);
    
    --perform /a nor /b
    u_A_AND_B : entity work.nor_gate port map(
        a => w_a_not,
        b => w_b_not,
        q => w_q);

    --drive output
    q <= w_q;

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

> __Note:__ If at any point you want to stop the tutorial and continue later, you can always reopen your text editor and terminal at the block's root folder, or from anywhere run:
```legohdl open tutorials.gates```

<br>

# 2. Building the Block

The other half to hardware designing involves verification. We will create a testbench to verify the entity _and_gate_ behaves according to the following truth table.

| A  | B  |\|| Q  |
|----|----|--|----|
| 0  | 0  |  | 0  |
| 0  | 1  |  | 0  |
| 1  | 0  |  | 0  |
| 1  | 1  |  | 1  |

## Creating a file from the template

Different types of HDL files can follow similiar code layouts, such as when designing a 2-process FSM or a testbench. For these situations, its beneficial to create a boilerplate template file for when that code-style is needed.

We can see what files exist in our legoHDL template by using the `list` command.

```
$ legohdl list -template
INFO:   Files available within the selected template: C:/Users/chase/.legohdl/template/
Relative Path                                                Hidden  
------------------------------------------------------------ --------
/.gitignore                                                  -
/.hidden/tb/TEMPLATE.vhd                                     yes
/src/TEMPLATE.vhd                                            -
```

We have a testbench template file `/.hidden/tb/TEMPLATE.vhd` available for use within our template, however, it wasn't automatically copied into our project when we created it because it is hidden.

Reference this file for creating our testbench `and_gate_tb.vhd`.
```
$ legohdl new ./test/and_gate_tb.vhd -file="/.hidden/tb/TEMPLATE.vhd"
```

The contents of `and_gate_tb.vhd` should resemble the following:
```VHDL
--------------------------------------------------------------------------------
-- Block   : tutorials.gates
-- Author  : Chase Ruskin
-- Created : December 16, 2021
-- Entity  : and_gate_tb
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

entity and_gate_tb is
end entity;

architecture bench of and_gate_tb is
    --declare DUT component

    --declare constants/signals
    constant dly : time := 10 ns;

begin
    --instantiate DUT

    --verify design within process
    process begin


        report "SIMULATION COMPLETE";
        wait;
    end process;

end architecture;
```

## Getting a component declaration and instantiation

Now we need to instantiate our Design-Under-Test (DUT), which is _and_gate_, and run it through the previous truth table.

Use the `get` command to return both the component declaration and instantiation code for the _and_gate_ entity.

```
$ legohdl get and_gate -comp -inst
```
The console outputs the following:
```
--- ABOUT ---
------------------------------------------------------------------------------
 Block: tutorials.gates
 Entity: and_gate
 Description:
  Takes two bits and performs the AND operation. Q <- A & B.

  Both A and B are a singular bit and each must be '1' for Q to be '1'. Built
  from only NOR gates.
------------------------------------------------------------------------------

--- CODE ---
component and_gate
port(
    a : in  std_logic;
    b : in  std_logic;
    q : out std_logic);
end component;

signal w_a : std_logic;
signal w_b : std_logic;
signal w_q : std_logic;

uX : and_gate port map(
    a => w_a,
    b => w_b,
    q => w_q);

```
In `and_gate_tb.vhd`, perform the following:
1. Below the line `--declare DUT component`, copy and paste the component declaration. 
2. Below the line `--declare constants/signals`, copy and paste the I/O connection signals. 
3. Below the line `--instantiate DUT`, copy and paste the instantiation code.

Now within our process we write a few lines of code to assert the DUT functions properly.

The testbench _and_gate_tb_ is now complete.

```VHDL
--------------------------------------------------------------------------------
-- Block   : tutorials.gates
-- Author  : Chase Ruskin
-- Created : December 16, 2021
-- Entity  : and_gate_tb
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

entity and_gate_tb is
end entity;

architecture bench of and_gate_tb is
	--declare DUT component
	component and_gate
	port(
		a : in  std_logic;
		b : in  std_logic;
		q : out std_logic);
	end component;

	--declare constants/signals
	constant dly : time := 10 ns;
	signal w_a : std_logic;
	signal w_b : std_logic;
	signal w_q : std_logic;

begin
	--instantiate DUT
	DUT : and_gate port map(
		a => w_a,
		b => w_b,
		q => w_q);

	--verify design within process
	process begin
		--test 00
		w_a <= '0';
		w_b <= '0';
		wait for dly;
		assert w_q = '0' report "(0 & 0) /= 1" severity error;
		
		--test 01
		w_a <= '0';
		w_b <= '1';
		wait for dly;
		assert w_q = '0' report "(0 & 1) /= 1" severity error;

		--test 10 
		w_a <= '1';
		w_b <= '0';
		wait for dly;
		assert w_q = '0' report "(1 & 0) /= 1" severity error;

		--test 11
		w_a <= '1';
		w_b <= '1';
		wait for dly;
		assert w_q = '1' report "(1 & 1) /= 0" severity error;

		report "SIMULATION COMPLETE";
		wait;
	end process;

end architecture;
```

Our testbench uses an instance of the entity _and_gate_. Let's verify this with the `graph` command like last time.

```
$ legohdl graph
```

## Generating a blueprint

At this point in the design process, we want to verify that _and_gate_ is performing correctly before we begin using it. We introduce 2 new commands to handle this: `export` and `build`.

> __Note:__ For the purposes of this tutorial trying to be as dependency-free as possible so that everyone may follow it, we will utilize a _pseudo-plugin_ called __demo__. This is a legoHDL plugin that mainly just prints text to the console. We will use this to avoid assuming/forcing a backend EDA tool/simulator.

From the `graph` command, we can see legoHDL knows how our designs are connected, yet our plugin does not. We need a way to tell our plugin what files we need to build our current design. We will create a [blueprint](./../glossary.md#blueprint) for our plugin to understand what files are needed.

```
$ legohdl export
```
The last line from the console should say where the blueprint file is located:
```
INFO:   Blueprint found at: C:/Users/chase/develop/hdl/tutorials/gates/build/blueprint
```

## Building a design

Now that the blueprint is created, we can build our project with a plugin. Let's look at what plugins we have available.

```
$ legohdl list -plugin
Alias           Command     
--------------- ----------------------------------------------------------------
hello           echo "hello world!"
demo            python $LEGOHDL/plugins/demo.py
```
We currently have 2 plugins at our disposal: __hello__ and __demo__.
The __hello__ plugin will only output "hello world!" to our console; not helpful at all but demonstrates that plugins are at the most basic level a command.

```
$ legohdl build +hello
INFO:   echo "hello world!" 
hello world!
```

Build with the __demo__ plugin.
```
$ legohdl build +demo
```
The plugin's help text will display due to the plugin internally defining this functionality. legoHDL's role during `build` is to only pass off the command `python $LEGOHDL/plugins/demo.py` to the terminal to execute.

> __Note:__ All arguments after the plugin's alias will be also passed down from legoHDL to the terminal when it executes the plugin's command.

Build with the __demo__ plugin to perform a pseudo-simulation.
```
$ legohdl build +demo -sim
INFO:   python $LEGOHDL/plugins/demo.py -sim 
echo PSEUDO SIMULATOR 
PSEUDO SIMULATOR
Compiling files...
VHDL C:/Users/chase/develop/hdl/tutorials/gates/src/nor_gate.vhd
VHDL C:/Users/chase/develop/hdl/tutorials/gates/src/and_gate.vhd
VHDL C:/Users/chase/develop/hdl/tutorials/gates/test/and_gate_tb.vhd
Running simulation using testbench and_gate_tb...
Simulation complete.
```

<br>

# 3. Releasing the Block


## Creating a block-level VHDL package

Before we release the first version, let's create a package file that consists of all the component declarations available within this block. A package is an optional but helpful VHDL unit that will allow easier reference to these components later. legoHDL automates this package file creation.
```
$ legohdl export -pack="./src/gates.vhd"
```

We specified the VHDL package file to be created at `./src/gates.vhd`. Opening the file shows the following contents.

```VHDL
--------------------------------------------------------------------------------
-- Block: tutorials.gates
-- Created: December 16, 2021
-- Package: gates
-- Description:
--  Auto-generated package file by legoHDL. Components declared:
--      nor_gate    and_gate    
--------------------------------------------------------------------------------
 
library ieee;
use ieee.std_logic_1164.all;
 
package gates is
 
    component nor_gate
    port(
        a : in  std_logic;
        b : in  std_logic;
        q : out std_logic);
    end component;
 
    component and_gate
    port(
        a : in  std_logic;
        b : in  std_logic;
        q : out std_logic);
    end component;
 
end package;

```

## Setting the first version

We are done making changes and working with the HDL code within this block; it's time for release! We will call this version 1.0.0.
```
$ legohdl release v1.0.0
```

We can check the status of all of our workspace's blocks in the catalog using the `list` command.

```
$ legohdl list
Library          Block                Status   Version    Vendor          
---------------- -------------------- -------- ---------- ----------------
tutorials        gates                D I      1.0.0                             
```

Notice that the `release` command also installed the _gates_ block to the workspace cache, indicated by the `I` in status.
The `D` indicates the block is also downloaded/developing because it is found in our workspace's local development path.

# Page Review

Woo-hoo! We learned how to:
- create a new block and new files with `new`
- view blocks, plugins, and template files with `list`
- check how our design connects together with `graph`
- generate a blueprint file of the current design with `export`
- build with a plugin that will perform some desired action with `build`
- create a VHDL package file consisting of the block's components with `export -pack`
- release a completed block with a specified version with `release`

On the next page, we will see how legoHDL handles using HDL designs from external blocks by making a new block _comparator_ that will require the _gates_ block.
