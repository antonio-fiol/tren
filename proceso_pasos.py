import tornado.ioloop
from tornado import gen
from eventos import Evento

class ProcesoPasos(object):
    class Finalizado(Evento): pass

    def iniciar(self):
        self.cont = True
        self.andando = False
        self.finalizado = False
        self.waiters = set()
        self.siguiente_paso()

    def parar(self):
        self.cont = False

    def continuar(self):
        return self.cont

    def siguiente_paso(self):
        if self.continuar():
            if self.andando:
                tiempo = self.paso()
            else:
                tiempo = self.primer_paso()
                self.andando = True
            if tiempo:
                tornado.ioloop.IOLoop.current().add_timeout(tiempo, self.siguiente_paso)
        else:
            self.limpieza()
            self.finalizado = True
            for future in self.waiters:
                future.set_result(messages)
            self.waiters = set()
            ProcesoPasos.Finalizado(self).publicar()

    def primer_paso(self):
        return self.paso()

    def paso(self):
        return None

    def limpieza(self):
        pass

    @gen.coroutine
    def esperar(self):
        if not self.finalizado:
            yield self._esperar()

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

    def new_messages(self, messages):
        logging.info("Sending new message to %r listeners", len(self.waiters))
        self.cache.extend(messages)
        if len(self.cache) > self.cache_size:
            self.cache = self.cache[-self.cache_size:]

