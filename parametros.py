import inspect
import tornado.web
import collections
from tornado import gen
from singleton import singleton
from eventos import Evento
from representacion import Desc
from collections import defaultdict
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if log.level == logging.NOTSET:
    log.setLevel(logging.WARN)


class EventoParametros(Evento):
    """ Un parametro ha cambiado en la seccion que emite el evento. El evento incluye cual y el nuevo valor. """
    def __init__(self, emisor, cl, name, val):
        Evento.__init__(self, emisor)
        self.cl = cl
        self.name = name
        self.val = val

@singleton
class Parametros(object):
   """ Gestor de parametros expuestos """
   def __init__(self):
       self.d={}

   def get(self, cl, name):
       try:    return self.d[cl][name]
       except: return None

   def set(self, cl, name, val, doc=None):
       log.info("Parametros.set("+str(cl)+","+str(name)+","+str(val)+","+str(doc)+")")
       if cl not in self.d:
           Seccion(cl)
       self.d[cl][name]=val
       if doc:
           self.d[cl].doc[name]=doc
       return val

   def json_friendly_dict(self):
       return { k: v.json_friendly() for k, v in self.d.items() }


class Seccion(Desc, collections.MutableMapping):
    """Clase que se comporta como un dict pero por debajo lleva dos
       y uno de ellos representa el primer valor asignado a una clave.

       La version JSON {"a": valor_actual, "d": primer_valor_asignado}"""

    def __init__(self, cl, *args, **kwargs):
        self.desc = cl
        self.store = dict()
        self.store_d = dict()
        self.doc = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys
        Parametros().d[cl]=self

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        if key not in self.store:
            self.store_d[key] = value
        self.store[key] = value
        EventoParametros(self, self.desc, key, value).publicar()

    def __delitem__(self, key):
        del self.store[key]
        del self.store_d[key]
        EventoParametros(self, self.desc, key, None).publicar()

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def json_friendly(self):
        return { k: {"a":v, "d":self.store_d[k], "doc":self.doc.get(k)} for k, v in self.store.items() }

class expuesto(object):
   """ Decorador para exponer un atributo en la configuracion. Aplicar a un metodo sin parametros que devuelve una constante. """
   def __init__(self, wrapped):
       self.wrapped = wrapped
       self.cl = inspect.stack()[1][3]
       #Parametros().get(self.cl, self.wrapped.__name__)
       self.__get__(None,None)

   def __get__(self, inst, objtype=None):
       p = Parametros()
       retval = p.get(self.cl, self.wrapped.__name__)
       if retval == None:
           #log.debug("expuesto calling wrapped")
           retval = self.wrapped()
           #log.debug("retval="+str(retval))
           if retval != None:
               p.set(self.cl, self.wrapped.__name__, retval, self.wrapped.__doc__)
       return retval

class ParametroHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        seccion = self.get_argument("seccion", None)
        nombre = self.get_argument("nombre", None)
        val = self.get_argument("val", None)

        Parametros().set(seccion,nombre,float(val))

        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=[{"request_done":True}]))


#class C(object):
#   @expuesto
#   def val(): return 10


