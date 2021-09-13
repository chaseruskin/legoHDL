from .language import Language
import logging as log

class Verilog(Language):

    def __init__(self, fpath):
        super().__init__(fpath)
        self._std_parsers = *self._std_parsers,'#','[',']','='
        self._param_end = -1
        self._port_end = -1

    def decipher(self, design_book, cur_lib, verbose):
        if(verbose):
            log.info("Deciphering VERILOG file...")
            log.info(self._file_path)
        #keep case sensitivity
        c_stream = self.generateCodeStream(True,True,*self._std_parsers)
        #print(c_stream)
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
                        self._port_end = i
                    else:
                        self._param_end = i
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
                    #print(m_name)
                    #print(u.getName(False))
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
        #keep cases and keep terminators
        true_code = self.generateCodeStream(True, True, *self._std_parsers)
        print(true_code)
        signals = []
        constants = []
        #iterate through all important code words
        for i in range(0,len(true_code)):
            if(true_code[i] == "input"):
                print("found input")
                signals = self.addSignal(signals, i, true_code, declare=True)
            elif(true_code[i] == "output"):
                print("found output")
                signals = self.addSignal(signals, i, true_code, declare=True)
            elif(true_code[i] == "inout"):
                print("found inout")
                signals = self.addSignal(signals, i, true_code, declare=True)
            elif(true_code[i] == "parameter"):
                print("found parameter")
                constants = self.addSignal(constants, i, true_code, declare=True)
                pass
        pass
        signals_txt = ''
        #write all identified constants
        for const in constants:
            signals_txt = signals_txt + const + "\n"
        #write an extra new line to separate constants from signals
        if(len(constants)):
            signals_txt = signals_txt + "\n"
        #write all identified signals
        for sig in signals:
            signals_txt = signals_txt + sig + '\n'
        #print(signals_txt)
        return signals_txt
        pass

    #append a signal/generic string to a list of its respective type
    def addSignal(self, stash, c, true_stream, declare=False):
        names = []
        supported_signals = ['wire', 'reg', 'logic']
        port_dir = true_stream[c]
        #is there a specific type?
        s_type = 'wire'
        if(port_dir == 'input'):
            if(true_stream[c+1] in supported_signals):
                s_type = true_stream[c+1]
        elif(true_stream[c+1] == 'logic'):
            s_type = 'logic'
        
        is_param = (port_dir == 'parameter')
        if(is_param):
            s_type = port_dir


        in_bus = False  
        bus_width = ''
        def_value = ''
        def_pos = -1
        #print(self._param_end)
        while True:
            if(def_pos > -1 and (is_param and c != self._param_end) or (not is_param and c != self._port_end)):
                 def_value = def_value + true_stream[c]
            
            #capture the last signal of this assignment
            if(true_stream[c+1] == ';' or c == self._param_end or c == self._port_end):
                #print(c)
                if(true_stream[c] == ')' and true_stream[c+1] == ';' and def_pos == -1):
                    names.append(bus_width+" "+true_stream[c-1])
                elif(def_pos > -1):
                    names.append(bus_width+" "+true_stream[def_pos-1])
                    #add default value to every assignment
                    for i in range(len(names)):
                        names[i] = names[i] + def_value
                else:
                    names.append(bus_width+" "+true_stream[c])
                break
            #multiple signals are assigned to this same type
            if(true_stream[c+1] == ','):
                names.append(bus_width+" "+true_stream[c])
            #find out the bus width (if applicable)
            if(true_stream[c] == '['):
                bus_width = ' '
                in_bus = True
            if(in_bus):
                bus_width = bus_width + true_stream[c]
            if(true_stream[c] == ']'):
                in_bus = False

            #find default value
            if(true_stream[c] == '='):
                def_pos = c
                def_value = ' = '
            c = c + 1

        #go through all names found for this signal type
        for n in names:
            stash.append(s_type+n+";")
        return stash

    #write out the mapping instance of an entity (can be pure instance using 'entity' keyword also)
    def writeComponentMapping(self, pureEntity=True, lib=''):
        #get parsed case-sensitive code stream with terminators
        c_stream = self.generateCodeStream(True,True,*self._std_parsers)

        signals = ['tes']
        parameters = ['bop','bop2']
        module_name = None
        #1. gather the inputs and outputs
        for i in range(len(c_stream)):
        # look for keywords then look for comma
            if(c_stream[i] == 'module'):
                in_ports = True
                module_name = c_stream[i+1]
            #find parameters and ports
            elif(c_stream[i] == "input"):
                pass
            elif(c_stream[i] == "output"):
                pass
            elif(c_stream[i] == "inout"):
                pass
            elif(c_stream[i] == "parameter"):
                pass

        
        r = module_name+" uX"
        if(len(parameters)):
            r = r + '\n#(\n'
            for param in parameters:
                if(param == parameters[len(parameters)-1]):
                    r = r + "    ."+param+"("+param+")\n"
                    r = r + ")"
                else:
                    r = r + "    ."+param+"("+param+"),\n"
        
        if(len(signals)):
            r = r + '\n(\n'
            for sig in signals:
                if(sig == signals[len(signals)-1]):
                    r = r + "    ."+sig+"("+sig+")\n"
                    r = r + ")"
                else:
                    r = r + "    ."+sig+"("+sig+"),\n"
        r = r + ';'
        return r
    #write out the entity but as a component
    def writeComponentDeclaration(self):
        print("NOT USED")
        return ''
        pass


    pass