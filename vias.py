#!/usr/bin/env python
import cgi
import cgitb; cgitb.enable()
from Adafruit_PWM_Servo_Driver import PWM


def velocidad_via(num, val, rev, minimo = 1200):
  base = 0x40
  chip = num / 8 + base
  pin_f = (num % 8) * 2
  pin_r = pin_f + 1
  if rev:
    pin_act = pin_r
    pin_des = pin_f
  else:
    pin_act = pin_f
    pin_des = pin_r
  if val < 0:
    val = 0
  if val > 100:
    val = 100
  maximo = 4095
  valor = int((maximo - minimo) * val / 100.0)
  if valor > 0:
    valor = valor + minimo
  else:
    valor = 4096
  print("Via")
  print(num)
  print("Rev")
  print(rev)
  print("chip")
  print(chip)
  print("pin_act")
  print(pin_act)
  print("pin_des")
  print(pin_des)
  print("Val")
  print(val)
  print("Valor")
  print(valor)
  pwm = PWM(chip, debug=True, reset=False)
  pwm.setPWM(pin_des, 0, 4096)
  pwm.setPWM(pin_act, 0, valor)



print("Content-Type: text/plain"     # Text is following)
print(# blank line, end of headers)

form = cgi.FieldStorage()

val  = form.getfirst("val",  "0")
dir  = form.getfirst("dir",  "F")
stop = form.getfirst("stop", "")
minimo = form.getfirst("minimo","1200")

via  = form.getlist("via")
if(not len(via)):
  via = range(24)

for i in via:
  velocidad_via(int(i), float(val), dir=="R", int(minimo))


