# .cfg Files

This page describes technical information about the structure and syntax of configuration files (.cfg files) under legoHDL.

legoHDL stores and retrieves data from files with a `.cfg` extension. This file structure has been pre-existing and loosely defined [here](https://en.wikipedia.org/wiki/INI_file) on wikipedia. Some differences/unique features will be highlighted on this page relating to how legoHDL interprets these file types.

## Syntax

- Keys and sections are case-insensitive. 
- leading and trailing whitespace is trimmed from keys and regular values (indentation is ignored).

## Grammar

- Sections must be on their own line (ignoring leading whitespace).
- A key declaration must be the beginning of a line (ignoring leading whitespace).

## Structure

There are 4 components to legoHDL cfg files: 
- comments
- sections
- keys
- values

## Comments

Single-line comments are supported and must begin with a `;`.

```INI
; a comment!
```

## Sections

Sections are enclosed with `[` `]`. Sections must be defined on their own line. Sections can be nested up to 2 levels; begin a section with `[.` instead of `[` to signify this section is nested within the immediately previously declared section.

```INI
[workspace]


[.lab] ; flattens out to section "workspace.lab"

```

## Keys

Keys must be the first thing on a new line and followed by a `=`. Keys must be a single word wihout spaces. Keys are used to define values.

```INI
public-key = 42942

secret-key = 30
```

## Values

Values are WYSIWYG. There are three types of value intpretations: _basic literals_, _string literals_, and _lists_.

### Basic literals

A basic literal evaluates as a string and is not encapsulated by any delimiters. Leading and trailing whitespace is trimmed. A new-line within a basic literal is converted into a space. This design implementation allows for neater formatting, increasing user readability.

```ini
basic-key = What you see is what you get!

summary = This is a long block of text. In order to keep readability a priority, 
          newlines will be treated as a space and the leading whitespace for
          each line will be ignored.
```

### String literals

A string literal evaluates as a string and allows for any character to be stored within the string except the delimiting character (`"`).

```ini
; a key that captures the ';' character
true-key = "Do not touch; this is important!"

; a key that captures the '=' character
question = "Does P = NP ?"
```

### Lists

A list evaulates each item as either a string literal or basic literal. The value must begin with a `(` character and end with a `)` character. Items are separated by a `,` character.

```ini
; this key lists items of basic literals
list-key = (item1, item2, item3)

; this stores a combination of string literals and basic literals
combo-key = (
    "0",
    200,
    "1",
    300
)
```