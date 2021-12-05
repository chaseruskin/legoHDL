# Commands

<!-- Alternate quote: “Now I am the ruler of all the ocean! The waves obey my every whim!” -Ursula, The Little Mermaid -->

In this chapter, reference is provided for how to interface with legoHDL. The commands are loosely divided into two main categories: development and management.

- [Development](./development.md)
- [Management](./management.md)

### _Tip_: How to Read Commands

The basic usage structure for every command is:

```legohdl <command> [item] [flags]```

Everything written after the call to `legohdl` is considered an argument. All commands and flags are evaluated as case-insensitive.

A flag must start with a `-`. Flags are used to control how the command functions.

`-comp`

Any time `< >` are used, the string within the `< >` is used as a hint as to what the value should be to replace the entire `< >`.

`<block>`

Any time `[ ]` are used, that argument is optional.

`[-open]`

Any time `( )` are used, the arguments grouped within only function together.

`(-url [-fork])`

Any time `|` is used, only one of the arguments in question can be chosen per call (this is an OR operator).

`-profile | -template`


Sometimes a flag can store a value, in that case a `=` follows the name of the flag along with the desired value.

`-comp=vhdl`

Quotes can be used to make sure a flag or value is correctly captured on the command-line.

`-comp="vhdl"`
