from .language import Language
import logging as log

class Verilog(Language):

    def decipher(self, design_book, cur_lib, verbose):
        if(verbose):
            log.info("Deciphering VERILOG file...")
            log.info(self._file_path)
        #keep case sensitivity
        c_stream = self.generateCodeStream(True,True,*self._std_parsers,"#")
        print(c_stream)
        #store a list of all available module names
        all_available_modules = []
        for g in design_book.values():
            for u in g.values():
                all_available_modules.append(u)

        module_name = None
        in_ports = in_params = in_module = False
        parenth_count = 0
        for i in range(len(c_stream)):
            if(c_stream[i] == "module"):
                module_name = c_stream[i+1]
                #print(module_name)
                in_ports = True
            elif(c_stream[i] == "endmodule"):
                #the current module is now finished deciphering
                design_book[cur_lib][module_name.lower()].setChecked(True)
                in_module = False
                module_name == None
            elif(c_stream[i] != module_name and in_ports):
                #entering parameters
                if(c_stream[i] == "#"):
                    in_params = True
                    continue

                #stack up/down the parentheses to get to the bottom of ports or params list
                if(c_stream[i] == "("):
                    parenth_count = parenth_count + 1
                    continue
                elif(c_stream[i] == ")"):
                    parenth_count = parenth_count - 1

                #exiting ports list and entering the actual module code
                if(parenth_count == 0):
                    if(not in_params):
                        in_ports = False
                    in_params = False
                    in_module = True
                #if we find anything or than an empty ports list, its not a testbench
                elif(c_stream[i] != ';' and not in_params):
                    design_book[cur_lib][module_name.lower()].unsetTB()
            #inside the module "architecture"
            elif(in_module):
                #check with every possible unit if its an instance
                for u in all_available_modules:
                    ignore_case = False
                    m_name = c_stream[i]
                    #if the unit is from vhdl, ignore case-sensitivity
                    if(u.getLanguageType() == u.Language.VHDL):
                        ignore_case = True
                        m_name = m_name.lower()
                    print(m_name)
                    print(u.getName(False))
                    if(m_name == u.getName(low=ignore_case)):
                        #add if not already added to the requirements for this module
                        if(u not in design_book[cur_lib][module_name.lower()].getRequirements()):
                            design_book[cur_lib][module_name.lower()].addRequirement(u)
                            pass
                        #only enter recursion if the unit has not already been completed ("checked")
                        if(not design_book[u.getLib()][u.getName()].isChecked()):
                            u.getLang().decipher(design_book, u.getLib(), verbose)
                            pass
                pass
            pass

        return design_book

    #generate string of component's signal declarations to be interfaced with the port
    def writeComponentSignals(self):
        print("writing signals")
        return ''
        pass

    #write out the mapping instance of an entity (can be pure instance using 'entity' keyword also)
    def writeComponentMapping(self, pureEntity=False, lib=''):
        c_stream = self.generateCodeStream(True,True,*self._std_parsers,'#')

        signals = []
        module_name = None
        #1. gather the inputs and outputs
        for i in range(len(c_stream)):
        # look for 'input' and 'output' keyword, then look for comma
            if(c_stream[i] == 'module'):
                in_ports = True
                module_name = c_stream[i+1]
            #entering ports section
            elif(in_ports):

                if(c_stream[i] == '#'):
                    in_params = True

        
        r = module_name+" uX"
        return r
        pass

    #write out the entity but as a component
    def writeComponentDeclaration(self):
        print("NOT USED")
        return ''
        pass


    pass