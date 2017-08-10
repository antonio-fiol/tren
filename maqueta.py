import logging
import tornado.ioloop
import tornado.web
import tornado.httpserver
import os.path
import math
import datetime
import signal
from math               import copysign
from datetime           import timedelta
from tornado.concurrent import Future
from tornado            import gen
from dijkstra           import shortestPath
from messagebuffer      import MessageBuffer
from polyregress        import Pair, PolySolve
from singleton          import singleton
from parametros         import expuesto, Parametros, ParametroHandler, EventoParametros, Seccion
from representacion     import Desc, Id, IdDesc, iniciales
from eventos import Evento, SuscriptorEvento, GestorEventos
from filtros import FiltroInercia
from timed import timed_avg_and_freq
import audio_maqueta as audio
from tira import Tira, TiraHandler
from weather import Weather, WeatherHandler
from tts import TTS

# Making this a non-singleton is left as an exercise for the reader.
global_message_buffer = MessageBuffer()

# El acceso a / lleva al HTML principal
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect("/static/test.html")

class DrawingHandler(tornado.web.RequestHandler):
    name = "drawing.svg"
    def get(self):
        self.write(dict(path="/static/"+self.name))

# URL para recibir las actualizaciones de forma asincrona (long poll)
class UpdateHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        cursor = self.get_argument("cursor", None)
        if not cursor:
            cursor = "No cursor matches this value"
            # Cuando un cliente nuevo se conecta, le pedimos a la maqueta que lo publique todo
            m=Maqueta()
            m.pedir_publicar_velocidades()
            m.pedir_publicar_deteccion()
            m.pedir_publicar_desvios()
            m.pedir_publicar_semaforos()
            m.pedir_publicar_trenes()
            m.pedir_publicar_parametros()
            m.pedir_publicar_tiras()
            m.pedir_publicar_weather()
            m.publicar_todo()
        # Save the future returned by wait_for_messages so we can cancel
        # it in wait_for_messages
        self.future = global_message_buffer.wait_for_messages(cursor=cursor)
        messages = yield self.future
        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=messages))

    def on_connection_close(self):
        logging.info("Connection closed")
        global_message_buffer.cancel_wait(self.future)

# Gestion directa de los tramos de via
class ViaHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        val = self.get_argument("val", "0")
        stop = self.get_argument("stop", None)
        freq = self.get_argument("freq", None)
        via = self.get_arguments("via")

        # Si la peticion no es para una via especifica (o varias), asumimos que es para todas.
        if not len(via):
           via = list(Maqueta.tramos.keys())
           if int(val)==0 and not stop:
              # Boton de poner tension, les damos una pasada a los desvios
              for idd in Maqueta.desvios:
                 Maqueta.desvios[idd].cambiar(Maqueta.desvios[idd].estado,forzar=True)

        # Identificamos los tramos a los que hace referencia la peticion, buscando por nombre
        tramos=[]
        for v in via:
            t = Maqueta.tramos[v]
            if t:
                tramos.append(t)

        # Boton de paro de emergencia, quita tension en todos los tramos
        if stop:
            Maqueta().stop()

        # Cambio de frecuencia del chip, usado para pruebas
        elif freq:
            print("FREQ(" + str(freq) + ")")
            for c in Maqueta.chips_vias:
                c.setPWMFreq(float(freq), debug=True)
        # Velocidad para los tramos
        else:
            print("Poniendo velocidad " + str(val) + " a vias " + str(via) + " --> " + str(tramos))
            for t in tramos:
                t.poner_velocidad(float(val))

        if self.request.connection.stream.closed():
            return
        # Solo indicamos exito de la operacion, y se ignora en el cliente.
        self.write(dict(messages=[{"request_done":True}]))

class TrenHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        clase = self.get_argument("clase", None)
        val = self.get_argument("val", None)
        quitar = self.get_argument("quitar",None)
        tren = self.get_arguments("id")
        add_sta = self.get_argument("addSta",None)
        remove_sta = self.get_argument("removeSta",None)
        sentido = self.get_argument("sentido",None)
        invertir = self.get_argument("invertir",None)
        sonido = self.get_argument("sonido",None)
        manual = self.get_argument("manual",None)
        auto = self.get_argument("auto",None)
        opcion = self.get_argument("opcion",None)
        estado = self.get_argument("estado",None)
        paro_progresivo = self.get_argument("paro_progresivo",None)
        medir = self.get_argument("medir",None)
        demo = self.get_argument("demo",None)

        # Si la peticion no se asocia a un tren concreto, se asume que es para todos.
        guardar_velocidad = False
        if(not len(tren)):
           tren = [x.id for x in Tren.trenes]
           guardar_velocidad = True

        # Recuperamos los trenes que existen de verdad de entre los que se incluyen en la peticion
        trenes=[]
        for v in tren:
            el = [x for x in Tren.trenes if x.id == int(v)]
            if el:
                trenes.append(el[0])

        # Cambio de velocidad del tren
        if val != None:
            print("Poniendo velocidad " + str(val) + " a trenes " + str(tren) + " --> " + str(trenes) + " guardar_velocidad="+str(guardar_velocidad))
            for t in trenes:
                t.poner_velocidad(float(val), manual=(manual=="1" or manual=="true"), guardar_velocidad=guardar_velocidad )
        elif guardar_velocidad and self.get_argument("restaurar", None):
            print("Restaurando velocidades a trenes " + str(tren) + " --> " + str(trenes))
            for t in trenes:
                t.restaurar_velocidad()

        # Cambio de la clase del tren
        if clase != None:
            print("Poniendo clase " + clase + " a trenes " + str(tren) + " --> " + str(trenes))
            for t in trenes:
                t.poner_clase(clase)

        # Quitar tren(es) que se ha(n) perdido
        if bool(quitar):
            print("Quitando trenes " + str(tren) + " --> " + str(trenes))
            for t in trenes:
                t.quitar()

        # Invertir tren(es)
        if bool(invertir):
            print("Invirtiendo sentido de trenes " + str(tren) + " --> " + str(trenes))
            for t in trenes:
                t.invertir()

        # Agregar o eliminar estaciones al recorrido del tren
        if(add_sta != None):
            for t in trenes:
                t.add_sta(maqueta.encontrar_estacion(add_sta,sentido))
        if(remove_sta != None):
            for t in trenes:
                print("Quitando estacion "+str(remove_sta)+" de "+str(t))
                t.remove_sta(int(remove_sta))

        if sonido:
            for t in trenes:
                print("Sonido "+sonido+" en "+str(t))
                t.reproducir_sonido(sonido)

        if auto:
            for t in trenes:
                t.set_auto(auto=="1" or auto=="true")

        if opcion:
            for t in trenes:
                t.cambiar_opcion(int(opcion), estado=="true")

        if paro_progresivo:
            for t in trenes:
                t.paro_progresivo(empezar=True)

        if medir and Maqueta().pista_medicion:
            for t in trenes:
                try:
                    Maqueta().pista_medicion.puede_medir(t)
                except Exception as e:
                    self.write(dict(messages=[{"request_done":False, "e":str(e)}]))
                    return

        if demo:
            for t in trenes:
                t.demo(maqueta.demos[int(demo)])

        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=[{"request_done":True}]))

# Cambio de los desvios
class DesvioHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        val = self.get_argument("id", None)
        color = self.get_argument("color", "verde")

        desvio = Maqueta.desvios[int(val)]
        estado = Desvio.colores[color]
        print("Poniendo " + str(desvio.desc) + " a " + str(estado) + "=" + color)
        desvio.cambiar(estado)

        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=[{"request_done":True}]))

# Cambio de los semaforos
class SemaforoHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        val = self.get_argument("id", None)
        color = self.get_argument("color", "verde")

        semaforo = Maqueta.semaforos[val]
        estado = Semaforo.colores[color]
        print("Poniendo " + str(semaforo.desc) + " a " + str(estado) + "=" + color)
        semaforo.cambiar(estado)

        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=[{"request_done":True}]))

# Control de luces
class LuzHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        val = self.get_argument("id", None)
        estado = self.get_argument("estado", None)

        luz = Maqueta.luces[val]
        estado = estado=="true"

        print("Poniendo " + str(luz.desc) + " a " + str(estado))
        luz.estado(estado)

        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=[{"request_done":True}]))

