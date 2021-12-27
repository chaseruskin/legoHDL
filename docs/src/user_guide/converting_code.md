# Converting Code

This page walks through the general procedure for transforming an already existing HDL project into a usable block
within legoHDL.

<br>

### A local project

1. Determine the local path of your current workspace.
```
$ legohdl list -workspace
```
2. Move the HDL project's root folder within the current workspace's local path.

3. Open a terminal at the HDL project's root folder.

4. Initialize a block and provide its [identifier](./../glossary.md#block-identifier), `<block>`.
```
$ legohdl init <block>
```

<br>

### A remote project

1. Copy the remote repository URL (paste it where `<url>` is in the following command).

2. From the terminal run, create a new block and provide its [identifier](./../glossary.md#block-identifier), `<block>`. 

    - Add the `-fork` flag to detach the block from the remote repository url if you will not be able to push changes to it.

    - Add the `-open` flag to optionally open the block in your configured text-editor.

```
$ legohdl new <block> -remote="<url>"
```

<br>

## Off-The-Shelf Examples

This section lists random or popular HDL git repositories available on GitHub that are easily integrated into legoHDL.