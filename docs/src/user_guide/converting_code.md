# Converting Code

This page walks through the general procedure for transforming an already existing HDL project into a usable block
within legoHDL.

<br>

### Local projects

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

### Remote projects

1. Copy the remote repository URL (paste it where `<url>` is in the following command).

2. From the terminal run, create a new block and provide its [identifier](./../glossary.md#block-identifier), `<block>`. 

    - Add the `-fork` flag to detach the block from the remote repository url if you will not be able to push changes to it.

    - Add the `-open` flag to optionally open the block in your configured text-editor.

```
$ legohdl new <block> -remote="<url>"
```

<br>

# Off-The-Shelf Examples

This section lists random or popular HDL git repositories available on GitHub that are easily integrated into legoHDL.

## Basic RISC-V CPU
- Project: https://github.com/Domipheus/RPU.git
- Author: [Colin Riley](https://github.com/Domipheus)

One-line command:
```
$ legohdl new cpu.riscv -remote="https://github.com/Domipheus/RPU.git" -fork -open
```

From the project's root directory:
```
$ legohdl info -more
--- METADATA ---
[block]
name     = riscv
library  = cpu
version  = 0.0.0
remote   = 
vendor   = 
requires = ()

--- STATS ---
Location = /Users/chase/develop/eel4712c/cpu/riscv/
Size     = 465.19 KB
Level    = DNLD
Required by:
        N/A

VHDL units:
    tb_unit_decoder_RV32_01    alu_int32_div_tb           
    tb_unit_alu_RV32I_01       rpu_core_tb                
    register_set               constants                  
    core                       alu_RV32I                  
    mem_controller             control_unit               
    decoder_RV32               alu_int32_div              
    lint_unit                  csr_unit                   
    pc_unit                    
```

Viewing the entity design hierarchy:
```
$ legohdl graph
INFO:   Identified top-level unit: core
INFO:   Identified top-level testbench: rpu_core_tb
INFO:   Generating dependency tree...
--- DEPENDENCY TREE ---
\- cpu.rpu_core_tb 
   \- cpu.core 
      +- cpu.mem_controller 
      +- cpu.pc_unit 
      +- cpu.control_unit 
      +- cpu.decoder_RV32 
      +- cpu.alu_RV32I 
      |  \- cpu.alu_int32_div 
      +- cpu.register_set 
      +- cpu.csr_unit 
      \- cpu.lint_unit 


--- BLOCK ORDER ---
[1]^-   cpu.riscv(@v0.0.0)
```

Everything checks out; from here you can release this block as a new version using `release` and reuse any designs in a different project.


## Simple UART
- Project: https://github.com/jakubcabal/uart-for-fpga
- Author: [Jakub Cabal](https://github.com/jakubcabal)

One-line command:
```
$ legohdl new comms.uart -remote=https://github.com/jakubcabal/uart-for-fpga.git -fork -open
```

From the project's root directory:
```
$ legohdl info -more
--- METADATA ---
[block]
name     = uart
library  = comms
version  = 0.0.0
remote   = 
vendor   = 
requires = ()

--- STATS ---
Location = /Users/chase/develop/eel4712c/comms/uart/
Size     = 331.37 KB
Level    = DNLD
Required by:
        N/A

VHDL units:
    RST_SYNC                 UART_LOOPBACK_CYC1000    UART2WBM                 
    UART2WB_FPGA_CYC1000     UART                     UART_PARITY              
    UART_CLK_DIV             UART_TX                  UART_DEBOUNCER           
    UART_RX                  UART_TB                  
```

Viewing the entity hierarchy:
```
$ legohdl graph uart -tb=uart_tb
INFO:   Identified top-level testbench: UART_TB
INFO:   Generating dependency tree...
--- DEPENDENCY TREE ---
\- comms.UART_TB 
   \- comms.UART 
      +- comms.UART_CLK_DIV 
      +- comms.UART_DEBOUNCER 
      +- comms.UART_RX 
      |  +- comms.UART_CLK_DIV 
      |  \- comms.UART_PARITY 
      \- comms.UART_TX 
         +- comms.UART_CLK_DIV 
         \- comms.UART_PARITY 


--- BLOCK ORDER ---
[1]^-   comms.uart(@v0.0.0)
```

Everything checks out; from here you can release this block as a new version using `release` and reuse any designs in a different project. Before releasing, you could also run `legohdl export -pack` to create a VHDL package file for all non-testbench design components.
