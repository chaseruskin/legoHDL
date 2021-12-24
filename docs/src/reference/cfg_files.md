# .cfg Files

This page describes technical information about the structure and syntax of configuration files (.cfg files) under legoHDL.

legoHDL stores and retrieves data from files with a `.cfg` extension. This file structure has been pre-existing and loosely defined [here](https://en.wikipedia.org/wiki/INI_file) on wikipedia. Some differences/unique features will be highlighted on this page relating to how legoHDL interprets these file types.

## Syntax

- Keys and sections are case-insensitive. 
- leading and trailing whitespace is trimmed from keys and regular values (indentation is ignored).


## Structure

There are 4 components to legoHDL cfg files: 
- comments
- sections
- keys
- values

### Comments

Single-line comments are supported and must begin with a `;`.

```INI
; a comment!
```

### Sections

Sections are enclosed with `[` `]`. Sections must be defined on their own line. Sections can be nested up to 2 levels; begin a section with `[.` instead of `[` to signify this section is nested within the immediately previously declared section.

```INI
[workspace]
...

[.lab] ; flattens out to section "workspace.lab"
...
```

### Keys

Keys must be the first thing on a new line and followed by a `=`. Keys must be a single word wihout spaces. Keys are used to define values.

```INI
secret-key = 30
```

### Values

Values are WYSIWYG. All values are interpreted as strings. When not encapsulating a value in double quotes (`"` `"`), a newline in the value is converted into a single space during file reading. You can also you double quotes to make sure `;` or any other special cfg characters are kept in the value.

Values can also be lists under the following rules:
- use `(` to begin the list and `)` to end the list
- items are separated by `,`

```INI
; normal value
norm-key = What you see is what you get!
; this key will keep the ';'
save-key = "DO NOT TOUCH; THIS IS IMPORTANT"
; this key lists items
list-key = (item1, item2, item3)
```