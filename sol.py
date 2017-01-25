from tira import *
import time

t = Tira(i2cdebug=True, num_leds=180, dobleces=1, invirtiendo=True)
for estilo in [ "", "-gris50", "-color" ]:
  for im in [ "sol20", "sol40", "sol60" ]:
    for x in range(100):
      t.poner_imagen("sol/"+im+estilo+".jpg", 1, x)
      time.sleep(.2)
