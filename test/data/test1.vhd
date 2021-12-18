-- File: test1.vhd
-- Author: Chase Ruskin
-- Description:
--  Includes VHDL code to test against legoHDL functions. This initial comment block
--  will also be tested to see if it is returned when getting an entity.
-- Note:
--  Code may be purposely written poorly to test the VHDL analysis in legoHDL.

library ieee;
use IEEE.std_logic_1164.all;
--rigorous code-writing
entity Test1 is port(a:in std_logic;B: out std_logic_vector(7 downto 0 ) ); end entity Test1;

architecture rtl of test1 is signal W_A : std_logic_vector; --begin

    begin
        
        W_A <= a;
        
        B <= W_A;
        
    end architecture;