from Antonio_I2C import Adafruit_I2C
from PIL import Image
from memoized import memoized
from os import walk
import os.path
import datetime
import webcolors
from tornado            import gen
import tornado.web
from eventos import Evento, GestorEventos
from representacion import IdDesc
from parametros import expuesto, Parametros, EventoParametros
from weather import Weather

class Tira(IdDesc, object):
   """ Tira de LEDs basada en WS2812B controlada por un Arduino.
       El Arduino responde por I2C.
       La longitud de la tira se escribe en el registro 255.
       Los datos RGB de la tira se escriben desde el registro 0 en adelante.
       Para iniciar la transicion se indica el numero de pasos en el registro 254.
   """

   MAX_IN = 255
   MAX_OUT = 255
   @expuesto
   def GAMMA():
       """ Valor gamma necesario para las tiras de led utilizadas.
           1.0 = sin cambios. Valores altos = mayor contraste en tonos claros. """
       return 2.8

   @expuesto
   def PASOS_BLANCO():
       """Numero de pasos de la transicion a blanco."""
       return 1
   @expuesto
   def PASOS_APAGAR():
       """Numero de pasos de la transicion a apagado."""
       return 1
   @expuesto
   def PASOS_COLOR():
       """Numero de pasos de la transicion a color fijo o degradado."""
       return 128
   @expuesto
   def PASOS_IMAGEN():
       """Numero de pasos de la transicion a una imagen."""
       return 128
   @expuesto
   def PASOS_IMAGEN_DIA():
       """Numero de pasos de la transicion entre instantes de un dia. Deberia durar menos de un segundo."""
       return 18
   @expuesto
   def DURACION_DIA_S():
       """Tiempo que dura un dia completo, en segundos."""
       return 120

   class EventoCambiado(Evento):
       """ La tira ha cambiado de color o imagen """
       pass

   tiras = {}
   imagenes = {}

   def __init__(self, address=0x04, desc=None, debug=False, i2cdebug=False,
                      num_leds=16, dobleces=0, invirtiendo=True,
                      direccion_longitud=255, direccion_pasos=254, direccion_num_tira=253, direccion_flash=252,
                      num_tira=0):
       """Inicializa una tira ajustando todos los parametros de entrada.
          Si el arduino no tenia consciencia de la longitud de la tira,
          reiniciara y puede que no funcione correctamente durante un tiempo."""
       if not len(Tira.imagenes):
           for (dirpath, dirnames, filenames) in walk("static/imagenes_tira"):
               # print(dirpath, dirnames, filenames)
               for fn in filenames:
                   Tira.imagenes[fn.split(".",1)[0]] = os.path.join(dirpath, fn)

       self.i2c = Adafruit_I2C(address)
       self.i2c.debug = i2cdebug
       self.address = address
       self.direccion_longitud = direccion_longitud
       self.direccion_pasos = direccion_pasos
       self.direccion_num_tira = direccion_num_tira
       self.direccion_flash = direccion_flash
       self.num_tira = num_tira
       self.debug = debug
       self.id = 1+len(Tira.tiras)
       if desc:
           self.desc = str(desc)
       else:
           self.desc = "Tira"+str(self.id)
       self.sig = None
       self.set_num_leds(num_leds)
       self.dobleces = dobleces
       self.invirtiendo = invirtiendo
       self.color1 = '#000000'
       self.color2 = '#000000'
       self.imagen = None
       self.incremento_pct = None
       self.pct_fila = 0
       self.gamma = Tira.GAMMA
       self.listener_brillo = None
       Tira.tiras[self.id]=self

       GestorEventos().suscribir_evento(EventoParametros, self.recibir_evento_cambio_parametros, Parametros().d["Tira"])

   def cambiar(self, imagen="__apagar", color1='#000000', color2='#000000'):
       """Cambia la visualizacion de la tira a una imagen, fija o iterable, color o degradado.
          El parametro imagen puede tomar, ademas del nombre de imagen, los valores especiales:
          __apagar, __blanco, _color1 (un color), _color2 (degradado)."""
       if imagen in Tira.imagenes:
           if imagen[0:3]=="Dia":
               self.poner_imagen(jpg=Tira.imagenes[imagen], tiempo_s=Tira.DURACION_DIA_S)
           else:
               self.poner_imagen(jpg=Tira.imagenes[imagen])
           self.imagen = imagen
       elif imagen == "__blanco":
           self.blanco()
           self.color1 = self.color2 = '#ffffff'
           self.imagen = imagen
       elif imagen == "__apagar":
           self.apagar()
           self.color1 = self.color2 = '#000000'
           self.imagen = imagen
       elif imagen == "_color1":
           self.degradado(color1,color1)
           self.imagen = imagen
       elif imagen == "_color2":
           self.degradado(color1,color2)
           self.imagen = imagen
       else:
           raise Exception("Imagen Incorrecta: "+str(imagen))
       Tira.EventoCambiado(self).publicar()

   def enviar_num_tira(self):
       """ Envia el numero de tira (tipicamente 0 / 1) al arduino."""
       self.i2c.write8(self.direccion_num_tira,self.num_tira)

   def set_num_leds(self, n):
       """ Indica al arduino la longitud de la tira. """
       self.cancelar_sig()
       self.enviar_num_tira()
       self.i2c.write8(self.direccion_longitud,n)
       self.num_leds = n
       return self

   def enviar_flash(self, t):
       """ Pide al arduino que haga un flash de t milisegundos. """
       print("{0}: Enviando flash de {1} ms.".format(tornado.ioloop.IOLoop.current().time(), t))
       self.enviar_num_tira()
       self.i2c.write8(self.direccion_flash, t)

   class Siguiente:
       """Siguiente iteracion de la imagen."""
       def __init__(self, tira, jpg, pasos, nuevo_pct_fila, tiempo_s):
           """Siguiente iteracion de la imagen. Guarda referencia a todos los valores."""
           self.detener=False
           self.tira = tira
           self.jpg = jpg
           self.pasos = pasos
           self.nuevo_pct_fila = nuevo_pct_fila
           self.tiempo_s = tiempo_s

       def f(self):
           """Poner la siguiente imagen."""
           if self.detener: return
           while self.nuevo_pct_fila > 100.0: self.nuevo_pct_fila -= 100.0
           self.tira.poner_imagen(self.jpg, self.pasos, self.nuevo_pct_fila, self.tiempo_s)

   def poner_imagen(self, jpg="imagen.jpg", pasos=None, pct_fila=None, tiempo_s=None, desde_cero=False):
       """Ilumina la tira basado en el ambiente de un fichero JPG."""
       if self.debug: print("imagen {0} - {1}pasos - pct_fila={2}% - tiempo_s={3}s - desde_cero={4}".format(jpg, pasos, pct_fila, tiempo_s, desde_cero))
       self.cancelar_sig()
       if tiempo_s is not None:
           self.tiempo_s = tiempo_s
           self.incremento_pct = 100.0 / tiempo_s
           pasos = Tira.PASOS_IMAGEN_DIA
           if desde_cero:
               self.pct_fila = 0
       else:
           self.tiempo_s = None
           self.incremento_pct = None
       if pct_fila is not None:
           self.pct_fila = pct_fila
       self.set_bytes(self.jpg_to_bytes(jpg, self.pct_fila), pasos or Tira.PASOS_IMAGEN)
       if self.incremento_pct:
           # Reprogramar
           self.sig = Tira.Siguiente(self, jpg, pasos, self.pct_fila+self.incremento_pct, tiempo_s)
           tornado.ioloop.IOLoop.current().add_timeout(datetime.timedelta(seconds=1), self.sig.f)
       return self

   def apagar(self, pasos=None):
       """Apaga la tira."""
       if self.debug: print("apagar")
       self.cancelar_sig()
       self.set_bytes([0]*(3*self.num_leds), pasos or Tira.PASOS_APAGAR)
       return self

   def blanco(self, pasos=None):
       """Enciende la tira a su maximo brillo (color blanco)."""
       if self.debug: print("blanco")
       self.cancelar_sig()
       self.set_bytes([Tira.MAX_OUT]*(3*self.num_leds), pasos or Tira.PASOS_BLANCO)
       return self

   def cancelar_sig(self):
       if self.sig:
           self.sig.detener = True
           self.sig = None
           self.tiempo_s = None
           self.incremento_pct = None

   @memoized
   def calcular_degradado(self, color1, color2):
       """Calcula los bytes a enviar a la tira para mostrar un degradado entre dos colores."""
       deg = self._calcular_degradado(color1, color2, int(self.num_leds/(self.dobleces+1)) )
       return self.doblar_y_aplanar(deg)

   def doblar_y_aplanar(self, entrada):
       """A partir de una entrada en forma de lista de tuplas (lista de pixels),
          crea la lista de bytes a enviar a la tira, considerando dobleces e inversiones."""
       ret = [ pixeldata for n in range(self.dobleces+1) for pixeldata in ( reversed(entrada) if (self.invirtiendo and n%2) else entrada ) ]
       # [item for sublist in list for item in sublist] # Truco para aplanar una lista
       return [color for pixel in ret for color in pixel]

   def _calcular_degradado(self, color1, color2, num_pixels):
       """Calcula la lista de pixels que componen un degradado de color."""
       c1 = webcolors.hex_to_rgb(color1)
       c2 = webcolors.hex_to_rgb(color2)
       saltos = num_pixels - 1
       return list(list((p*a+(saltos-p)*b)/saltos for a,b in zip(c1,c2)) for p in range(num_pixels) )
       #return list((p*a+(saltos-p)*b)/saltos for p in range(num_leds) for a,b in zip(c1,c2) )

   def degradado(self, color1, color2, pasos=None):
       """Enciende la tira con un degradado de color."""
       self.color1 = color1
       self.color2 = color2
       try:
           grad = self.calcular_degradado(color1, color2)
           if self.debug: print(grad)
           self.set_bytes(grad, pasos or Tira.PASOS_COLOR)
       except:
           print("ERROR: Imposible establecer degradado color1="+str(color1)+" color2="+str(color2))
           raise

   @memoized
   def jpg_to_bytes(self, jpg, pct_fila=None):
       """Calcula los bytes a enviar a la tira para crear un ambiente basado en una imagen JPG."""
       im = Image.open(jpg)
       if pct_fila is not None and pct_fila >= 0 and pct_fila <= 100:
          fila = int( (im.size[1]-1) * pct_fila / 100 )
          if self.debug: print("fila={0}".format(fila))
          im = im.crop((0,fila,im.size[0],fila+1))
       im = im.resize((int(self.num_leds/(self.dobleces+1)) ,1), Image.ANTIALIAS)
       # im.getdata() no es una lista, pero se parece suficiente.
       # Si en algun momento se necesita, se puede cambiar por list(im.getdata())
       return self.doblar_y_aplanar( im.getdata() )

   def set_bytes(self, bytes=[], pasos=128):
       """Envia al arduino los bytes de una imagen, tras aplicar la transformacion gamma."""

       brillo = 100.0*sum(bytes)/len(bytes)/Tira.MAX_IN

       bytes=self.transformar_gamma(bytes)

       self.enviar_num_tira()

       for i in range(int(len(bytes)/3)):
           self.i2c.writeList(i, bytes[3*i:3*i+3])

       self.i2c.write8(self.direccion_pasos, int(pasos))

       if self.listener_brillo: self.listener_brillo(brillo)

       return self

   def json_friendly_dict(self):
       """Devuelve un diccionario de atributos convertible a JSON, con los datos fundamentales y estado de la tira."""
       return { k: self.__dict__[k] for k in [ "id", "num_leds", "desc", "address", "imagen", "color1", "color2" ] }

   def transformar_gamma(self, bytes):
       """Aplica a los bytes de entrada la transformacion gamma para corregir
          el efecto visual en la iluminacion de tonos medios."""
       if isinstance(bytes, str):
           bytes = list(bytearray(bytes))
       return [ int(pow(float(i) / float(Tira.MAX_IN), self.gamma) * Tira.MAX_OUT + 0.5)  for i in bytes ]

   def recibir_evento_cambio_parametros(self, evento):
       """Recibe el evento de cambio de parametros para enviar de nuevo
          la imagen a la tira aplicando nuevo gamma."""
       if self.gamma != Tira.GAMMA:
           if self.debug: print("Ajustando gamma")
           self.gamma = Tira.GAMMA
           self.cambiar(self.imagen, self.color1, self.color2)

   def weather(self):
       Weather().usa_tira(self)

# Manejo de tira LED
class TiraHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        key = self.get_argument("id", None)
        if key:
            tira = Tira.tiras[int(key)]
            tira.cambiar(imagen=self.get_argument("imagen", None),
                         color1=self.get_argument("color1", None),
                         color2=self.get_argument("color2", None),
            )

        if self.request.connection.stream.closed():
            return
        self.write(Tira.imagenes)



if __name__ == '__main__':
    Tira(i2cdebug=True, num_leds=100).blanco()
    print(Tira.imagenes)
