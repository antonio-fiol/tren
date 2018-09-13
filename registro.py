from tornado.concurrent import Future
class RegistroMac(object):
    __registro = {}
    @classmethod
    def instance(cls, name):
        if name in cls.__registro: return cls.__registro[name]
        else: return RegistroMac(name)

    def __init__(self, name):
        self.__registro[name] = self

        self.__lista = [] # obj                                                                       
        self.__key = lambda x: x
        self.__mapa = {} # val => (mac, future)                                                          
        self.__mapafinal = {} # mac => obj

    def registrar(self, obj):
        self.__lista.append(obj)

    def key(self, k):
        self.__key = k

    def valmac(self, val, mac):                                                                  
       print("valmac({},{})".format(val,mac))
       ret = Future()                                                                           
       if mac in self.__mapafinal:
           ret.set_result(self.__mapafinal[mac])
           return ret

       self.__mapa[int(val)] = (mac, ret)                                                        

       print(len(self.__mapa))
       print(self.__mapa)

       print(len(self.__lista))
       print(self.__lista)

       if len(self.__mapa) == len(self.__lista):                                               
           for val, obj in zip( sorted(self.__mapa, reverse=True), # Val alto = primero                                           
                                 sorted(self.__lista, key=self.__key) ):         
              print("val: "+str(val))                                                           
              print("obj: "+str(obj))                                                     
              mac = self.__mapa[val][0]
              print("mac: "+mac)                                                 
              print("future: "+str(self.__mapa[val][1]))                                              
              self.__mapa[val][1].set_result(obj)                                             
              self.__mapafinal[mac]=obj
              obj.mac = mac
                                                                                                
       return ret                                                                               
 