# Funcionalidad de chat
class MessageNewHandler(tornado.web.RequestHandler):
    def post(self):
        message = Maqueta().createChatMessage(self.get_argument("body"))

        # to_basestring is necessary for Python 3's json encoder,
        # which doesn't accept byte strings.
        message["chat"]["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=message))
        print(message)
        global_message_buffer.new_messages([message])

        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(message)

# Diccionario de locomotoras
class LocomotoraHandler(tornado.web.RequestHandler):
    def get(self):
        # Realmente no hay nada que hacer, solo devolver el diccionario de locomotoras.
        self.write(Maqueta.locomotoras)

# Listado de estaciones disponibles en la maqueta
class EstacionHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        estaciones = maqueta.exportar_estaciones()
        if self.request.connection.stream.closed():
            return
        self.write(estaciones)

class DemoHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        demos = maqueta.exportar_demos()
        if self.request.connection.stream.closed():
            return
        self.write(demos)

class SonidoHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        tren = self.get_argument("tren", None)
        sonido = self.get_argument("sonido", None)

        if tren and sonido:
            t = next((x for x in Tren.trenes if x.id == int(tren)), None)
            if t:
                t.buscar_y_reproducir_sonido(sonido)
            else:
                print("Tren "+tren+" no encontrado. No podemos reproducir sonido.")


        if self.request.connection.stream.closed():
            return
        self.write(audio.AudioSystem().sonidos)

# Instrucciones shell especiales
class ShellHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        key = self.get_argument("id", None)
        if key:
            sh = Maqueta.shells[int(key)]

            print("Instruccion especial " + str(sh.desc) + " ejecutando " + str(sh.cmdline))
            os.system(sh.cmdline)

        if self.request.connection.stream.closed():
            return
        self.write({ k: Maqueta.shells[k].__dict__ for k in Maqueta.shells})

# Construiccion de la aplicacion, y mapeo de las URLs
def make_app():
    return tornado.web.Application(
    [
        (r"/", MainHandler),
        (r"/drawing", DrawingHandler),
        (r"/update", UpdateHandler),
        (r"/via", ViaHandler),
        (r"/luz", LuzHandler),
        (r"/tren", TrenHandler),
        (r"/desvio", DesvioHandler),
        (r"/semaforo", SemaforoHandler),
        (r"/chat/new", MessageNewHandler),
        (r"/locomotoras", LocomotoraHandler),
        (r"/estaciones", EstacionHandler),
        (r"/demos", DemoHandler),
        (r"/parametro", ParametroHandler),
        (r"/sonidos", SonidoHandler),
        (r"/shell", ShellHandler),
        (r"/tira", TiraHandler),
        (r"/weather", WeatherHandler),
        ],
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    debug=True,
    gzip=True
    )

# La maqueta, en el fondo, es un grafo de nodos conectados
# Esta clase, basicamente abstracta, incluye la logica relacionada con el grafo.
class Nodo(Desc, object):
    nodos = []

    def __init__(self, debug=False):
        self.debug = debug
        Nodo.nodos.append(self)
        # Nodos de entrada
        self.a = []
        # Nodos de salida
        self.b = []
        # Descripcion
        self.desc = "Nodo"+str(len(Nodo.nodos))
        if(self.debug):
            print(self.desc + " inicializado - " + str(self))

    def validate(self):
        valid = True
        if(len(self.a)==0):
            print(self.desc + " no tiene entrada.")
            valid = False
        if(len(self.b)==0):
            print(self.desc + " no tiene salida.")
            valid = False
        if self.desvio and not isinstance(self.desvio, Desvio):
            err = str(self)+" tiene un desvio que no es un desvio. Revisar el separador decimal en la longitud del tramo."
            raise ValueError(err)
        if not (self.desvio and (self==self.desvio.centro or self==self.desvio.centro.inv)):
            if(len(self.a)>1):
                print(self.desc + " tiene mas de una entrada: " + ",".join(x.desc for x in self.a))
            if(len(self.b)>1):
                print(self.desc + " tiene mas de una salida: " + ",".join(x.desc for x in self.b))

        return valid

# Clase de apoyo para objetos que tienen colores
class Coloreado(object):
    VERDE = 1
    ROJO = 2
    colores = { "verde": VERDE, "rojo": ROJO }
    cambios_estado = {VERDE:ROJO, ROJO:VERDE}

    def color(self):
        if(self.estado == Coloreado.VERDE):
            return "verde"
        if(self.estado == Coloreado.ROJO):
            return "rojo"
        return None

    def intercambiar_estado(self):
        self.cambiar(self.cambios_estado.get(self.estado, None))

class ReservaImposible(Exception): pass

class Desvio(Desc, Coloreado):

    class EventoCambiado(Evento):
        """ El desvio ha cambiado de posicion """
        pass
    class EventoLiberado(Evento):
        """ El desvio ha sido liberado, ya sea por cambio manual o por decision de un tren """
        def __init__(self, emisor, por_cambio=False, por_tren=None):
            Evento.__init__(self, emisor)
            self.por_cambio = por_cambio
            self.por_tren = por_tren

    def __init__(self, num, inv=False, estado_inicial=Coloreado.VERDE, duracion_pulso=None):
        self.desc = "Desvio " + str(num)
        self.centro = Tramo(desc=self.desc + " centro", longitud=0.05, desvio=self, registrar=False)
        self.verde = Tramo(desc=self.desc + " verde", longitud=0.05, desvio=self, registrar=False)
        self.rojo = Tramo(desc=self.desc + " rojo", longitud=0.05, desvio=self, registrar=False)
        if not inv:
           conexion(self.centro, self.verde)
           conexion(self.centro, self.rojo)
        else:
           conexion(self.centro.inv, self.verde.inv)
           conexion(self.centro.inv, self.rojo.inv)
        self.estado = estado_inicial
        self.auto = { Coloreado.VERDE: {}, Coloreado.ROJO: {} }
        self.validaciones = { Coloreado.VERDE: [], Coloreado.ROJO: [] }
        self.duracion_pulso = duracion_pulso
        self.reserva = None
        self.t_reserva = None
        Maqueta.desvios.update({ num: self })

    def registrar_chip_desvios(self, chip, pin, chip_rv):
        print("Registrando " + str(chip) + " en " + self.desc + " con pin=" + str(pin) + " y chip_rv="+str(chip_rv))
        self.chip = chip
        self.chip_rv = chip_rv
        self.pin = pin
        self.pines_colores = { Desvio.VERDE: chip_rv.verde, Desvio.ROJO: chip_rv.rojo }
        self.cambiar(self.estado, pub=False, forzar=True)

    def cambiar(self, estado, pub=True, forzar=False, reserva=None):
        if(estado != Desvio.ROJO and estado != Desvio.VERDE):
            return False

        if not all(a.validar_cambio(self, estado) for a in self.validaciones[estado]):
            if reserva: raise ReservaImposible
            return False

        self.reservar(reserva)
        try:
            for a in list(self.auto[estado].keys()):
                print(" R--> "+a.desc)
                a.reservar(reserva)
        except ReservaImposible:
            self.liberar(reserva, estado=estado, pub=False)
            raise

        if(forzar or estado != self.estado):
            self.chip_rv.activar(self.pines_colores[estado])
            self.chip.pulso(self.pin, self.duracion_pulso)
            self.chip_rv.desactivar(self.pines_colores[estado])
            self.estado = estado
            print("Cambiado "+self.desc+" a "+self.color())
            for a in list(self.auto[estado].keys()):
                print(" --> "+a.desc)
                a.cambiar(self.auto[estado][a],pub=False,reserva=reserva)
                
            self.notificar_cambio_a_trenes()
            if pub:
                self.EventoCambiado(self).publicar()
                maqueta.pedir_publicar_desvios()
        return True

    def reservar(self, reserva):
        if self.reserva and reserva and self.reserva != reserva:
            raise ReservaImposible
        if self.reserva and not reserva:
                self.reserva.perder_reserva(self)
                self.reserva = None
                self.t_reserva = None
                self.EventoLiberado(self, por_cambio=True).publicar()
                maqueta.pedir_publicar_desvios()
        if reserva:
            print("Reservado desvio "+self.desc+" para "+str(reserva.id))
            self.reserva = reserva
            self.t_reserva = tornado.ioloop.IOLoop.current().time()
            maqueta.pedir_publicar_desvios()

    def liberar(self, tren, estado=None, pub=True):
        if self.reserva == tren:
            print("Liberado desvio "+str(self))
            self.reserva = None
            self.t_reserva = None

            for a in list(self.auto[estado or self.estado].keys()):
                # Solo liberar dependientes si no hay ningun desvio reservado que automaticamente debiera reservarlo
                if not any( d for d in Maqueta().desvios.values() if (d.reserva and a in d.auto[d.estado]) ):
                    a.liberar(tren, pub=pub)

            if pub: self.EventoLiberado(self, por_tren=tren).publicar()
            maqueta.pedir_publicar_desvios()

    def id_tren_reserva(self):
        if self.reserva: return self.reserva.id
        else:            return None

    def notificar_cambio_a_trenes(self):
        for t in Tren.trenes:
            # Lllamar a t.desvio_cambiado(self) en la siguiente iteracion del bucle
            tornado.ioloop.IOLoop.current().add_callback(t.desvio_cambiado, self)

    def tramo_activo(self, centro=None):
        quiza_inv = lambda x: x.inv if centro == self.centro.inv else x
        if(self.estado == Desvio.VERDE):
            return quiza_inv(self.verde)
        if(self.estado == Desvio.ROJO):
            return quiza_inv(self.rojo)
        return None

    def centro_correspondiente(self, rama=None):
        if rama==self.verde.inv or rama==self.rojo.inv:
            return self.centro.inv
        else:
            return self.centro

    def color_rama(self, rama):
        if rama==self.verde or rama==self.verde.inv:
            return Coloreado.VERDE
        if rama==self.rojo  or rama==self.rojo.inv:
            return Coloreado.ROJO
        return None


class Tramo(Nodo):
    debug = False
    POL_F = 1
    POL_R = -1

    def __init__(self, desc=None, longitud=0.05, desvio=None, inv=None, limites=[], registrar=True):
        Nodo.__init__(self)
        self.desvio = desvio
        self.desc = desc
        self.longitud = longitud
        self.tren = None
        self.velocidad = None
        self.stopped = False
        self.limites = limites

        self.chip_vias = None
        self.chip_vias_pin = None
        self.chip_compartido = None

        if(inv):
            self.polaridad=Tramo.POL_R
            self.inv = inv
        else:
            self.polaridad=Tramo.POL_F
            if desc:
                self.inv = type(self)(desc=(desc+" invertido"), longitud=longitud, desvio=desvio, inv=self, limites=[l.inv() for l in limites], registrar=False)
            else:
                self.inv = type(self)(longitud=longitud, desvio=desvio, inv=self, limites=[l.inv() for l in limites], registrar=False)
        self.tramos_compartiendo_chip = set([self.inv])
        if registrar:
            Maqueta.tramos.update({self.desc:self})

    def get_limites(self):
        return self.limites

    def registrar_chip_vias(self, chip, pin, compartido=None):
        self.chip_vias = chip
        self.chip_vias_pin = pin
        self.chip_compartido = compartido
        if compartido:
            self.tramos_compartiendo_chip = set(compartido.tramos) - set( [self] )
        #self.poner_velocidad(0.0, pub=False)
        self.stop(pub=False)  # Al arrancar, arrancar sin tension

    def deteccion(self, t):
        ret = None
        if(t):
            if Tramo.debug:
                print("Tramo "+self.desc+" deteccion (tiene tren) ...")
            tr = self.tren_en_tramo_fisico()
            if tr:
                if Tramo.debug:
                    print("... y ya lo tenia (o quiza en el invertido).")
                tr.desaparecido(False)
            else:
                # Hay un tren en este tramo. Ver si viene de algun tramo anterior
                tren_encontrado, tramo_encontrado = self.buscar_tren_en_tramo_anterior()
                if(tren_encontrado):
                    if Tramo.debug:
                        print("... encontrado tren " + str(tren_encontrado))
                    ret = tren_encontrado.tramo
                    self.tren = tren_encontrado
                    if tren_encontrado.tramo == tramo_encontrado:
                        tren_encontrado.mover(self)
                        print("Movido tren " + str(self.tren) + " a " + str(self))
                    else:
                        print("Movido tren (no movida cabecera) " + str(self.tren) + " a " + str(self))
                else:
                    tren_encontrado_en_inv, tramo_encontrado = self.inv.buscar_tren_en_tramo_anterior()
                    if tren_encontrado_en_inv:
                        ret = self.inv.deteccion(t)
                    else:
                        if Tramo.debug:
                            print("... y debe ser nuevo")
                        self.tren = Tren(self)
                        print("Nuevo tren " + str(self.tren) + " en " + str(self))
                maqueta.pedir_publicar_deteccion()
        else:
            if self.tren:
                tornado.ioloop.IOLoop.current().add_callback(self.tren_no_esta)
            if self.inv.tren:
                tornado.ioloop.IOLoop.current().add_callback(self.inv.tren_no_esta)
            
        # Callback deteccion

        return ret

    def tren_no_esta(self):
        if(self.tren.tramo != self):
            self.quitar_tren()
        else:
            # El tren no se ha movido, sino que ha desaparecido
            self.tren.desaparecido()

    def quitar_tren(self):
        if(self.tren):
            print("Quitando tren "+str(self.tren.id)+" de " + self.desc)
            self.tren = None
            maqueta.pedir_publicar_deteccion()
            tornado.ioloop.IOLoop.current().add_callback(maqueta.revisar_trenes_eliminados)
        if (self.velocidad != None):
            self.poner_velocidad(0.0)

    def buscar_tren_en_tramo_anterior(self, signo_velocidad=None):
        if Tramo.debug:
            print("Tramo.buscar_tren_en_tramo_anterior("+str(self)+")")

        if signo_velocidad == None:
            signo_velocidad = copysign(1, self.velocidad)
        if signo_velocidad > 0:
            tramos_anteriores = self.a
        else:
            tramos_anteriores = self.b
        for tramo in tramos_anteriores:
            if isinstance(tramo, Muerta):
                continue
            if Tramo.debug:
                print("Buscando tren en " + tramo.desc)
            if(tramo.tren):
                if Tramo.debug:
                    print("Encontrado tren " + str(tramo.tren))
                return tramo.tren, tramo
            desvio = tramo.desvio
            if(desvio):
                encontrado = None
                if Tramo.debug:
                    print("El tramo pertenece a un desvio")
                if(desvio.centro == tramo):
                    if Tramo.debug:
                        print("y es el centro")
                    encontrado, t_e = desvio.tramo_activo().buscar_tren_en_tramo_anterior(signo_velocidad)
                if(desvio.centro.inv == tramo):
                    if Tramo.debug:
                        print("y es el centro invertido")
                    encontrado, t_e = desvio.tramo_activo().inv.buscar_tren_en_tramo_anterior(signo_velocidad)
                if(desvio.tramo_activo() == tramo):
                    if Tramo.debug:
                        print("y es el tramo activo (r/v)")
                    encontrado, t_e =  desvio.centro.buscar_tren_en_tramo_anterior(signo_velocidad)
                if desvio.tramo_activo().inv == tramo:
                    if Tramo.debug:
                        print("y es el tramo activo (r/v) invertido")
                    encontrado, t_e = desvio.centro.inv.buscar_tren_en_tramo_anterior(signo_velocidad)
                if encontrado:
                    return encontrado, t_e
        return None, None

    def nodos_siguientes(self, signo_velocidad):
        if signo_velocidad > 0:
            return self.b # Adelante, el siguiente es el siguiente
        elif signo_velocidad < 0:
            return self.a # Atras, el siguiente es realmente el anterior
        else:
            return [] # Si esta parado... no se mueve!!

    def tramo_siguiente(self, signo_velocidad=None):
        if signo_velocidad == None:
            signo_velocidad = copysign(1, self.velocidad)

        siguientes = self.nodos_siguientes(signo_velocidad)

        ret = None
        for siguiente in siguientes:
          # Si llega aqui, siguiente tiene que tener algun valor
          if isinstance(siguiente,Muerta):
            continue
          elif siguiente.desvio:
                if(siguiente.desvio.centro == siguiente):
                    ret = siguiente.desvio.tramo_activo().tramo_siguiente(signo_velocidad)
                if(siguiente.desvio.centro.inv == siguiente):
                    ret = siguiente.desvio.tramo_activo().inv.tramo_siguiente(signo_velocidad)
                if(siguiente.desvio.rojo == siguiente or siguiente.desvio.verde == siguiente):
                    if(siguiente.desvio.tramo_activo() == siguiente):
                        ret = siguiente.desvio.centro.tramo_siguiente(signo_velocidad)
                    else:
                        continue # Desvio Girado
                if(siguiente.desvio.rojo.inv == siguiente or siguiente.desvio.verde.inv == siguiente):
                    if(siguiente.desvio.tramo_activo().inv == siguiente):
                        ret = siguiente.desvio.centro.inv.tramo_siguiente(signo_velocidad)
                    else:
                        continue # Desvio Girado
          else:
            ret = siguiente
        return ret
            
    def stop(self, pub=True):
        if not self.chip_vias:
            print("ALERTA: Tramo " + self.desc + " no tiene chip de vias !!!")
            return
        self.chip_vias.stop(self.chip_vias_pin)
        self.velocidad = None
        self.stopped = True
        for t in self.tramos_compartiendo_chip:
            t.velocidad = None
            t.stopped = True

        if pub:
            maqueta.pedir_publicar_velocidades()

    def poner_velocidad(self, val=0.0, minimo=None, pub=True):
        if not self.chip_vias:
            print("ALERTA: Tramo " + self.desc + " no tiene chip de vias !!!")
            return
        v_antigua = self.velocidad
        v_compartidos_antigua = { t:t.velocidad for t in self.tramos_compartiendo_chip }

        self.velocidad = val
        self.stopped = False
        for t in self.tramos_compartiendo_chip:
            t.velocidad = 0.0
            t.stopped = False

        if(v_antigua != self.velocidad or v_compartidos_antigua != { t:t.velocidad for t in self.tramos_compartiendo_chip }):
            print("Tramo " + self.desc + " poniendo velocidad " + str(val) + " en el chip")
            self.chip_vias.poner_velocidad(self.chip_vias_pin, self.polaridad, val, minimo=minimo)
            if pub:
                maqueta.pedir_publicar_velocidades()

    def tren_en_tramo_fisico(self):
        return self.tren or self.inv.tren

    @expuesto
    def FACTOR_PESO_POR_TREN_EN_TRAMO(): return 0.2
    @expuesto
    def ADICION_PESO_POR_TREN_EN_TRAMO(): return 0.2
    @expuesto
    def FACTOR_PESO_POR_TREN_EN_INVERTIDO(): return 1
    @expuesto
    def ADICION_PESO_POR_TREN_EN_INVERTIDO(): return 1
    @expuesto
    def ADICION_PESO_POR_TREN_PARADO_EN_TRAMO(): return 3
    @expuesto
    def ADICION_PESO_POR_TREN_PARADO_EN_INVERTIDO(): return 3
    @expuesto
    def ADICION_PESO_POR_CAMBIAR_DESVIO(): return 0.01
    @expuesto
    def FACTOR_PESO_POR_TRAMO_EN_OTRA_RUTA(): return 0.5

    def peso(self, otro=None):
        if isinstance(otro, Estacion):
            p = self.longitud * (otro.punto_parada or 50) / 100.0
        else:
            p = self.longitud

        # Reglas basicas
        if self.tren: p+=(self.longitud*Tramo.FACTOR_PESO_POR_TREN_EN_TRAMO + Tramo.ADICION_PESO_POR_TREN_EN_TRAMO)
        if self.inv.tren: p+=(self.longitud*Tramo.FACTOR_PESO_POR_TREN_EN_INVERTIDO + Tramo.ADICION_PESO_POR_TREN_EN_INVERTIDO)
        if self.tren and self.tren.velocidad == 0: p+=Tramo.ADICION_PESO_POR_TREN_PARADO_EN_TRAMO
        if self.inv.tren and self.inv.tren.velocidad == 0: p+=Tramo.ADICION_PESO_POR_TREN_PARADO_EN_INVERTIDO
        if self.desvio and self not in (self.desvio.tramo_activo(), self.desvio.tramo_activo().inv, self.desvio.centro, self.desvio.centro.inv):
            p+=Tramo.ADICION_PESO_POR_CAMBIAR_DESVIO

        # Calculo avanzado
        # [item for sublist in self.puntos for item in sublist] # Truco para aplanar una lista
        lista = [ {tramo:tren} for tren in Tren.trenes for tramo in tren.ultima_ruta_calculada if tramo == self or tramo == self.inv ]
        #if lista:
        #    print(self.desc+".peso(): lista="+str(lista)+" ==> "+str(len(lista)))
        p+= len(lista)*Tramo.FACTOR_PESO_POR_TRAMO_EN_OTRA_RUTA

        return p

class ColeccionTramos(Desc, object):
    def __init__(self, *args, **kwargs):
        if "tramos" in kwargs:
            self.tramos = kwargs["tramos"]
        else:
            self.tramos = list(args) + [ t.inv for t in args ]
        self.desc = iniciales(type(self).__name__)+str([ t.desc for t in self.tramos ])
        self.inv = self

class TramosConDeteccionCompartida(ColeccionTramos):
    def deteccion(self, t):
        ret = None
        tr, fisico = self.tren_en_tramo_fisico()
        if(t):
            if Tramo.debug:
                print("Tramo "+self.desc+" deteccion (tiene tren) ...")
            if tr:
                if Tramo.debug:
                    print("... y ya lo tenia en alguno de los tramos fisicos.")
                tr.desaparecido(False)
            else:
                # Hay un tren en este tramo. Ver si viene de algun tramo anterior
                tren_encontrado, seccion = self.buscar_tren_en_tramos_anteriores()
                if(tren_encontrado):
                    nuevo_tramo = seccion
                else:
                    nuevo_tramo = self.tramos[0]
                ret = nuevo_tramo.deteccion(t)
                maqueta.pedir_publicar_deteccion()
        else:
            if tr:
                tornado.ioloop.IOLoop.current().add_callback(fisico.tren_no_esta)
        return ret

    def tren_en_tramo_fisico(self):
        return next(((tramo.tren, tramo) for tramo in self.tramos if tramo.tren), (None,None))

    def buscar_tren_en_tramos_anteriores(self):
        return next( ( (tren, tramo) for (tren,tramo_encontrado), tramo in ((tramo.buscar_tren_en_tramo_anterior(), tramo) for tramo in self.tramos) if tren), (None,None) )

class SensorDePaso(TramosConDeteccionCompartida):
    """ Idea alternativa para tramos que no se pueden cortar, usando un sensor de paso. """
    # TODO: Probar !!!!
    def __init__(self, *args):
        if len(args)!=2: raise ValueError("Un sensor de paso esta entre 2 tramos, no "+str(len(args)))
        super(SensorDePaso, self).__init__(tramos=[args[1], args[0].inv])
        self.t = None

    def deteccion(self, t):
        tramo_estaba = None
        if t != self.t: # Flanco
            self.t = t
            if t: # De subida --> actuamos
                tramo_estaba = super(SensorDePaso, self).deteccion(t)
                tramo_estaba.quitar_tren()
        return tramo_estaba

class TramosConAlimentacionCompartida(ColeccionTramos):
    def registrar_chip_vias(self, chip, pin):
        self.chip_vias = chip
        self.chip_vias_pin = pin
        for tramo in self.tramos:
            tramo.registrar_chip_vias(chip, pin, compartido=self)

class TramoX(Tramo):
    def validate(self):
        valid = True
        if(len(self.a)==0):
            print(self.desc + " no tiene entrada.")
            valid = False
        if(len(self.b)==0):
            print(self.desc + " no tiene salida.")
            valid = False
        if(len(self.a)!=2):
            print(self.desc + " deberia tener 2 entradas. Tiene "+ str(len(self.a)))
            valid = False
        if(len(self.b)!=2):
            print(self.desc + " deberia tener 2 salidas. Tiene "+ str(len(self.b)))
            valid = False
        return valid


class Semaforo(Tramo,Coloreado):
    debug = False

    class EventoCambiado(Evento):
        """ El semaforo ha cambiado de color (o se ha apagado) """
        pass

    def __init__(self, desc=None, longitud=0.05, desvio=None, inv=None, limites=[], limites_rojo=[], limites_verde=[], registrar=True):
        Tramo.__init__(self, desc, longitud, desvio, inv, limites, registrar)
        self.luz= { Semaforo.ROJO: Luz(registrar=False), Semaforo.VERDE: Luz(registrar=False) }
        self.limites_rojo = limites_rojo
        self.limites_verde = limites_verde
        self.validaciones = { Coloreado.VERDE: [], Coloreado.ROJO: [] }
        self.cambiar(Semaforo.VERDE, pub=False, forzar=True) # FIXME: Deberia ser None en lugar de VERDE
        Maqueta.semaforos.update({self.desc:self})

    def get_limites(self):
        return self.limites + (self.limites_rojo if self.estado == Semaforo.ROJO else self.limites_verde)

    def cambiar(self, estado, pub=True, forzar=False):
        if(estado != Semaforo.ROJO and estado != Semaforo.VERDE and estado != None):
            return False
        if estado and not all(a.validar_cambio(self, estado) for a in self.validaciones[estado]):
            return False

        if(forzar or estado != self.estado):
            for c,l in list(self.luz.items()):
                l.estado(c==estado,pub=pub)
            self.estado = estado
            self.notificar_cambio_a_trenes()
            if Semaforo.debug:
                print("Semaforo "+self.desc+": cambiar: get_limites()-->"+str(self.get_limites()))
            if pub:
                self.EventoCambiado(self).publicar()
                maqueta.pedir_publicar_semaforos()
        return True

    def notificar_cambio_a_trenes(self):
        for t in Tren.trenes:
            # Lllamar a t.semaforo_cambiado(self) en la siguiente iteracion del bucle
            tornado.ioloop.IOLoop.current().add_callback(t.semaforo_cambiado,self)

    def stop(self, pub=True):
        Tramo.stop(self, pub)
        self.cambiar(None, pub=pub)

    def poner_velocidad(self, val=0.0, minimo=None, pub=True):
        Tramo.poner_velocidad(self, val=val, minimo=minimo, pub=pub)
        if self.estado == None:
            self.cambiar(Semaforo.VERDE, pub) or self.cambiar(Semaforo.ROJO, pub)

class Luz(Desc, object):
    luces = []

    class EventoCambiado(Evento):
        """ La luz se ha encendido o apagado """
        pass

    def __init__(self, desc=None, registrar=True):
        self.encendida = False
        self.chip = None
        self.pin = None
        self.controlada_por_deteccion = False
        Luz.luces.append(self)
        if desc:
            self.desc=desc
        else:
            self.desc = "Luz"+str(len(Luz.luces))
        if registrar:
            Maqueta.luces.update({self.desc:self})

    def registrar_chip_desvios(self, chip, pin, chip_rv):
        print("Registrando " + str(chip) + " en " + self.desc)
        self.chip = chip
        self.pin = pin
        # Enviar al chip el estado actual, porque se habia incializado
        # al crear el objeto pero el chip no estaba registrado
        self.estado(self.encendida, pub=False)

    def estado(self,encendida,pub=True,forzar=False):
        # No permite cambios si esta controlada por deteccion
        if self.controlada_por_deteccion and not forzar: return

        print(self.desc + " " + str(encendida))
        # Guardar estado por si no estaba registrado aun el chip
        self.encendida = encendida
        # Pasar al chip
        if self.chip:
            if encendida:
                self.chip.activar(self.pin)
            else:
                self.chip.desactivar(self.pin)
        if pub:
            self.EventoCambiado(self).publicar()
            maqueta.pedir_publicar_luces()

    def deteccion(self, d):
        self.controlada_por_deteccion = True
        if d != self.encendida:
            self.estado(d, forzar=True)

    def on(self):
        self.estado(True)

    def off(self):
        self.estado(False)

    def estado_a_bool(self):
        return bool(self.encendida)

class PermitirEstado(SuscriptorEvento):
    def __init__(self, cambiable, estado):
        self.cambiable = cambiable
        self.estado = estado
        self.estado_vuelta = None
        self.controlador = True
        self.repr = "PermitirEstado "+str(self.cambiable)+" "+str(self.estado)
        self.cambiable.validaciones[self.estado].append(self)

    def si(self, objeto_bool, inv=False):
        self.ya_no()
        self.controlador = objeto_bool
        self.inv = inv
        self.cuando(Evento, self.controlador)

    def si_no(self, objeto_bool):
        self.si(objeto_bool, inv=True)

    def con_vuelta_a(self, estado_vuelta):
        self.estado_vuelta = estado_vuelta

    def validar_cambio(self, cambiable, estado):
        # Restringir cambios solo para el objeto y estado configurados, unicamente en modo real
        if self.cambiable == cambiable and self.estado == estado and not Maqueta.modo_dummy:
            return self.controlador.estado_a_bool() != self.inv  # Equivalente XOR
        else:
            return True

    def recibir(self, evento):
        if not self.validar_cambio(self.cambiable, self.cambiable.estado):
            if self.estado_vuelta:
                self.cambiable.cambiar(self.estado_vuelta)
            else:
                self.cambiable.intercambiar_estado()

class Muerta(Nodo):
    def __init__(self, inv=None):
        Nodo.__init__(self)
        if(inv):
            self.inv = inv
        else:
            self.inv = Muerta(self)
        
    def validate(self):
        return True

    def peso(self):
        return 999999999

class Locomotora(object):
    def __init__(self, id, desc, coeffs=None, minimo=None, porcentaje_minimo=None, muestras_inercia=None):
        if porcentaje_minimo and not minimo:
            minimo = int(porcentaje_minimo * 4096 / 100)
        Maqueta.locomotoras.update({id:desc})
        if coeffs:
            DatosVelocidad.COEFFS_INICIO.update({id:coeffs})
        if minimo!=None:
            DatosVelocidad.MINIMO_INICIO.update({id:minimo})
        if muestras_inercia!=None:
            DatosVelocidad.MUESTRAS_INERCIA.update({id:muestras_inercia})
            DatosVelocidad.MUESTRAS_INERCIA.doc.update({id:"Numero de muestras que el sistema asume que se mantiene la anterior velocidad calculada, para la locomotora "+desc+"."})
        print("Locomotora id="+id+" desc="+str(desc)+" coeffs="+str(coeffs)+" minimo="+str(minimo)+" muestras_inercia="+str(muestras_inercia))

class Demo(IdDesc):
    def __init__(self, id, desc, estaciones):
        self.id = id
        self.desc = desc
        Maqueta.demos.update({id:self})
        self.estaciones = [ Maqueta.estaciones[x] for x in estaciones if Maqueta.estaciones[x] ]
        print("Demo "+str(self.id)+": "+str(self.desc)+": "+str(self.estaciones))

    def diccionario_atributos(self):
        return {
            "id": self.id,
            "desc": self.desc,
            "estaciones": [ e.diccionario_atributos() for e in self.estaciones ],
        }



class DatosVelocidad(object):
    COEFFS_INICIO = {
        "desconocido": [0,0.01,0],
    }
    MINIMO_INICIO = Seccion("MinimoValorArranque",{
        "desconocido": 600,
    })
    MUESTRAS_INERCIA = Seccion("NumeroMuestrasInercia",{
        "desconocido": 1,
    })
    MUESTRAS_INERCIA.doc["desconocido"]="Numero de muestras que el sistema asume que se mantiene la anterior velocidad calculada, para cualquier locomotora que no tenga un parametro de inercia propio."

    def __init__(self, clase, tren=None):
        self.clase = clase
        self.tren = tren
        try:
            self.coeffs = DatosVelocidad.COEFFS_INICIO[clase]
        except:
            print("No encuentro coeficientes de inicio para clase "+str(clase))
            print("COEFFS_INICIO="+str(DatosVelocidad.COEFFS_INICIO))
            self.coeffs = DatosVelocidad.COEFFS_INICIO["desconocido"]

        self.ajustar_minimo_e_inercia()

        self.puntos = [ [] for i in range(0,10) ] # 10 segmentos de puntos
        for i in range(1,101,4):
            self.anadir_punto(i,self.f(i, inercia=False),recalcular=False)
        self.actualizar_coeffs()

        GestorEventos().suscribir_evento(EventoParametros, self.ajustar_minimo_e_inercia, DatosVelocidad.MINIMO_INICIO)
        GestorEventos().suscribir_evento(EventoParametros, self.ajustar_minimo_e_inercia, DatosVelocidad.MUESTRAS_INERCIA)

    def ajustar_minimo_e_inercia(self, evento=None):
        try:
            self.minimo = DatosVelocidad.MINIMO_INICIO[self.clase]
        except:
            print("No encuentro minimo de inicio para clase "+str(self.clase))
            print("MINIMO_INICIO="+str(DatosVelocidad.MINIMO_INICIO))
            self.minimo = DatosVelocidad.MINIMO_INICIO["desconocido"]

        try:
            self.muestras_inercia = DatosVelocidad.MUESTRAS_INERCIA[self.clase]
        except:
            print("No encuentro muestras de inercia para clase "+str(self.clase))
            print("MUESTRAS_INERCIA="+str(DatosVelocidad.MUESTRAS_INERCIA))
            self.muestras_inercia = DatosVelocidad.MUESTRAS_INERCIA["desconocido"]
        self.filtro_inercia = FiltroInercia(self.muestras_inercia)

    def f(self,x, inercia=True):
        y = r = 0
        for c in self.coeffs:
            y = y + c * pow(x, r)
            r += 1
        y = max(y,0) # Nunca negativo
        if inercia:
            y = self.filtro_inercia.procesar(y)
        return y
        

    def encontrar_x_para_y_poco_menor_que(self,y):
        x = 0
        for nuevo_x in range(0,100):
            #print("nuevo_x="+str(nuevo_x)+" nuevo_y="+str(self.f(nuevo_x))+" y="+str(y))
            if self.f(nuevo_x) > y:
                break
            x = nuevo_x
        return x

    def anadir_punto(self,x,y,recalcular=True):
        segmento = int(math.ceil(float(x) / 10.0) - 1)
        p = self.puntos[segmento]
        self.last=Pair([x,y])
        p.append(self.last)
        if len(p) > 10:
           p.pop(0)

        if recalcular:
            self.actualizar_coeffs()

    def actualizar_coeffs(self):
        data = [item for sublist in self.puntos for item in sublist] # Truco para aplanar una lista

        self.coeffs = PolySolve().calculate(2,data)

        maqueta.publicar_datos_velocidad_tren(self.clase,
                                              self.tren,
                                              [ [p.x,p.y] for p in data ],
                                              self.coeffs,
                                              [self.last.x,self.last.y])

class Estacion(Desc, object):
    cnt = 0

    class EventoEstacion(Evento):
        def __init__(self, estacion, tren):
            Evento.__init__(self, estacion)
            self.estacion = estacion
            self.tren = tren

    class EventoTrenParado(EventoEstacion):
        """ Un tren se ha parado en la estacion """
        pass
    class EventoTrenArrancando(EventoEstacion):
        """ Un tren ha arrancado para salir de la estacion """
        pass

    def __init__(self, nombre, sentido, tramo=None, punto_parada=None, t_parada=6.0, desc=None):
        Estacion.cnt += 1
        self.id = Estacion.cnt
        self.nombre = nombre
        self.sentido = sentido
        self.tramo = tramo
        self.punto_parada = punto_parada
        self.t_parada = t_parada
        if self.tramo:
            self.lce=LimiteCondicionalEstacion(self)
            self.tramo.limites.append(self.lce)
        self.tren_parado_en_estacion = None
        self.indicador_tren_parado = None
        self.asociacion = None
        self.desc = desc or self.__repr__()
        Maqueta.estaciones.update({(nombre,sentido):self})

    def controlar_tramo_previo(self, v_intercambio):
        self.lce.limite_true.velocidad_inicio=v_intercambio
        self.tramo.a[0].limites.append(LimiteCondicionalTramoAnteriorEstacion(self, self.tramo.a[0], v_intercambio))

    def tren_parado(self,tren):
        if self.tren_parado_en_estacion != tren:
            self.tren_parado_en_estacion = tren
            if self.indicador_tren_parado:
                self.indicador_tren_parado.on()
            self.EventoTrenParado(self,tren).publicar()

    def tren_arrancando(self,tren):
        if self.tren_parado_en_estacion:
            self.tren_parado_en_estacion = None
            if self.indicador_tren_parado:
                self.indicador_tren_parado.off()
            self.EventoTrenArrancando(self,tren).publicar()

    def activa(self):
        return bool(self.tramo) and bool(self.tramo.tren) and self in self.tramo.tren.sta

    def diccionario_atributos(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "sentido": self.sentido,
            "activa": self.activa(),
        }

    def __repr__(self):
        return "Estacion "+str(self.id)+" en "+str(self.tramo)+" "+self.sentido

    def peso(self, otro=None):
        return 0

class AsociacionEstaciones(Desc,object):
    def __init__(self, nombre, sentido, estaciones, desc=None):
        Estacion.cnt += 1
        self.id = Estacion.cnt
        self.nombre = nombre
        self.sentido = sentido
        self.estaciones = estaciones
        for e in self.estaciones:
            e.asociacion = self
        self.desc = desc or "Asociacion "+str(nombre)+"-"+str(sentido)+" "+str(estaciones)
        Maqueta.estaciones.update({(nombre,sentido):self})

    def diccionario_atributos(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "sentido": self.sentido,
        }

class Tren(Id, object):
    trenes = []
    cnt = 0
    MIDIENDO = 8
    COLISION_FRONTAL = 7
    MODO_MANUAL = 6
    DESAPARECIDO = 5
    CERCA_FIN_DE_VIA = 4
    FIN_DE_VIA = 3
    COLISION_INMINENTE = 2
    COLISION_POSIBLE = 1

    @expuesto
    def PORCENTAJE_VELOCIDAD_TRAMO_SIGUIENTE(): return 100.0
    @expuesto
    def PORCENTAJE_VELOCIDAD_TRAMO_ANTERIOR(): return 100.0
    @expuesto
    def TIEMPO_MODO_MANUAL_S():
        """Tiempo que dura un impulso de avance/retroceso en modo manual."""
        return 0.6
    @expuesto
    def ESPACIO_LIBERAR_DESVIOS_M():
        """Espacio pasado un desvio tras el cual un tren liberara el desvio en cuestion.
           Deberia ser superior a la longitud maxima de cualquier composicion."""
        return 0.6
    @expuesto
    def ESPACIO_SEGURIDAD_RECALCULO_M():
        """Distancia minima hasta el proximo desvio para que un tren pueda recalcular
           su ruta. Si el tren se encuentra mas cerca, se asume que cambiar el siguiente
           desvio podria descarrilar el tren."""
        return 0.2
    @expuesto
    def TIEMPO_PARO_PROGRESIVO_S():
        """Tiempo de frenada para el paro progresivo cuando el tren circula a su
           velocidad maxima. Velocidades menores implicaran tiempos de parada menores."""
        return 5

    class EventoTren(Evento):
        def __init__(self, emisor):
            Evento.__init__(self,emisor)
            self.tren = emisor

    class EventoNuevo(EventoTren):
        """ Se ha creado un tren nuevo """
        pass
    class EventoAtributosModificados(EventoTren):
        """ Se ha modificado alguno de los atributos del tren """
        pass
    class EventoCambioVelocidad(EventoTren):
        """ La velocidad programada del tren ha cambiado """
        pass
    class EventoVelocidadCero(EventoCambioVelocidad):
        """ La velocidad programada del tren ha cambiado """
        pass
    class EventoMovido(EventoTren):
        """ El tren ha cambiado de tramo """
        pass
    class EventoDesaparecido(EventoTren):
        """ El tren ha desaparecido """
        pass
    class EventoEncontrado(EventoTren):
        """ El tren se ha encontrado de nuevo """
        pass
    class EventoQuitado(EventoTren):
        """ Se ha quitado un tren desaparecido """
        pass
    class EventoCambioZona(EventoTren):
        """ El tren ha cambiado de zonas (no indica si entrando o saliendo) """
        pass

    class EventoCambioVelocidadEfectiva(EventoTren):
        """ El tren ha acelerado o frenado (ojo, esto ocurre muy a menudo) """
        def __init__(self, emisor, anterior, actual):
            super(Tren.EventoCambioVelocidadEfectiva, self).__init__(emisor)
            self.anterior = anterior
            self.actual = actual

        def signo(self):
            return copysign(1,actual-anterior)

        def signo_abs(self):
            return copysign(1,abs(actual)-abs(anterior))

    class EventoVelocidadEfectivaCero(EventoCambioVelocidadEfectiva):
        """ El tren ha frenado hasta velocidad cero """
        def __init__(self, emisor, anterior):
            super(Tren.EventoVelocidadEfectivaCero, self).__init__(emisor, anterior, 0)

    def __init__(self, tramo):
        Tren.cnt += 1
        # Datos basicos
        self.id = Tren.cnt
        self.tramo = tramo
        self.clase = "desconocido"

        # Datos de movimiento
        self.velocidad = 0.0
        self.velocidad_efectiva = 0.0
        self.velocidad_guardada = None
        self.estado_colision = None
        self.tren_colision = None
        self.estado_colision_f = None
        self.tren_colision_f = None
        self.t_quitar_modo_manual = None
        self.datos_velocidad = DatosVelocidad(self.clase, self)
        self.parando = False

        # Posicionamiento fino
        self.espacio_recorrido_en_tramo = 0
        self.t_ultima_actualizacion_espacio = tornado.ioloop.IOLoop.current().time()
        self.t_entrada_en_tramo = self.t_ultima_actualizacion_espacio
        self.tramo_a_v_constante = False

        # Zonas y sonido
        self.zonas = []
        self.altavoces = audio.Fader()

        # Ruta y movimiento automatico
        self.auto = False
        self.sta = []
        self.tabla_liberacion_desvios = {}
        self.esperando_liberacion = None
        self.ultima_ruta_calculada = []

        self.opciones_activas = SuscriptorEvento.activables[:]
        self.auto_quitar = None

        # Registro en la maqueta
        Tren.trenes.append(self)
        self.EventoNuevo(self).publicar()
        Maqueta().pedir_publicar_trenes()

        # Registrarse para saber cuando cambia de zona el mismo, y cambiar los altavoces
        GestorEventos().suscribir_evento(Tren.EventoCambioZona, self.recibir_evento_cambio_zona, self)

        # Registrarse para saber cuando se libera un desvio, quiza lo este esperando
        GestorEventos().suscribir_evento(Desvio.EventoLiberado, self.recibir_evento_desvio_liberado)

        # Registrarse para saber cuando se ha parado en una estacion, y poder cambiar la ruta
        GestorEventos().suscribir_evento(Estacion.EventoTrenParado, self.recibir_evento_tren_parado)
        # Registrarse para saber cuando se ha parado en una estacion, y poder reservar los desvios
        GestorEventos().suscribir_evento(Estacion.EventoTrenArrancando, self.recibir_evento_tren_arrancando)

        # Inicializar velocidad (evitar que arranque al posarlo en un tramo con tension)
        self.poner_velocidad(0.0)

    def poner_clase(self, clase):
        self.clase = clase
        self.datos_velocidad = DatosVelocidad(self.clase, self)
        self.EventoAtributosModificados(self).publicar()
        Maqueta().pedir_publicar_trenes()

    def set_auto(self, auto):
        if self.auto != auto:
            self.auto = auto
            self.EventoAtributosModificados(self).publicar()
            Maqueta().pedir_publicar_trenes()
            if auto:
                self.recalcular_ruta()
            else:
                self.liberar_todos_desvios()

    def poner_velocidad(self, velocidad, manual=False, guardar_velocidad=False):
        v_anterior = self.velocidad
        self.velocidad = velocidad
        self.parando = False
        if manual:
            self.t_quitar_modo_manual = tornado.ioloop.IOLoop.current().time() + Tren.TIEMPO_MODO_MANUAL_S
        self.detectar_colisiones()
        self.pasar_velocidad_a_tramos()
        if velocidad == 0 and v_anterior != 0:
            self.EventoVelocidadCero(self).publicar()
        if velocidad != v_anterior:
            self.EventoCambioVelocidad(self).publicar()
        if guardar_velocidad and v_anterior > 0:
            self.velocidad_guardada = v_anterior
        else:
            self.velocidad_guardada = None
        Maqueta().pedir_publicar_trenes()

    def restaurar_velocidad(self):
        if self.velocidad_guardada:
            self.poner_velocidad(self.velocidad_guardada)

    def paro_progresivo(self, empezar=False):
        if self.parando or empezar:
            inc=1
            ms=10*Tren.TIEMPO_PARO_PROGRESIVO_S
            if ms<=0 or self.velocidad < 0: # Si el parametro nos dice que el paro es inmediato o el tren va hacia atras
                self.poner_velocidad(0)
                return # Paro inmediato y no procesamos mas
            while ms<30: # Proteccion para evitar iteraciones demasiado rapidas
                ms*=2
                inc*=2
            self.poner_velocidad(max(0,self.velocidad - inc))
            self.parando=True
            if self.velocidad > 0:
                # Reprogramar
                tornado.ioloop.IOLoop.current().add_timeout(datetime.timedelta(milliseconds=ms), self.paro_progresivo)

    def pasar_velocidad_a_tramos(self, anterior=None):
        print("Tren "+str(self.id)+" =====> ESTE")
        self.tramo.poner_velocidad(self.velocidad_efectiva, minimo=self.datos_velocidad.minimo)
        siguiente = self.tramo.tramo_siguiente()
        velocidad_siguiente = self.velocidad_efectiva
        # Prueba para reducir el efecto de aceleracion al cambiar de tramo
        velocidad_siguiente *= max(0.01, Tren.PORCENTAJE_VELOCIDAD_TRAMO_SIGUIENTE / 100.0)
        #velocidad_siguiente = 0
        if anterior: # and Tren.PORCENTAJE_VELOCIDAD_TRAMO_ANTERIOR < 100.0:
            velocidad_anterior = self.velocidad_efectiva * max(0.01, Tren.PORCENTAJE_VELOCIDAD_TRAMO_ANTERIOR / 100.0)
            #velocidad_anterior = 0
            print("Tren "+str(self.id)+" =====> ANTERIOR")
            anterior.poner_velocidad(velocidad_anterior, minimo=self.datos_velocidad.minimo)
        ######
        if siguiente and (self.estado_colision not in ( Tren.COLISION_INMINENTE, Tren.DESAPARECIDO )) and (siguiente.tren==self or not siguiente.tren):
            print("Tren "+str(self.id)+" =====> SIGUIENTE")
            siguiente.poner_velocidad(velocidad_siguiente, minimo=self.datos_velocidad.minimo)

    def desvio_cambiado(self, desvio):
        """ Recibir notificacion inmediata de que ha cambiado un desvio. """
        # De momento, ignoramos que desvio ha cambiado
        # pero tenemos que pasar la velocidad a los tramos, porque
        # el tramo siguiente podria haber cambiado

        # Intentamos evitar que si hay un tren en el nuevo tramo siguiente, ese tren rebote
        self.detectar_colisiones()

        # Y pasamos la velocidad a los tramos, solo para cambiar la del siguiente
        self.pasar_velocidad_a_tramos()

    def semaforo_cambiado(self, semaforo):
        # De momento, ignoramos
        pass

    def add_sta(self, estacion):
        """ Agregar una estacion al final de la lista de estaciones. """
        if estacion:
            self.sta.append(estacion)
            self.recalcular_ruta()
            self.EventoAtributosModificados(self).publicar()
            Maqueta().pedir_publicar_trenes()

    def remove_sta(self, id_estacion):
        """ Eliminar todas las ocurrencias de una estacion de la lista. """
        self.sta = [ s for s in self.sta if s.id != id_estacion ]
        self.recalcular_ruta()
        self.EventoAtributosModificados(self).publicar()
        Maqueta().pedir_publicar_trenes()

    def rotate_sta(self, n=1):
        """ Pasar la primera estacion de la lista al final de la lista
            de estaciones, siempre que haya mas de una. """
        print("rotate_sta n="+str(n))
        if len(self.sta) > 1:
            n = n%len(self.sta)
            self.sta = self.sta[n:] + self.sta[:n]
            self.recalcular_ruta(reservar=False)
            self.EventoAtributosModificados(self).publicar()
            Maqueta().pedir_publicar_trenes()

    def invertir(self):
        """ Cambiar el sentido de circulacion de un tren. Sirve para girarlo al posarlo sobre la via, o cuando se ha saltado un desvio. """
        # Solo podemos invertir un tren parado, que este en algun tramo
        if self.velocidad==0 and self.tramo and self.estado_colision != Tren.DESAPARECIDO:
           print("Tren "+str(self.id)+" invirtiendo sentido --> "+str(self.tramo.inv.desc))
           self.tramo_a_v_constante = False
           print(str(self.tramo)+".tren=None")
           self.tramo.tren = None
           self.mover(self.tramo.inv)
           self.tramo.tren = self
           self.EventoMovido(self).publicar()
           Maqueta().pedir_publicar_deteccion()

    def mover(self, tramo):
        """ Mover el tren a un nuevo tramo.
            Adicionalmente, libera desvios en automatico.
            Metodo encadenable. """
        self.desaparecido(False)
        self.actualizar_espacio_recorrido()
        if self.tramo_a_v_constante:
            self.recoger_datos_velocidad()

        tramo_anterior = self.tramo
        self.liberar_desvios_segun_tramo(tramo_anterior)
        self.tramo = tramo
        self.t_entrada_en_tramo = self.t_ultima_actualizacion_espacio = tornado.ioloop.IOLoop.current().time()
        self.espacio_recorrido_en_tramo = 0
        self.tramo_a_v_constante = True

        self.recalcular_ruta()

        Maqueta().detectar_colisiones() # Llamada de forma inmediata (TODO: Revisar si es necesaria)
        self.pasar_velocidad_a_tramos(anterior=tramo_anterior)

        self.EventoMovido(self).publicar()
        Maqueta().pedir_publicar_trenes()       
        return self

    #from entryexit import entryexit
    #@entryexit()
    def recalcular_ruta(self, aplicar_margen_seguridad=False, iniciar_por=[], reservar=True):
        """ Recalcula la ruta, opcionalmente aplicando un margen de seguridad.
            La ruta solo se recalcula si hay estaciones y el tren esta en automatico.
            El calculo de la ruta provoca la reserva de desvios. """

        if self.auto and self.sta:
            # Quito mi ruta para que no se considere en el recalculo
            self.ultima_ruta_calculada = []

            s0 = self.sta[0]
            if iniciar_por:
                #print("Tren "+str(self.id)+" buscando camino mas corto DESDE "+iniciar_por[-1].desc+" hacia "+s0.tramo.desc)
                #sp = shortestPath(Maqueta().graph, iniciar_por[-1], s0.tramo)
                print("Tren "+str(self.id)+" buscando camino mas corto DESDE "+iniciar_por[-1].desc+" hacia "+s0.nombre+"-"+s0.sentido)
                sp = shortestPath(Maqueta().graph, iniciar_por[-1], s0)
                if sp: sp = iniciar_por[:-1] + sp
            else:
                #print("Tren "+str(self.id)+" buscando camino mas corto hacia "+s0.tramo.desc)
                #sp = shortestPath(Maqueta().graph, self.tramo, s0.tramo)
                print("Tren "+str(self.id)+" buscando camino mas corto hacia "+s0.nombre+"-"+s0.sentido)
                sp = shortestPath(Maqueta().graph, self.tramo, s0)

            print([ p.desc for p in sp ])

            # Al rotar estaciones interesa recalcular la ruta pero no reservar los desvios.
            # Ya se reservaran al salir de la estacion.
            if not reservar: return

            # Intentar reservar el primer grupo de desvios que hay que atravesar
            desvioEncontrado = False
            desvios_reservados = []
            espacio_hasta_primer_desvio = 0.0
            try:
                for paso in sp:
                    print("paso: "+str(paso))

                    if not isinstance(paso, Tramo): continue

                    if paso.desvio:
                        if aplicar_margen_seguridad and self.velocidad_efectiva != 0 and espacio_hasta_primer_desvio < Tren.ESPACIO_SEGURIDAD_RECALCULO_M:
                            return
                        #print("paso.desvio: "+str(paso.desvio))
                        desvioEncontrado = True
                        if paso in (paso.desvio.verde, paso.desvio.verde.inv):
                            #print("reservando verde")
                            paso.desvio.cambiar(Desvio.VERDE, reserva=self)
                            desvios_reservados.append(paso.desvio)
                        if paso in (paso.desvio.rojo, paso.desvio.rojo.inv):
                            #print("reservando rojo")
                            paso.desvio.cambiar(Desvio.ROJO, reserva=self)
                            desvios_reservados.append(paso.desvio)
                    elif desvioEncontrado:
                        if paso.longitud > Tren.ESPACIO_SEGURIDAD_RECALCULO_M:
                            self.marcar_desvios_reservados(hasta=paso, lista=desvios_reservados)
                            break
                    else: # No es desvio y aun no se ha encontrado
                        if paso == self.tramo: espacio_hasta_primer_desvio += max(0, paso.longitud - self.espacio_recorrido_en_tramo)
                        else:                  espacio_hasta_primer_desvio += paso.longitud
                self.ultima_ruta_calculada = sp

            except ReservaImposible:
                print("Reserva imposible al reservar "+str(paso.desvio)+". Liberando todo.")
                self.esperando_liberacion = paso.desvio
                for paso in sp:
                    if isinstance(paso, Tramo) and paso.desvio:
                        print("Liberando "+str(paso.desvio))
                        paso.desvio.liberar(self)
                self.ultima_ruta_calculada = []
                #if self.tren_colision and self.esperando_liberacion.reserva == self.tren_colision:
                #    self.reclamar_desvios(self.tren_colision)

    def intentar_resolver_colision_frontal(self):
        self.intentar_modificar_ruta()

    def intentar_modificar_ruta(self, favor=False):
        if self.auto and self.sta:
            print(str(self)+": intentar_modificar_ruta")
            nueva_ruta = []
            cambiar_desvio = None
            cambiado = False
            print(str(self)+": intentar_modificar_ruta: tabla_liberacion_desvios="+str(self.tabla_liberacion_desvios))  
            print(str(self)+": intentar_modificar_ruta: ultima_ruta_calculada="+str(self.ultima_ruta_calculada))

            for paso in self.ultima_ruta_calculada:
                print(str(self)+": intentar_modificar_ruta: paso="+str(paso))
                if isinstance(paso, Tramo):
                    if paso.desvio and paso in (paso.desvio.centro, paso.desvio.centro.inv):
                        cambiar_desvio = paso.desvio
                    elif cambiar_desvio and cambiar_desvio == paso.desvio:
                        paso_cambiado = {
                           paso.desvio.verde: paso.desvio.rojo,
                           paso.desvio.rojo: paso.desvio.verde,
                           paso.desvio.verde.inv: paso.desvio.rojo.inv,
                           paso.desvio.rojo.inv: paso.desvio.verde.inv,
                        }[paso]
                        print(str(self)+": intentar_modificar_ruta: evaluando posibilidad de cambiar "+paso.desc+" por "+paso_cambiado.desc)
                        # Quito mi ruta para que no se considere en el recalculo, pero la guardo para recuperarla despues
                        backup = self.ultima_ruta_calculada
                        self.ultima_ruta_calculada = []
                        sp = shortestPath(Maqueta().graph, paso_cambiado, self.sta[0])
                        self.ultima_ruta_calculada = backup
                        if sp:
                           cf = self.analizar_colision_frontal2(nueva_ruta+sp)
                           if not cf:
                               print(str(self)+": intentar_modificar_ruta: cambiado")
                               nueva_ruta.append(paso_cambiado)
                               cambiado = True
                               break
                           else:
                               print(str(self)+": intentar_modificar_ruta: no cambia porque seguiria en colision frontal, en este caso con "+str(cf))
                               cambiar_desvio = None
                    else:
                        cambiar_desvio = None
                nueva_ruta.append(paso)
            print(str(self)+": intentar_modificar_ruta: estado_colision="+str(self.estado_colision))
            print(str(self)+": intentar_modificar_ruta: nueva_ruta="+str(nueva_ruta))
            print(str(self)+": intentar_modificar_ruta: cambiado="+str(cambiado))
            if cambiado or not self.ultima_ruta_calculada:
                print(str(self)+": intentar_modificar_ruta: recalculando a partir de nueva_ruta")
                if nueva_ruta:
                    Maqueta().sendChatMessage(str(self)+" Estoy en "+str(self.tramo)+". Cambio ruta para evitar colisionar. "+str(nueva_ruta)+"... ", origin=self)
                else:
                    Maqueta().sendChatMessage(str(self)+" Estoy en "+str(self.tramo)+". Calculo ruta para intentar avanzar.", origin=self)
                    self.estado_colision = None
                self.recalcular_ruta(iniciar_por=nueva_ruta)
                # Hay un bucle infinito si ultima_ruta_calculada=[] en este punto e intentamos analizar colisiones de nuevo.
                # Tambien hay bucle infinito si esta haciendo un favor.
                if self.ultima_ruta_calculada and not nueva_ruta and not favor:
                    self.analizar_colisiones()
            else:
                print(str(self)+": intentar_modificar_ruta: como no ha cambiado la ruta, libera desvios")
                self.liberar_todos_desvios()
                if self.tren_colision and not favor:
                    print(str(self)+": y pedimos el favor de que sea el "+str(self.tren_colision)+" que modifique.")
                    Maqueta().sendChatMessage(str(self)+" Estoy en "+str(self.tramo)+". No consigo cambiar ruta para evitar colisionar. Se lo pido a "+str(self.tren_colision), origin=self)
                    self.tren_colision.intentar_modificar_ruta(favor=True)

    def perder_reserva(self, desvio):
        print("NOT_IMPLEMENTED: perder_reserva")
        # TODO implementar

    def marcar_desvios_reservados(self, hasta, lista):
        print("Marcando desvios "+str(lista)+" hasta "+str(hasta))
        liberar = [ key for key,value in self.tabla_liberacion_desvios.items() if any(i for i in lista if i in value) ]
        print("     liberar="+str(liberar))
        for l in liberar:
            for d in self.tabla_liberacion_desvios[l]:
                 if d not in lista:
                     print("     liberando "+str(d))
                     d.liberar(self)
            del self.tabla_liberacion_desvios[l]
        if hasta in self.tabla_liberacion_desvios:
            self.tabla_liberacion_desvios[hasta] |= set(lista)
        else:
            self.tabla_liberacion_desvios[hasta] = set(lista)

    def recibir_evento_desvio_liberado(self, evento):
        print(str(self)+": recibir_evento_desvio_liberado: "+str(evento)) # TODO: Esto no acaba de funcionar
        print(str(self)+": recibir_evento_desvio_liberado: esperando_liberacion="+str(self.esperando_liberacion))
        print(str(self)+": recibir_evento_desvio_liberado: estado_colision="+str(self.estado_colision))
        if evento.emisor == self.esperando_liberacion or (self.estado_colision == Tren.FIN_DE_VIA and not self.esperando_liberacion):
           print("recibir_evento_desvio_liberado: se cumplen condicion 1")
           if not evento.por_cambio:
              print("recibir_evento_desvio_liberado: se cumple condicion 2")
              if not evento.por_tren == self:
                  print("recibir_evento_desvio_liberado: se cumplen todas las condiciones")
                  self.recalcular_ruta(aplicar_margen_seguridad=True)

    def recibir_evento_tren_parado(self, evento):
        if evento.tren == self:
            print("recibir_evento_tren_parado")
            if self.sta and (evento.estacion == self.sta[0] or evento.estacion.asociacion == self.sta[0]):
                self.rotate_sta()

    def recibir_evento_tren_arrancando(self, evento):
        if evento.tren == self:
            print("recibir_evento_tren_arrancando")
            self.recalcular_ruta()

    def liberar_todos_desvios(self):
        # Usamos list(...) para clonar las claves, para evitar un error por
        # modificar el tamano del dict mientras iteramos (eliminando entradas).
        for t in list(self.tabla_liberacion_desvios):
            self.liberar_desvios_segun_tramo(t)
        # Eliminar informacion de ruta calculada
        self.ultima_ruta_calculada = []

    def liberar_desvios_segun_tramo(self, tramo):
        if tramo in self.tabla_liberacion_desvios:
            for d in self.tabla_liberacion_desvios[tramo]:
                d.liberar(self)
            del self.tabla_liberacion_desvios[tramo]

    @timed_avg_and_freq(10000)
    def detectar_colisiones(self):
        self.analizar_colisiones()
        vea = self.velocidad_efectiva

        limites = [ LimiteVelocidad(abs(self.velocidad)) ] # Limitar a la velocidad programada

        if not (self.estado_colision == Tren.MODO_MANUAL or self.estado_colision == Tren.MIDIENDO):  # Si es avance manual, no respetamos los limites del tramo
            limites.extend(self.tramo.get_limites())

        if self.estado_colision == Tren.COLISION_INMINENTE:
            limites.append(LimiteColisionInminente())
        elif self.estado_colision_f == Tren.COLISION_FRONTAL:
            #limites.append(LimiteDesvioGirado()) # TODO: Limite especifico. Este simplemente garantiza que no pasa del tramo.
            pass
        elif self.estado_colision == Tren.COLISION_POSIBLE:
            limites.append(LimiteColisionPosible())
        elif self.estado_colision == Tren.CERCA_FIN_DE_VIA:
            limites.append(LimiteCercaFinDeVia())
        elif self.estado_colision == Tren.FIN_DE_VIA:
            s = self.tramo.nodos_siguientes(self.velocidad)
            if len(s)==1 and isinstance(s[0],Muerta):
                limites.append(LimiteViaMuerta())
            else:
                limites.append(LimiteDesvioGirado())
        else: # No hay nada que restrinja la velocidad
            pass
        
        limite_en_el_punto = min([l.calcular_limite(self) for l in limites])

        # Nunca limitar a menos de 1.0... salvo que sea cero
        if limite_en_el_punto > 0.0 and limite_en_el_punto < 1.0:
            limite_en_el_punto = 1.0

        inc = copysign(1,self.velocidad) # Era 2.
        if limite_en_el_punto < abs(self.velocidad_efectiva): # Vamos demasiado rapido. Frenar.
            self.velocidad_efectiva = limite_en_el_punto * copysign(1,self.velocidad)
            print("Tren "+str(self.id)+" frenando: limite: "+str(limite_en_el_punto)+" velocidad_efectiva: "+str(self.velocidad_efectiva))
        elif limite_en_el_punto > abs(self.velocidad_efectiva+inc) and not (self.estado_colision == Tren.MODO_MANUAL or self.estado_colision == Tren.MIDIENDO): # Vamos demasiado lento. Acelerar.
            self.velocidad_efectiva = self.velocidad_efectiva + inc
            print("Tren "+str(self.id)+" acelerando: limite: "+str(limite_en_el_punto)+" velocidad_efectiva: "+str(self.velocidad_efectiva))
        elif limite_en_el_punto > abs(self.velocidad_efectiva) or self.estado_colision == Tren.MODO_MANUAL: # Vamos casi bien. Ajustar.
            print(limites)
            print("ajustando: velocidad_efectiva="+str(self.velocidad_efectiva)+" estado_colision="+str(self.estado_colision)+" velocidad="+str(self.velocidad))
            self.velocidad_efectiva = limite_en_el_punto * copysign(1,self.velocidad)
            print("Tren "+str(self.id)+" ajustando: limite: "+str(limite_en_el_punto)+" velocidad_efectiva: "+str(self.velocidad_efectiva))

        s = self.tramo.nodos_siguientes(self.velocidad)
        if self.velocidad_efectiva == 0.0 and len(s)==1 and isinstance(s[0],Muerta):
            # Si vamos a una via muerta, paramos completamente el tren (fin de trayecto).
            self.velocidad = 0.0
            self.EventoVelocidadCero(self).publicar()
            Maqueta().pedir_publicar_trenes()

        if self.velocidad_efectiva != vea:
            if self.tramo_a_v_constante:
                print("El tren "+str(self.id)+" ya no circula a velocidad constante por el tramo "+self.tramo.desc)
                self.tramo_a_v_constante = False
            if self.velocidad_efectiva == 0:
                self.EventoVelocidadEfectivaCero(self, vea).publicar()
            self.EventoCambioVelocidadEfectiva(self, vea, self.velocidad_efectiva).publicar()
            self.pasar_velocidad_a_tramos()
            Maqueta().pedir_publicar_trenes() # para publicar la velocidad efectiva

    def desaparecido(self, d=True):
        if d:
            self.estado_colision = Tren.DESAPARECIDO
            self.EventoDesaparecido(self).publicar()
            if self.clase=="desconocido":
                self.auto_quitar = tornado.ioloop.IOLoop.current().add_timeout(datetime.timedelta(seconds=10), self.quitar)
                self.quitar()

        elif self.estado_colision == Tren.DESAPARECIDO:
            if self.auto_quitar: tornado.ioloop.IOLoop.current().remove_timeout(self.auto_quitar)
            self.estado_colision = None
            self.EventoEncontrado(self).publicar()
            self.analizar_colisiones()
        Maqueta().pedir_publicar_trenes()

    def quitar(self):
        # Evitar que un tren quitado reciba eventos
        GestorEventos().eliminar_suscriptor(self.recibir_evento_cambio_zona)
        GestorEventos().eliminar_suscriptor(self.recibir_evento_desvio_liberado)
        GestorEventos().eliminar_suscriptor(self.recibir_evento_tren_parado)

        # Si tenia algun desvio reservado, liberarlo
        self.liberar_todos_desvios()

        # Eliminar el tren de los tramos en los que estuviera
        for t in Maqueta.tramos:
            if Maqueta.tramos[t].tren_en_tramo_fisico() == self:
                Maqueta.tramos[t].quitar_tren()
                Maqueta.tramos[t].inv.quitar_tren()

        # Avisar al mundo de la eliminacion
        self.EventoQuitado(self).publicar()


    @timed_avg_and_freq(10000)
    def analizar_colisiones(self):
        self.actualizar_espacio_recorrido()
        aec = self.estado_colision
        aec_f = self.estado_colision_f

        if aec == Tren.DESAPARECIDO:
            return

        if aec == Tren.MODO_MANUAL and self.t_quitar_modo_manual < tornado.ioloop.IOLoop.current().time():
            self.t_quitar_modo_manual = None
            self.estado_colision = None
            self.poner_velocidad(0.0)
            print("QUITANDO MANUAL!!")
        elif self.t_quitar_modo_manual:
            self.estado_colision = Tren.MODO_MANUAL
            print("MANUAL!!")

        if not (self.estado_colision == Tren.MODO_MANUAL or self.estado_colision == Tren.MIDIENDO):
          siguiente = self.tramo.tramo_siguiente(self.velocidad)

          if self.velocidad == 0.0:
            # No nos movemos, asi que no hay posibilidad de colisionar.
            if self.estado_colision:
                print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" relaja el estado de colision porque no se mueve")
                self.estado_colision = None
                self.tren_colision = None
          else:
            # Nos movemos, es necesario analizar la situacion

            # Analizamos colision frontal
            ft = self.analizar_colision_frontal2()
            if ft and self.estado_colision_f!=Tren.COLISION_FRONTAL:
                print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" detecta COLISION FRONTAL porque encuentra el tren "+str(ft.id)+" en el tramo "+ft.tramo.desc)
                self.estado_colision_f = Tren.COLISION_FRONTAL
                self.tren_colision_f = ft
            elif not ft and self.estado_colision_f==Tren.COLISION_FRONTAL:
                print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" relaja el estado de colision frontal")
                self.estado_colision_f = None
                self.tren_colision_f = None

            if siguiente:
                # Analizamos colision por otros motivos (alcance o X)
                siguiente_tren = siguiente.tren_en_tramo_fisico()
                if siguiente_tren and siguiente_tren!=self:  # TODO Arreglar que cuando un tren esta entre dos tramos no va hacia atras
                    if self.estado_colision!=Tren.COLISION_INMINENTE:
                        print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" detecta COLISION INMINENTE porque el tramo siguiente es "+siguiente.desc+" y tiene el tren "+str(siguiente_tren.id))
                        self.estado_colision = Tren.COLISION_INMINENTE
                        self.tren_colision = siguiente_tren

                else: # No hay tren en el primer tramo, miramos el segundo
                    segundo = siguiente.tramo_siguiente(self.velocidad)
                    if segundo:
                        segundo_tren = segundo.tren_en_tramo_fisico()
                        if segundo_tren and segundo_tren!=self:
                            # Obtenemos el tramo en el que esta realmente el tren. Asumimos que deteccion y tren cuadran.
                            segundo = segundo_tren.tramo
                            # El producto de las velocidades de los trenes por las polaridades
                            # de los tramos es positivo si los trenes se persiguen.
                            # Y es negativo si van uno contra otro. Esto genera colision inminente.
                            # Cero si esta parado el otro tren. Tambien inminente.
                            if (segundo.polaridad * self.tramo.polaridad * segundo_tren.velocidad * self.velocidad) <= 0:
                                if self.estado_colision!=Tren.COLISION_INMINENTE:
                                    print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" detecta COLISION INMINENTE porque el tramo siguiente al siguiente es "+segundo.desc+" y tiene el tren "+str(segundo_tren.id)+" circulando en sentido contrario o parado")
                                    self.estado_colision = Tren.COLISION_INMINENTE
                                    self.tren_colision = segundo_tren
                            else:
                                if self.estado_colision!=Tren.COLISION_POSIBLE:
                                    print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" detecta COLISION POSIBLE porque el tramo siguiente al siguiente es "+segundo.desc+" y tiene el tren "+str(segundo_tren.id))
                                    self.estado_colision = Tren.COLISION_POSIBLE
                                    self.tren_colision = segundo_tren

                        else: # todo libre dos tramos adelante
                            # No se preve colision
                            if self.estado_colision:
                                print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" relaja el estado de colision al no detectar trenes en los dos tramos siguientes")
                                self.estado_colision = None
                                self.tren_colision = None

                    else: # not segundo:
                        if self.estado_colision!=Tren.CERCA_FIN_DE_VIA:
                            print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" detecta CERCA DE FIN DE VIA porque el tramo siguiente es "+siguiente.desc+" y no hay otro tramo siguiente")
                            self.estado_colision = Tren.CERCA_FIN_DE_VIA
                            self.tren_colision = None

            elif not siguiente:
                # Fin de via, no hay tramo siguiente ...
                if self.estado_colision!=Tren.FIN_DE_VIA:
                    print("Tren "+str(self.id)+" en tramo "+self.tramo.desc+" detecta FIN DE VIA")
                    self.estado_colision = Tren.FIN_DE_VIA
                    self.tren_colision = None

        if aec != self.estado_colision or aec_f != self.estado_colision_f:
            if self.estado_colision_f == Tren.COLISION_FRONTAL:
                self.intentar_resolver_colision_frontal()
            #if self.estado_colision == Tren.COLISION_INMINENTE:
            #    if not self.reclamar_desvios(self.tren_colision):
            #        # Reclamar desvios al tren con el que colisionamos no ha servido
            #        self.intentar_modificar_ruta()
            Maqueta().pedir_publicar_trenes()
                        
    def analizar_colision_frontal2(self, ruta=None):
        if not (self.auto and self.sta):
            return None

        #print(str(self)+": analizar_colision_frontal2")
        tramos_sin_salida_analizados = 0

        if not ruta: ruta = self.ultima_ruta_calculada

        for i,t in enumerate(ruta):
            if t.desvio: # Iterar solo por los tramos
                continue

            if tramos_sin_salida_analizados > 1:
                break

            #print(str(self)+": analizar_colision_frontal2: analizando "+str(t))
            # Sumar 1 si el tramo tiene salida
            d=None
            for s in ruta[i+1:]:
                #print(str(self)+": analizar_colision_frontal2: s="+str(s))

                if not isinstance(s, Tramo): break # Salir si llegamos a via muerta

                if d:
                    # El anterior formaba parte de un desvio, pero no lo hemos contado
                    # porque no era el centro de ese desvio. Este sera el centro, asi
                    # que lo ignoramos completamente y seguimos con el siguiente.
                    d=None
                    continue

                d=s.desvio
                if not d:
                    break
                if s in ( d.centro, d.centro.inv ):
                    #print(str(self)+": analizar_colision_frontal2: salida desde "+str(s))
                    tramos_sin_salida_analizados+=1
                    break

            # Mirar si hay tren frontal en tramo siguiente
            st = next( (t for t in ruta[i+1:] if isinstance(t,Tramo) and not t.desvio), None)

            if not (st and isinstance(st, Tramo)): break

            st_tren = st.tren_en_tramo_fisico()
            if st_tren and st_tren!=self:
                    # Hay tren. Frontal?
                    if st.tren == st_tren: # El tren esta realmente en el tramo siguiente. Frontal si va marcha atras o parado.
                        frontal = (st_tren.velocidad <= 0)
                    elif st.inv.tren == st_tren: # El tren esta en el invertido. Frontal si va marcha alante o parado.
                        frontal = (st_tren.velocidad >= 0)
                    else: # El tren esta en otro tramo (ej. X). Frontal solo si parado.
                        frontal = (st_tren.velocidad == 0)
                    if frontal:
                        print(str(self)+": analizar_colision_frontal2 -->"+str(st_tren))
                        return st_tren

        #print(str(self)+": analizar_colision_frontal2 -->None")
        return None


    def reclamar_desvios(self, tren):
        print(str(self) + ": reclamar_desvios tren="+str(tren))
        print("Esperando liberacion de "+str(self.esperando_liberacion))
        if self.esperando_liberacion and self.esperando_liberacion.reserva == tren:
            tren.liberar_todos_desvios()
            return True
        return False

    def actualizar_espacio_recorrido(self):
        # e = v x t
        ahora = tornado.ioloop.IOLoop.current().time()
        anterior = self.espacio_recorrido_en_tramo
        self.espacio_recorrido_en_tramo += (self.estimar_velocidad() * (ahora - self.t_ultima_actualizacion_espacio))
        self.t_ultima_actualizacion_espacio = ahora
        if anterior < Tren.ESPACIO_LIBERAR_DESVIOS_M and self.espacio_recorrido_en_tramo >= Tren.ESPACIO_LIBERAR_DESVIOS_M:
            self.liberar_desvios_segun_tramo(self.tramo)
        self.revisar_cambio_zonas()

    def revisar_cambio_zonas(self):
        self.zonas = [ z for z in Maqueta().zonas if z.tiene_tren(self) ]

    def recibir_evento_cambio_zona(self, evento):
        print("Tren "+str(self.id)+" recibiendo evento de cambio de zona")
        self.altavoces.nuevo(audio.Combi([z.altavoces for z in self.zonas if z.altavoces != None]))
        print(self.altavoces)

    def buscar_y_reproducir_sonido(self, sonido, callback=None):
        s = audio.AudioSystem().sonido(self.clase, sonido)
        if s:
            print("Encontrado sonido ", s, " para tren ", self)
            self.reproducir_sonido(s, callback=callback)
        else:
            print("Sonido "+sonido+" no encontrado para clase "+self.clase)

    def reproducir_sonido_estacion(self, estacion, texto, callback=None):
        print(str(self)+": reproducir_sonido_estacion("+str(estacion)+", "+str(texto)+")")
        if self.sta:
            e = self.sta[0]
            if len(self.sta)>1 and e in ( estacion, estacion.asociacion ):
                e = self.sta[1]
            texto_completo = texto.format(tren=self, estacion=estacion.desc, destino=e.desc)
            print("reproducir_sonido_estacion: texto_completo="+texto_completo)
            TTS().tts(texto_completo, self.reproducir_sonido, callback_fin=callback)

    def reproducir_sonido(self,x,callback=None):
        print(str(self)+": reproducir_sonido: x="+str(x)+" altavoces="+str(self.altavoces))
        print("callback="+str(callback))
        f = audio.Wav(x)
        f.canales = self.altavoces
        f.callback = callback
        s = audio.AudioSystem()
        s.nueva_fuente(f)

    def recoger_datos_velocidad(self):
        tiempo = self.t_ultima_actualizacion_espacio - self.t_entrada_en_tramo
        print("El tren "+str(self.id)+", de clase "+self.clase+" ha recorrido " + self.tramo.desc + ", de "+str(self.tramo.longitud)+" metros, a velocidad constante efectiva " + str(self.velocidad_efectiva) + " en " + str(tiempo) + " segundos. Cree que el tramo tiene "+str(self.espacio_recorrido_en_tramo)+" metros (error: "+str(100.0*self.espacio_recorrido_en_tramo/self.tramo.longitud-100.0)+"%).")
        print("MEDIDA_V_CONSTANTE,"+str(self.id)+","+self.clase+"," + self.tramo.desc + ","+str(self.tramo.longitud)+"," + str(self.velocidad_efectiva) + "," + str(tiempo) + "," + str(self.espacio_recorrido_en_tramo) + "," + str(100.0*self.espacio_recorrido_en_tramo/self.tramo.longitud-100.0)+"%")

        vel_real = self.tramo.longitud/tiempo
        self.datos_velocidad.anadir_punto(abs(self.velocidad_efectiva), vel_real)


    def estimar_velocidad(self):
        # v = f(velocidad_efectiva, clase)
        v = abs(self.velocidad_efectiva)

        # Sea como sea la grafica, la velocidad de un tren parado es 0.
        if(v==0):
           return 0

        # La velocidad estimada tiene el signo de la velocidad efectiva, y
        # el valor es funcion de los datos de velocidad
        s = copysign(1, self.velocidad_efectiva)
        return s * self.datos_velocidad.f(v)

    def cambiar_opcion(self, opc, valor):
        self.opciones_activas[opc] = (self.opciones_activas[opc][0], valor)
        Maqueta().pedir_publicar_trenes()

    def demo(self, d):
        self.sta = []
        for e in d.estaciones: self.add_sta(e)
        self.set_auto(True);
        self.buscar_y_reproducir_sonido("silbato",lambda fuente_sonido: self.poner_velocidad(60))

    def diccionario_atributos(self):
        return {
            "id": self.id,
            "clase": self.clase,
            "velocidad": self.velocidad,
            "v_ef": self.velocidad_efectiva,
            "v_g": self.velocidad_guardada,
            "estado": self.estado_colision or self.estado_colision_f,
            "tramo": self.tramo.desc if self.tramo else None,
            "sta": [s.diccionario_atributos() for s in self.sta],
            "auto": self.auto,
            "opciones_activas": [ { "opcion": k.json_friendly_dict(), "valor": v } for k,v in self.opciones_activas ]
        }

