#graph module used to generate flat dependency tree, topologically sort it
from .entity import Entity


class Graph:
    def __init__(self):
        #store with adj list (list of vertices)
        self.__adj_list = dict()
        self._unit_bank = dict()
        pass
    
    #takes in two entities and connects them [entity, dep-name]
    def addEdge(self, to, fromm): #to->upper-level module... from->lower-level module
        #add to list if vertex does not exist
        if(to not in self.__adj_list.keys()):
            self.__adj_list[to] = list()
        if(fromm not in self.__adj_list.keys()):
            self.__adj_list[fromm] = list()
        
        if(fromm not in self.__adj_list[to]):
            self.__adj_list[to].append(fromm)
            pass
        pass

    def addLeaf(self, to):
        self._unit_bank[to.getFull()] = to

    def removeEdge(self, to, fromm):
        if(fromm in self.__adj_list[to]):
            self.__adj_list[to].remove(fromm)
        pass

    def topologicalSort(self):
        order = list()
        nghbr_count = dict()
        #print(len(self.__adj_list))
        #determine number of dependencies a vertex has
        for v in self.__adj_list.keys():
            nghbr_count[v] = len(self.__adj_list[v])
        #no connections were made, just add all units found
        if(len(self.__adj_list) == 0):
            for key,u in self._unit_bank.items():
                order.append(u)
  
        #continue until all are transferred
        while len(order) < len(self.__adj_list):
            #if a vertex has zero dependencies, add it to the list
            for v in nghbr_count.keys():
                if nghbr_count[v] == 0:
                    if(not self._unit_bank[v].isPKG() or True):
                        #print(self._unit_bank[v])
                        order.append(self._unit_bank[v]) #add actual entity obj

                    nghbr_count[v] = -1 #will not be recounted
                    #who all depends on this module?
                    for k in self.__adj_list.keys():
                        if(v in self.__adj_list[k]):
                            #decrement every vertex dep count that depended on recently added vertex
                            nghbr_count[k] = nghbr_count[k] - 1
                    continue

        return order

    #only display entities in the tree (no package units)
    def output(self):
        print('---DEPENDENCY TREE---')
        for v in self.__adj_list.keys():
            if(not self._unit_bank[v].isPKG()):
                print("vertex: [",v,"]",end=' <-- ')
                for u in self.__adj_list[v]:
                    if(not self._unit_bank[u].isPKG()):
                        print(u,end=' ')
                print()

    def getVertices(self):
        return len(self.__adj_list)

    pass