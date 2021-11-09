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

import sys, re
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


    def getBounds(self, cseg, central_i, tokens):
        '''
        Returns the upper and lower bounds of a code statement by branching to the left
        and right of `central_i` index.

        Parameters:
            cseg ([str]): code segment
            central_i (int): index where the pivot occurs for a bus
            tokens ((str,str)): the L and R tokens to stop at
        Returns:
            l_bound (str): list of items on lhs condensed to a str from [str]
            r_bound (str): list of items on rhs condensed to a str from [str]
        '''
        l_bound = []
        r_bound = []
        tkn_cnt = 0
        #head leftways
        for i in range(central_i-1, -1, -1):
            #stop once token count is positive
            if(cseg[i] == tokens[1]):
                tkn_cnt -= 1
            if(cseg[i] == tokens[0]):
                tkn_cnt += 1
            #exit case
            if(tkn_cnt == 1):
                break
            l_bound += [cseg[i]]
        #reset token counter
        tkn_cnt = 0
        #head rightways
        for i in range(central_i+1, len(cseg), 1):
            #stop once token count is positive
            if(cseg[i] == tokens[0]):
                tkn_cnt += 1
            if(cseg[i] == tokens[1]):
                tkn_cnt -= 1
            #exit case
            if(tkn_cnt == -1):
                break
            r_bound += [cseg[i]]
        #reverse lhs because algorithm read R -> L
        l_bound.reverse()
        #condense to single str
        l_bound = apt.listToStr(l_bound, delim='')
        #print("LHS:",l_bound)
        #condenset to single str
        r_bound = apt.listToStr(r_bound, delim='')
        #print("RHS:",r_bound)
        return l_bound,r_bound


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




    


# ==============================================================================
# ==============================================================================
# === ARCHIVED CODE... TO DELETE ===============================================
# ==============================================================================
# ==============================================================================


    # :todo: rename and polish
    @DeprecationWarning
    def setUnitName(self, name_pairs, keep_case):
        '''
        Find all unit names within the source file and replace with its new
        revised name. 
        
        Used when installing a version and entity names get appended with the 
        version number.

        Parameters:
            name_pairs (?) : ?
            keep_case (bool): False for VHDL and True for VERILOG
        Returns:
            None
        '''

        all_pairs = []
        all_langs = []
        for key,pairs in name_pairs.items():
                for n in pairs:
                    all_pairs.append(n)
                    all_langs.append(key)

        #do major find and replace
  
        #open file to manipulate lines
        with open(self.getPath(), 'r') as f:
            content = f.readlines()
            #must we have an exact match? yes if verilog
            #else convert to all lower case if not caring
            if(not keep_case):
                tmp_content = []
                for c in content: 
                    tmp_content.append(c.lower())
                content = tmp_content

            #try to locate every name pair
            for i in range(len(all_pairs)):
                file_data = []
                n = all_pairs[i]
                #find the biggest matching name
                name_to_locate = n[0]
                #read through each text line
                for line in content:
                    #this is a verilog module we are looking for
                    if(all_langs[i] == 'VERILOG'):
                        #if we are inside a VHDL file we don't care
                        if(not keep_case):
                            name_to_locate = name_to_locate.lower()
                        pass

                    #replace all occurences of the name this line with the remaining line with replaced entity name
                    line = line.replace(name_to_locate,n[1])

                    file_data.append(line)
                    pass
                #check if remaining name pairs if n is a subset of any other name pairs
                for j in range(i+1, len(all_pairs)):
                    m = all_pairs[j]
                    if(m[0].count(name_to_locate) and not m[0].count(n[1]) and m[0] != name_to_locate):
                        #update with new thing to look for
                        all_pairs[j] = (m[0].replace(name_to_locate,n[1]), m[1])

                content = file_data
                pass

            f.close()
        #write back new transformed data
        with open(self._file_path, 'w') as f:
            for line in content:
                f.write(line)
        pass