class LimiteVelocidad(object):
    def __init__(self, limite_velocidad):
        self.limite_velocidad = limite_velocidad
        self._inv = self

    def get_limite_velocidad(self, tren):
        return self.limite_velocidad

    def calcular_limite(self, tren):
        return self.get_limite_velocidad(tren)

    def inv(self):
        return self._inv

    def __repr__(self):
        return type(self).__name__+"("+str(self.limite_velocidad)+")"

class LimiteCondicional(LimiteVelocidad):
    def __init__(self, condicion, limite_true, limite_false, inv=None):
        self.condicion = condicion
        self.limite_true = limite_true
        self.limite_false = limite_false
        self._inv = inv or LimiteCondicional(condicion, limite_true.inv(), limite_false.inv(), inv=self)

    def get_limite_velocidad(self, tren):
        if self.condicion(maqueta):
            return self.limite_true.get_limite_velocidad(tren)
        else:
            return self.limite_false.get_limite_velocidad(tren)

    def calcular_limite(self, tren):
        if self.condicion(maqueta, tren):
            return self.limite_true.calcular_limite(tren)
        else:
            return self.limite_false.calcular_limite(tren)

    def __repr__(self):
        return type(self).__name__+"(condicion,"+str(self.limite_true)+","+str(self.limite_false)+")"


