from singleton import singleton
import tornado.ioloop

class Suscripcion(object):
    def __init__(self, suscriptor,emisor=None):
        self.suscriptor = suscriptor
        self.emisor = emisor

class Evento(object):
    def __init__(self, emisor):
        self.emisor = emisor
        self.t_publicacion = None

    def publicar(self):
        self.t_publicacion = tornado.ioloop.IOLoop.current().time()
        GestorEventos().propagar(self)

    def __repr__(self):
        return type(self).__name__+": "+str(self.__dict__)

class SuscriptorEvento(object):
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

    def __repr__(self):
        ret = type(self).__name__
        if hasattr(self, "repr"):
            ret+=" "
            ret+=str(self.repr)
        if hasattr(self, "eventos") and self.eventos:
            ret+=" cuando " + ", ".join(self.eventos)
        return ret

    def json_friendly_dict(self):
        ret = { "tipo_accion": type(self).__name__ }
        if hasattr(self, "repr"):
            ret["repr"] = self.repr
        if hasattr(self, "eventos") and self.eventos:
            ret["cuando"] = self.eventos
        return ret

        

@singleton
class GestorEventos(object):
    def __init__(self):
        self.suscriptores = {}

    def propagar(self, evento):
        print("Propagando "+str(evento))
        for tipo in self.suscriptores:
            if issubclass(type(evento),tipo):
                for s in self.suscriptores[type(evento)]:
                    if s.emisor == evento.emisor or not s.emisor:
                        tornado.ioloop.IOLoop.current().add_callback(s.suscriptor, evento)
                        #s.suscriptor(evento) llamado en la siguiente iteracion del bucle

    def suscribir_evento(self, tipo, suscriptor, emisor=None): # Suscriptor es un metodo que recibe el evento como parametro
        if tipo in self.suscriptores:
            self.suscriptores[tipo].append(Suscripcion(suscriptor,emisor))
        else:
            self.suscriptores[tipo]=[Suscripcion(suscriptor,emisor)]

    def eliminar_suscriptor(self, suscriptor):
        print("eliminar_suscriptor: suscriptor="+str(suscriptor))
        for sr in self.suscriptores.values():
            [ sr.remove(sn) for sn in sr if sn.suscriptor == suscriptor ]

