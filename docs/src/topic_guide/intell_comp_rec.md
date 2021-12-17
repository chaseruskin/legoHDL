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

_Scope-overlapping_ occurs between these two entities because they share the same identifier, which consists of their entity name and library name.

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

We define the _instance_ as the code that could lead to multiple entity solutions based off its identifier (`math.adder` in the problem stated). 

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

Data collected for contenders labeled as A and B:

instance | math.counter:adder (A) | math.ALU:counter (B)
---------|------------------------|-----------------
N (G)    | N (G*)                 | N (G*)
c_in     | c_in (IN)              | c_in (IN)
input1   | input1 (IN)            | a (IN)
input2   | input2 (IN)            | b (IN)
sum      | sum (OUT)              | sum (OUT)
c_out    | c_out (OUT)            | c_out (OUT)

> __Note:__ A '(G)' represents a generic defined, while '(IN)' and '(OUT)' represents input and output ports, respectively. Notice for the instance we are unable to determine the port directions from code. A '*' indicates it has a default value (and thus may be omitted from the instance code).

Since both A and B have the generic N, we cannot determine yet which one the instance belongs to. We move on to the ports.

contender A | contender B
------------|------------
1           | 1  

Both A and B have an input port "c_in", and the instance must define this connection for either contender because there's no default value. However, this port gives no insight as the name is identical in both contenders.

contender A | contender B
------------|------------
2           | 2 

Contender A has an input port "input1", which matches with a piece of the instance. A's score gets +1. Contender B has no such port, and thus it is ineligible. At this point ICR knows which entity the instance belongs to. We will carry the remaining checks out for completeness.

contender A | contender B
------------|------------
3           | 0  

Contender A has an input port "input2", which matches a piece of the instance and thus gets +1. Contender B no longer can check against the instance interface due to being previously ineligible/disqualified.
   
contender A | contender B
------------|------------
4           | 0  

Contender A's port "sum" matches with a port in the instance.

contender A | contender B
------------|------------
5           | 0  

Contender A's port "c_out" matches with a port in the instance.

contender A | contender B
------------|------------
6           | 0  

There are no more interface pieces in the instance to check. Scoring is done. Scores are transformed into a percentage.

_contender's %-score_ = (_contender's score_) / (_total instance interface elements_)

contender A | contender B
------------|------------
100%        | 0%


ICR selected contender A, which was the _math.counter:adder_ entity. This was what we wanted!

## Pitfalls

There are 2 methods to instantiating a unit in VHDL and Verilog: positional association and name association. Name association is generally recommended and is the format legoHDL outputs compatible code. However, positional association is still a synthesizable construct and based on the previous problem could hinder ICR.

When positional association is used, legoHDL loses data on what the interface names are to cross-check with the contenders. The only data it can collect is on the number of connections in the instance's interface. See [more examples](./intell_comp_rec.md#more-icr-examples) to see how ICR performs when encountering positional association.

I don’t think there is a single synthesis tool that will support a design using more than one unique entity from the same _scope-overlapping_ space, even though legoHDL can distinguish when each one is used in context from ICR. For this, a design may be limited to only using one of these unique entities for every _scope-overlapping_ problem, yet all the entities are allowed to coexist through legoHDL.

This means any time the same _scope-overlapping_ problem appears in a design, it must select the same entity every time in order to be synthesizable.

If a design would not select the same entity every time when running ICR, an extra layer of scope could be added to an entity’s name by prepending the block name to the entity name. For example, making `entity ALU_adder` and `entity counter_adder`. This would resolve the _scope-overlapping_ problem and avoid running ICR entirely.

## More ICR examples

### positional association


