class Entity:

    def __init__(self, file, title, deps=list(), preFiles=list(), isTB=True):
        self._reg_file = file
        self._lib,self._name = title.split('.')
        self._pre_files = preFiles
        self._dpndencies = deps
        self._is_tb = isTB

    def getFull(self):
        return self.getLib()+'.'+self.getName()

    def getLib(self):
        return self._lib

    def getName(self):
        return self._name

    def isTb(self):
        return self._is_tb

    def addExterns(self, e):
        if(not isinstance(e, list)):
            raise ValueError("Extern e argument must be a list of tuples.")
        if(len(self.getExternal()) == 0):
            self._extern_libs = e
        else:
            self._extern_libs = self.getExternal() + e

    def getExternal(self):
        if(hasattr(self, "_extern_libs")):
            return self._extern_libs
        return []

    def getDependencies(self):
        return self._dpndencies

    def setTb(self, b):
        self._is_tb = b

    def getAllFiles(self):
        return self._pre_files + [self.getFile()]

    def getFile(self):
        return self._reg_file

    def addDependency(self, deps):
        if(deps.lower() not in self._dpndencies):
            self._dpndencies.append(deps)

    def addPreFile(self, f):
        self._pre_files.append(f)

    def addFile(self, file):
        self._reg_file.append(file)

    def getPorts(self):
        if(hasattr(self, '_ports')):
            return self._ports
        else:
            return ''

    def setPorts(self, port_txt):
        self._ports = ''
        lineCount = len(port_txt.split('\n'))
        counter = 1
        for line in port_txt.split('\n'):
            if(line.lower().count("entity")):
                line = line.lower().replace("entity","component")
            self._ports = self._ports + line
            if(counter < lineCount):
                self._ports = self._ports + "\n"
            counter = counter + 1
        self.getMapping() 

    def getMapping(self):
        if(hasattr(self, "_mapping")):
            return self._mapping
        self._mapping = ''
        port_txt = self.getPorts()

        signals = dict() #store all like signals together to output later

        nl = port_txt.find('\n')
        txt_list = list()
        while nl > -1:
            txt_list.append(port_txt[:nl])
            port_txt = port_txt[nl+1:]
            nl = port_txt.find('\n')
        #format header
        port_txt = txt_list[0].replace("component", "uX :")
        port_txt = port_txt.replace("is", "")+"\n"
        
        #format ports
        isGens = False
        for num in range(1, len(txt_list)-2):
            line = txt_list[num]
            if(line.count("port")):
                port_txt = port_txt + line.replace("port", "port map").strip()+"\n"
                continue
            if(line.count("generic")):
                port_txt = port_txt + line.replace("generic", "generic map").strip()+"\n"
                isGens = True
                continue
            col = line.find(':')
            if(isGens and line.count(')')):
                isGens = False
                port_txt = port_txt+")\n"
                continue

            sig_dec = line[col+1:].strip()
            spce = sig_dec.find(' ')
            sig_type = sig_dec[spce:].strip()
            if(sig_type.count(';') == 0):
                sig_type = sig_type + ';'
            sig = line[:col].strip()
            if(not isGens):
                if(not sig_type in signals):
                    signals[sig_type] = list()
                signals[sig_type].append(sig)
            
            line = "    "+line[:col].strip()+"=>"+sig
            if((not isGens and num < len(txt_list)-3) or (isGens and txt_list[num+1].count(')') == 0)):
                line = line + ',' #only append ',' to all ports but last
            port_txt = port_txt+line+"\n"
        
        #format footer
        port_txt = port_txt + txt_list[len(txt_list)-2].strip()+"\n"

        #print signal declarations
        for sig,pts in signals.items():
            line = "signal "
            for p in pts:
                line = line + p +', '
            line = line[:len(line)-2] + ' : ' + sig
            self._mapping = self._mapping + line + '\n'

        self._mapping = self._mapping + '\n' + port_txt
        if(len(signals) == 0):
            self._mapping = ''
        return self._mapping

    def __repr__(self):
        return(f'''
entity: {self.getFull()}
files: {self._reg_file}
dependencies: {self._dpndencies}
is tb? {self._is_tb}
external entities: {self.getExternal()}
        ''')