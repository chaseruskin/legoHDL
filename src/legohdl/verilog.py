# Project: legohdl
# Script: verilog.py
# Author: Chase Ruskin
# Description:
#   This script inherits language.py and implements the behaviors for
#   verilog/systemverilog code files (syntax, deciphering).

from .language import Language
import logging as log
from .unit import Unit


class Verilog(Language):


    def __init__(self, fpath, M='', L='', N='', V=''):
        '''
        Create a VERILOG language file object.

        Parameters:
            fpath (str): HDL file path
            M (str): the legohdl block market the file belongs to
            L (str): the legohdl block library the file belongs to
            N (str): the legohdl block name the file belongs to
            V (str): the legohdl block version the file belongs to
        Returns:
            None
        '''
        super().__init__(fpath, M, L, N, V)
        self._comment = "//"
        self._multi_comment = ("/*","*/")
        self._std_delimiters = *self._std_delimiters,'#','[',']','='
        
        self._param_begin = -1
        self._param_end = -1
        self._port_begin = -1
        self._port_end = -1

        ### new important stuff
        self._seps = [':', '=', '(', ')', '#', ',', '.', '[', ']']
        self._dual_chars = ['<=']
        self._comment = '//'

        self.spinCode()
        ###

        self._about_txt = self.getCommentBlock()

        #run with VERILOG decoder
        self.identifyDesigns()
        pass

    def identifyDesigns(self):
        '''
        Analyzes the current VERILOG file to only identify design units. Does not
        complete their data. 
        
        Dynamically creates attr _designs.

        Parameters:
            None
        Returns:
            _designs ([Unit]): list of units found in this file
        '''
        if(hasattr(self, "_designs")):
            return self._designs

        #get the list of statements
        c_statements = self.spinCode()

        self._designs = []

        #looking for design units in each statement
        for code_seg in c_statements:
            if(code_seg[0] == 'module'):
                print(code_seg[1])
                self._designs += [Unit(self.getPath(), Unit.Design.ENTITY, self.M(), self.L(), self.N(), self.V(), code_seg[1], about_txt=self._about_txt)]
        return self._designs


    def decipher(self, design_book=dict(), cur_lib='', verbose=False):
        '''
        Analyzes the current VERILOG file to collect data for all identified design 
        units.
        '''
        current_map = Unit.Jar[self.M()][self.L()][self.N()]

        if(verbose):
            log.info("Deciphering VERILOG file..."+self.getPath())

        #keep case sensitivity
        c_stream = self.generateCodeStream(True, True, *self._std_delimiters)
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
                self._port_begin = i+3
            elif(c_stream[i] == "endmodule"):
                #the current module is now finished deciphering
                current_map[module_name].setChecked(True)
                in_module = False
                module_name == None
            elif(c_stream[i] != module_name and in_ports):
                #entering parameters
                if(c_stream[i] == "#"):
                    in_params = True
                    self._param_begin = i+2
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
                        self.collectPorts(current_map[module_name], c_stream[self._port_begin:i])
                    else:
                        self._port_begin = i+2
                        self._param_end = i
                        self.collectGenerics(current_map[module_name], c_stream[self._param_begin:i])
                    in_params = False
                    in_module = True
                #if we find anything or than an empty ports list, its not a testbench
                elif(c_stream[i] != ';' and not in_params):
                    # :todo: write interface
                    #current_map[module_name]
                    pass
                    pass
            #inside the module "architecture"
            elif(in_module):
                #check with every possible unit if its an instance
                # :todo: count the number of modules that share that name, then prompt user to select which one
                # to resolve ambiguity
                for u in all_available_modules:
                    m_name = c_stream[i]
                    u_name = u.E()
                    #if the unit is from vhdl, ignore case-sensitivity
                    if(u.getLang() == u.Language.VHDL):
                        m_name = m_name.lower()
                        u_name = u.E().lower()
                    #print(m_name)
                    #print(u.getName(False))
                    if(m_name == u_name):
                        #add if not already added to the requirements for this module
                        if(u not in current_map[module_name].getRequirements()):
                            current_map[module_name].addRequirement(u)
                            pass
                        #only enter recursion if the unit has not already been completed ("checked")
                        if(not Unit.Jar[u.M()][u.L()][u.N()][u.E()].isChecked()):
                            u.getLang().decipher(dict(), u.getLib(), verbose)
                            pass
                pass
            pass

        return design_book


    def collectPorts(self, unit, words):
        '''
        From a subset of the code stream, parse through and create HDL Port
        objects. Modifies unit's _interface attribute.

        Parameters:
            unit (Unit): the unit who's interface the ports belong to
            words ([str]): the subset of code stream
        Returns:
            None
        '''
        #add comma to end
        last_flavor = []
        last_way = ''

        words = words + [',']
        while words.count(','):
            sep = words.index(',')
            piece = words[:sep]
            if(len(piece) == 0):
                words = words[sep+1:]
                continue
            #complete fields backward from comma
            port_name = piece[-1]
            #scrap together what is left
            next_flavor = []
            for w in piece[0:len(piece)-1]:
                if(w == 'input' or w == 'output' or w == 'inout'):
                    last_way = w
                else:
                    next_flavor += [w]
            #use last type if this type is unspecified
            if(len(next_flavor) == 0):
                next_flavor = last_flavor
            #update last flavor to the most recent type found
            else:
                last_flavor = next_flavor

            unit.getInterface().addPort(port_name, last_way, next_flavor)

            words = words[sep+1:]

        pass


    def collectGenerics(self, unit, words):
        '''
        From a subset of the code stream, parse through and create HDL Generic
        objects. Modifies unit's _interface attribute.

        Parameters:
            unit (Unit): the unit who's interface the generics belong to
            words ([str]): the subset of code stream
        Returns:
            None
        '''
        #add additional comma to end to make iteration easier
        #pivot on '='
        while words.count('='):
            sep = words.index('=')
            param_name = words[sep-1]
            value = words[sep+1]

            flavor = ['integer']

            #anything between name and 'parameter' keyword? -> thats the type
            
            # :todo: allow for searching rest of document for these parameters and ports and
            #filling in the data as the file gets read down the road in 'decipher'

            unit.getInterface().addGeneric(param_name, flavor, value)

            #step through the remaining words
            words = words[sep+1:]
        pass


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