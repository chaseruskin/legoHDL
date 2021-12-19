# Using Blocks: Comparator

On this page, we begin to see more of the package management aspects of legoHDL as we create a second project called _comparator_. _Comparator_ will need to use external designs previously created in the block _gates_. Before we create our next block, let's learn how to edit the template.

## Editing the template

Open the template's folder.

```
$ legohdl open -template
```

All files in here we will copied when creating a new block, except for any files within folders beginning with `.`. A [Block.cfg](./../glossary.md#blockcfg) file will always be created by legoHDL for every block, so no need to include that here.

Edit the `./src/TEMPLATE.vhd` file with the following code.

```VHDL
--------------------------------------------------------------------------------
-- Block: %BLOCK%
-- Author: %AUTHOR%
-- Created: %DATE%
-- Entity: TEMPLATE
-- Description:
--
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

entity TEMPLATE is
	port(
	
	);
end entity;


architecture rtl of TEMPLATE is


begin


end architecture;
```

We use [placeholders](./../glossary.md#placeholder) to mark the spot for data be filled in when the file is created. These placeholders will change values based on factors external of the template, such as today's date for `%DATE%`, the block's identifier for `%BLOCK%`, or the file's name for `TEMPLATE`.

Save the file and exit the template.

Create a new block `comparator` under the library `tutorials` and open it.

```
$ legohdl new tutorials.comparator -open
```

Our comparator will require an XOR gate, so let's design an XOR gate next.

<br>

## Creating XOR gate

The first design for the _comparator_ block will be an XOR gate.

Let's review the schematic for an XOR gate from purely NOR gates.

![xor_from_nor](./../images/XOR_from_NOR.svg.png)

Notice how the upper 3 NOR gates are the equivalent to the AND gate we previously designed. Rather than using 5 instances of a NOR gate, we will save time by using 1 AND gate instance and 2 instances of the NOR gate.

Create a new file from our previously edited template file and call it `xor_gate.vhd`.

```
$ legohdl new ./src/xor_gate.vhd -file="/src/TEMPLATE.vhd"
```

Fill in a description of how the design will behave below `-- Description:`. Then, define the entity's interface like our previous designs.

```VHDL
entity xor_gate is
    port(
        a, b : in std_logic;
        q : out std_logic);
end entity;
```

Now we define the architecture according to the previous schematic.

Uh-oh, _and_gate_ and _nor_gate_ are not defined in this project!

That's okay, accessing these entities is the same as we've done.

```
$ legohdl get and_gate -inst
--- ABOUT ---
------------------------------------------------------------------------------
 Block: tutorials.gates
 Entity: and_gate
 Description:
  Takes two bits and performs the AND operation. Q <- A & B.

  Both A and B are a singular bit and each must be '1' for Q to be '1'. Built
  from 3 instances of logical NOR gates.
------------------------------------------------------------------------------

--- CODE ---
signal a : std_logic;
signal b : std_logic;
signal q : std_logic;

uX : entity tutorials.and_gate port map(
    a => a,
    b => b,
    q => q);
```

> __Note:__ Specifying the entity's entire scope will produce the same result. `legohdl get tutorials.gates:and_gate -inst`

Copy and paste the outputted code to instantiate an _and_gate_. Connect signals according to the schematic.

Get the _nor_gate_ instance code.

```
$ legohdl get nor_gate -inst
--- ABOUT ---
------------------------------------------------------------------------------
 Block: tutorials.gates
 Entity: nor_gate
 Description:
  Takes two bits and performs the NOR operation. Q = ~(A | B).

  Both A and B are a singular bit and must both be '0' for Q to be '1'.
------------------------------------------------------------------------------

--- CODE ---
signal a : std_logic;
signal b : std_logic;
signal q : std_logic;

uX : entity tutorials.nor_gate port map(
    a => a,
    b => b,
    q => q);
```

Copy and paste the _nor_gate_ code to create 2 instances connected together with the 1 _and_gate_ according to the schematic.

The final code should resemble the following.

```VHDL
--------------------------------------------------------------------------------
-- Block: tutorials.comparator
-- Author: Chase Ruskin
-- Created: December 18, 2021
-- Entity: xor_gate
-- Description:
--	Q = A ^ B.
--	
--	Takes two singular bits A and B, and performs the XOR operation to produce
--	Q.
--------------------------------------------------------------------------------

library ieee;
library tutorials;
use ieee.std_logic_1164.all;

entity xor_gate is
    port(
        a, b : in std_logic;
        q : out std_logic);
end entity;


architecture rtl of xor_gate is

	signal w_and_q : std_logic;
	signal w_nor_q : std_logic;

begin
	--send inputs A and B through AND-gate
	u_AND : entity tutorials.and_gate port map(
		a => a,
		b => b,
		q => w_and_q);
	
	--send inputs A and B through NOR-gate
	u_NOR : entity tutorials.nor_gate port map(
		a => a,
		b => b,
		q => w_nor_q);
	
	--send outputs from AND and NOR through a NOR-gate to produce XOR
	u_XOR : entity tutorials.nor_gate port map(
		a => w_and_q,
		b => w_nor_q,
		q => q);

end architecture;
```

> __Note:__ _nor_gate_ and _and_gate_ are external HDL files. They belong to the library _tutorials_. Since we instantiated them using VHDL's entity instantiation technique, we must declare their library at the top of the file with the line `library tutorials;`

Run the graph command, but now with each entity's entire scope being displayed using the `-disp-full` [flag](./../glossary.md#flag).

```
$ legohdl graph -disp-full
INFO:	Identified top-level unit: xor_gate
WARNING:	No testbench detected.
INFO:	Generating dependency tree...
--- DEPENDENCY TREE ---
\- tutorials.comparator:xor_gate 
   +- tutorials.gates:and_gate 
   |  \- tutorials.gates:nor_gate 
   \- tutorials.gates:nor_gate 


--- BLOCK ORDER ---
[2]^-	tutorials.comparator(@v0.0.0)
[1]^-	tutorials.gates(@v1.0.0)
```

Looks good! Notice how we know have a block order of requirements, and it shows what version of the block _gates_ is being referenced to create the current design.

## Creating a Comparator

Now open `./src/comparator.vhd` to create our final design, which will use 3 _nor_gates_, 2 _and_gates_, and 1 _xor_gate_.

First, write a description about our design and fill in the entity interface.

```VHDL
--------------------------------------------------------------------------------
-- Block: tutorials.comparator
-- Author: Chase Ruskin
-- Created: December 18, 2021
-- Entity: comparator
-- Description:
--	Compares two singular bits: A and B. Outputs 3 different results. 
--
--	'lt' = (A < B)
--	'eq' = (A == B)
--	'gt' = (A > B)
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

entity comparator is
	port(
		a, b : in std_logic;
		lt, eq, gt : out std_logic);
end entity;
```

Now imagine we have completely blanked on what entities we can use. How could we remember?

View what blocks are available.

```
$ legohdl list
Library          Block                Status   Version    Vendor
---------------- -------------------- -------- ---------- ----------------
tutorials        comparator           D
tutorials        gates                  I      1.0.0
```

Okay, we have a _gates_ block installed to use, but what entities were designed in there?

View information about the _gates_ block.

```
$ legohdl info tutorials.gates
--- METADATA ---    
[block]
name     = gates    
library  = tutorials
version  = 1.0.0    
remote   = 
vendor   = 
requires = ()   
```

Not very helpful right now, but we can see the metadata defined in its Block.cfg. Let's try to get more information with the `-more` flag.

```
$ legohdl info tutorials.gates -more
--- METADATA ---    
[block]
name     = gates    
library  = tutorials
version  = 1.0.0    
remote   =
vendor   =
requires = ()

--- STATS ---
Location = C:/Users/chase/.legohdl/workspaces/primary/cache/_/tutorials/gates/gates/
Size     = 31.98 KB
Level    = INSTL
Required by:
        N/A

VHDL units:
    and_gate       gates          nor_gate       and_gate_tb
```

And look! We can see what VHDL primary design units are defined in the block (as well as if there were any Verilog modules). 

Now that we know the units at our disposal, let's inspect them.

```
$ legohdl get gates
--- ABOUT ---
------------------------------------------------------------------------------
 Block: tutorials.gates
 Created: December 18, 2021
 Package: gates
 Description:
  Auto-generated package file by legoHDL. Components declared:
      and_gate    nor_gate
------------------------------------------------------------------------------

```

_gates_ is a VHDL package file. Let's use it to help instantiate our _nor_gate_ and _and_gate_.

Add the `library` and `use` clauses for _gates_ above `library ieee;`. 

```VHDL
library tutorials;
use tutorials.gates.all;
library ieee;
...
```

In the _comparator's_ architecture, we only need the component instantiations for _and_gate_ and _nor_gate_. We can access those by combining flags `-comp` and `-inst`.

Get the component instantiations for _nor_gate_ and _and_gate_, as well as the entity instantiation for _xor_gate_.

```
$ legohdl get and_gate -comp -inst
```
```
$ legohdl get nor_gate -comp -inst
```
```
$ legohdl get xor_gate -inst
```

Copy and paste their outputted code into `comparator.vhd`, and connect signals accordingly. The final comparator architecture resembles the following.

```VHDL
architecture rtl of comparator is

	signal w_not_a : std_logic;
	signal w_not_b : std_logic;
	signal w_not_eq : std_logic;

begin
	--invert incoming A bit
	u_NEG_A : nor_gate port map(
		a => a,
		b => a,
		q => w_not_a);
	
	--invert incoming B bit
	u_NEG_B : nor_gate port map(
		a => b,
		b => b,
		q => w_not_b);
	
	--output a < b when /a = '0' and b = '1'
	u_AND_LT : and_gate port map(
		a => w_not_a,
		b => b,
		q => lt);
	
	--output a > b when a = '1' and /b = '0'
	u_AND_GT : and_gate port map(
		a => a,
		b => w_not_b,
		q => gt);
		
	--inequality logic created by XOR
	u_NOT_EQ : entity work.xor_gate port map(
		a => a,
		b => b,
		q => w_not_eq);
	
	--invert the XOR output to get equality logic
	u_EQ : nor_gate port map(
		a => w_not_eq,
		b => w_not_eq,
		q => eq);

end architecture;
```

View the current design's hierarchy tree.
```
$ legohdl graph
INFO:	Identified top-level unit: comparator
WARNING:	No testbench detected.
INFO:	Generating dependency tree...
--- DEPENDENCY TREE ---
\- tutorials.comparator 
   +- tutorials.nor_gate 
   +- tutorials.and_gate [A]
   |  \- tutorials.nor_gate 
   \- tutorials.xor_gate 
      +- tutorials.and_gate [A]
      \- tutorials.nor_gate 


--- BLOCK ORDER ---
[2]^-	tutorials.comparator(@v0.0.0)
[1]^-	tutorials.gates(@v1.0.0)
```

Awesome! This is how we intended our design to look.

> __Note:__ Graphs are compressed by default; meaning duplicate branches use referecnce points. Use `-expand` to see the graph completely output duplicate branches.

Export a blueprint file so we can use a plugin to build our design.

```
$ legohdl export
```

## Defining Labels

Most commonly your HDL projects may require project-specific files outside of the HDL code such as constraints files, test vector files, tcl scripts, etc. 

Imagine our task now is to use our psuedo-plugin to implement this design for an FPGA.

Try to route (implement) our exported design.

```
$ legohdl build +demo -route
INFO:	python $LEGOHDL/plugins/demo.py -route 
Error: no routing file (.csv) was found for label @PIN-MAP.
```

> __Note:__ Remember, the plugin produced its own error; all build commands are simply a wrapper for the entered plugin's command.

Our plugin expects a custom [label](./../glossary.md#label) to collect data for the routing step.

FPGA implementations typically require a constraints file like in this example, which lists the pin assginments for our top-level design. 

For our projects, our constraints file will be `.csv` files. How can we get this file into our blueprint for our plugin to use?

Add a new local label called `PIN-MAP` that will search for any `.csv` files within the current block.

```
$ legohdl config -"label.local.PIN-MAP=*.csv"
CREATED: label.local.pin-map = *.csv
```

Create a file called `pins.csv`.
```
$ legohdl new ./pins.csv -file
```
Copy the following contents in `./pins.csv`.
```CSV
PA1,a
PA7,b
PC3,lt
PC2,gt
PC0,eq
```

Assume our FPGA has pins called `PA1`, `PA7`, `PC3`, `PC2`, and `PC0`, that we want to map to our design's ports `a`, `b`, `lt`, `gt`, and `eq`, respectively.

Export a new blueprint.
```
$ legohdl export
```
Inspecting the blueprint file, we can see legoHDL included a file as a `PIN-MAP` label.
```
@PIN-MAP C:/Users/chase/develop/hdl/tutorials/comparator/pins.csv
@VHDL-LIB tutorials C:/Users/chase/.legohdl/workspaces/primary/cache/_/tutorials/gates/gates/src/gates.vhd
@VHDL-LIB tutorials C:/Users/chase/.legohdl/workspaces/primary/cache/_/tutorials/gates/gates/src/nor_gate.vhd
@VHDL-LIB tutorials C:/Users/chase/.legohdl/workspaces/primary/cache/_/tutorials/gates/gates/src/and_gate.vhd
@VHDL-SRC C:/Users/chase/develop/hdl/tutorials/comparator/src/xor_gate.vhd
@VHDL-SRC C:/Users/chase/develop/hdl/tutorials/comparator/src/comparator.vhd
@VHDL-SRC-TOP comparator C:/Users/chase/develop/hdl/tutorials/comparator/src/comparator.vhd
```

Now rebuild with the __demo__ plugin and its `-route` option.

```
$ legohdl build +demo -route
INFO:	python $LEGOHDL/plugins/demo.py -route 
echo PSEUDO PIN MAPPER 
PSEUDO PIN MAPPER 
Routing pins for device A2CG1099-1...
PA1 --> a
PA7 --> b
PC3 --> lt
PC2 --> gt
PC0 --> eq
Pin assignments complete.
```

Great work! We've customized our [workflow](./../glossary.md#workflow) to go along with our plugin. 

> __Note:__ Remember, plugins are developed by _you_, meaning you can choose what labels to expect and what to do with the listed files in the blueprint!

# Page Review

Woo-hoo! On this page, we learned how to:
- edit the template and use placeholders for generic run-time values within files
- use entities from outside the current block
- find information such as units defined for a particular block with `info`
- create a label to search for particular supportive files during export and added into the blueprint