class ForzadoAPartirDe(LimiteVelocidad):
    def __init__(self, velocidad_inicio, inicio_forzado, forzar_en, limite_velocidad, debug=False):
        LimiteVelocidad.__init__(self, limite_velocidad)
        self.inicio_forzado = inicio_forzado
        self.forzar_en = forzar_en
        self.velocidad_inicio = velocidad_inicio
        self.debug = debug
        self.last_debug = None

    def get_inicio_forzado(self, tren):
        return self.inicio_forzado

    def get_forzar_en(self, tren):
        return self.forzar_en

    def get_velocidad_inicio(self, tren):
        return self.velocidad_inicio

    def calcular_limite(self, tren):
        inicio_forzado = self.get_inicio_forzado(tren)
        forzar_en = self.get_forzar_en(tren)
        velocidad_inicio = self.get_velocidad_inicio(tren)
        limite_velocidad = self.get_limite_velocidad(tren)

        punto_inicio = inicio_forzado * tren.tramo.longitud / 100 # Siempre positivo
        punto_a_forzar = forzar_en * tren.tramo.longitud / 100    

        # Calcular velocidad limite en ese punto de la via
        if abs(tren.espacio_recorrido_en_tramo) < abs(punto_inicio):      # Aun no empezamos a limitar
            limite_en_el_punto = velocidad_inicio
        elif abs(tren.espacio_recorrido_en_tramo) >= abs(punto_a_forzar): # Forzamos
            limite_en_el_punto = limite_velocidad
        else:                                                             # Calculamos
            # y = mx + b ; b=v_inicio ; x=e_recorrido-punto_inicio ; m=delta_y/delta_x=(lim-v_inicio)/(p_forzar-p_inicio)
            limite_en_el_punto = abs(velocidad_inicio) + (limite_velocidad - abs(velocidad_inicio)) * (abs(tren.espacio_recorrido_en_tramo)-punto_inicio) / (punto_a_forzar - punto_inicio)

        if self.debug:
            m = str(self) + " calcular_limite espacio_recorrido="+str(tren.espacio_recorrido_en_tramo)+" limite_en_el_punto="+str(limite_en_el_punto)
            if m != self.last_debug:
                print(m)
                self.last_debug = m
        return limite_en_el_punto

    def __repr__(self):
        return type(self).__name__+"("+str(self.velocidad_inicio)+","+str(self.forzar_en)+","+str(self.limite_velocidad)+")"

