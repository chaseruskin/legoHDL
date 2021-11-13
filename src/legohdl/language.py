# Project: legohdl
# Script: language.py
# Author: Chase Ruskin
# Description:
#   This script is a parent class parser for VHDL and Verilog files. It will
#   break down the source code and split into valid tokens through the 
#   'generate_code_stream' method. 
#
#   A file (language) has entities. A file object's role is to create the 
#   entities/design units from its code, depending on if its 1 of the 2 
#   supported languages: VHDL or verilog.

import re
from abc import ABC, abstractmethod
from .apparatus import Apparatus as apt


class Language(ABC):


    def __init__(self, fpath, block):
        '''
        Create an HDL language file object.

        Parameters:
            fpath (str): HDL file path
            block (Block): the Block the file belongs to
        Returns:
            None
        '''
        #format the file path
        self._file_path = apt.fs(fpath)

        #remember the block this file belongs to
        self._block = block

        self._multi = ('/*', '*/')
        pass
    
    
    @abstractmethod
    def identifyDesigns(self):
        '''
        Analyzes the current VHDL file to only identify design units. Does not
        complete their data. 
        
        Dynamically creates attr _designs.

        Parameters:
            None
        Returns:
            _designs ([Unit]): list of units found in this file
        '''
        pass
    

    @abstractmethod
    def decode(self, u, recursive=True):
        '''
        Decipher and collect data on a unit's instantiated lower-level entities.

        Parameters:
            u (Unit): the unit file who's interface to update
            recursive (bool): determine if to tunnel through entities
        Returns:
            None
        '''
        pass


    @abstractmethod
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
        pass


    @abstractmethod
    def getComponents(self, pkg_str):
        '''
        Return a list of component names that are available in this package.

        Parameters:
            pkg_str (str): the string following a vhdl 'use' keyword.
        Returns:
            comps ([str]): entity names found as component declarations in package
        '''
        pass


    @abstractmethod
    def collectInstanceMaps(self, cseg):
        '''
        Parse entity instantiation mappings to form a generics list and ports list from 
        an instantiation code statement.

        If a component was instantiated by position, '?' will appear in the list to get
        an appropriate length of number of ports mapped.

        Parameters:
            cseg ([str]): a vhdl code statement
        Returns:
            p_list ([str]): list of ports identified (all lower-case)
            g_list ([str]): list of generics identified (all lower-case)
        '''
        pass


    def spinCode(self):
        '''
        Turn an HDL file into a list of its statements. 
        
        Omits comments and preserves case sensitivity. Makes sure that certain
        tokens are an individual component within the list. 
        
        Uses _comment (str) to specify the single-line comment token. 
        Uses _seps ([str]) to determine what characters deserve their own index. 
        Uses _dual_chars ([str]) to combine any two-character tokens to be a single index.
        Uses _multi ((str, str)) to identify multi-line comment sections.
        Uses _atomics ([str]) to separate special keywords into their own statements.
        
        Dynamically creates attr _code_stream so the operation can be reused.

        Parameters:
            None
        Returns:
            _code_stream ([[str]]): a list of statements that are word-separated
        '''
        #dynamic return once operation has been performed
        if(hasattr(self, "_code_stream")):
            return self._code_stream

        self._code_stream = []

        #current statement
        statement = []
        in_multi = False

        #read the HDL file to break into words
        with open(self.getPath(), 'r') as file:
            #transform lines into statements
            code = file.readlines()
            line_cnt = 0
            for line in code:
                line_cnt += 1
                #strip off an excessive whitespace
                line = line.strip()

                # :todo: determine if inside a string to use '--' inside a string

                #reduce down to valid code (non-comments)
                c_index = line.find(self._comment)
                if(c_index > -1):
                    line = line[:c_index]
                #find a beginning to a multi-line comment section
                m0_index = line.find(self._multi[0])
                if(m0_index > -1):
                    line_l = line[:m0_index]
                #find an end to a multi-line comment section
                m1_index = line.find(self._multi[1])
                if(m1_index > -1):
                    in_multi = False
                    #trim everything within the comment section
                    line_r = line[m1_index+len(self._multi[1]):]
                #reset line if a multi-line comment was detected
                if(m0_index > -1 or m1_index > -1):
                    line = ''
                #add lhs of multi-line comment
                if(m0_index > -1):
                    line = line_l
                #add rhs of multi-line comment
                if(m1_index > -1):
                    line = line + line_r

                #skip if line is blank or within a multi-line comment section
                if(((len(line) == 0 and m0_index <= -1) or in_multi) and line_cnt < len(code)):
                    continue
                #enter the mult-line comment section for next line
                if(m0_index > -1 and m1_index <= -1):
                    in_multi = True
                
                #make sure certain characters will be their own items in the statement
                for sep in self._seps:
                    line = line.replace(sep, ' '+sep+' ')

                #find the ';' and create new statements if found
                sc_index = -1
                while line.count(';') or line_cnt == len(code):
                    sc_index = line.find(';')
                    #no ';' was found but the rest of the code must be collected
                    if(sc_index == -1 and len(code) == line_cnt):
                        sc_index = len(line)
                        line_cnt += 1

                    #split the statement into a list of its words
                    statement += line[:sc_index].split()

                    #skip any empty statements
                    if(len(statement) == 0):
                        continue
                        
                    #combine dual characters together
                    statement_final = []
                    for i in range(len(statement)-1):
                        for dc in self._dual_chars:
                            if(statement[i] == dc[0] and statement[i+1] == dc[1]):
                                statement_final.append(dc)
                                #make empty so these indices don't get added
                                statement[i] = ''
                                statement[i+1] = '' 
                                continue
                        if(statement[i] != ''):
                            statement_final.append(statement[i])
                    #make sure to add last item
                    if(statement[-1] != ''):
                            statement_final.append(statement[-1])
                    #separate special keywords into their own statement lists
                    for word in statement_final:
                        if(word.lower() in self._atomics):
                            #find index where the atomic word is in the statement
                            a_i = statement_final.index(word)
                            #split the statement
                            if(len(statement_final[:a_i])):
                                self._code_stream += [statement_final[:a_i]]
                            self._code_stream += [[word]]
                            #update remaining pieces of the statement
                            statement_final = statement_final[a_i+1:]
                        pass
                    #only add non empty statement lists
                    if(len(statement_final) > 0):
                        self._code_stream += [statement_final]
                    statement = []
                    #update remaining line string
                    line = line[sc_index+1:]
                    #reset semi-colon index
                    sc_index = -1
                    pass

                #add any code after ';'
                statement += line[sc_index+1:].split()
                pass
            pass

        for cs in self._code_stream:
           #print(cs)
           pass
        return self._code_stream


    def getAbout(self):
        '''
        Read the beginning of the file and return all the text hidden in comments,
        as-is. Reads up until a non-comment line (line can be empty).

        Dynamically creates attr _about (str) to be reused.

        Parameters:
            None
        Returns:
            _about (str): the text behind the first continuous block of comments
        '''
        #return text if already computed
        if(hasattr(self, "_about")):
            return self._about

        self._about = ''
        in_multi = False
        in_single = False

        #open the HDL file
        with open(self.getPath(), 'r') as file:
            #read every line
            for line in file.readlines():
                #every newline starts off as not a comment
                in_single = False

                #strip off an excessive whitespace
                if(in_multi):
                    line = line.replace('\n','')
                else:
                    line = line.strip()

                #find a beginning to a multi-line comment section
                m0_index = line.find(self._multi[0])
                if(m0_index > -1):
                    line = line[m0_index+len(self._multi[0]):]
                    in_multi = True

                #grab only single-line comment if not in multi-line section
                c_index = line.find(self._comment)
                if(c_index > -1 and not in_multi):
                    line = line[c_index+len(self._comment):]
                    in_single = True

                #find an end to a multi-line comment section
                m1_index = line.find(self._multi[1])
                if(m1_index > -1 and in_multi):
                    #keep everything within the comment section
                    line = line[:m1_index]

                #skip if line is blank or within a multi-line comment section
                if(in_multi or in_single):
                    self._about = self._about + line + '\n'
                #exit when not in comments anymore
                else:
                    break

                #exit the mult-line comment section for next line
                if(m1_index > -1 and in_multi):
                    in_multi = False
                pass
            pass

        return self._about


    def getBounds(self, dtype, central_i, tokens):
        '''
        Returns the upper and lower bounds of a code statement by branching to the left
        and right of `central_i` index.

        Parameters:
            dtype ([str]): code segment corresponding to the datatype
            central_i (int): index where the pivot occurs for a bus
            tokens ((str,str)): the L and R tokens to stop at
        Returns:
            l_bound,r_bound ((str,str)): list of items on lhs and rhs from [str] to str
        '''
        l_bound = []
        r_bound = []
        tkn_cnt = 0
        #return nothing
        if(central_i == -1):
            return ('','')
        #head leftways
        for i in range(central_i-1, -1, -1):
            #stop once token count is positive
            if(dtype[i] == tokens[1]):
                tkn_cnt -= 1
            if(dtype[i] == tokens[0]):
                tkn_cnt += 1
            #exit case
            if(tkn_cnt == 1):
                break
            l_bound += [dtype[i]]
        #reset token counter
        tkn_cnt = 0
        #head rightways
        for i in range(central_i+1, len(dtype), 1):
            #stop once token count is positive
            if(dtype[i] == tokens[0]):
                tkn_cnt += 1
            if(dtype[i] == tokens[1]):
                tkn_cnt -= 1
            #exit case
            if(tkn_cnt == -1):
                break
            r_bound += [dtype[i]]
        #reverse lhs because algorithm read R -> L
        l_bound.reverse()
        #condense to single str
        l_bound = apt.listToStr(l_bound, delim='')
        #print("LHS:",l_bound)
        #condenset to single str
        r_bound = apt.listToStr(r_bound, delim='')
        #print("RHS:",r_bound)
        return (l_bound,r_bound)


    def swapUnitNames(self, name_pairs):
        '''
        Uses a regular expression to find/replace all unit identifiers. Ignores
        case sensitivity when finding names.

        Parameters:
            name_pairs ([[str]]): list of pairs of names to be [found, replaced]
        Returns:
            None
        '''
        data = []
        #open the file
        with open(self.getPath(), 'r') as f:
            data = f.readlines()
            #iterate through every name pair to find/replace
            for pair in name_pairs:
                #replace pairs only that have complete word
                expression = re.compile('\\b'+pair[0]+'\\b', re.IGNORECASE)
                #iterate through every line of the file data
                for i in range(len(data)):
                    data[i] = expression.sub(pair[1], data[i])
                pass
            pass

        #rewrite the file with new replacements
        with open(self.getPath(), 'w') as f:
            f.writelines(data)
        pass


    def getPath(self):
        '''Returns this _file_path (str) for this Language object.'''
        return self._file_path


    def getOwner(self):
        '''Returns the _block (Block) that owns this file.'''
        return self._block


    def __str__(self):
        return f'''
        file: {self.getPath()}
        owner: {self.getOwner().M()+'.'+self.getOwner().L()+'.'+self.getOwner().N()+'('+self.getOwner().V()+')'}
        '''
    

    pass