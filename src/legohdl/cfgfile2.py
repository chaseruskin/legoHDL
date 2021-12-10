# ------------------------------------------------------------------------------
# Project: legohdl
# Script: cfgfile2.py
# Author: Chase Ruskin
# Description:
#   The CFG/INI file class. It handles reading/writing the custom configuration 
#   files used for settings and blocks.
# ------------------------------------------------------------------------------


class cfg:

    #section tokens
    S_BEGIN = '['
    S_CHILD_DEC = '>['

    S_END = ']'
    S_PARENT_DEC = ']-'

    TAB = ' '*4

    #key/value tokens
    KEY_ASSIGNMENT = '='
    NULL = ''

    #list value tokens
    L_BEGIN = '('
    L_END = ')'
    L_SEP = ','

    @classmethod
    def read(cls, filepath: str, data: dict):
        '''
        Opens the specified file and reads its contents to a dictionary
        according to the spec.

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
        with open(filepath, 'r') as ini:
            lines = ini.readlines()
            for l in lines:
                in_str = next_in_str
                #clean up any comments from the file line
                l, next_in_str = cls._trimComments(l, in_str=in_str)
                #trim off new lines and white space
                l = l.strip()
                #print(next_in_str)

                #add newlines if empty line and within a key's value
                if(len(in_str) and cur_key != None and len(l) == 0):
                    cur_sect[cur_key] = cur_sect[cur_key] + '\n'

                #skip empty lines
                if(len(l) == 0):
                    continue
                
                #check for section
                new_sect, prev_parents, cur_sect = cls._addSection(l, data, prev_parents, cur_sect)
                if(new_sect):
                    continue

                #check for new keys (properties)
                key_l,_ = cls._trimComments(l, in_str=in_str, c_token='=')
                key_l = key_l.strip().lower()

                #find first '='
                v_i = l.find(cls.KEY_ASSIGNMENT)
                
                #skip if not in a valid key (must have a '=' on same line as key declaration)
                if(len(key_l.split()) > 1 or key_l == '=' or v_i <= 0):
                    #else update
                    if(cur_key != None):
                        spacer = ' '
                        #check what the previous status was
                        if(len(in_str)):
                            spacer = '\n'
                        if(len(cur_sect[cur_key]) == 0):
                            spacer = ''
                        cur_sect[cur_key] = cur_sect[cur_key] + spacer + l.strip()
                    continue

                #assign to the key location in the data structure
                cur_sect[key_l] = l[v_i+1:].strip()
                #update which key is the current
                cur_key = key_l

                print(l)
            pass

        return True


    @classmethod
    def _trimComments(cls, line, c_token=';', in_str=''):
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
        #trim off comments
        c = line.find(c_token)
        #continue scanning line to find where a valid comment starts
        while(c > -1 and c in invalid_comments):
            c = line[c+1:].find(c_token)

        if(c > -1):
            line = line[:c]
        return line, in_str


    @classmethod
    def _addSection(cls, line, data, prev_parents, cur_sect):
        '''
        Determines if the current line contains a valid section and adds to the dictionary
        if so. Updates prev_parent if the new section is a parent type.
        
        Parameters:
            line (str): line to parse
            data (dict): dictionary to fill and add new key
            prev_parents ([str]): previous sections that may be stemming from this new section
            cur_sect (dict): current inner-level of data dictionary
        Returns:
            success (bool): if a new section was added
            prev_parents ([str]): the previous parents
        '''
        #skip if invalid beginning tokens
        if(line[0] != cls.S_BEGIN and line.startswith(cls.S_CHILD_DEC) == False):
            return False, prev_parents, cur_sect
        #skip if invalid ending tokens
        if(line[-1] != cls.S_END and line.endswith(cls.S_PARENT_DEC) == False):
            return False, prev_parents, cur_sect

        #find string between section tokens and convert to lower-case
        b_i = line.find('[')
        e_i = line.rfind(']')
        new_key = line[b_i+1:e_i].lower()

        #clear the chain if new node is indicated by not being a child
        if(line.startswith(cls.S_CHILD_DEC) == False):
            prev_parents = []

        #traverse through tree to assign new dictionary
        deeper_data = data
        if(len(prev_parents)):
            deeper_data = data[prev_parents[0]]
            for p in prev_parents[1:]:
                deeper_data = deeper_data[p]

        #create new key (overwrites any existing)
        deeper_data[new_key] = {}

        #continue deeper down the tree
        if(line.endswith(cls.S_PARENT_DEC)):
            prev_parents += [new_key]
            pass
        
        #update current section dictionary
        cur_sect = deeper_data[new_key]

        return True, prev_parents, cur_sect


    @classmethod
    def write(cls, filepath: str, data: dict):

        pass

    
    @classmethod
    def castStr(cls, val, tab_cnt=0, frmt_list=True):
        '''
        Return a string representation of a value.

        Parameters:
            val (*): any dtype value
            tab_cnt (int): number of tabs to place before value
            frmt_list (bool): determine if to use list symbols if val is list
        Returns:
            (str): conversion to string
        '''
        if(val == None):
            return ''
        if(isinstance(val, (int, str, bool))):
            return (tab_cnt*cls.TAB) + str(val)
        if(isinstance(val, list)):
            #add beginning list symbol
            returnee = ''
            if(frmt_list):
                returnee = (tab_cnt*cls.TAB)+cls.L_BEGIN+'\n'
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
                returnee = returnee + '\n'+(tab_cnt*cls.TAB)+cls.L_END
            return returnee


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
        #return empty list
        if(val == cls.NULL):
            return []
        #check if using list tokens
        if(val[0] != cls.L_BEGIN or val[-1] != cls.L_END):
            #return list split by spaces
            return val.split()
        b_i = val.find('(')
        e_i = val.rfind(')')
        elements = val[b_i+1:e_i].strip()
        #separate according to the list separator and trim any trailiing/leading whitespace
        elements = [e.strip() for e in elements.split(cls.L_SEP)]
        #filter out any blank elements
        return list(filter(lambda a: len(a), elements))


    pass


data = {}
cfg.read('./input.cfg', data)
print(data)

req = cfg.castList(data['block']['requires'])

print(cfg.castStr(False))
print(req)
print(cfg.castStr(req, frmt_list=True))