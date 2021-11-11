# Project: legohdl
# Script: verilog.py
# Author: Chase Ruskin
# Description:
#   This script inherits language.py and implements the behaviors for
#   verilog/systemverilog code files (syntax, deciphering).

from .language import Language
from .unit import Unit


class Verilog(Language):


    def __init__(self, fpath, block):
        '''
        Create a VERILOG language file object.

        Parameters:
            fpath (str): HDL file path
            block (Block): the block this language file belongs to
        Returns:
            None
        '''
        super().__init__(fpath, block)

        self._seps = [':', '=', '(', ')', '#', ',', '.', '[', ']', '"']
        self._dual_chars = ['<=', '==']
        self._comment = '//'
        self._atomics = ['end', 'endmodule', 'endtask', 'endcase', \
            'endfunction', 'endprimitive', 'endspecify', 'endtable', 'begin', \
            'endgenerate', 'generate']

        self.spinCode()

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
        for cseg in c_statements:
            if(cseg[0] == 'module'):
                #log.info("Identified module "+cseg[1])
                self._designs += [Unit(cseg[1], self.getPath(), Unit.Design.ENTITY, self)]
                dsgn_unit = self._designs[-1]
                self.getInterface(dsgn_unit, c_statements[c_statements.index(cseg):])
                pass
        return self._designs


    def decode(self, u, recursive=True):
        '''
        Decipher and collect data on a unit's lower-level entities.

        Parameters:
            u (Unit): the unit file who's interface to update
            recursive (bool): determine if to tunnel through entities
        Returns:
            None
        '''
        #get the code statements
        csegs = self.spinCode()
        skips = ['reg', 'wire', 'module', 'always', 'case', 'while', \
            'repeat']

        in_module = False
        in_case = False

        #do not decode unit again if already decoded
        if(u.isChecked()):
            return

        for cseg in csegs:
            #print(cseg)
            #determine when entering module
            if(cseg[0] == 'module' and cseg[1] == u.E()):
                in_module = True
            elif(in_module == False):
                continue

            #check for exit case - finding 'endmodule'
            if(cseg[0] == 'endmodule'):
                u.setChecked(True)
                return

            if(cseg[0] == 'case'):
                in_case = True
            if(cseg[0] == 'endcase'):
                in_case = False

            #look for equal amount of brackets
            if(cseg.count('(') > 0 and (cseg.count('(') - cseg.count(')') == 0)):
                #now check for entity name
                comp_name = cseg[0]
                #skip a code label from generate statement
                if(cseg[0] == ':' and len(cseg) > 2):
                    comp_name = cseg[2]
                #get comp name from a case-generate statement
                elif(in_case and cseg.count(':')):
                    comp_name = cseg[cseg.index(':')+1]
                    if(comp_name.isdigit()):
                        continue
                #skip past if statements for if-generate statement
                elif(cseg[0] == 'if' or cseg[1] == 'if'):
                    pb_cnt = 1
                    i = cseg.index('if')+2
                    while pb_cnt > 0:
                        if(cseg[i] == '('):
                            pb_cnt += 1
                        elif(cseg[i] == ')'):
                            pb_cnt -=1
                        i += 1
                    if(i < len(cseg)):
                        comp_name = cseg[i]
                    else:
                        continue
                    pass
                #hop over 'else' keyword
                elif(cseg[0] == 'else'):
                    comp_name = cseg[1]

                #skip keyword misleaders
                if(comp_name in skips):
                    continue
                #gather instantiated ports and generics
                p_list, g_list = self.collectInstanceMaps(cseg[cseg.index(comp_name):])
                #try to locate the unit with the given information
                comp_unit = Unit.ICR(comp_name, lib=None, ports=p_list, gens=g_list)
                if(comp_unit != None):
                    #add as a requirement
                    u.addReq(comp_unit)
                    #enter decoding for the lower-level unit
                    if(comp_unit.isChecked() == False and recursive):
                        comp_unit.getLanguageFile().decode(comp_unit, recursive)
                pass

        pass


    def getInterface(self, u, csegs):
        '''
        Decipher and collect data on a unit's interface (entity code).

        Assumes `csegs` begins at the first statement that declares the entity.
        Exits on the first statement beginning with "end".

        Parameters:
            u (Unit): the unit file who's interface to update
            csegs ([[str]]): list of code statements (which are also lists)
        Returns:
            None
        '''

        #store generic identifiers
        g_ids = []
        #store port identifiers
        p_ids = []
        #keep information for where the generic declaration ends
        g_end = 0
        g_index = 2
        #iterate through every code segment
        for cseg in csegs:
            #print(cseg)
            #check for exit case - finding 'endmodule'
            if(cseg[0] == 'endmodule'):
                #print(u.getInterface())
                #if(u.E() == 'johnson_ctr'):
                    #exit()
                return
            #get the list of generics and ports from module declaration statement
            if(cseg[0] == 'module'):
                #handle generics
                g_end = 0
                g_index = 2
                if(cseg.count('#')):
                    g_index = g_index+cseg.index('#')
                    gseg = cseg[g_index:] #skip '#' and first '('
                    g_end, g_ids = self._getIdentifiers(gseg)
                    #print("GENERICS:",g_ids)
                    pass
                #grab remaining items as the ports list
                pseg = cseg[g_index+g_end+1:]
                _, p_ids = self._getIdentifiers(pseg)
                #print("PORTS:",p_ids)
                pass
            #check module declaration statement for port declaration data
            if(cseg[0] == 'module'):
                seg_i = 0
                dtype = []
                l = ''
                r = ''
                route = None
                entry_route = False
                route_keywords = ['input', 'output', 'inout']
                for c in cseg:
                    #track what route is last declared
                    if(c in route_keywords):
                        route = c
                        entry_route = True
                        #print("ROUTE",route)
                        dtype = []
                        l = ''
                        r = ''
                    #try to capture a datatype specified between route and identifier
                    elif(entry_route and c not in p_ids):
                        dtype += [c]
                        if(c == ':'):
                            l,r = self.getBounds(cseg, seg_i, ('[',']'))
                    elif(route != None and c in p_ids):
                        entry_route = False
                        #implicitly set port datatype as wire
                        if(dtype == []):
                            dtype = ['wire']
                        u.getInterface().addPort(c, route, dtype, (l,r))
                    pass
                    seg_i += 1

                #only use segment about generics
                gseg = cseg[g_index:g_index+g_end]
                #iterate through all generics
                for gen in g_ids:
                    #print(gseg)
                    val = []
                    i_center = gseg.index(gen)
                    tmpseg = gseg[i_center:]
                    if(tmpseg.count('=')):
                        tmpseg = tmpseg[tmpseg.index('=')+1:]
                        i_end = len(tmpseg) #ignore final ')' if comes to that
                        #find comma
                        if(tmpseg.count(',')):
                            i_end = tmpseg.index(',') 
                        #between is the pieces for the value
                        val = tmpseg[:i_end]
                        #print("gen:",gen,val)
                    u.getInterface().addGeneric(gen, [], val)

                pass
            #found an input declaration
            elif(cseg[0] == 'input'):
                pass
            #found an output declaration
            elif(cseg[0] == 'output'):
                pass
            #found an inout declaration
            elif(cseg[0] == 'inout'):
                pass
            #found a parameter declaration
            elif(cseg[0] == 'parameter'):
                pass
            #check if this is further defining a port
            elif(cseg[0] == 'wire' and cseg[-1] in p_ids):
                pass
            #check if this is further defining a port
            elif(cseg[0] == 'reg' and cseg[-1] in p_ids):
                pass
        pass


    def _getIdentifiers(self, cseg):
        '''
        Determines the list of identififers from the module declaration.

        Parameters:
            cseg ([str]): the module declaration line.
        Returns:
            dec_end (int): ending index of the given identifier section
            ids ([str]): list of identifier names
        '''
        #track amount of brackets (begins with '(')
        pb_cnt = 1
        dec_end = 0
        #store identifier names
        ids = []
        #find when this identifier section ends (pb_cnt == 0)
        while pb_cnt > 0 and dec_end < len(cseg):
            #count pb's
            if (cseg[dec_end] == '('):
                pb_cnt += 1
            elif(cseg[dec_end] == ')'):
                pb_cnt -= 1
            #update to next index
            dec_end += 1
        #slice to the end of identifer section
        cseg = cseg[:dec_end-1]
        #append a ',' to end for algorithm
        cseg = cseg + [',']
        #iterate through every token 
        while cseg.count(',') and len(cseg) > 1:
            i = 0
            #get name right before assignment
            if(cseg[1] == '='):
                ids += [cseg[0]]
                #jump to next comma
                i = cseg.index(',')
            #get identifier right before comma
            elif(cseg[1] == ','):
                ids += [cseg[0]]
                #jump to next comma
                i = cseg.index(',')
            #increment i with every passage
            i = i+1
            #slowly trim away code statement
            cseg = cseg[i:]  

        return dec_end-1, ids


    def getComponents(self, pkg_str):
        '''
        Return a list of component names that are available in this package.

        Parameters:
            pkg_str (str): the string following a vhdl 'use' keyword.
        Returns:
            comps ([str]): entity names found as component declarations in package
        '''
        pass


    def collectInstanceMaps(self, cseg):
        '''
        Parse entity instantiation mappings to form a generics list and ports list from 
        an instantiation code statement.

        If a component was instantiated by position, '?' will appear in the list to get
        an appropriate length of number of ports mapped.

        Assumes first code word in the segment is the module name.

        Parameters:
            cseg ([str]): a vhdl code statement
        Returns:
            p_list ([str]): list of ports identified (all lower-case)
            g_list ([str]): list of generics identified (all lower-case)
        '''
        #print("COLLECTING INSTANCE NAMES...")
        #print(cseg)   
        #collect data on the port identifiers and generic identifiers 
        p_list = []
        g_list = []
        #flags indicating when in relevant sections
        in_generics = False
        in_ports = False
        #track bracket count
        pb_cnt = 0
        #store previous code word
        prev_c = ''
        #also track how many mappings occur for generics and ports
        g_comma_cnt = 0
        p_comma_cnt = 0
        #step through each token
        for c in cseg:
            #track bracket count to know when entering/exiting sections
            if(c == '('):
                pb_cnt += 1
            elif(c == ')'):
                pb_cnt -= 1

            #enter generics with '#' symbol
            if(c == '#'):
                in_generics = True
            #enter ports when encounter the first '(' and not in generics
            elif(c == '(' and pb_cnt == 1 and in_generics == False):
                in_ports = True
            #exiting an interface section when the bracket count is 0
            elif(pb_cnt == 0):
                in_generics = False
                #break code segment iteration once ports are done
                if(in_ports == True):
                    in_ports = False
                    break
            #collect generics data
            elif(in_generics):
                #detect a interface identifier following a '.'
                if(prev_c == '.'):
                    #print("GEN:",c)
                    g_list += [c]
                #also count commas in case instance identifiers are not used
                if(c == ',' or (g_comma_cnt == 0 and c != '(' and c!= ')')):
                    g_comma_cnt += 1
            #collect ports data
            elif(in_ports):
                #detect a interface identifier following a '.'
                if(prev_c == '.'):
                    #print("PORT:",c)
                    p_list += [c]
                #also count commas in case instance identifiers are not used
                if(c == ',' or (p_comma_cnt == 0 and c != '(' and c!= ')')):
                    p_comma_cnt += 1
            #store the previous code token
            prev_c = c
            pass

        #add ? for the missing instance mappings
        diff = g_comma_cnt - len(g_list)
        for i in range(diff):
            g_list += ['?']

        diff = p_comma_cnt - len(p_list)
        for i in range(diff):
            p_list += ['?']

        #print("GEN COUNT:",g_comma_cnt)
        #print("PORT COUNT:",p_comma_cnt)
        #print(g_list)
        #print(p_list)
        return p_list, g_list


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


    pass