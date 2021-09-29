################################################################################
#   Project: legohdl
#   Script: filepacker.py
#   Author: Chase Ruskin
#   Description:
#       This script handles reading/writing the custom properties files used
#   for settings and blocks.
################################################################################


class Filepacker:

    COMMENT = ';'

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
            line_lvl = int(line_lvl/4)

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

        return map

    pass


with open("/Users/chase/OneDrive - University of Florida/settings.properties", 'r') as f:
    res = Filepacker.load(f)
    print("\nObj:",res)
    print('here',res['label']['shallow'])