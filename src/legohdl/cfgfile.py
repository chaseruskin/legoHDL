# Project: legohdl
# Script: cfgfile.py
# Author: Chase Ruskin
# Description:
#   This script handles reading/writing the custom configuration files used
#   for settings and blocks.

import logging as log


class CfgFile:

    COMMENT = ';','#'
    SPACES = ' '*4
    TAB = '\t'
    QUOTES = '\'\"'

    HEADER = '[]'
    VAR = '='
    LIST = '[]'
    NULL = ''

    NEAT = True


    @classmethod
    def load(cls, datafile, ignore_depth=False):
        '''
        Load the items from cfg file into a dictionary.

        Parameters:
            datafile (file): a python file object written in cfg
            ignore_depth (bool): all headers are seen at first level and each variable 
            is assigned to previous header
        Returns:
            (dict): multi-level dictionary of items from cfg file
        '''


        def tunnel(mp, key, scope_stack, data=None):
            '''
            Recursively tracks through a dictionary to get to correct scope level.

            Parameters:
                mp (dict): the dictionary to add key/val pair to
                key (str): new key to be added within correct scope
                scope_stack ([str]): list of existing keys to traverse
                data (*): any value; if None then a {} will be added as value
            Returns:
                mp (dict): the dictionary with new key/val pair
            '''
            if(len(scope_stack)):
                nxt = scope_stack[0]
                mp[nxt] = tunnel(mp[nxt], key, scope_stack[1:], data)
            else:
                if(data != None):
                    #store value                   
                    mp[key] = data
                #create new dictionary level
                else:
                    mp[key] = {}
            return mp


        def collectList(cnt, val, tmp):
            '''
            Parse through an assigned list. Returns the bracket count and
            running list variable.

            Parameters:
                val (str):
                tmp (str):
            Returns:
                cnt (int):
                tmp (str):
            '''
            cnt += val.count(cls.LIST[0]) - val.count(cls.LIST[1])
            val = val.replace(cls.LIST[0],'').replace(cls.LIST[1],'')
            items = val.split(',')
            for i in items:
                if(len(i)):
                    tmp += [i]
            return cnt, tmp

        #dictionary to fill and return as end result
        mapp = dict()

        scope = [] # stores levels of scope keys for map dictionary
        tmp = [] # temporary list used to store an assigned list
        line_cnt = 0 # track the current line being read
        bracket_cnt = 0 # count if we are inside a list
        in_quote = False # stay in assignment if in quote
        #store the last variable's name and value
        last_var = {'key' : None, 'val' : None} 

        #read each line
        lines = datafile.readlines()
        for line in lines:
            line_cnt += 1

            #trim line from comment markers
            for C in cls.COMMENT:
                if(line.count(C) and in_quote == False):
                    #trim line only if before a quote
                    c_i = line.find(C)
                    q1_i = line.find(cls.QUOTES[0])
                    q2_i = line.find(cls.QUOTES[1])
                    if((q1_i == -1 or c_i < q1_i) and (q2_i == -1 or c_i < q2_i)):
                        line = line[:line.find(C)]
            pass
            #skip blank lines
            if(len(line.strip()) == 0):
                continue
            
            #determine how far in scope by # of 4-space groups
            c = line[0]
            lvl = 0
            tabs = 0
            while c == ' ' or c == cls.TAB:
                if(c == cls.TAB):
                    tabs += 1
                lvl += 1
                c = line[lvl]
            #divide number of spaces by its length (4) and add every tab
            lvl = int((lvl-tabs)/len(cls.SPACES))+tabs

            #identify headers
            if(not in_quote and line.strip().startswith(cls.HEADER[0]) and line.strip().endswith(cls.HEADER[1])):
                #every header is 1-deep if ignore scopes
                if(ignore_depth):
                    lvl = 0
                
                key = line.strip()[1:len(line.strip())-1]
                #pop off scopes
                scope = scope[0:lvl]
                    
                #create new dictionary spot scoped to specific location
                mapp = tunnel(mapp, key, scope)
                #append to scope
                scope.append(key)
                continue

            #identify assignments
            sep = line.find(cls.VAR)
            if(sep > -1):
                key = line[:sep].strip()
                #strip excessive whitespaces
                value = line[sep+1:].strip()
                #update if we are in quotes
                in_quote = in_quote ^ (value.count(cls.QUOTES[0]) + value.count(cls.QUOTES[1])) % 2 == 1

                if(ignore_depth and len(scope)):
                    lvl = 1

                #update what scope the assignment is located in
                scope = scope[0:lvl]

                #determine if its a list
                if(value.startswith(cls.LIST[0])):
                    tmp = []
                    bracket_cnt, tmp = collectList(bracket_cnt, value, tmp)
                else:
                    tmp = value
                #finalize into dictionary
                if(bracket_cnt == 0):
                    value = tmp
                    #print(value)
                    last_var['key'] = key
                    last_var['val'] = value
                    mapp = tunnel(mapp, key, scope, value)
                    
            elif(bracket_cnt):
                #strip excessive whitespae and quotes
                value = line.strip()
                #update if we are in quotes
                in_quote = in_quote ^ (value.count(cls.QUOTES[0]) + value.count(cls.QUOTES[1])) % 2 == 1
                #update the bracket count and other temporary value for the current variable
                bracket_cnt, tmp = collectList(bracket_cnt, value, tmp)
                #finalize into dictionary
                if(bracket_cnt == 0):
                    value = tmp
                    mapp = tunnel(mapp, key, scope, value)
            #evaluate if no '=' sign is on this line and not a header line
            elif(last_var['key'] != None):
                #extended line string
                ext_value = line.strip()
                if(len(ext_value)):
                    in_quote = in_quote ^ (ext_value.count(cls.QUOTES[0]) + ext_value.count(cls.QUOTES[1])) % 2 == 1
                    #automatically insert space between the different lines
                    last_var['val'] = last_var['val'] + ' ' +ext_value
                    mapp = tunnel(mapp, last_var['key'], scope, last_var['val'])
            else:
                exit(log.error("Syntax: Line "+str(line_cnt)))

        return mapp


    @classmethod
    def save(cls, data, datafile, comments=dict(), ignore_depth=False, space_headers=False):
        '''
        Write dictionary to data file in cfg format.

        Parameters:
            data (dict): a multi-level python dictionary object
            datafile (file): a python file object to be written in cfg format
            comments (dict): a dictionary of strings where the keys are headers with pipes for scopes and 
            the comments will be placed before that header/assignment
            ignore_depth (bool): ignores tabs and assumes each variable is one level within headers
            space_headers (bool): determine if to write newlines for subsequent headers
        Returns:
            (bool): true if save was successful
        '''
        another_header = False


        def write_comment(scoped_list, spacing, isHeader):
            '''Write additional comments above a header or field.'''
            #generate the key from the scoped list input
            key = ''
            for i in scoped_list:
                key = key + i
                if(i != scoped_list[-1]):
                    key = key + '|'
                pass
            #find the key in the given comments dictionary
            if(key.lower() in comments):
                val = comments[key.lower()]
                # add proper indentation for the said comment
                if((val[0] == cls.HEADER and isHeader) or \
                    (val[0] == cls.VAR and not isHeader)):
                    lines = val[1].split('\n')
                    for l in lines:
                        datafile.write(spacing+l+"\n")
                pass
            pass
        

        def write_dictionary(mp, lvl=0, l_len=0, scope=[]):
            nonlocal another_header
            #determine proper indentation
            indent = cls.TAB*lvl
            #do not indent if ignoring depth
            if(ignore_depth):
                indent = ''
            if(isinstance(mp, dict)):
                for k in mp.keys():
                    isHeader = isinstance(mp[k], dict)
                    #write helpful comments if available
                    write_comment(scope+[k], indent, isHeader)
                    #write a header
                    if(isHeader):
                        scope += [k.lower()]
                        #write a separating new-line
                        if(another_header and space_headers):
                            datafile.write('\n')
                        datafile.write(indent+cls.HEADER[0]+k+cls.HEADER[1]+'\n')
                        another_header = True
                    #write the beginning of an assignment
                    else:
                        #get all field names for this current scope
                        fields = cls.getAllFields(data, scope=scope)

                        #compute the longest distance length word
                        dist = len(fields[0])
                        for f in fields[1:]:
                            if(len(f) > dist):
                                dist = len(f)
  
                        #provide nice spacing and aligning of VAR ('=')
                        var_assign = indent+k+((dist-len(k)+1)*' ')+cls.VAR+' '
                        #pass the current line length to the next value
                        l_len = len(var_assign)

                        datafile.write(var_assign)
                    #recursively proceed to next level
                    write_dictionary(mp[k], lvl+1, l_len, scope)
                    #pop off value that was recursively passed to the method
                    if(isHeader):
                        scope.pop()
            #write a value (rhs of assignment)
            else:
                #if its a list, use brackets
                if(isinstance(mp, list)):
                    if(len(mp)):
                        #write beginning of list
                        datafile.write(cls.LIST[0]+'\n')
                        #indent lists by 1 tab in ignore depth
                        if(ignore_depth):
                            indent = cls.TAB
                        #write items of the list
                        for i in mp:
                            datafile.write(indent+i+',\n')
                        #ensure closing bracket is farthest left
                        if(ignore_depth or lvl == 0):
                            lvl = 1
                        #close off the list
                        datafile.write(cls.TAB*(lvl-1)+cls.LIST[1]+'\n')
                    #write empty list
                    else:
                        datafile.write(cls.LIST+'\n')
                #else, store value directly as is
                else:
                    #ensure mp is a string type to write
                    mp = '' if(mp == None) else mp
                    mp = str(mp)
                    
                    #try to write the value in a 'nice' format
                    if(cls.NEAT):
                        #write over to new line on overflow (exceed 80 chars)
                        cursor = 0
                        first_word = True
                        words = mp.split()
                        for w in words:
                            if(first_word):
                                datafile.write(w+' ')
                            cursor += len(w+' ')
                            #evaluate before writing
                            if(cursor+l_len >= 80):
                                datafile.write('\n')
                                datafile.write(' '*l_len)
                                cursor = 0
                            if(not first_word):
                                datafile.write(w+' ')
                            
                            first_word = (cursor == 0)

                        if(cursor != 0 or len(mp) == 0):
                            datafile.write('\n')
                            pass
                    #write the value as-is
                    else:
                        datafile.write(mp+'\n')
            pass

        #recursively call method to write all dictionary key/values
        write_dictionary(data)
        return True


    @classmethod
    def castBool(cls, str_val):
        '''
        Return boolean converted from string data type.

        Parameters:
            str_val (str): string to cast to boolean
        Returns:
            (bool): str_val determined as a boolean type

        Accepted true cases are: 'true', '!=0', 'yes', 'on', 'enable'. All others
        will return false.
        '''
        if(isinstance(str_val, bool)):
            return str_val
        str_val = str_val.lower()
        return (str_val == 'true' or (str_val.isdigit() and str_val != '0') or 
                str_val == 'yes' or str_val == 'on' or str_val == 'enable')
    

    @classmethod
    def castNone(cls, str_blank):
        '''
        Return if string is of type None (empty ''), else return string.

        Parameters:
            str_blank (str):
        Returns
            None if `str_blank` == '' else returns `str_blank` unmodified
        '''
        if(str_blank == cls.NULL):
            return None
        else:
            return str_blank


    @classmethod
    def castInt(cls, str_int):
        '''
        Return integer if string is an integer, else return 0.

        Parameters:
            str_int (str):
        Returns
            (int):
        '''
        if(isinstance(str_int, int)):
            return str_int
        mult = 1
        if(len(str_int) and str_int[0] == '-'):
            mult = -1
            str_int = str_int[1:]
        if(str_int.isdigit()):
            return int(str_int)*mult
        else:
            return 0


    @classmethod
    def getAllFields(cls, data, scope=[]):
        '''
        Returns a list of all field names found within the dictionary, regardless
        of scope.

        If 'scope' is passed, it will look for down into that header trail's fields.

        Parameters:
            data (dict): python dictionary object
            scope ([str]): a list of headers to scope down-to for filtering fields (lower-case)
        Returns:
            ([str]): list of all field names (keys, even within scopes)
        '''


        def fieldSearch(mapp, fields=[], scope=[]):
            for k in mapp.keys():
                if(isinstance(mapp[k], dict)):
                    if((len(scope) == 0 or k.lower() in scope)):
                        fields = fieldSearch(mapp=mapp[k],fields=fields,scope=scope)
                else:
                    fields += [k]
            return fields


        return fieldSearch(data, scope=scope)


    pass