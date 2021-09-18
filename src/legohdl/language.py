################################################################################
#   Project: legohdl
#   Script: language.py
#   Author: Chase Ruskin
#   Description:
#       This script is a parent class parser for VHDL and Verilog files. It will
#   break down the source code and split into valid tokens through the 
#   'generate_code_stream' method.
################################################################################


from abc import ABC, abstractmethod
from .apparatus import Apparatus as apt
import sys,os

class Language(ABC):

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        self._std_delimiters = "(",")",":",";",","
        
        #determine if the file is VHDL or Verilog/SystemVerilog
        _,self._ext = os.path.splitext(fpath)
        #create as all lower case
        if(self._ext != None):
            self._ext = '*'+self._ext.lower()
        #determine which comments to ignore in generating code stream
        if(self._ext in apt.VERILOG_CODE):
            self._comments = "//"
            self._multi_comment = ("/*","*/")
        elif(self._ext in apt.VHDL_CODE):
            self._comments = "--"
            self._multi_comment = None
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

    #find all unit names within the source file and replace accordingly
    def setUnitName(self, name_pairs):
        if(self._ext in apt.VHDL_CODE):
            case_sense = False
        elif(self._ext in apt.VERILOG_CODE):
            case_sense = True

        all_pairs = []
        all_langs = []
        for key,pairs in name_pairs.items():
                for n in pairs:
                    all_pairs.append(n)
                    all_langs.append(key)

        #do major find and replace
  
        #open file to manipulate lines
        with open(self._file_path, 'r') as f:
            content = f.readlines()
            #must we have an exact match? yes if verilog
            #else convert to all lower case if not caring
            if(not case_sense):
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
                for line in content:
                    #this is a verilog module we are looking for
                    if(all_langs[i] == 'VERILOG'):
                        #if we are inside a VHDL file we don't care
                        if(not case_sense):
                            name_to_locate = name_to_locate.lower()
                        pass

                    #ensure it only replaces once
                    cont = j = 0
                    while j != -1:
                        j = line[cont:].find(name_to_locate)
                        if(j > -1):
                            line = line[:cont] + line[cont:].replace(name_to_locate,n[1])
                        cont = j+len(n[1])
                    
                    #check if remaining name pairs if n is a subset of any other name pairs
                    for j in range(i+1, len(all_pairs)):
                        m = all_pairs[j]
                        if(m[0].count(name_to_locate) and not m[0].count(n[1])):
                            #update with new thing to look for
                            all_pairs[j] = (m[0].replace(name_to_locate,n[1]), m[1])

                    file_data.append(line)
                    pass
                content = file_data
                pass

            f.close()
        #write back new transformed data
        with open(self._file_path, 'w') as f:
            for line in content:
                f.write(line)
        pass
    
    #turn a HDL file in to a string of words
    def generateCodeStream(self, keep_case, keep_term, *extra_parsers):
        code_stream = []
        #take in a single word, return a list of the broken up words
        def chopSticks(piece):
            #inner method to continously split delimiters that are bunched
            def computeNextIndex(w):
                min_index = sys.maxsize
                for d in extra_parsers:
                    tmp_i = w.find(d)
                    if(tmp_i > -1 and tmp_i < min_index):
                        min_index = tmp_i
                if(min_index == sys.maxsize):
                    return -1
                return min_index
                
            #print(delimiters)
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
            return chopped
        in_comments = False
        #read the vhdl file to break into words
        with open(self._file_path, 'r') as file:
            for line in file.readlines():
                #drop rest of line if comment is started
                comment_start = line.find(self._comments)
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
                        if(not keep_term):
                            sliced = sliced.replace("(","")
                            sliced = sliced.replace(")","")
                        if(len(sliced)):
                            code_stream = code_stream + [sliced]

        #print(code_stream)
        return code_stream
    pass