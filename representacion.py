class IdDesc(object):
   def __repr__(self):
       return type(self).__name__+" "+str(self.id)+" "+str(self.desc)

class Desc(object):
    def __repr__(self):
        return type(self).__name__+" "+str(self.desc)

    # Al migrar de python2 a python3, dos Tramo se vuelven "unorderable", asi que agregamos dos funciones de comparacion.
    def __lt__(self, other):
        if isinstance(other, Desc):
          return self.desc < other.desc # El operador corresponde con __lt__
        return NotImplemented # Valor especial para indicar que no somos capaces de comparar

    # Al migrar de python2 a python3, dos Tramo se vuelven "unorderable", asi que agregamos dos funciones de comparacion.
    def __le__(self, other):
        if isinstance(other, Desc):
           return self.desc <= other.desc # El operador corresponde con __le__
        return NotImplemented # Valor especial para indicar que no somos capaces de comparar


class Id(object):
   def __repr__(self):
       return type(self).__name__+" "+str(self.id)

import re
def iniciales(s):
   return re.sub("[a-z]", "", s)