class LimiteViaMuerta(ForzadoAPartirDe):
    def __init__(self):
        #                               velocidad_inicio,                  inicio_forzado, forzar_en, limite_velocidad
        ForzadoAPartirDe.__init__(self, LimiteCercaFinDeVia.VELOCIDAD_FIN, None,           None,      0) # inicio_forzado y forzar_en = None porque lo calculamos debajo

    def get_inicio_forzado(self, tren):
        if tren.velocidad_efectiva > 0: # Entra de frente a la via muerta
            return 50.0 # Frena a partir de la mitad del tramo
        else: # Entra marcha atras a la via muerta
            return 0    # Frena desde el principio

    def get_forzar_en(self, tren):
        if tren.velocidad_efectiva > 0: # Entra de frente a la via muerta
            return 75.0
        else: # Entra marcha atras a la via muerta
            return 10.0

class LimiteDesvioGirado(ForzadoAPartirDe):
    @expuesto
    def PORCENTAJE_INICIO_FORZADO():
        """Porcentaje del tramo en el que se inicia la parada cuando el siguiente desvio esta girado."""
        return 60

    @expuesto
    def PORCENTAJE_FORZAR_EN():
        """Porcentaje del tramo en el que el tren se detiene por completo cuando el siguiente desvio
           esta girado."""
        return 80

    def __init__(self):
        ForzadoAPartirDe.__init__(self, velocidad_inicio=LimiteCercaFinDeVia.VELOCIDAD_FIN,
                                        inicio_forzado=LimiteDesvioGirado.PORCENTAJE_INICIO_FORZADO,
                                        forzar_en=LimiteDesvioGirado.PORCENTAJE_FORZAR_EN,
                                        limite_velocidad=0)

