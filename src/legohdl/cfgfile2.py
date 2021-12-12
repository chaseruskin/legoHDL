# ------------------------------------------------------------------------------
# Project: legohdl
# Script: cfgfile2.py
# Author: Chase Ruskin
# Description:
#   The CFG/INI file class. It handles reading/writing the custom configuration 
#   files used for settings and blocks.
# ------------------------------------------------------------------------------

from .map import Map


class Key:

    def __init__(self, name, val):
        self._name = name
        self._val = val

    def __repr__(self):
        return self._val

    pass


class Section(Map):

    def __init__(self, *args, name='', **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name

    pass


class Cfg:

    #section tokens
    S_DELIM = '.'

    S_BEGIN = '['
    S_CHILD_DEC = '['+S_DELIM

    S_END = ']'
    S_PARENT_DEC = S_DELIM+']'

    TAB = ' '*4

    #key/value tokens
    KEY_ASSIGNMENT = '='
    NULL = ''

    #list value tokens
    L_BEGIN = '('
    L_END = ')'
    L_SEP = ','

    #instance checking
    SECT = (dict, Section)


    def __init__(self, filepath, data=Section(), comments=Section(), en_mult_lvl=True):
        '''
        Create a CFG file object.

        The _data attr stores all values as str and uses lower-case names
        for sections/keys.

        Parameters:
            filepath (str): path to the cfg file
            data (dict): initial data contents
            comments (dict): optional comments for each data section/key (single-level)
            en_mult_lvl (bool): determine if to nest sections
        Returns:    
            None
        '''
        self._filepath = filepath
        self._data = data
        self._comments = comments
        self._multi_level = en_mult_lvl
        pass


    def read(self):
        '''
        Opens the specified file and reads its contents to a dictionary
        according to the spec. Loads the _data attribute

        Parameters:
            filepath (str): path to the cfg file
            data (dict): data dictionary object to fill
        Returns:
            None
        '''
        in_str = ''
        next_in_str = ''
        prev_parents = []
        cur_sect = {}
        cur_key = None
        #open the file
        with open(self._filepath, 'r') as ini:
            lines = ini.readlines()
            for l in lines:
                in_str = next_in_str
                #clean up any comments from the file line
                l, next_in_str = self._trimComments(l, in_str=in_str)
                #trim off new lines and white space
                l = l.strip()
                #print(next_in_str)

                #add newlines if empty line and within a key's value
                if(len(in_str) and cur_key != None and len(l) == 0):
                    cur_sect[cur_key]._val = cur_sect[cur_key]._val + '\n'

                #skip empty lines
                if(len(l) == 0):
                    continue
                
                #check for section
                new_sect, prev_parents, cur_sect = self._addSection(l, prev_parents, cur_sect)
                if(new_sect):
                    continue

                #check for new keys (properties)
                key_l,_ = self._trimComments(l, in_str=in_str, c_token='=')
                key_true = key_l.strip()
                key_l = key_l.strip().lower()

                #find first '='
                v_i = l.find(Cfg.KEY_ASSIGNMENT)
                
                #skip if not in a valid key (must have a '=' on same line as key declaration)
                if(len(key_l.split()) > 1 or key_l == Cfg.KEY_ASSIGNMENT or v_i <= 0):
                    #else update
                    if(cur_key != None):
                        spacer = ' '
                        #check what the previous status was
                        if(len(in_str)):
                            spacer = '\n'
                        if(len(cur_sect[cur_key]._val) == 0):
                            spacer = ''
                        cur_sect[cur_key]._val = cur_sect[cur_key]._val + spacer + l.strip()
                    continue

                #assign to the key location in the data structure (and expand tabs)
                cur_sect[key_l] = Key(key_true, l[v_i+1:].strip().replace('\t', Cfg.TAB))
                #update which key is the current
                cur_key = key_l

                print(l)
            pass

        return True


    def get(self, key, dtype=str, returnkey=False):
        '''
        Returns the value behind the given key. 
        
        Each key is converted to lower-case for comparison. Returns None if DNE.
        Will return a copy of dictionary level if not enough components were given for
        key (dtype must be set to dict to avoid None return). An empty key
        will return the entire _data attr.

        Parameters:
            key (str): sections/keys to traverse dictionary separated by delimiter
            returnkey (bool): determine if to return just the str or Key object
        Returns:
            (dtype): str, int, bool, list or
            (Key) : true key name and its converted datatype
        '''
        #split key into components
        keys = [k.lower() for k in key.split(Cfg.S_DELIM)]

        #traverse through the dictionary structure to the requested key
        node = self._data
        #verify an empty key was not entered
        if(keys != ['']):
            for k in keys:
                if(isinstance(node, Cfg.SECT) and k in node.keys()):
                    node = node[k]
                else:
                    return None
        #if the end result is still a dictionary then return None
        if(isinstance(node, Cfg.SECT)):
            if(dtype == dict or dtype == Section):
                cp = Section(name=node._name)
                for k in node.keys():
                    cp[k] = self.get(key+'.'+k, dtype=dict, returnkey=returnkey)
                return cp
            else:
                return None

        true_key = node._name
        node = node._val

        #perform proper cast
        if(dtype == bool):
            val = Cfg.castBool(node)
        elif(dtype == int):
            val = Cfg.castInt(node)
        elif(dtype == list):
            val = Cfg.castList(node)
        #default is to return str
        else:
            val = str(node)

        #return Key object with its value (converted) and true name
        if(returnkey):
            return Key(true_key, val)
        #return just the converted value
        return val


    def set(self, key, val, override=True):
        '''
        Writes the value behind the given key. Each key is converted to lower-case
        for comparison. Will make new key if DNE.

        Will only overwrite a dictionary if val is a dtype dict and override is True.
        Copies contents of dictionary to store.

        Parameters:
            key (str): sections/keys to traverse dictionary separated by delimiter
            val (any): any datatype value to be converted to string for dictionary entry
            override (bool): determine if to override existing value if key exists
        Returns:
            None
        '''
        #split key into components as lower-case
        keys = [k.lower() for k in key.split(Cfg.S_DELIM)]
        true_key = key.split(Cfg.S_DELIM)[-1]

        #traverse through the dictionary structure to the requested key
        node = self._data
        for k in keys[:len(keys)-1]:
            if(isinstance(node, Cfg.SECT)):
                if(k not in node.keys()):
                    node[k] = Section(name=k)
                node = node[k]
            else:
                return

        #if the end result is not a dictionary then return None
        if(isinstance(node, Cfg.SECT) == False):
            return

        #do not override the exisiting value if the key already exists
        if(override == False and keys[-1] in node.keys()):
            return

        #overwrite entire dictionary and copy if val is a dtype dict
        if(isinstance(val, Cfg.SECT)):
            #recursive call
            for k in val.keys():
                self.set(key+'.'+k, val[k], override=True)
        #write new value as string
        else:
            node[keys[-1]] = Key(true_key, Cfg.castStr(val))
        pass


    def write(self, f=None, data=None, lvl=0, cur_key='', auto_indent=True, neat_keys=True):
        '''
        Saves the _data attr to a .cfg file.

        Parameters:
            None
        Returns:
            None 
        '''
        if(f == None):
            f = self._filepath
        if(data == None):
            data = self._data

        contents = ''
        #compute number of spaces for nice formatting
        T = Cfg.TAB*int(lvl)*int(auto_indent)

        #compute longest key name
        keys = list(filter(lambda a: isinstance(data[a], Cfg.SECT) == False, list(data.keys())))
        longest_key = 0
        for k in keys:
            longest_key = len(k) if(len(k) > longest_key) else longest_key

        #traverse through the data
        for sect in list(data.keys()):
            #write comments for the section or key
            next_cur_key = cur_key+'.'+sect
            if(len(cur_key) == 0):
                next_cur_key = sect

            cmt = self._writeComment(next_cur_key, newline=T+'; ')
            #write a new line if comment exists for a section
            if((lvl != 0 or len(contents) or ('' in self._comments.keys())) and isinstance(data[sect], Cfg.SECT)):
                contents = contents + '\n'
            #write the comment (will be blank if not found)
            contents = contents + cmt

            #write section
            if(isinstance(data[sect], Cfg.SECT)):
                contents = contents + T
                if(lvl > 0):
                    contents = contents + Cfg.S_CHILD_DEC
                else:
                    contents = contents + Cfg.S_BEGIN
                print(type(data[sect]))
                print(data[sect]._name)
                contents = contents + data[sect]._name +Cfg.S_END+'\n'

                #recursive call to proceed into the nested section
                contents = contents + self.write(f, data[sect], lvl=(lvl+1), cur_key=next_cur_key, auto_indent=auto_indent, neat_keys=neat_keys)
                continue
            #write the key/value pair
            print(data[sect]._name,data[sect])
            #write extra spacing for key assignments to align if trying to be neat
            diff = (longest_key+1)-len(sect)
            diff = diff if(neat_keys) else 1
            spacer = len(T) + len(sect) + diff + len(Cfg.KEY_ASSIGNMENT) + 1
            #write "<key> = "
            key_var = data[sect]._name + ' '*diff + Cfg.KEY_ASSIGNMENT + ' '
            #obtain the string value
            val = data[sect]._val
            #check if it is a list hidden in dtype str
            is_list = (len(val) > 1 and val[0] == Cfg.L_BEGIN and val[-1] == Cfg.L_END)
            #determine number of spaces for a new line if rolling over text
            if(is_list or neat_keys == False):
                spacer = 0
            #write the value
            contents = contents + self._writeWithRollOver(T+key_var+val,newline=' '*spacer)+'\n'
            pass

        if(lvl != 0):
            return contents

        with open(f, 'w') as ini:
            contents = self._writeComment(cur_key) + contents
            ini.write(contents)

        pass


    def _writeComment(self, key, newline='; '):
        key = key.lower()
        if(key not in self._comments.keys()):
            return ''
        print(newline)
        
        cmt = newline+self._comments[key].replace('\t', Cfg.TAB)
        return self._writeWithRollOver(cmt, newline=newline)+'\n'

    
    def _writeWithRollOver(self, txt, newline='', limit=80):
        '''
        Formats text in a clean fashion without splitting words when crossing a
        newline. Breaks a string into sections split by newlines no greater than
        length 'limit'.

        Parameters:
            txt (str):
            newline (str):
            limit (int):
        Returns:
            frmt_txt (str):
        '''
        frmt_txt = ''
        #use real limit after first line
        real_limit = limit-len(newline)

        #chop up words
        while(len(txt)):
            next_line = txt[:limit]

            entr = next_line.find('\n')
            if(entr > -1 and entr <= limit):
                #print(next_line)
                limit = entr
                next_line = txt[:limit]
                txt = next_line + ' ' + txt[limit+1:]
            else:
                #check if in middle of a word (lhs)
                if(len(txt) > limit-1 and txt[limit-1] != ' '):
                    #check if next character is a space (rhs)
                    if(len(txt) > limit and txt[limit] != ' '):
                        crsr = limit-1
                        #find closest previous space
                        sp_i = next_line.find(' ')
                        #backtrack
                        if(sp_i > -1):
                            while(crsr > 0 and txt[crsr] != ' '):
                                crsr -= 1
                        #forward track
                        else:
                            while(crsr < len(txt) and txt[crsr] != ' '):
                                crsr += 1
                        limit = crsr
                    pass
            if(limit < 1):
                limit = 1
            #add newly formatted line
            frmt_txt = frmt_txt + txt[:limit]
            #add newline characters
            if(limit < len(txt)):
                frmt_txt = frmt_txt + '\n'+newline

            if(limit < len(txt)-1 and (txt[limit] == ' ' or txt[limit] == '\n')):
                limit = limit+1
            #shrink the remaining text left to format
            txt = txt[limit:]
            #print(txt)
            #return to the actual limit
            limit = real_limit
            pass

        #print(frmt_txt)
        return frmt_txt


    @classmethod
    def castStr(cls, val, tab_cnt=0, frmt_list=True):
        '''
        Return a string representation of a value.

        Parameters:
            val (any): any dtype value
            tab_cnt (int): number of tabs to place before value
            frmt_list (bool): determine if to use list symbols if val is list
        Returns:
            (str): conversion to string
        '''
        #get the str if a Key object was passed in
        if(isinstance(val, Key)):
            val = val._val
        #return blank string if None
        if(val == None):
            return ''

        hanging_end = False
        #make sure tab is never negative
        if(tab_cnt < 0):
            tab_cnt = 0

        #cast with built-in conversion
        if(isinstance(val, (int, str, bool))):
            return (tab_cnt*cls.TAB) + str(val)

        #cast using special string conversion format
        if(isinstance(val, list)):
            #add beginning list symbol
            returnee = ''
            if(frmt_list):
                returnee = cls.L_BEGIN+'\n'

            #iterate through every value and add as a string
            for x in val:
                returnee = returnee + cls.castStr(x, (tab_cnt+1)*(frmt_list))
                if(x != val[-1]):
                    if(frmt_list):
                        returnee = returnee+cls.L_SEP+'\n'
                    else:
                        returnee = returnee+' '
                pass

            #close the list with ending list symbol
            if(frmt_list):
                #drop closing list symbol onto newline
                if(hanging_end):
                    returnee = returnee + '\n'+(tab_cnt*cls.TAB)
                returnee = returnee + cls.L_END

            return returnee

        #default blank string
        return ''


    @classmethod
    def castBool(cls, val):
        '''
        Return boolean converted from string data type.

        Parameters:
            val (str): string to cast to boolean from a key's value
        Returns:
            (bool): str_val determined as a boolean type

        Accepted true cases are: 'true', '!=0', 'yes', 'on', 'enable'. All others
        will return false.
        '''
        if(isinstance(val, bool)):
            return val
        val = val.lower()
        return (val == 'true' or (val.isdigit() and val != '0') or 
                val == 'yes' or val == 'on' or val == 'enable')
    

    @classmethod
    def castNone(cls, val):
        '''
        Return if string is of type None (an empty ''), else return string.

        Parameters:
            val (str): a key's value
        Returns
            None if `val` == '' else returns `val` unmodified
        '''
        if(val == cls.NULL):
            return None
        else:
            return val


    @classmethod
    def castInt(cls, val):
        '''
        Return integer if string is an integer, else return 0.

        Parameters:
            val (str): a key's value
        Returns
            (int): value converted to type integer
        '''
        if(isinstance(val, int)):
            return val
        #handle negative sign by multiplying by -1
        mult = 1
        if(len(val) and val[0] == '-'):
            mult = -1
            val = val[1:]
        if(val.isdigit()):
            return int(val)*mult
        else:
            return 0


    @classmethod
    def castList(cls, val):
        '''
        Return the value broken up as a list. 
        
        If uses list tokens, it will be broken up according to list seperators. 
        If it is a regular string, it will be broken up by spaces. An empty string
        will return an empty list.

        Parameters:
            val (str): a key's value
        Returns:
            [(str)] : list of strings divided from val
        '''
        if(isinstance(val, Key)):
            val = val._val
        #return empty list
        if(val == Cfg.NULL or val == None):
            return []

        #replace square brackets with new smooth brackets
        if(val[0] == '['):
            val = Cfg.L_BEGIN + val[1:]
        if(val[-1] == ']'):
            val = val[:len(val)-1] + Cfg.L_END

        #check if using list tokens
        if(val[0] != Cfg.L_BEGIN or val[-1] != Cfg.L_END):
            #return list split by spaces
            return val.split()

        #trim off list tokens
        b_i = val.find(Cfg.L_BEGIN)
        e_i = val.rfind(Cfg.L_END)
        elements = val[b_i+1:e_i].strip()

        #separate according to the list separator and trim any trailiing/leading whitespace
        elements = [e.strip() for e in elements.split(Cfg.L_SEP)]
        #filter out any blank elements
        return list(filter(lambda a: len(a), elements))


    def _trimComments(self, line, c_token=';', in_str=''):
        '''
        Finds valid comments (outside of strings) and returns
        the trimmed version of a line from a cfg file.
        
        Parameters:
            line (str): line to parse
            c_token (chr): character that is a comment symbol
            in_str (chr): determine if to start off inside a string or not (the quote character)
        Returns:
            short_line (str): line without comments
            in_str (bool): if the next line will be within a string
        '''
        #store where invalid comments are in the line
        invalid_comments = []

        for i in range(len(line)):
            #grab current character
            ch = line[i]
            #toggle upon encountering a quote
            if((ch == '\'' or ch == '\"') and not len(in_str)):
                in_str = ch
            elif(len(in_str) and ch == in_str):
                in_str = ''
            elif(len(in_str) and ch == c_token):
                invalid_comments += [i]
            pass

        #trim off comments
        c = line.find(c_token)
        #continue scanning line to find where a valid comment starts
        while(c > -1 and c in invalid_comments):
            c = line[c+1:].find(c_token)

        if(c > -1):
            line = line[:c]
        return line, in_str


    def _addSection(self, line, prev_parents, cur_sect):
        '''
        Determines if the current line contains a valid section and adds to the dictionary
        if so. Updates prev_parent if the new section is a parent type.
        
        Parameters:
            line (str): line to parse
            prev_parents ([str]): previous sections that may be stemming from this new section
            cur_sect (dict): current inner-level of data dictionary
        Returns:
            success (bool): if a new section was added
            prev_parents ([str]): the previous parents
        '''
        #skip if invalid beginning tokens
        if(line[0] != Cfg.S_BEGIN and line.startswith(Cfg.S_CHILD_DEC) == False):
            return False, prev_parents, cur_sect
        #skip if invalid ending tokens
        if(line[-1] != Cfg.S_END and line.endswith(Cfg.S_PARENT_DEC) == False):
            return False, prev_parents, cur_sect

        #find string between section tokens and convert to lower-case

        b_i = line.find(Cfg.S_BEGIN)
        #trim scope operator from beginning
        b_i = b_i+1 if(line[:b_i+2] == Cfg.S_CHILD_DEC) else b_i

        e_i = line.rfind(Cfg.S_END)
        #trim scope operator from end
        e_i = e_i-1 if(line[e_i-1:] == Cfg.S_PARENT_DEC) else e_i

        true_key = line[b_i+1:e_i]
        new_key = true_key.lower()

        #clear the chain if new node is indicated by not being a child
        if((line.startswith(Cfg.S_CHILD_DEC) == False) or (self._multi_level == False)):
            prev_parents = []

        #traverse through tree to assign new dictionary
        nested_data = self._data
        if(len(prev_parents)):
            nested_data = self._data[prev_parents[0]]
            for p in prev_parents[1:]:
                nested_data = nested_data[p]

        #create new key (overwrites any existing)
        nested_data[new_key] = Section(name=true_key)

        #continue deeper down the tree
        if(line.endswith(Cfg.S_PARENT_DEC) or (line.startswith(Cfg.S_CHILD_DEC) == False)):
            prev_parents += [new_key]
            pass
        
        #update current section dictionary
        cur_sect = nested_data[new_key]

        return True, prev_parents, cur_sect


    pass