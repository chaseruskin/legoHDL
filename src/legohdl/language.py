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

import sys,os
from abc import ABC, abstractmethod
from .apparatus import Apparatus as apt
import logging as log
from .map import Map


class Language(ABC):

    #class container to store a list of all known files
    _ProcessedFiles = Map()

    def __init__(self, fpath, M='', L='', N='', V=''):
        '''
        Create an HDL language file object.

        Parameters:
            fpath (str): HDL file path
            M (str): the legohdl block market the file belongs to
            L (str): the legohdl block library the file belongs to
            N (str): the legohdl block name the file belongs to
            V (str): the legohdl block version the file belongs to
        Returns:
            None
        '''

        #format the file path
        self._file_path = apt.fs(fpath)

        if(self.getPath().lower() in self._ProcessedFiles.keys()):
            log.info("Already processed: "+self.getPath())
            return
        
        #create a group of standard delimiters
        self._std_delimiters = "(",")",":",";",",","="

        #remember what block owns this file
        self._M = M
        self._L = L
        self._N = N
        self._V = V

        #add to processed list
        self._ProcessedFiles[self.getPath().lower()] = self
        pass
    
    
    @abstractmethod
    def identifyDesigns(self):
        pass


    @abstractmethod
    def decipher(self, design_book, cur_lib, verbose):
        pass


    #generate string of component's signal declarations to be interfaced with the port
    @abstractmethod
    def writeComponentSignals(self):
        pass


    #write out the mapping instance of an entity (can be pure instance using 'entity' keyword also)
    @abstractmethod
    def writeComponentMapping(self, pureEntity=False, lib=''):
        pass


    #write out the entity but as a component
    @abstractmethod
    def writeComponentDeclaration(self):
        pass


    # :todo: rename and polish
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
                if(self._multi_comment != None):
                    mc_start = line.find(self._multi_comment[0])
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
                if(self._multi_comment != None):
                    mc_end = line.find(self._multi_comment[1])
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


    def getPath(self):
        return self._file_path


    def M(self):
        return self._M


    def L(self):
        return self._L


    def N(self):
        return self._N


    def V(self):
        return self._V


    def __str__(self):
        return f'''
        file: {self.getPath()}
        owner: {self.M()+'.'+self.L()+'.'+self.N()+'('+self.V()+')'}
        '''
    pass