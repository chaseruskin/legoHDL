from .language import Language
import logging as log

class Verilog(Language):

    def __init__(self, fpath):
        super().__init__(fpath)
        self._std_delimiters = *self._std_delimiters,'#','[',']','='
        self._param_end = -1
        self._port_end = -1

    def decipher(self, design_book, cur_lib, verbose):
        if(verbose):
            log.info("Deciphering VERILOG file...")
            log.info(self._file_path)
        #keep case sensitivity
        c_stream = self.generateCodeStream(True,True,*self._std_delimiters)
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
    def writeComponentSignals(self, return_names=False):
        #print("writing signals")
        #keep cases and keep terminators
        true_code = self.generateCodeStream(True, True, *self._std_delimiters)
        #print(true_code)
        signals = []
        parameters = []
        #iterate through all important code words
        for i in range(0,len(true_code)):
            if(true_code[i] == "input"):
                #print("found input")
                signals = self.addSignal(signals, i, true_code, declare=(not return_names))
            elif(true_code[i] == "output"):
                #print("found output")
                signals = self.addSignal(signals, i, true_code, declare=(not return_names))
            elif(true_code[i] == "inout"):
                #print("found inout")
                signals = self.addSignal(signals, i, true_code, declare=(not return_names))
            elif(true_code[i] == "parameter"):
                #print("found parameter")
                parameters = self.addSignal(parameters, i, true_code, declare=(not return_names))
                pass
        pass
        signals_txt = ''
        #write all identified parameters
        for const in parameters:
            signals_txt = signals_txt + const + "\n"
        #write an extra new line to separate parameters from signals
        if(len(parameters)):
            signals_txt = signals_txt + "\n"
        #write all identified signals
        for sig in signals:
            signals_txt = signals_txt + sig + '\n'
        #print(signals_txt)
        #only return the list of names and parameters
        if(return_names):
            return (signals, parameters)
        else:
            return signals_txt

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
        bus_width = ' '
        def_value = ''
        def_pos = -1
        #print(self._param_end)
        while True:
            #done writing these signals from this type if seeing another port next
            if(true_stream[c+1] == 'input' or true_stream[c+1] == 'output' or true_stream[c+1] == 'inout'):
                break
            if(def_pos > -1 and (is_param and c != self._param_end) or (not is_param and c != self._port_end)):
                 def_value = def_value + true_stream[c]
            if(declare == False):
                bus_width = ''
            #capture the last signal of this assignment
            if(true_stream[c+1] == ';' or c == self._param_end or c == self._port_end):
                # do not add bus width if not declaring signals (only need names)
                if(true_stream[c] == ')' and true_stream[c+1] == ';' and def_pos == -1):
                    names.append(bus_width+true_stream[c-1])
                elif(def_pos > -1):
                    names.append(bus_width+true_stream[def_pos-1])
                    #add default value to every assignment
                    if(declare):
                        for i in range(len(names)):
                            names[i] = names[i] + def_value
                else:
                    names.append(bus_width+true_stream[c])
                break
            #multiple signals are assigned to this same type
            if(true_stream[c+1] == ','):
                names.append(bus_width+true_stream[c])
            #find out the bus width (if applicable)
            if(true_stream[c] == '['):
                bus_width = ' '
                in_bus = True
            if(in_bus):
                bus_width = bus_width + true_stream[c]
            if(true_stream[c] == ']'):
                bus_width = bus_width + ' '
                in_bus = False

            #find default value
            if(true_stream[c] == '='):
                def_pos = c
                def_value = ' = '
            c = c + 1
        #print(names)
        #simply return the list of found port names
        if(not declare):
            stash += names
            return stash
            
        #go through all names found for this signal type
        for n in names:
                stash.append(s_type+n+";")
        return stash

    #write out the mapping instance of an entity (can be pure instance using 'entity' keyword also)
    def writeComponentMapping(self, pureEntity=True, lib=''):
        #get parsed case-sensitive code stream with terminators
        c_stream = self.generateCodeStream(True,True,*self._std_delimiters)

        signals, parameters = self.writeComponentSignals(return_names=True)
        #print(signals, parameters)
        module_name = None
        #1. gather the inputs and outputs
        for i in range(len(c_stream)):
        # look for keywords then look for comma
            if(c_stream[i] == 'module'):
                module_name = c_stream[i+1]
                break

        def_name = "uX"
        r = module_name
        #write out parameter section
        if(len(parameters)):
            r = r + ' #(\n'
            for param in parameters:
                if(param == parameters[len(parameters)-1]):
                    r = r + "    ."+param+"("+param+")\n"
                    r = r + ")\n" + def_name
                else:
                    r = r + "    ."+param+"("+param+"),\n"
        else:
            r = r + " " + def_name
        #write out port section
        if(len(signals)):
            r = r + ' (\n'
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
        print("declaration")
        dec_text = ''
        in_module = False
        end_parenth = False
        with open(self._file_path, 'r') as file:
            for line in file.readlines():
                #find when within module
                if "module" in line:
                    in_module = True
                pass

                if(in_module):
                    dec_text = dec_text + line
                #stop reading the lines if we found the end of the module
                if "endmodule" in line:
                    break
                
                #find first time that token ')' is followed by ';'
                if(end_parenth == False):
                    token_1 = line.rfind(')')
                if(token_1 > -1):
                    end_parenth = True

                #we found a ')', now is the next character a ';'?
                if(end_parenth):
                    token_2 = line[token_1+1:].strip()
                    #start from beginning of next line to find ';'
                    if(token_2 == ''):
                        token_1 = -1
                        pass
                    #found ';' as next character
                    elif(token_2 == ';'):
                        in_module = False
                    #did not find ';' as next character
                    else:
                        end_parenth = False
            pass

        return dec_text

    pass