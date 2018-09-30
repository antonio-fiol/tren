from singleton import singleton
import tornado.ioloop
from datetime import timedelta
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if log.level == logging.NOTSET:
    log.setLevel(logging.WARN)

class Suscripcion(object):
    def __init__(self, suscriptor,emisor=None):
        self.suscriptor = suscriptor
        self.emisor = emisor

class Evento(object):
    def __init__(self, emisor):
        self.emisor = emisor
        self.t_publicacion = None

    def publicar(self, *args, **kwargs):
        self.t_publicacion = tornado.ioloop.IOLoop.current().time()
        if args: self.args = list(args)
        if kwargs: self.kwargs = kwargs
        GestorEventos().propagar(self)

    def __repr__(self):
        return type(self).__name__+": "+str(self.__dict__)

class SuscriptorEvento(object):
    class Fin(Evento):
        def __init__(self, emisor, evento_original):
            self.__dict__.update(evento_original.__dict__)
            self.emisor = emisor
            self.t_publicacion = None
            self.evento_original = evento_original
            log.info(self)

    activables = []

    def recibir(self, evento):
        pass

    def si(self, condicion):
        self.condicion = condicion
        return self

    def si_activo_para_tren(self, por_defecto=True):
        # Registrar acciones activables para un tren
        SuscriptorEvento.activables.append( (self, por_defecto) )
        # Guardar condicion
        self.activo = lambda evento: evento and evento.tren and self in [ x[0] for x in evento.tren.opciones_activas if x[1] ]
        return self

    def comprobar_y_recibir(self, evento):
        if not hasattr(self, "condicion") or not self.condicion or self.condicion(evento):
           if not hasattr(self, "activo") or not self.activo or self.activo(evento):
              if hasattr(self, "retardo") and self.retardo:
                  def rr():
                      log.info("propagacion retardada: "+str(evento))
                      self.recibir(evento)
                  tornado.ioloop.IOLoop.current().add_timeout(timedelta(seconds=self.retardo), rr)
              else:
                  self.recibir(evento)

    def cuando(self, tipo_evento, emisor=None): # El metodo es encadenable: xxx.cuando(Evento).cuando(Evento)...
        GestorEventos().suscribir_evento(tipo_evento, self.comprobar_y_recibir, emisor)
        if not hasattr(self, "eventos"):
            self.eventos = []

        if emisor:
           ev = { "emisor": str(emisor), "tipo_evento": tipo_evento.__name__ }
        else:
           ev = { "tipo_evento": tipo_evento.__name__ }
        self.eventos.append(ev)
        return self

    def ya_no(self):
        GestorEventos().eliminar_suscriptor(self.comprobar_y_recibir)

    def tras(self, segundos):
        self.retardo = segundos

    def __repr__(self):
        ret = type(self).__name__
        if hasattr(self, "repr"):
            ret+=" "
            ret+=str(self.repr)
        if hasattr(self, "eventos") and self.eventos:
            ret+=" cuando " + ", ".join(map(str,self.eventos))
        return ret

    def json_friendly_dict(self):
        real = self
        ret = {}
        # Delegación es un patrón por el que un suscriptor de eventos
        # traslada los eventos a otro suscriptor, procesándolos antes
        if hasattr(self, "delegado") and self.delegado:
            real = self.delegado
            ret["delegacion"] = type(self).__name__
        # Tipo de accion y representacion vienen del evento real
        ret["tipo_accion"] = type(real).__name__
        if hasattr(real, "repr"):
            ret["repr"] = real.repr
        # Eventos siempre del propio suscriptor
        if hasattr(self, "eventos") and self.eventos:
            ret["cuando"] = self.eventos
        return ret

    def mapear_clave_concurrencia(self, evento):
        return None

class SuscriptorGenerico(SuscriptorEvento):
    def __init__(self, metodo_recibir):
        self.metodo_recibir = metodo_recibir
        self.repr = metodo_recibir.__repr__()

    def recibir(self, evento):
        self.metodo_recibir(evento)

class DescartarConcurrencia(SuscriptorEvento):
    def __init__(self, delegado, max_concurrencia = 1):
        self.delegado = delegado
        self.max_concurrencia = 1
        self.concurrencia = {}

        GestorEventos().suscribir_evento(SuscriptorEvento.Fin, self.fin, self.delegado)

    def recibir(self, evento):
        autorizar = False
        clave = self.delegado.mapear_clave_concurrencia(evento)
        if clave in self.concurrencia:
            if self.concurrencia[clave] < self.max_concurrencia:
                self.concurrencia[clave] += 1
                autorizar = True
        else:
            self.concurrencia[clave] = 1
            autorizar = True
        if autorizar:
            self.delegado.recibir(evento)

    def fin(self, evento):
        clave = self.delegado.mapear_clave_concurrencia(evento)
        self.concurrencia[clave] -= 1
        if self.concurrencia[clave] == 0: del self.concurrencia[clave]

@singleton
class GestorEventos(object):
    def __init__(self):
        self.suscriptores = {}

    def propagar(self, evento):
        log.debug("Propagando "+str(evento))
        for tipo in self.suscriptores:
            if issubclass(type(evento),tipo):
                for s in self.suscriptores[tipo]:
                    if s.emisor == evento.emisor or not s.emisor:
                        tornado.ioloop.IOLoop.current().add_callback(s.suscriptor, evento)
                        #s.suscriptor(evento) llamado en la siguiente iteracion del bucle

    def suscribir_evento(self, tipo, suscriptor, emisor=None): # Suscriptor es un metodo que recibe el evento como parametro
        if tipo in self.suscriptores:
            self.suscriptores[tipo].append(Suscripcion(suscriptor,emisor))
        else:
            self.suscriptores[tipo]=[Suscripcion(suscriptor,emisor)]

    def eliminar_suscriptor(self, suscriptor):
        log.info("eliminar_suscriptor: suscriptor="+str(suscriptor))
        for sr in self.suscriptores.values():
            [ sr.remove(sn) for sn in sr if sn.suscriptor == suscriptor ]

