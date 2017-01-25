class singleton(object):
    """ Decorador singleton. Aplicar a una clase, y solo existira una instancia de la misma. """
    def __init__(self,klass):
        self.klass = klass
        self.instance = None

    def __call__(self,*args,**kwds):
        if self.instance == None:
            self.instance = self.klass(*args,**kwds)
        return self.instance

    # Para permitir metodos de clase
    def __getattr__(self, name):
        return getattr(self.klass, name)


