from tornado.concurrent import Future
class Registro(object):
    __registro = None

    @classmethod
    def instance(cls, name):
        cls.__registro = cls.__registro or {}
        if name in cls.__registro: return cls.__registro[name]
        else: return cls(name)

    def __init__(self, name):
        self.__registro[name] = self

        self.__lista = [] # obj                                                                       
        self.__key = lambda x: x
        self.__mapa = {} # val => (mac, future)                                                          
        self.mapafinal = {} # mac => obj

    def registrar(self, obj):
        self.__lista.append(obj)

    def key(self, k):
        self.__key = k

    def result(self, future, obj, v):
        future.set_result(obj)
        self.mapafinal[v]=obj

    def kv(self, k, v):
       print("kv({},{})".format(k,v))
       ret = Future()                                                                           
       if v in self.mapafinal:
           ret.set_result(self.mapafinal[v])
           return ret

       self.__mapa[k] = (v, ret)
       print( "{}: mapa: {} lista: {}".format(self.__class__.__name__, len(self.__mapa), len(self.__lista)) )
       if len(self.__mapa) == len(self.__lista):                                               
           for k, obj in zip( sorted(self.__mapa, reverse=True), # k alto = primero                                           
                              sorted(self.__lista, key=self.__key) ):
              print("k: "+str(k))
              print("obj: "+str(obj))
              v = self.__mapa[k][0]
              print("v: "+v)
              print("future: "+str(self.__mapa[k][1]))
              self.result(self.__mapa[k][1], obj, v)
                                                                                                
       return ret                                                                               

class RegistroMac(Registro):
    def valmac(self, val, mac):
        return self.kv(int(val), mac)

    def result(self, future, obj, v):
        future.set_result(obj)
        self.mapafinal[v]=obj
        obj.mac = v

class RegistroIP(Registro):
    def ip(self, addr):
        return self.kv(addr, addr)

    def result(self, future, obj, v):
        future.set_result(v)
        self.mapafinal[v]=v

