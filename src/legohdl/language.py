from abc import ABC, abstractmethod
from .apparatus import Apparatus as apt
import sys

class Language(ABC):

    def __init__(self, fpath):
        self._file_path = apt.fs(fpath)
        self._std_parsers = "(",")",":",";"
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
    def setUnitName(self, name_pairs, case_sense=False):
        #do major find and replace
        file_data = []
        #various characters that could be next to the unit name
        endpoints = [' ', '.', '\n', '\t', '--', '//']
        #open file to manipulate lines
        with open(self._file_path, 'r') as f:
            for line in f.readlines():
                #must we have an exact match? yes in verilog
                if(not case_sense):
                    line = line.lower()
                #test every combination of endpoint pairs to find/replace unit name
                for n in name_pairs:
                    for ep in endpoints:
                        for ep2 in endpoints:
                                line = line.replace(ep+n[0]+ep2, ep+n[1]+ep2)

                file_data.append(line)
            f.close()
        #write back new transformed data
        with open(self._file_path, 'w') as f:
            for line in file_data:
                f.write(line)
        pass
    
    #turn a HDL file in to a string of words
    def generateCodeStream(self, keep_case, keep_term, *extra_parsers):
        code_stream = []
        #take in a single word, return a list of the broken up words
        def chopSticks(piece):

            def computeNextIndex(w):
                min_index = sys.maxsize
                for d in extra_parsers:
                    tmp_i = w.find(d)
                    if(tmp_i > -1 and tmp_i < min_index):
                        min_index = tmp_i
                if(min_index == sys.maxsize):
                    return -1
                else:
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
        #read the vhdl file to break into words
        with open(self._file_path, 'r') as file:
            for line in file.readlines():
                #drop rest of line if comment is started
                comment_start = line.find('--')
                if(comment_start == 0):
                    continue
                elif(comment_start > -1):
                    line = line[:comment_start]

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