# :todo: refactor and polish
    @DeprecationWarning
    def generateCodeStream(self, keep_case, keep_term, *extra_parsers, keep_parenth=True):
        '''
        Turn an HDL file into a list of its words.

        Parameters:
            keep_case (bool): convert all words to lower or keep case sensitivity
            keep_term (bool): decide if to keep all semi-colons (terminators)
            extra_parsers (*str): special tokens that need to be separate words
        Returns:
            ([str]): list of words from HDL file
        '''


        #take in a single word, return a list of the broken up words
        def chopSticks(piece):
            'Take in a single word, and return a list of the further broken up words.'


            def computeNextIndex(w):
                'Continuously split delimiters that are bunched together.'

                min_index = sys.maxsize
                for d in extra_parsers:
                    tmp_i = w.find(d)
                    if(tmp_i > -1 and tmp_i < min_index):
                        min_index = tmp_i
                if(min_index == sys.maxsize):
                    return -1
                return min_index
            

            index = computeNextIndex(piece)

            chopped = []
            #return if no delimiter or if word is only the delimiter
            if(piece in extra_parsers or index == -1):
                return [piece]
            else:
                while True:
                    #append the front half
                    if(index > 0):
                        chopped.append(piece[0:index])
                    #append the demiliter itself
                    chopped.append(piece[index])
                    #see if there is another delimiter in this word to split up
                    next_index = computeNextIndex(piece[index+1:])
                    #print("next:", next_index,"word:",piece[index+1:])
                    if(next_index > -1):
                        #append what will be skipped over
                        if(next_index > 0):
                            chopped.append(piece[index+1:next_index+index+1])
                        #shorten piece to what remains
                        piece = piece[index+next_index+1:]
                        #print("new piece:",piece)
                        index = 0
                    else:
                        #append the back half
                        if(index+1 < len(piece)):
                            chopped.append(piece[index+1:])
                        break
                #print(chopped)
                pass

            return chopped

        code_stream = []
        in_comments = False
        #read the HDL file to break into words
        with open(self.getPath(), 'r') as file:
            for line in file.readlines():
                #drop rest of line if comment is started
                comment_start = line.find(self._comment)
                if(comment_start == 0):
                    continue
                elif(comment_start > -1):
                    line = line[:comment_start]
                
                #handle multi-line comment sections
                if(self._multi_comment != None and not in_comments):
                    multi_comment_start = line.find(self._multi_comment[0])
                    
                    in_comments = (multi_comment_start > -1)
                    if(in_comments):
                        #does the comment section end on the same line it stated?
                        multi_comment_end = line.find(self._multi_comment[1])
                        past_extras = line[multi_comment_end+len(self._multi_comment[1]):]
                        #trim to the start of the comments
                        line = line[:multi_comment_start]
                        if(multi_comment_end > -1):
                            #append the stuff past the comments
                            line = line + past_extras
                            in_comments = False
                #inside multi-line comment block
                if(in_comments):
                    multi_comment_end = line.find(self._multi_comment[1])
                    in_comments = (multi_comment_end < 0)
                    #skip if still in multi-comment block
                    if(in_comments):
                        continue
                    else:
                        #produce the line past the comments
                        line = line[multi_comment_end+len(self._multi_comment[1]):]

                next_line = line.split()
                #iterate through each word in the line
                for word in next_line:
                    #convert all word's to lowercase if not keeping case sensitivity
                    if(not keep_case):
                        word = word.lower()
                    #drop all semicolons
                    if(not keep_term):
                        word = word.replace(";","")
                    #perform a split on words containing "(" ")" or ":"
                    chopped = chopSticks(word)
                    #drop all parentheses
                    for sliced in chopped:
                        if(not keep_parenth):
                            sliced = sliced.replace("(","")
                            sliced = sliced.replace(")","")
                        if(len(sliced)):
                            code_stream = code_stream + [sliced]

        #print(code_stream)
        return code_stream


    @DeprecationWarning
    def getCommentBlock(self):
        '''
        Read the beginning of the file and return all the text hidden in comments,
        as-is.

        Parameters:
            None
        Returns:
            a_txt (str): the text behind the first continuous block of comments
        '''
        a_txt = ''
        in_cmts = False

        with open(self.getPath(), 'r') as file:
            for line in file.readlines():
                line = line.strip()
                #skip empty lines
                if(len(line) == 0):
                    continue

                #is this line a comment line?
                c_start = line.find(self._comment)
                #is this line a multi-line comment?
                mc_start = line.find(self._multi[0])
                if(mc_start > -1):
                    if(mc_start < c_start or c_start <= -1):
                        c_start = mc_start
                        in_cmts = True
                
                #stop collecting text if outside of comments
                if(c_start <= -1 and in_cmts == False):
                    break

                #by default capture the rest of the line as text
                c_end = len(line)
                #handle leaving multi-line comment sections
                if(self._multi != None):
                    mc_end = line.find(self._multi[1])
                    if(mc_end > -1):
                        in_cmts = False
                        c_end = mc_end
                #trim to relevant text accordingly
                line = line[c_start+len(self._comment):c_end]
                #append this line to the info text
                a_txt = a_txt + line + '\n'
                pass
            pass
        return a_txt


    pass