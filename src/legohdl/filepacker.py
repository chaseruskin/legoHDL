################################################################################
#   Project: legohdl
#   Script: filepacker.py
#   Author: Chase Ruskin
#   Description:
#       This script handles reading/writing the custom properties files used
#   for settings and blocks.
################################################################################

import logging as log

class Filepacker:

    COMMENT = ';','#'
    TAB = ' '*4

    HEADER = '[]'
    VAR = '='
    LIST = '[]'

    @classmethod
    def load(cls, datafile):
        '''
        Return the python dictionary of all key/value pairs.

        Parameters
        ---
        datafile : a python file object
        '''
        map = dict()

        def tunnel(mp, key, scope_stack, data=None):
            '''
            Tracks through a dictionary to get to correct scope level.
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
            '''
            cnt += val.count(cls.LIST[0]) - val.count(cls.LIST[1])
            val = val.replace(cls.LIST[0],'').replace(cls.LIST[1],'')
            items = val.split(',')
            for i in items:
                if(len(i)):
                    tmp += [i]
            return cnt, tmp

        scope = [] # stores levels of scope keys for map dictionary
        tmp = [] # temporary list used to store an assigned list
        line_cnt = 0 # track the current line being read
        bracket_cnt = 0 # count if we are inside a list
        lines = datafile.readlines()
        for line in lines:
            line_cnt += 1
            #trim line from comment markers
            for C in cls.COMMENT:
                if(line.count(C)):
                    line = line[:line.find(C)]
            pass
            #skip blank lines
            if(len(line.strip()) == 0):
                continue
            
            #determine how far in scope by # of 4-space groups
            c = line[0]
            lvl = 0
            while c == ' ':
                lvl += 1
                c = line[lvl]
            lvl = int(lvl/len(cls.TAB))

            #identify headers
            if(line.strip().startswith(cls.HEADER[0]) and line.strip().endswith(cls.HEADER[1])):
                key = line.strip()[1:len(line.strip())-1]
                
                #pop off scopes
                scope = scope[0:lvl]
                    
                #create new dictionary spot scoped to specific location
                map = tunnel(map, key, scope)
                #append to scope
                scope.append(key)
                continue

            #identify assignments
            sep = line.find(cls.VAR)
            if(sep > -1):
                key = line[:sep].strip()
                #strip excessive whitespace
                value = line[sep+1:].strip()

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
                    map = tunnel(map, key, scope, value)
                    
            elif(bracket_cnt):
                value = line.strip()
                bracket_cnt, tmp = collectList(bracket_cnt, value, tmp)
                #finalize into dictionary
                if(bracket_cnt == 0):
                    value = tmp
                    map = tunnel(map, key, scope, value)
            else:
                exit(log.error("Syntax: Line "+str(line_cnt)))

        return map

    @classmethod
    def save(cls, data, datafile, comments={}):
        '''
        Write python dictionary to data file.

        Parameters:
        ---
        data : a python dictionary object
        datafile : a python file object
        comments : a dictionary of strings where the keys are headers where
                   the comments will be placed before that header/assignment
        '''
        def write_comment(c_str, spacing, isHeader):
            # add proper indentation for the said comment
            if((c_str[0] == Filepacker.HEADER and isHeader) or 
                (c_str[0] == Filepacker.VAR and not isHeader)):
                lines = c_str[1].split('\n')
                for l in lines:
                    datafile.write(spacing+l+"\n")

        def write_dictionary(mp, lvl=0):
            #determine proper indentation
            indent = cls.TAB*lvl
            if(isinstance(mp, dict)):
                for k in mp.keys():
                    isHeader = isinstance(mp[k], dict)
                    #write helpful comments if available
                    if(k in comments.keys()):
                        write_comment(comments[k], indent, isHeader)
                    #write a header
                    if(isHeader):
                        datafile.write(indent+cls.HEADER[0]+k+cls.HEADER[1]+'\n')
                    #write the beginning of an assignment
                    else:
                        datafile.write(indent+k+' '+cls.VAR+' ')
                    #recursively proceed to next level
                    write_dictionary(mp[k], lvl+1)
            #write a value (rhs of assignment)
            else:
                #if its a list, use brackets
                if(isinstance(mp, list)):
                    if(len(mp)):
                        #write beginning of list
                        datafile.write(cls.LIST[0]+'\n')
                        #write items of the list
                        for i in mp:
                            datafile.write(indent+i+',\n')
                        #close off the list
                        datafile.write(cls.TAB*(lvl-1)+cls.LIST[1]+'\n')
                    #write empty list
                    else:
                        datafile.write(cls.LIST+'\n')
                #else, store value directly as is
                else:
                    datafile.write(mp+'\n')
        
        #recursively call method to write all dictionary key/values
        write_dictionary(data)

        return True

    pass

c = {}

c['active-workspace'] = (Filepacker.VAR,\
'''
; description:
;   What workspace listed under [workspace] currently being used.
;   If an empty assignment, a lot of functionality will be unavailable.
; value: 
;   string''')

c['general'] = (Filepacker.HEADER,\
'''; ---
; settings.dat
; ---
; description:
;   A properties file to manually configure the packaging and development tool.
; help:
;   For more information, read the documentation at ___.

; --- General settings ---
; description:
;   Various assignments related to the tool in general.''')

c['author'] = (Filepacker.VAR,\
'''
; description:
;   Your name! (or code-name, code-names are cool too)
; value: 
;   string''')

c['label'] = (Filepacker.HEADER,\
'''
; --- Label settings ---
; description:
;   User-defined groupings of filetypes, to be collected and written to the
;   recipe file on export. Labels help bridge a custom workflow with the user's
;   backend tool.''')

c['script'] = (Filepacker.HEADER,\
'''
; --- Script settings ---
; description:
;   User-defined aliases to execute backend scripts/tools. Assignments can
;   be either a string or list of strings separated by commas.
; value:
;   assignments of string''')

c['workspace'] = (Filepacker.HEADER,\
'''
; --- Workspace settings ---
; description:
;   User-defined spaces for working with blocks. Blocks must appear in the 
;   workspace's path to be recognized as downloaded. Multiple markets can be
;   configured to one workspace and markets can be shared across workspaces.
;   Block downloads and installations in one workspace are separate from those 
;   of another workspace.
; value:
;   headers with 'path' assignment of string and 'market' assignment of list 
;   of strings''')

c['market'] = (Filepacker.HEADER,\
'''
; --- Market settings ---
; description:
;   The list of available markets to be connected to workspaces. A market allows
;   blocks to be visible from remote repositories and downloaded/installed 
;   across machines. If a market is not configured to a remote repository, its
;   assignment is empty.
; value:
;   assignments of string''')

c['recursive'] = (Filepacker.HEADER,\
'''
; description:
;   Find these files throughout all blocks used in the current design.
; value:
;   assignments of string''')

c['shallow'] = (Filepacker.HEADER,\
'''
; description:
;   Find these files only throughout the current block.
; value:
;   assignments of string''')

data = None
with open('./settings.properties','r') as f:
    dat = Filepacker.load(f)

with open('./tmp.properties','w') as f:
    Filepacker.save(dat, f, c)