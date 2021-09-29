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

    COMMENT = ';'
    TAB = ' '*4

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
            cnt += val.count('[') - val.count(']')
            val = val.replace('[','').replace(']','')
            items = val.split(',')
            for i in items:
                if(len(i)):
                    tmp += [i]
            return cnt, tmp

        scope = [] # stores levels of scope keys for map dictionary
        tmp = [] # temporary list used to store an assigned list
        line_cnt = 0 # track the current line being read
        bracket_cnt = 0 # count if we are inside a list
        lvl = 0 # count how far in scope we are

        lines = datafile.readlines()
        for line in lines:
            line_cnt += 1
            #trim line from comment marker
            if(line.count(cls.COMMENT)):
                line = line[:line.find(cls.COMMENT)]
            pass
            #skip blank lines
            if(len(line.strip()) == 0):
                continue
            
            #determine how far in scope by # of 4-space groups
            c = line[0]
            line_lvl = 0
            while c == ' ':
                line_lvl += 1
                c = line[line_lvl]
            line_lvl = int(line_lvl/len(cls.TAB))

            #identify headers
            if(line.strip().startswith('[') and line.strip().endswith(']')):
                key = line.strip()[1:len(line.strip())-1]
                
                #pop off scopes
                diff = lvl - line_lvl
                for i in range(diff):
                    scope.pop()
                    
                #create new dictionary spot scoped to specific location
                map = tunnel(map, key, scope)
                #append to scope
                scope.append(key)

                lvl = len(scope)
                continue

            #identify assignments
            sep = line.find('=')
            if(sep > -1):
                key = line[:sep].strip()
                #strip excessive whitespace
                value = line[sep+1:].strip()
                #determine if its a list
                if(value.startswith('[')):
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
                exit(log.error("Invalid file! Error on line "+str(line_cnt)))

        return map

    @classmethod
    def save(cls, data, datafile, comments={}):
        '''
        Write python dictionary to data file.

        Parameters:
        ---
        comments: a dictionary of strings where the keys are headers where
                  the comments will be placed before that header/assignment
        '''
        def write_comment(c_str, spacing):
            # add proper indentation for the said comment
            lines = c_str.split('\n')
            for l in lines:
                datafile.write(spacing+l+"\n")

        def write_dictionary(mp, lvl=0):
            #determine proper indentation
            indent = cls.TAB*lvl
            if(isinstance(mp, dict)):
                for k in mp.keys():
                    #write helpful comments if available
                    if(k in comments.keys()):
                        write_comment(comments[k], indent)
                    #write a header
                    if (isinstance(mp[k], dict)):
                        datafile.write(indent+'['+k+']\n')
                    #write the beginning of an assignment
                    else:
                        datafile.write(indent+k+' = ')
                    #recursively proceed to next level
                    write_dictionary(mp[k], lvl+1)
            #write a value (rhs of assignment)
            else:
                #if its a list, use brackets
                if(isinstance(mp, list)):
                    if(len(mp)):
                        #write beginning of list
                        datafile.write('[\n')
                        #write items of the list
                        for i in mp:
                            datafile.write(indent+i+',\n')
                        #close off the list
                        datafile.write(cls.TAB*(lvl-1)+']\n')
                    #write empty list
                    else:
                        datafile.write('[]\n')
                #else, store value directly as is
                else:
                    datafile.write(mp+'\n')
        
        #recursively call method to write all dictionary key/values
        write_dictionary(data)

        return True

    pass

c = {}

c['active-workspace'] = \
'''
; description:
;   What workspace listed under [workspace] currently being used.
;   If an empty assignment, a lot of functionality will be unavailable.
; value: 
;   string'''

c['general'] = \
'''; ---
; settings.dat
; ---
; description:
;   A properties file to manually configure the packaging and development tool.
; help:
;   For more information, read the documentation at ___.

; --- General settings ---
; description:
;   Various assignments related to the tool in general.'''

c['author'] = \
'''
; description:
;   Your name! (or code-name, code-names are cool too)
; value: 
;   string'''

c['label'] = \
'''
; --- Label settings ---
; description:
;   User-defined groupings of filetypes, to be collected and written to the
;   recipe file on export. Labels help bridge a custom workflow with the user's
;   backend tool.'''

c['script'] = \
'''
; --- Script settings ---
; description:
;   User-defined aliases to execute backend scripts/tools. Assignments can
;   be either a string or list of strings separated by commas.
; value:
;   assignments of string'''

c['workspace'] = \
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
;   of strings'''

c['market'] = \
'''
; --- Market settings ---
; description:
;   The list of available markets to be connected to workspaces. A market allows
;   blocks to be visible from remote repositories and downloaded/installed 
;   across machines. If a market is not configured to a remote repository, its
;   assignment is empty.
; value:
;   assignments of string'''