class LimiteColisionInminente(ForzadoAPartirDe):
    @expuesto
    def VELOCIDAD_INICIO():
        """Velocidad de entrada al tramo cuando existe riesgo de colision inminente."""
        return 20

    @expuesto
    def MARGEN_SEGURIDAD_M():
        """Distancia al tramo siguiente a partir de la cual no se considera seguro
           continuar avanzando y por tanto hay que iniciar la parada."""
        return 1.00

    @expuesto
    def PORCENTAJE_TRAMO_FRENADA():
        """Porcentaje del tramo que dura la frenada desde VELOCIDAD_INICIO hasta 0."""
        return 10

    def __init__(self):
        #                               velocidad_inicio,                         inicio_forzado, forzar_en, limite_velocidad
        ForzadoAPartirDe.__init__(self, LimiteColisionInminente.VELOCIDAD_INICIO, None,           None,      0) # Inicio y forzado dependen del tramo

    def get_inicio_forzado(self, tren):
        ret = 100.0 * ( tren.tramo.longitud - float(LimiteColisionInminente.MARGEN_SEGURIDAD_M) ) / tren.tramo.longitud
        #print("get_inicio_forzado -->"+str(ret) #TODO)
        return max(0, ret) # es un %

    def get_forzar_en(self, tren):
        return LimiteColisionInminente.PORCENTAJE_TRAMO_FRENADA + self.get_inicio_forzado(tren)

