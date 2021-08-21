from .language import Language
import logging as log

class Verilog(Language):

    def decipher(self, design_book, cur_lib, verbose):
        if(verbose):
            log.info("Deciphering VERILOG file...")
            log.info(self._file_path)
        #keep case sensitivity
        c_stream = self.generateCodeStream(True,True,*self._std_parsers)
        print(c_stream)
        module_name = None
        in_ports = in_module = False
        for i in range(len(c_stream)):
            if(c_stream[i] == "module"):
                module_name = c_stream[i+1]
                in_module = True
                print(module_name)
            elif(c_stream[i] == "endmodule"):
                in_module = False
                module_name == None
            elif(in_module):
                #skip self module name
                if(c_stream[i] == module_name):
                    continue
                #check with every possible unit if its an instance
                for g in design_book.values():
                    for u in g.values():
                        if(c_stream[i] == u.getName(low=False)):
                            print("found a requirement!",u.getName(low=False))
                            if(u not in design_book[cur_lib][module_name.lower()].getRequirements()):
                                design_book[cur_lib][module_name.lower()].addRequirement(u)
                                #print(design_book[cur_lib][module_name.lower()].getRequirements())
                                pass
                            #only enter recursion if the unit has not already been completed ("checked")
                            if(not design_book[u.getLib()][u.getName()].isChecked()):
                                u.getVHD().decipher(design_book, u.getLib(), verbose)
                                pass

        return design_book
        pass

    #generate string of component's signal declarations to be interfaced with the port
    def writeComponentSignals(self):
        pass

    #write out the mapping instance of an entity (can be pure instance using 'entity' keyword also)
    def writeComponentMapping(self, pureEntity=False, lib=''):
        pass

    #write out the entity but as a component
    def writeComponentDeclaration(self):
        pass


    pass