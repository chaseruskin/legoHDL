# Intelligent Component Recognition (ICR)

Both VHDL and Verilog have very limited levels of scopes: although VHDL has libraries for design units, Verilog has no such concept.

This page describes how legoHDL handles _scope-overlapping_.

### What is _scope-overlapping?_

For this document, we define _scope-overlapping_ to be when two unique design units share the same scope and identifier.

## The Problem 

Take two design units available for use in your legoHDL workspace.

- math.ALU:adder
    - an entity named _adder_ found in the block _ALU_ under the library _math_
```VHDL
-- Block: math.ALU
-- Entity: adder
entity adder is 
    generic ( 
        N : positive := 8 
    );
    port (
        c_in  : in  std_logic; 
        a     : in  std_logic_vector(N-1 downto 0);
        b     : in  std_logic_vector(N-1 downto 0);
        sum   : out std_logic_vector(N-1 downto 0);
        c_out : out std_logic
    );
end entity;
```
- math.counter:adder
    - an entity named _adder_ found in the block _counter_ under the library _math_
```VHDL
-- Block: math.counter
-- Entity: adder
entity adder is
    generic ( 
        N : positive := 32
    );
    port (
         c_in   : in  std_logic;
         input1 : in  std_logic_vector(N-1 downto 0);
         input2 : in  std_logic_vector(N-1 downto 0);
         sum    : out std_logic_vector(N-1 downto 0);
         c_out  : out std_logic
    );
end entity;
```

_Scope-overlapping_ occurs between these two entities because they share the same entity name and library name.

If taking a VHDL coding approach, both entities could be instantiated with the following code.

```VHDL
u_ADD : entity math.adder 
    generic map ( 
        ... 
    ) port map ( 
        ... 
    )
```
The problem lies in that `math.adder` may refer to either entity.

As the developer, your latest project involves using the adder from the _counter_ block, yet how would legoHDL know this when the identifiers to instantiate the unit is the same?

## The Solution: ICR

ICR is a scoring algorithm ran when _scope-overlapping_ occurs in the design. 

ICR selects the unit with the highest computed score among its contenders. 

We define a _contender_ to be those unique entities that share the same space in scope-overlapping. In the problem statement above, there are 2 contenders: the _adder_ from _ALU_ and the _adder_ from _counter_.

We define an _interface_ as the collective combination of an entity's defined generics and ports.

We define the _instance_ as the code that could lead to multiple entity solutions based off its identifier (`math.adder` in our problem). 

ICR gathers the interface data from all contenders as well as the interface data defined in the mapping of the instance. Based on this data and a set of known rules, it begins to calculate scores and rule out ineligible contenders.

Some rules are the following:
- +1 point is awarded to a contender for having a matching interface piece with the instance
- An output port can be omitted/left unconnected and a contender can still remain elgibile.
- If a contender's interface does not define a default value for a generic or an input port, the instance must have that generic or input port mapped. Failure to have this mapping will cause the contender to be ineligible.
- If any generic or port from the instance is not found in the contender's interface, the contender must be ruled inelgibile.

## Solving the example problem

Using the `legohdl get` command, you as the developer would instantiate the _adder_ from _counter_ with the following output.

```
$ legohdl get math.counter:adder -inst
--- ABOUT ---
------------------------------------------------------------------------------
 Block: math.counter
 Entity: adder
 Description:
  Instantiates N full adders to create a N-bit ripple carry adder
  architecture.
------------------------------------------------------------------------------

--- CODE ---
constant N : positive := 8;

signal w_cin    : std_logic;
signal w_input1 : std_logic_vector(N-1 downto 0);
signal w_input1 : std_logic_vector(N-1 downto 0);
signal w_sum    : std_logic_vector(N-1 downto 0);
signal w_cout   : std_logic;

uX : entity math.adder generic map(
        N => N)
    port map(
        c_in   => w_c_in,
        input1 => w_input1,
        input2 => w_input2,
        sum    => w_sum,
        c_out  => w_cout);
```

Within your latest entity's architecture, you have instantiated the `math.adder` entity.

```VHDL
architecture ...
begin
    ...

    --please use the adder from our counter block here!
    u_ADD : entity math.adder generic map(
            N => N)
        port map(
            c_in   => w_c_in,
            input1 => w_input1,
            input2 => w_input2,
            sum    => w_sum,
            c_out  => w_cout);

    ...
end architecture;
```

To build the latest design, we must export the blueprint file for our plugin to use.

During export, ICR is ran to determine which contender the given instance should belong to in order to complete the design hierarchy tree.