class LimiteColisionPosible(ForzadoAPartirDe):
    debug = False

    @expuesto
    def PORCENTAJE_INICIO_FORZADO():
        """Porcentaje del tramo en el que el tren empieza a frenar de forma independiente de la
           velocidad del tren que le precede."""
        return 60

    @expuesto
    def PORCENTAJE_FORZAR_EN():
        """Porcentaje del tramo en el que el tren alcanza la velocidad minima, igual a la
           velocidad de entrada para una colision inminente."""
        return 90

    def __init__(self):
        ForzadoAPartirDe.__init__(self,
                                  velocidad_inicio=100,
                                  inicio_forzado=LimiteColisionPosible.PORCENTAJE_INICIO_FORZADO,
                                  forzar_en=LimiteColisionPosible.PORCENTAJE_FORZAR_EN,
                                  limite_velocidad=LimiteColisionInminente.VELOCIDAD_INICIO)

    def calcular_limite(self, tren):
        limite_forzado_a_partir_de = ForzadoAPartirDe.calcular_limite(self,tren)
        if self.debug:
            print("LimiteColisionPosible: limite_forzado_a_partir_de="+str(limite_forzado_a_partir_de))

        v_estimada_tren_delante = tren.tren_colision.estimar_velocidad()
        if self.debug:
            print("LimiteColisionPosible: v_estimada_tren_delante="+str(v_estimada_tren_delante))

        v_equivalente_para_este_tren = tren.datos_velocidad.encontrar_x_para_y_poco_menor_que(v_estimada_tren_delante)
        if self.debug:
            print("LimiteColisionPosible: v_equivalente_para_este_tren="+str(v_equivalente_para_este_tren))

        dec = 2
        # Nunca por debajo de la velocidad del de delante
        # Frenada lenta (desaceleracion) respecto a la velocidad actual
        # Nunca por debajo de LimiteColisionInminente.VELOCIDAD_INICIO
        limite_colision = max(v_equivalente_para_este_tren, abs(tren.velocidad_efectiva-dec), LimiteColisionInminente.VELOCIDAD_INICIO)
        if self.debug:
            print("LimiteColisionPosible: limite_colision="+str(limite_colision))

        limite = min(limite_forzado_a_partir_de, limite_colision)
        if self.debug:
            print("LimiteColisionPosible: limite="+str(limite))

        return limite


class LimiteCercaFinDeVia(ForzadoAPartirDe):
    @expuesto
    def VELOCIDAD_FIN():
        """Velocidad de seguridad cuando el tren se acerca a un tramo sin salida (via muerta o desvio girado)."""
        return 38

    @expuesto
    def PORCENTAJE_INICIO_FORZADO():
        """Porcentaje del tramo en el que se inicia la reduccion de velocidad al acercarse a un tramo sin salida."""
        return 65

    @expuesto
    def PORCENTAJE_FORZAR_EN():
        """Porcentaje del tramo en el que se adopta la VELOCIDAD_FIN."""
        return 85

    def __init__(self):
        ForzadoAPartirDe.__init__(self, velocidad_inicio=100,
                                        inicio_forzado=LimiteCercaFinDeVia.PORCENTAJE_INICIO_FORZADO,
                                        forzar_en=LimiteCercaFinDeVia.PORCENTAJE_FORZAR_EN,
                                        limite_velocidad=LimiteCercaFinDeVia.VELOCIDAD_FIN)

class LimiteSemaforoRojo(ForzadoAPartirDe):
    def __init__(self, maximo=100, porcentaje=20.0, inicio_forzado=0, debug=False):
        #                               velocidad_inicio, inicio_forzado, forzar_en,  limite_velocidad
        ForzadoAPartirDe.__init__(self, maximo,           inicio_forzado, porcentaje, 0, debug)
        self._inv = LimiteVelocidad(100.0)
        self._inv._inv = self  # Aunque no creo que sea necesario...

class LimiteAcercamiento(ForzadoAPartirDe):
    def __init__(self, velocidad_inicio, forzar_en, limite_velocidad):
        #                               velocidad_inicio, inicio_forzado, forzar_en, limite_velocidad
        ForzadoAPartirDe.__init__(self, velocidad_inicio, 0,              forzar_en, limite_velocidad)
        self._inv = LimiteVelocidad(100.0)
        self._inv._inv = self  # Aunque no creo que sea necesario...

class LimiteSiTrenEnTramoEstacion(LimiteCondicional):
    def __init__(self, estacion, tramo, limite_aplicable):
        self.estacion = estacion
        self.tramo = tramo
        LimiteCondicional.__init__(self, self.tren_en_tramo_estacion, limite_aplicable, LimiteVelocidad(100) )
        self._inv = LimiteVelocidad(100)
        self.tren_parando = None
        self.debug = False

    def tren_en_tramo_estacion(self, maqueta, tren):
        if(self.debug): print(str(self)+" tren_en_tramo_estacion(...,"+str(tren))
        ret = False
        if (tren.tramo == self.tramo):
            if(self.debug): print(str(self)+" tren en "+str(self.tramo))
            if self.estacion.tren_parado_en_estacion == tren: return True
            if tren.auto:
                ret = (self.estacion == tren.sta[0] or self.estacion.asociacion == tren.sta[0])
            else:
                ret = (self.estacion in tren.sta or self.estacion.asociacion in tren.sta)
        if(self.debug): print(str(self)+" ret="+str(ret))
        return ret

class LimiteCondicionalEstacion(LimiteSiTrenEnTramoEstacion):
    def __init__(self, estacion):
        LimiteSiTrenEnTramoEstacion.__init__(self, estacion, estacion.tramo, LimiteEstacion(estacion))

class LimiteCondicionalTramoAnteriorEstacion(LimiteSiTrenEnTramoEstacion):
    def __init__(self, estacion, tramo, v_intercambio):
        LimiteSiTrenEnTramoEstacion.__init__(self, estacion, tramo, LimiteAcercamiento(40, 100, v_intercambio))
        self.debug = True  ## FIXME: No funciona el control del tramo previo

class LimiteEstacion(ForzadoAPartirDe):
    debug = False

    def __init__(self, estacion):
        #                               velocidad_inicio, inicio_forzado, forzar_en, limite_velocidad
        ForzadoAPartirDe.__init__(self, 100,              0,              None,      0) # Reescribimos get_forzar_en
        self.t_forzado = 0
        self.estacion = estacion

    def get_forzar_en(self, tren):
        return self.estacion.punto_parada

    def calcular_limite(self, tren):
        limite = ForzadoAPartirDe.calcular_limite(self,tren)
        if limite > 0:
            #print("LimiteEstacion: No esta parado")
            self.t_forzado = 0 # Anotar que NO esta parado
        else:
            #print("LimiteEstacion: Limite 0.")
            ahora = tornado.ioloop.IOLoop.current().time()
            #print("LimiteEstacion: t_parada="+str(self.estacion.t_parada)+" ahora="+str(ahora)+" t_forzado="+str(self.t_forzado)+" a-t="+str(ahora - self.t_forzado))
            if self.t_forzado == 0:
                print("Tren "+str(tren)+" parado en estacion")
                self.t_forzado = ahora # Anotar cuando se ha parado
                self.estacion.tren_parado(tren)
            if (ahora - self.t_forzado) > self.estacion.t_parada:
                self.estacion.tren_arrancando(tren)
                limite = 100 # Arrancar tras un tiempo de parada
        if LimiteEstacion.debug:
            print("LimiteEstacion: limite="+str(limite))
        return limite

class LimiteBajada(ForzadoAPartirDe):
    @expuesto
    def PORCENTAJE_REDUCCION():
        """Porcentaje que se reducira la velocidad de los trenes en los tramos
           de bajada, para que no se aceleren en exceso."""
        return 50

    def __init__(self, inicio_forzado, forzar_en):
        ForzadoAPartirDe.__init__(self, velocidad_inicio=100,
                                        inicio_forzado=inicio_forzado,
                                        forzar_en=forzar_en,
                                        limite_velocidad=None) # Dinamico
        self._inv = LimiteVelocidad(100.0)
        self._inv._inv = self  # Aunque no creo que sea necesario...

    def get_limite_velocidad(self, tren):
        return tren.velocidad * (100 - LimiteBajada.PORCENTAJE_REDUCCION) / 100

class Zona(Desc, object):
    class EventoZona(Evento):
        def __init__(self, emisor, tren):
            Evento.__init__(self,emisor)
            self.zona = emisor
            self.tren = tren

    class EventoEntraTren(EventoZona):
        """ Un tren ha entrado en la zona """
        pass
    class EventoSaleTren(EventoZona):
        """ Un tren ha salido de la zona """
        pass

    def __init__(self, desc):
        self.desc = desc
        self.tramos = {}
        self.trenes = []
        self.altavoces = None
        Maqueta().zonas.append(self)

    def incluye(self, tramo, desde=float("-inf"), hasta=float("inf"), inv=True):
        self.tramos[tramo]=dict(desde=desde, hasta=hasta)
        if inv:
            self.tramos[tramo.inv]=dict(desde=100-hasta,hasta=100-desde)
        #print(self.desc+" tramos="+str({ t.desc: (v["desde"], v["hasta"]) for t,v in self.tramos.iteritems()}))
        return self  # El metodo es encadenable

    def tiene_tren(self, tren):
        ret = self._tiene_tren(tren)
        if ret and tren not in self.trenes:
            self.trenes.append(tren)
            Zona.EventoEntraTren(self, tren).publicar()
            Tren.EventoCambioZona(tren).publicar()
        if tren in self.trenes and not ret:
            self.trenes.remove(tren)
            Zona.EventoSaleTren(self, tren).publicar()
            Tren.EventoCambioZona(tren).publicar()
        return ret

    def _tiene_tren(self,tren):
        if tren.tramo not in self.tramos:
            return False
        prt = 100.0 * (tren.espacio_recorrido_en_tramo / tren.tramo.longitud)
        return self.tramos[tren.tramo]["desde"] <= prt and prt < self.tramos[tren.tramo]["hasta"]

    def suena_por(self,combinacion_altavoces):
        self.altavoces = combinacion_altavoces
        return self  # El metodo es encadenable


class ZonaRestringida(object):
    # Comportamientos automaticos de los desvios (para cerrar las entradas de la X)
    #       Desvio   7, al ponerse  VERDE  cambiara     el desvio  11    a    ROJO    y el desvio  12    a    VERDE
    #Maqueta.desvios[ 7].auto[Desvio.VERDE].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    #Maqueta.desvios[10].auto[Desvio.ROJO ].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    #Maqueta.desvios[11].auto[Desvio.VERDE].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})
    #Maqueta.desvios[12].auto[Desvio.ROJO ].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})

    #ZonaRestringida({Maqueta.desvios[7]:Desvio.VERDE, Maqueta.desvios[10]:Desvio.ROJO},
    #                {Maqueta.desvios[11]:Desvio.VERDE, Maqueta.desvios[12]:Desvio.ROJO})

    def __init__(self, *args):
        """ Automatiza los desvios de acceso a una zona restringida.
            Los parametros son los grupos de accesos que dan acceso a la zona.
            Cada parametro es un dict con los desvios que dan acceso y el color necesario para acceder. """
        self.grupos = args
        print("self.grupos="+str(self.grupos))
        for grupo_accesos in self.grupos:
            print("grupo_accesos="+str(grupo_accesos)+" - "+str(type(grupo_accesos)))
            for acceso, color in grupo_accesos.items():
                print(acceso, color)
                acceso.auto[color].update(self.opuesto_otros(grupo_accesos))

    def opuesto_otros(self, grupo_accesos):
        """ Agrega todos los otros accesos y cambia los colores, devolviendo un solo dict. """
        #data = [item for sublist in self.puntos for item in sublist] # Truco para aplanar una lista
        return { k:color_opuesto for m in self.grupos if m!=grupo_accesos for k,c in m.items() for color_opuesto in list(Coloreado.colores.values()) if color_opuesto != c }

class Shell(object):
    def __init__(self, key, desc, cmdline):
        self.key = key
        self.desc = desc
        self.cmdline = cmdline
        Maqueta().shells[key]=self

def conexion(a,b):
    a.b.append(b)
    b.a.append(a)
    a.inv.a.append(b.inv)
    b.inv.b.append(a.inv)

