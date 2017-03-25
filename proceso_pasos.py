import tornado.ioloop
from tornado import gen
from tornado.concurrent import Future
from eventos import Evento

class ProcesoPasos(object):
    class Finalizado(Evento): pass

    def iniciar(self):
        self.cont = True
        self.andando = False
        self.finalizado = False
        self.waiters = set()
        self.timeout_handle = None
        tornado.ioloop.IOLoop.current().add_callback(self.siguiente_paso)

    def parar(self):
        self.cont = False

    def continuar(self):
        return self.cont

    @gen.coroutine
    def siguiente_paso(self):
        if self.continuar():
            if self.andando:
                print(self,"andando")
                tiempo = yield self.paso()
            else:
                print(self,"empezando")
                tiempo = yield self.primer_paso()
                self.andando = True
            print(self,"tiempo=",tiempo)
            if tiempo:
                self.timeout_handle = tornado.ioloop.IOLoop.current().add_timeout(tiempo, self.siguiente_paso)
            elif self.continuar():
                print("AVISO: ",self," se queda sin timeout. Podria no terminar nunca.")
        if not self.continuar(): # no es un "else"
            print(self,"no continuar")
            self.cancelar_siguiente_paso()
            self.limpieza()
            self.finalizado = True
            for future in self.waiters:
                print(future)
                future.set_result([])
                print(future)
            self.waiters = set()
            ProcesoPasos.Finalizado(self).publicar()

    def cancelar_siguiente_paso(self):
        print(self,"cancelar_siguiente_paso")
        if self.timeout_handle:
            print(self,"cancelar_siguiente_paso: timeout_handle=",self.timeout_handle)
            tornado.ioloop.IOLoop.current().remove_timeout(self.timeout_handle)
            print(self,"cancelar_siguiente_paso: eliminado")
            self.timeout_handle = None
            print(self,"cancelar_siguiente_paso: fin")
        else:
            print(self,"cancelar_siguiente_paso: no habia timeout_handle")

    def siguiente_paso_inmediato(self):
        self.cancelar_siguiente_paso()
        tornado.ioloop.IOLoop.current().add_callback(self.siguiente_paso)

    @gen.coroutine
    def primer_paso(self):
        p = yield self.paso()
        return p

    @gen.coroutine
    def paso(self):
        return None

    def limpieza(self):
        print(self,"limpieza")

    @gen.coroutine
    def esperar(self):
        print(self,"esperar: finalizado="+str(self.finalizado))
        if not self.finalizado:
            print(self,"esperar: finalizado="+str(self.finalizado))
            ret = yield self._esperar()
            print(self,"esperar: ret="+str(ret)+" finalizado="+str(self.finalizado))

    def _esperar(self):
        # Construct a Future to return to our caller.  This allows
        # wait_for_messages to be yielded from a coroutine even though
        # it is not a coroutine itself.  We will set the result of the
        # Future when results are available.
        result_future = Future()
        if self.finalizado:
            result_future.set_result(True)
            return result_future
        self.waiters.add(result_future)
        return result_future

    def cancelar_espera(self, future):
        self.waiters.remove(future)
        # Set an empty result to unblock any coroutines waiting.
        future.set_result([])

