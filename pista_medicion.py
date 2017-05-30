import tornado.ioloop
import sys
from maqueta            import ColeccionTramos, Desvio, Tren, Maqueta, DatosVelocidad
from singleton          import singleton
from parametros         import expuesto
from proceso_pasos      import ProcesoPasos
from tornado            import gen
from eventos            import GestorEventos
from dijkstra           import shortestPath
from datetime           import timedelta



@singleton
class PistaMedicion(ColeccionTramos):
    class MedicionMinimo(ProcesoPasos):
        def __init__(self):
            self.moviendo = False
            self.movido = False
            self.direccion = 1
            self.rango = ( 0, 100 )
            self.bak_minimo = PistaMedicion().midiendo.datos_velocidad.minimo
            self.iniciar()

        @gen.coroutine
        def paso(self):
            tren = PistaMedicion().midiendo
            tren.datos_velocidad.minimo = 0
            if not self.moviendo:
                print("Estoy parado. Calcular velocidad e iniciar movimiento.")
                if self.direccion > 0:
                    self.v = sum(self.rango)/2
                else:
                    self.v = -100
                self.moviendo = True
                self.movido = False
                print(tren, " midiendo a velocidad ",self.v)
                GestorEventos().suscribir_evento(Tren.EventoMovido, self.evento_tren_movido, tren)
                tren.estado_colision = Tren.MIDIENDO
                tren.poner_velocidad(self.v)
                if self.v<0: return timedelta(seconds=2)

            else:
                print("Estoy moviendo. Parar y decidir.")
                GestorEventos().eliminar_suscriptor(self.evento_tren_movido)
                PistaMedicion().midiendo.poner_velocidad(0)
                m, M = self.rango
                if self.movido:
                    print("Se ha movido.")
                    if self.direccion > 0:
                        self.rango = (m, self.v)
                    print("modo_dummy="+str(Maqueta.modo_dummy))
                    if not Maqueta.modo_dummy: # En modo dummy no podemos ir hacia atras.
                        self.direccion *= -1
                else:
                    print("No se ha movido.")
                    self.rango = (self.v, M)
                self.moviendo = False
                self.movido = False
                print("Rango: "+str(self.rango))
                m, M = self.rango
                if (M-m)<2:
                    try: Maqueta().sendChatMessage("Terminada la medicion del minimo para el tren "+str(tren.id)+": porcentaje_minimo="+str(M), origin=tren)
                    except:
                        print(sys.exc_info())
                    self.bak_minimo = int(M * 4096 / 100)
                    DatosVelocidad.MINIMO_INICIO[tren.clase] = tren.datos_velocidad.minimo = self.bak_minimo
                    self.parar()
                    return None
                return timedelta(seconds=1)

            return timedelta(seconds=10)

        def limpieza(self):
               import traceback
               traceback.print_stack()
               GestorEventos().eliminar_suscriptor(self.evento_tren_movido)
               tren = PistaMedicion().midiendo
               if tren:
                   tren.poner_velocidad(0)
                   tren.estado_colision = None
                   tren.datos_velocidad.minimo = self.bak_minimo
                   print("*************************** CONCLUSION MEDICION *************************")
                   print(tren)
                   print(self.rango)
                   print("*************************** CONCLUSION MEDICION *************************")

        def evento_tren_movido(self, evento):
            self.movido = True
            self.siguiente_paso_inmediato()

    class MedicionCurva(ProcesoPasos):
        @expuesto
        def CONTADOR_MEDIDAS():
            """ Numero de tramos a recorrer a cada velocidad. """
            return 12
        def __init__(self):
            print("MedicionCurva.__init__")
            self.movido = False
            self.v = 100
            self.contador_medidas = __class__.CONTADOR_MEDIDAS
            print("MedicionCurva.__init__ --> iniciar")
            self.iniciar()

        @gen.coroutine
        def primer_paso(self):
            print("MedicionCurva.primer_paso")
            GestorEventos().suscribir_evento(Tren.EventoMovido, self.evento_tren_movido, PistaMedicion().midiendo)
            self.movido = True   # Para no abortar antes de empezar
            return (yield self.paso())

        @gen.coroutine
        def paso(self):
            print("MedicionCurva.paso")
            tren = PistaMedicion().midiendo
            if not self.movido or self.v<=0: # Abortar medicion
                print("MedicionCurva.paso abortando medicion")
                try: Maqueta().sendChatMessage("Abortada medición de curva.", origin=tren)
                except:
                    print(sys.exc_info()[0])
                self.parar()
                return None
            if tren.velocidad != self.v:
                tren.estado_colision = Tren.MIDIENDO
                tren.poner_velocidad(self.v)
            if self.contador_medidas <= 0:
                self.v -= 10
                self.contador_medidas = __class__.CONTADOR_MEDIDAS
                if self.v <= 0:
                    try:
                        msg = 'Locomotora("{}",desc="{}",coeffs={},minimo={},muestras_inercia={})'.format(tren.clase,
                                                                                                   Maqueta.locomotoras[tren.clase],
                                                                                                   tren.datos_velocidad.coeffs,
                                                                                                   tren.datos_velocidad.minimo,
                                                                                                   tren.datos_velocidad.muestras_inercia)
                        print(msg)
                        Maqueta().sendChatMessage(msg, origin=tren)
                    except:
                        print(sys.exc_info()[0])
                    self.parar()
                    return None
            return timedelta(seconds=20) # No deberia tardar mas de 20 segundos en recorrer ningun tramo

        def limpieza(self):
               print("MedicionCurva.limpieza")
               import traceback
               traceback.print_stack()
               GestorEventos().eliminar_suscriptor(self.evento_tren_movido)
               tren = PistaMedicion().midiendo
               if tren:
                   tren.poner_velocidad(0)
                   tren.estado_colision = None
                   print("*************************** CONCLUSION MEDICION *************************")
                   print(tren)
                   #print(self.rango)
                   print("*************************** CONCLUSION MEDICION *************************")

        def evento_tren_movido(self, evento):
            self.movido = True
            self.contador_medidas -= 1
            self.siguiente_paso_inmediato()

    class Medicion(ProcesoPasos):
        def __init__(self):
            print("Medicion.__init__")
            self.pasos = [ PistaMedicion.MedicionCurva, PistaMedicion.MedicionMinimo ] # En orden inverso de ejecucion.
            GestorEventos().suscribir_evento(Tren.EventoDesaparecido, self.evento_tren_desaparecido, PistaMedicion().midiendo)
            self.iniciar()

        @gen.coroutine
        def paso(self):
            print("Medicion.paso")
            self.p = self.pasos.pop().__call__()
            print("Esperando a ",self.p)
            print("yield self.p.esperar()", (yield self.p.esperar()))
            print("Completado: finalizado=", self.p.finalizado)
            self.p = None
            if self.pasos:
                return timedelta(seconds=1)
            else:
                self.parar()
                return None

        def parar(self):
            print("Medicion.parar")
            super(PistaMedicion.Medicion, self).parar()
            if self.p: self.p.parar()

        def limpieza(self):
            print("Medicion.limpieza")
            PistaMedicion().limpieza()
            GestorEventos().eliminar_suscriptor(self.evento_tren_desaparecido)


        def evento_tren_desaparecido(self, evento):
            self.parar()


    def __init__(self, *args, **kwargs):
        ColeccionTramos.__init__(self,*args,**kwargs)
        self.desvio_color_list = []
        self.desvios = []
        self.midiendo = None
        self.medicion = None

        # Registrarse para saber cuando se libera un desvio, quiza lo este esperando
        GestorEventos().suscribir_evento(Desvio.EventoLiberado, self.recibir_evento_desvio_liberado)

        # Avisar a la maqueta de que existe
        Maqueta().pista_medicion = self

    def desvio_color(self):
        if not(self.desvio_color_list):
            for t1,t2 in zip(self.tramos, self.tramos[1:]+self.tramos[:1]):
                self.desvio_color_list += ( (t.desvio, t.desvio.color_rama(t)) for t in shortestPath(Maqueta().graph, t1, t2) if t.desvio and t.desvio.color_rama(t) )
            self.desvios = list(d for d,c in self.desvio_color_list)
            print(self.desvio_color_list)

        return self.desvio_color_list

    def recibir_evento_desvio_liberado(self, evento):
        if self.midiendo and evento.emisor and evento.emisor in self.desvios:
            print("Se ha liberado un desvio de la pista. Abortando medicion.")
            if self.medicion:
                self.medicion.parar()

    def puede_medir(self, tren):
        if tren.tramo in self.tramos:
            print("El tren ",tren," esta en un tramo de la pista.")
        else:
            raise Exception("El tren no esta en la pista de medicion.")

        ttf = (t.tren_en_tramo_fisico() for t in self.tramos)
        ttf_distinto = next((t for t in ttf if t and t != tren), None)
        if ttf_distinto:
            raise Exception("El tren "+str(ttf_distinto)+" nos impide realizar la medicion.")
        else:
            print("No hay ningun otro tren en la pista.")

        if tren.estado_colision == Tren.MIDIENDO:
            raise Exception("El tren ya esta midiendo.")

        for d,c in self.desvio_color():
            d.cambiar(c,reserva=tren)

        self.midiendo = tren

        tornado.ioloop.IOLoop.current().add_callback(self.medir)
        #GestorEventos().suscribir_evento(Tren.EventoMovido, self.recibir_evento_tren_movido, emisor=self.midiendo)

        return True

    def medir(self):
        if self.midiendo:
            self.medicion = PistaMedicion.Medicion()

    def limpieza(self):
        for d in self.desvios:
            d.liberar(self.midiendo)
        self.midiendo = self.medicion = None