@singleton
class Maqueta:
    desvios = {}
    semaforos = {}
    tramos = {}
    estaciones = {}
    chips_vias = []
    chips_detectores = []
    locomotoras = {}
    luces = {}
    zonas = []
    shells = {}
    demos = {}
    pista_medicion = None
    modo_dummy = False

    d = 1

    @timed_avg_and_freq(1000)
    def detectar(self):
        cambio = False
        for chip in self.chips_detectores:
            cambio |= chip.detectar()

    @timed_avg_and_freq(5000)
    def detectar_colisiones(self):
        for tren in Tren.trenes:
            tren.detectar_colisiones()
        if Maqueta.modo_dummy:
            for tren in Tren.trenes:
                if tren.espacio_recorrido_en_tramo >= tren.tramo.longitud:
                    t0 = tren.tramo
                    t1 = t0.tramo_siguiente()
                    print("modo_dummy: Tren "+str(tren)+" en tramo "+str(t0)+" saltando a "+str(t1))
                    t1.deteccion(True)
                    t0.deteccion(False)

    def __init__(self):
        self.pubvel = True
        self.pubdet = True
        self.pubdes = True
        self.pubsem = True
        self.pubtre = True
        self.publuz = True
        self.pubpar = True
        self.pubtir = True
        self.pubwea = True
        self.cnt_pub_velocidades = 0
        self.cnt_pub_trenes = 0
        GestorEventos().suscribir_evento(EventoParametros, self.recibir_evento_parametros)
        GestorEventos().suscribir_evento(Tira.EventoCambiado, self.recibir_evento_tira)
        GestorEventos().suscribir_evento(Weather.EventoCambiado, self.recibir_evento_weather)

    def validar(self):
        for n in Nodo.nodos:
           try:
               n.validate()
           except:
               print("ERROR validando nodo "+str(n))
               raise
        #from bellman_ford import Graph
        #self.bf_graph = Graph()
        self.graph = {}
        for n in Nodo.nodos:
            destinos = {}
            for d in n.b:
                dist = 1
                try: dist = d.longitud
                except: pass
                destinos[d] = dist
                #self.bf_graph.add_edge(n,d,dist)
            #destinos[n.inv] = 999999
            self.graph[n] = destinos
        print("==========================================")
        for e in Maqueta.estaciones.values():
            if isinstance(e,Estacion):
                self.graph[e.tramo][e] = 0
                self.graph[e] = {}
                #self.bf_graph.add_edge(e.tramo,e,0)
                print(e)

        for e in Maqueta.estaciones.values():
            if isinstance(e,AsociacionEstaciones):
                for x in e.estaciones:
                    self.graph[x][e] = 0
                    self.graph[e] = {}
                    #self.bf_graph.add_edge(e,x,0)
                print(e)
        print("==========================================")


    def pedir_publicar_velocidades(self):
        self.pubvel = True

    def pedir_publicar_deteccion(self):
        self.pubdet = True

    def pedir_publicar_desvios(self):
        self.pubdes = True

    def pedir_publicar_semaforos(self):
        self.pubsem = True

    def pedir_publicar_trenes(self):
        self.pubtre = True

    def pedir_publicar_luces(self):
        self.publuz = True

    def pedir_publicar_parametros(self):
        self.pubpar = True

    def pedir_publicar_tiras(self):
        self.pubtir = True

    def pedir_publicar_weather(self):
        self.pubwea = True

    def recibir_evento_parametros(self, evento):
        self.pedir_publicar_parametros()

    def recibir_evento_tira(self, evento):
        self.pedir_publicar_tiras()

    def recibir_evento_weather(self, evento):
        self.pedir_publicar_weather()

    def publicar_parametros(self):
        if self.pubpar:
          m = {"id": str(self.d), "parametros": Parametros().json_friendly_dict() }
          #print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubpar = False

    def publicar_tiras(self):
        if self.pubtir:
          m = {"id": str(self.d), "tiras": { k: t.json_friendly_dict() for k,t in Tira.tiras.items() } }
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubtir = False

    def publicar_weather(self):
        if self.pubwea:
          m = {"id": str(self.d), "weather": Weather().json_friendly_dict() }
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubwea = False

    def publicar_datos_velocidad_tren(self, clase, tren, data, coeffs, last):
          m = {"id": str(self.d), "datos_velocidad": { "clase": clase, "tren": tren.id, "data": data, "coeffs": coeffs, "last": last } }
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1

    def publicar_velocidades(self):
       if self.pubvel:
        if (self.cnt_pub_velocidades % 10) == 0:
          m = {"id": str(self.d), "velocidades": { k: { "F": self.tramos[k].velocidad, "R": self.tramos[k].inv.velocidad, "stop":self.tramos[k].stopped } for k in self.tramos } }
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubvel = False
        self.cnt_pub_velocidades += 1

    def tren_en(self, tramo):
        if tramo.tren:
            d = tramo.tren.diccionario_atributos()
            d["inv"]=False
        elif tramo.inv.tren:
            d = tramo.inv.tren.diccionario_atributos()
            d["inv"]=True
        else:
            d = None
        return d

    def publicar_deteccion(self):
       if self.pubdet:
          m = {"id": str(self.d), "deteccion": { k: self.tren_en(self.tramos[k]) for k in self.tramos } }
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubdet = False

    def publicar_desvios(self):
       if self.pubdes:
          now = tornado.ioloop.IOLoop.current().time()
          m = {"id": str(self.d), "desvios": { k: self.desvios[k].color() for k in self.desvios }, 
                                  "reservas": { k: self.desvios[k].id_tren_reserva() for k in self.desvios },
                                  "t_reservas": { k: self.desvios[k].t_reserva - now if self.desvios[k].t_reserva else None for k in self.desvios },
              }
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubdes = False

    def publicar_semaforos(self):
       if self.pubsem:
          m = {"id": str(self.d), "semaforos": { k: self.semaforos[k].color() for k in self.semaforos } }
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubsem = False

    def publicar_luces(self):
       if self.publuz:
          m = {"id": str(self.d), "luces": { k: self.luces[k].encendida for k in self.luces } }
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.publuz = False

    def publicar_trenes(self, eliminados=[]):
       if self.pubtre or eliminados:
        if (self.cnt_pub_trenes % 5) == 0 or eliminados:
          m = {
               "id": str(self.d),
               "trenes": { t.id: t.diccionario_atributos() for t in Tren.trenes },
               "estaciones": self.exportar_estaciones(asociaciones=False, solo_en_listado=False),
          }
          if eliminados:
              m["trenes_eliminados"]=eliminados
          print(m)
          global_message_buffer.new_messages([ m ])
          self.d +=1
          self.pubtre = False
        self.cnt_pub_trenes += 1

    def revisar_trenes_eliminados(self):
        eliminados = []
        for t in Tren.trenes:
            trenes_activos = [ self.tramos[k].tren for k in self.tramos ] + [ self.tramos[k].inv.tren for k in self.tramos ]
            if t not in trenes_activos:
                eliminados.append(t)
        for t in eliminados:
            Tren.trenes.remove(t)
        if eliminados:
            self.publicar_trenes(eliminados=[ t.id for t in eliminados ])

    def exportar_demos(self):
        print("exportar_demos")
        print(str(Maqueta.demos))
        return { id: d.diccionario_atributos() for id, d in Maqueta.demos.items() }

    def exportar_estaciones(self, asociaciones=True, solo_en_listado=True):
        print("exportar_estaciones(asociaciones="+str(asociaciones)+", solo_en_listado="+str(solo_en_listado))
        est = {}
        for k in list(Maqueta.estaciones.keys()):
            ek = Maqueta.estaciones[k]
            if (asociaciones and isinstance(ek, AsociacionEstaciones)) or (isinstance(ek, Estacion) and ((not ek.asociacion) or (not solo_en_listado))):
                if k[0] not in est:
                    est[k[0]] = {"s":[],"a":False,"d":ek.desc}
                est[k[0]]["s"].append(k[1])
                if isinstance(ek, Estacion):
                    est[k[0]]["a"] = est[k[0]]["a"] or ek.activa()
        print(est)
        return est

    def encontrar_estacion(self, nombre, sentido):
        return Maqueta.estaciones[(nombre,sentido)]

    def sendChatMessage(self, body, origin=None):
        message = self.createChatMessage(body, origin)
        print(message)
        global_message_buffer.new_messages([message])

    def createChatMessage(self, body, origin=None):
        message = {
            "id": str(self.d),
            "chat": {
                "body": body,
            },
        }
        if origin:
            message["chat"].update({
                "origin_class": type(origin).__name__,
                "origin_value": str(origin),
            })
            if hasattr(origin, "id") and origin.id:
                message["chat"]["origin_id"]=origin.id

        self.d+=1
        return message


    def stop(self):
        print("Quitando tension")
        # Quitar tension en tramos
        for t in self.tramos.values():
            t.stop()
        # Apagar las luces
        for l in self.luces:
            self.luces[l].estado(False)
        # Apagar las tiras
        for t in Tira.tiras.values():
            t.cambiar(imagen="__apagar")


    def publicar_todo(self):
        self.publicar_trenes()
        self.publicar_velocidades()
        self.publicar_desvios()
        self.publicar_semaforos()
        self.publicar_deteccion()
        self.publicar_luces()
        self.publicar_parametros()
        self.publicar_tiras()
        self.publicar_weather()

    @timed_avg_and_freq(1000)
    def accion_periodica(self):
        self.detectar()
        self.detectar_colisiones()
        self.publicar_todo()

class PulsoDeLuz(SuscriptorEvento):
    def __init__(self, luz, duracion=0.1): # duracion en segundos
        self.repr = self.luz = luz
        self.duracion = duracion

    def recibir(self, evento):
        if not self.luz.encendida:
            self.luz.on()
            tornado.ioloop.IOLoop.current().add_timeout(datetime.timedelta(seconds=self.duracion), self.luz.off)

class CambiarLuz(SuscriptorEvento):
    def __init__(self, luz, encender=False):
        self.repr = self.luz = luz
        self.encender = encender

    def recibir(self, evento):
        self.luz.estado(self.encender)

class EncenderLuz(CambiarLuz):
    def __init__(self, luz):
        CambiarLuz.__init__(self, luz, True)

class ApagarLuz(CambiarLuz):
    def __init__(self, luz):
        CambiarLuz.__init__(self, luz, False)

class CambiarSemaforo(SuscriptorEvento):
    def __init__(self, semaforo, color):
        self.repr = self.semaforo = semaforo
        self.color = color

    def recibir(self, evento):
        print("Cambiando semaforo automaticamente.")
        self.semaforo.cambiar(self.color)

class SonidoTren(SuscriptorEvento):
    def __init__(self, nombre):
        self.repr = self.nombre = nombre

    def recibir(self, evento):
        try:
            def callback_fin(*args, **kwargs):
                SuscriptorEvento.Fin(self, evento).publicar()
            evento.tren.buscar_y_reproducir_sonido(self.nombre, callback=callback_fin)
        except AttributeError:
            print("ERROR: SonidoTren utilizado con un evento sin atributo tren: "+str(evento))
        
class SonidoEstacion(SuscriptorEvento):
    def __init__(self, texto):
        self.repr = "SonidoEstacion"
        self.texto = texto

    def recibir(self, evento):
        try:
            tren = evento.tren
            estacion = evento.estacion
            def callback_fin(*args, **kwargs):
                SuscriptorEvento.Fin(self, evento).publicar()
            tren.reproducir_sonido_estacion(estacion, self.texto, callback=callback_fin)
        except AttributeError:
            print("ERROR: SonidoTren utilizado con un evento sin atributo tren o atributo estacion: "+str(evento))

    def mapear_clave_concurrencia(self, evento):
        if estacion in evento: return evento.estacion
        else: return None

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



def listar_eventos_disponibles():
    import inspect,sys
    for name, c in inspect.getmembers(sys.modules["maqueta"],
                                      lambda m: inspect.isclass(m) and (len(inspect.getmembers(m, inspect.isclass)) > 1 or issubclass(m,Evento))):
        print(name)
        for name2, c2 in inspect.getmembers(c, inspect.isclass):
            if issubclass(c2,Evento):
                if c2.__doc__: print("   "+name2+" "+str(c2.__doc__))
                else:          print("   "+name2)


def sig_handler(sig, frame):
    print("Parando todo...")
    tornado.ioloop.IOLoop.instance().add_callback(shutdown)

def shutdown():
    print("Parando servidor http...")
    server.stop()

    print('Iniciando parada...')
    io_loop = tornado.ioloop.IOLoop.instance()
    io_loop.stop()

    print("Parando maqueta...")
    Maqueta().stop()
    print("FIN")

    #deadline = tornado.ioloop.IOLoop.current().time() + 1

    #def stop_loop():
    #    now = tornado.ioloop.IOLoop.current().time()
    #    if now < deadline and (io_loop._callbacks or io_loop._timeouts):
    #        io_loop.add_timeout(now + 1, stop_loop)
    #    else:
    #        io_loop.stop()
    #        print('Shutdown')
    #stop_loop()


def setup():
    global maqueta
    maqueta = Maqueta()
    maqueta.validar()
    maqueta.detectar_colisiones()
    maqueta.publicar_todo()
    #print([ maqueta.tramos[tramo].desc + " " + str(maqueta.tramos[tramo].limites) for tramo in maqueta.tramos ])
    #print([ maqueta.tramos[tramo].inv.desc + " " + str(maqueta.tramos[tramo].inv.limites) for tramo in maqueta.tramos ])
    #t = Tren(maqueta.tramos["I2"].inv)

def simulacion():
    import time
    import random
    Tramo.debug = True
    for t in maqueta.tramos.values():
        t.poner_velocidad(0.0)
    maqueta.detectar()
    time.sleep(1)
    maqueta.detectar()

    maqueta.tramos["M2"].inv.deteccion(True)
    maqueta.tramos["M3"].inv.deteccion(True)
    maqueta.tramos["M5"].deteccion(True)

    for t in Tren.trenes:
        t.poner_clase(random.choice(list(maqueta.locomotoras.keys())))
    #t = Tren(maqueta.tramos["M2"].inv)
    #t = Tren(maqueta.tramos["M3"].inv)
    #t.poner_velocidad(100)
    #maqueta.semaforos["I2 invertido"].cambiar(Semaforo.ROJO)
    #Estacion.EventoTrenArrancando(Estacion("x","ccw"),None).publicar()

    #PistaMedicion().puede_medir(maqueta.tramos["E1"].tren)

def start():
    setup()
    print("***************************************************************************************")
    print("***************************************************************************************")
    print("******************************     S  T  A  R  T     **********************************")
    print("***************************************************************************************")
    print("***************************************************************************************")
    if Maqueta.modo_dummy: simulacion()

    app = make_app()
    global server
    server = tornado.httpserver.HTTPServer(app)
    server.listen(8888)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)


    timer = tornado.ioloop.PeriodicCallback(maqueta.accion_periodica,30)
    timer.start()

    # Descomentar las siguientes 4 lineas si se sospecha una fuga de memoria
    #from pympler import tracker
    #tr = tracker.SummaryTracker()
    #timer2 = tornado.ioloop.PeriodicCallback(tr.print_diff,60000)
    #timer2.start()

    tornado.ioloop.IOLoop.current().start()


