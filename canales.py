import math
import numpy
import time

class Canales(object):
    NUM_CANALES=6

    def normalizar(self, array):
        """Devuelve un array con las mismas proporciones y potencia 1."""
        pot = numpy.dot(array,array)
        if pot == 0:
           print("ERROR: POTENCIA CERO: " + str(array))
           raise Exception("Potencia Cero")
           #return array
        return array * (1 / math.sqrt(pot))

    def __eq__(self, other):
        """ Son iguales si y solo si son del mismo tipo y tienen el mismo estado interno """
        return type(self) is type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        """ Y son diferentes si no son iguales
            (http://stackoverflow.com/questions/4352244/python-should-i-implement-ne-operator-based-on-eq/30676267#30676267)
        """
        return not self == other

    def __hash__(self):
        """ Override the default hash behavior (that returns the id or the object)
            (http://stackoverflow.com/questions/390250/elegant-ways-to-support-equivalence-equality-in-python-classes)
        """
        return hash(tuple(sorted(self.__dict__.items())))

class CanalesEstaticos(Canales):
    def __init__(self, salida):
        """ Salida por N canales en funcion de un array de amplitudes, constante. """
        self.c = self.normalizar(salida)

    def canales(self):
        return self.c

    def __eq__(self, other):
        """ Son iguales si y solo si son ambos estaticos y con la misma salida """
        return isinstance(other,CanalesEstaticos) and self.__dict__ == other.__dict__

    def __repr__(self):
        return type(self).__name__+str(self.c)

class OnesOutput(CanalesEstaticos):
    def __init__(self):
        """ Salida por todos los canales con igual amplitud. """
        super(OnesOutput, self).__init__(numpy.ones(self.NUM_CANALES))

class UnCanal(CanalesEstaticos):
    def __init__(self, canal):
        """ Salida por un unico canal (0-N) """
        c = numpy.zeros(self.NUM_CANALES)
        c[canal]=1
        super(UnCanal, self).__init__(c)

class SinOutput(Canales):
    def __init__(self):
        """ Salida con variacion sinusoidal entre los canales 0 y 1 (frontales izq y der) """
        self.phase = 0.0

    def canales(self):
        ret = numpy.array([numpy.sin(self.phase), numpy.cos(self.phase)])
        ret.resize(self.NUM_CANALES)
        self.phase += 1e-2
        return ret

class Fader(Canales):
    def __init__(self, anterior=None, actual=None, dt=1):
        """ Salida progresiva desde una configuracion de canales hasta otra. """
        self.anterior = anterior
        self.actual = actual or OnesOutput()
        self.t0 = time.time()
        self.dt = dt

    def canales(self):
        if not self.anterior:
           return self.actual.canales()
        now = time.time()
        if now > (self.t0 + self.dt):
            self.anterior = None
            return self.actual.canales()
        factor = ( now - self.t0 ) / self.dt
        return self.normalizar( ( self.anterior.canales() * (1-factor) ) + ( self.actual.canales() * factor ) )

    def nuevo(self, nuevo_actual):
        #if nuevo_actual != self.actual:
            self.anterior = CanalesEstaticos(self.canales())
            self.actual = nuevo_actual
            self.t0 = time.time()

    def __repr__(self):
        return "Fader desde "+str(self.anterior)+" hasta "+str(self.actual)

class Combi(Canales):
    def __init__(self, cc):
        self.cc = cc

    def canales(self):
        if not self.cc:
            self.cc=[OnesOutput()]
        s=sum(x.canales() for x in self.cc if x is not None)
        if not hasattr(s, "__len__"):
            print("SUMA escalar con cc="+str(self.cc))
        return self.normalizar(s)

    def __repr__(self):
        return str(self.cc)

