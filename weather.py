import tornado.ioloop
import tornado.web
from tornado            import gen
from eventos            import Evento
from singleton          import singleton
from datetime           import timedelta
from parametros         import expuesto

from audio_maqueta import AudioSystem, RepeatingWav, NoHaySonidoPara, Combi, UnCanal, Fader, Wav
from proceso_pasos import ProcesoPasos
import random

def duracion_aleatoria(n, mn=1, mx=255, rand_pct=0):
     if rand_pct:
         return random.randrange( min(mx,max(mn,n*(100-rand_pct)//100)), 1+max(mn,min(mx, n*(100+rand_pct)//100) ))
     else:
         return n


class Relampago(ProcesoPasos):
       @expuesto
       def PORCENTAJE_ALEATORIEDAD_DURACION():
           """Porcentaje maximo en el que se altera la duracion de cada relampago."""
           return 50

       @expuesto
       def RETRASO_TRUENO_S():
           return 1.5

       @expuesto
       def AMPLIFICACION_TRUENO():
           return 1.0

       def __init__(self, tira):
           self.tira = tira
           self.pasos = [(200,None,.9),(10,200,.8),(10,200,.6),(100,600,.8),(200,500,.8),(10,200,.6),(10,200,.8),(100,600,.8)]
           tornado.ioloop.IOLoop.current().add_timeout(timedelta(seconds=Relampago.RETRASO_TRUENO_S), self.trueno)
           self.iniciar()

       @gen.coroutine
       def paso(self):
           (tf, ti, prob) = self.pasos.pop()
           ejecutar = (prob > random.random())
           while ( self.pasos and not ejecutar ):
               (tf, ti, prob) = self.pasos.pop()
               ejecutar = (prob > random.random())
           if ejecutar:
               tf = duracion_aleatoria(tf, rand_pct=self.PORCENTAJE_ALEATORIEDAD_DURACION)
               self.tira.enviar_flash(tf)
           if self.pasos:
               ti = duracion_aleatoria(ti, rand_pct=self.PORCENTAJE_ALEATORIEDAD_DURACION, mn=tf+10, mx=1200)
               return timedelta(milliseconds=ti)
           else:
               self.parar()
               return None

       def trueno(self):
           fichero_trueno = AudioSystem().sonido("weather", "thunder2", gen=False)
           if fichero_trueno:
               w=Wav(fichero_trueno)
               w.nivel = Relampago.AMPLIFICACION_TRUENO
               AudioSystem().nueva_fuente(w)

@singleton
class Weather(object):
    @expuesto
    def TIEMPO_ENTRADA_SALIDA_SONIDO_S(): return 2.0
    @expuesto
    def TIEMPO_ENTRE_RELAMPAGOS_S():
        """Porcentaje maximo en el que se altera la duracion de cada relampago."""
        return 10
    @expuesto
    def PORCENTAJE_ALEATORIEDAD_TIEMPO_ENTRE_RELAMPAGOS():
        """Porcentaje maximo en el que se altera la duracion de cada relampago."""
        return 50


    class EventoCambiado(Evento):
       """ El tiempo ha cambiado. """
       pass

    class Tormenta(ProcesoPasos):
        def __init__(self):
            self.iniciar()

        @gen.coroutine
        def primer_paso(self):
            return timedelta(seconds=duracion_aleatoria(Weather.TIEMPO_ENTRE_RELAMPAGOS_S,rand_pct=Weather.PORCENTAJE_ALEATORIEDAD_TIEMPO_ENTRE_RELAMPAGOS))

        @gen.coroutine
        def paso(self):
            self.r = Relampago(Weather().tira)
            yield self.r.esperar()
            return timedelta(seconds=duracion_aleatoria(Weather.TIEMPO_ENTRE_RELAMPAGOS_S,rand_pct=Weather.PORCENTAJE_ALEATORIEDAD_TIEMPO_ENTRE_RELAMPAGOS))

    class AutoLuces(object):
        @expuesto
        def PORCENTAJE_BRILLO_L1():
            """ Porcentaje de brillo para el inicio/fin del encendido/apagado de luces. """
            return 50.0
        @expuesto
        def PORCENTAJE_BRILLO_L2():
            """ Porcentaje de brillo para el fin/inicio del encendido/apagado de luces. """
            return 40.0
        @expuesto
        def PORCENTAJE_HISTERESIS():
            """ Histeresis asociada al proceso de encendido/apagado de luces. """
            return 10.0

        luces = []

        def __init__(self):
            Weather().tira.listener_brillo = self.brillo
            self.anterior = 100.0
        @classmethod
        def usa(cls, l):
            cls.luces = l
        def parar(self):
            Weather().tira.listener_brillo = None
            for luz in __class__.luces:
                luz.off()
        def brillo(self, br):
            #print("brillo "+str(br))
            l = len(__class__.luces)
            h = __class__.PORCENTAJE_HISTERESIS
            b = min(__class__.PORCENTAJE_BRILLO_L1,__class__.PORCENTAJE_BRILLO_L2)
            k = abs(__class__.PORCENTAJE_BRILLO_L1-__class__.PORCENTAJE_BRILLO_L2)
            m = k/(l-1)
            umbrales_encendido = ( m*x + b - h/2 for x in range(l) )
            umbrales_apagado   = ( m*x + b + h/2 for x in range(l) )
            for luz, ue, ua in zip(__class__.luces, umbrales_encendido, umbrales_apagado):
                if br < ue < self.anterior:
                    print("Tira indica brillo {} que se encuentra por debajo del umbral de encendido {} para {}".format(br,ue,luz))
                    luz.on()
                if br > ua > self.anterior:
                    print("Tira indica brillo {} que se encuentra por encima del umbral de apagado {} para {}".format(br,ua,luz))
                    luz.off()
            self.anterior = br

    def __init__(self):
        self.opciones = { "windy": False, "auto_luces": False }
        self.opcion_tira = "off"
        self.tira = None
        self.sonidos_activos = { }
        self.acciones_especiales = { "storm": Weather.Tormenta, "auto_luces": Weather.AutoLuces }
        self.acciones_activas = { }

    def __repr__(self):
        return type(self).__name__+" singleton"

    def usa_tira(self, tira):
        self.tira = tira

    def cambiar(self, opcion, estado):
        opcion = str(opcion)
        imagen = "Dia-"+opcion
        if opcion == "off":
            self.opcion_tira = "off"
            for i in self.opciones: self.opciones[i] = False
            if self.tira: self.tira.cambiar(imagen="__apagar")
        elif self.tira and imagen in self.tira.imagenes:
            self.opcion_tira = opcion
            self.tira.cambiar(imagen=imagen)
        elif opcion in self.opciones:
            self.opciones[opcion] = (estado=="true")
        else:
            print("Opcion no disponible: "+opcion)

        self.gestionar_sonido()
        self.gestionar_acciones_especiales()

        Weather.EventoCambiado(self).publicar()

    def quitar_lo_que_sobra(self, activos, quitar):
        for s in [ s for s in activos if s != self.opcion_tira and (s not in self.opciones or (s in self.opciones and not self.opciones[s]))]:
            quitar(s)

    def activar_lo_que_toque(self, activos, activar):
        for s in self.opciones:
            if self.opciones[s] and s not in activos:
                activar(s)

        if self.opcion_tira not in activos:
            activar(self.opcion_tira)

    def gestionar_sonido(self):
        
        def quitar_sonido(opcion):
            print("Quitando sonido para "+opcion)
            self.sonidos_activos[opcion].fade_out(Weather.TIEMPO_ENTRADA_SALIDA_SONIDO_S)
            del self.sonidos_activos[opcion]
            
        def activar_sonido(opcion):
            print("Activando sonido para "+opcion)
            wav = AudioSystem().sonido("weather", opcion, gen=False)
            if wav:
                print("Activando fuente "+wav)
                fuente = RepeatingWav(wav).fade_in(Weather.TIEMPO_ENTRADA_SALIDA_SONIDO_S)
                #fuente.canales=Fader()
                #fuente.canales.nuevo(Combi([UnCanal(0)]))
                AudioSystem().nueva_fuente(fuente)
                self.sonidos_activos[opcion] = fuente
            else:
                print("No hay sonido para "+opcion)
                fuente = NoHaySonidoPara(opcion)
                self.sonidos_activos[opcion] = fuente

        self.quitar_lo_que_sobra(self.sonidos_activos, quitar_sonido)
        self.activar_lo_que_toque(self.sonidos_activos, activar_sonido)

    def gestionar_acciones_especiales(self):
        def quitar_accion(opcion):
            print("Quitando accion para "+opcion)
            self.acciones_activas[opcion].parar()
            del self.acciones_activas[opcion]
            
        def activar_accion(opcion):
            print("Activando accion para "+opcion)
            if opcion in self.acciones_especiales:
                acc = self.acciones_especiales[opcion]
                print("Activando accion "+str(acc))
                a = acc()
                self.acciones_activas[opcion] = a
            else:
                print("No hay accion para "+opcion)

        self.quitar_lo_que_sobra(self.acciones_activas, quitar_accion)
        self.activar_lo_que_toque(self.acciones_activas, activar_accion)


    def stop(self):
        cambiar("off",None)

    def json_friendly_dict(self):
        """Devuelve un diccionario de atributos convertible a JSON, con los datos fundamentales y estado del objeto."""
        ret = {}
        ret.update(self.opciones)
        ret.update({ self.opcion_tira: True })
        return ret


class WeatherHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        opcion = self.get_argument("opcion", None)
        estado = self.get_argument("estado", None)
        Weather().cambiar(opcion, estado)

        if self.request.connection.stream.closed():
            return
        self.write({})


