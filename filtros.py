class FiltroInercia(object):
    def __init__(self, longitud=1):
        self.longitud = int(longitud)
        self.puntero = 0
        self.lista = [0.0] * self.longitud

    def procesar(self, x):
        self.lista[self.puntero] = x
        y = self.calcular()
        self.puntero = (self.puntero + 1) % self.longitud
        return y

    def calcular(self):
        return max(self.lista)


