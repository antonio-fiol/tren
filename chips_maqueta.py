import time
from MCP23017 import MCP23017
from Antonio_PWM_Servo_Driver import PWM
from maqueta import Maqueta
from representacion import Desc

class ChipDesvios(MCP23017):
    MARRON_D1=1
    BL_MARRON_D1=2
    VERDE_D1=4
    BL_AZUL_D1=8
    AZUL_D1=16
    BL_VERDE_D1=32
    NARANJA_D1=64
    BL_NARANJA_D1=128
    MARRON_D2=256
    BL_MARRON_D2=512
    VERDE_D2=1024
    BL_AZUL_D2=2048
    AZUL_D2=4096
    BL_VERDE_D2=8192
    NARANJA_D2=16384
    BL_NARANJA_D2=32768

    def __init__(self, address=0x40, desvios=[], verde=MARRON_D2, rojo=BL_MARRON_D2, debug=False, i2cdebug=False, chip_rv=None):
        MCP23017.__init__(self, address=address, debug=debug, i2cdebug=debug)
        self.rojo = rojo
        self.verde = verde
        self.chip_rv = (chip_rv or self)
        self.inicializar( dir=self.OUT, pol=self.POL_NORMAL )
        self.estado = 0
        for d in desvios:
            d.registrar_chip_desvios(self, pin=desvios[d], chip_rv=self.chip_rv)

    def pulso(self, pines):
        self.working = True
        self.activar(pines)
        time.sleep(0.1)
        self.desactivar(pines)
        self.working = False

    def activar(self, pines):
        self.estado |= pines
        if self.debug: print("Chip desvios "+ hex(self.address) + " - nuevo estado: " + bin(self.estado))
        self.estado_a_chip()

    def desactivar(self, pines):
        self.estado &= ~pines
        if self.debug: print("Chip desvios "+ hex(self.address) + " - nuevo estado: " + bin(self.estado))
        self.estado_a_chip()

    def estado_a_chip(self):
        #self.i2c.write8(self.GPIOA, self.estado & 0xff)
        #self.i2c.write8(self.GPIOB, self.estado >> 8)
        self.i2c.write16(self.GPIOA, self.estado)

class ChipDetector(MCP23017):
    # Obtener todas las entradas
    # Leer GPIOA y GPIOB que tienen direcciones consecutivas
    # El resultado es GPIOB>>8 + GPIOA  = Bits Lado izquierdo Bits Lado Derecho
    # $GET $CHIP 0x12 w

    def __init__(self, address=0x40, pines=[], sim=[], debug=False, i2cdebug=False):
        MCP23017.__init__(self, address=address, debug=debug, i2cdebug=i2cdebug)
        self.pines = pines
        self.sim = sim

        self.lastDebounceTime = [ 0.0 ] * 16
        self.lastState = [ None ] * 16
        self.state = [ None ] * 16
        self.debounceDelay = 0.1 # seconds
        if(self.debug):
            print("lastDebounceTime")
            print(self.lastDebounceTime)
            print("lastState")
            print(self.lastState)
            print("state")
            print(self.state)
        
        self.inicializar( dir=self.IN_PULL_UP, pol=self.POL_INVERT )
        Maqueta.chips_detectores.append(self)

        print("INIT ChipDetector.")
        print(self.i2c)
        print(self.i2c.bus)
        if not (self.i2c and self.i2c.bus):
            print("dummy")
            Maqueta.modo_dummy = True

    def detectar(self):
        changed = False

        if(self.i2c and self.i2c.bus):
          #a = self.i2c.readU8(self.GPIOA)
          #b = self.i2c.readU8(self.GPIOB)
          ab = self.i2c.readU16(self.GPIOA)
        else:
            try:
                ab = self.sim.pop(0)
            except:
                ab = 0

        # La siguiente linea pinta el valor de cada deteccion. Esta comentada porque es mucho ruido incluso en modo debug
        #print(hex(self.address) + " " + str(ab))

        now = time.time()

        # read the state into a local variable:
        reading = [False]*16
        for n in range(16):
          reading[n]= ((ab>>n&0x01) == 0x01)

          # check to see if input just changed
          # (i.e. the input went from LOW to HIGH),  and you've waited
          # long enough since the last change to ignore any noise:

          # If the switch changed, due to noise or pressing:
          if (reading[n] != self.lastState[n]):
            # reset the debouncing timer
            self.lastDebounceTime[n] = now

          if (self.state[n]):
              dd = self.debounceDelay * 3/2
          else:
              dd = self.debounceDelay
          t = (now - self.lastDebounceTime[n])    
          if (t > dd):
            # whatever the reading is at, it's been there for longer
            # than the debounce delay, so take it as the actual current state:

            # if the state has changed:
            if (reading[n] != self.state[n]):
              desc_tramo="--"
              if self.pines[n]:
                  desc_tramo = self.pines[n].desc
              if self.debug: print("ChipDetector<" + hex(self.address) +">: Cambiado "+ str(n) + " (" + desc_tramo + ") de " + str(self.state[n]) + " a " + str(reading[n]))
              self.state[n] = reading[n]
              changed = True

          # save the reading.  Next time through the loop,
          # it'll be the lastState:
          self.lastState[n] = reading[n]

        if(changed):
          print("ChipDetector<"+hex(self.address)+">.detectar returns " + str(changed))
          if(self.debug):
              #print("lastDebounceTime")
              #print(self.lastDebounceTime)
              #print("lastState")
              #print(self.lastState)
              print("state")
              print(self.state)
          for i in range(16):
            tramo = self.pines[i]
            if tramo:
              if(self.debug):
                  print(str(tramo) + ": " + str(self.state[i]))
              tramo.tiene_tren(self.state[i])

        return changed


class ChipVias(Desc, PWM):
    def __init__(self, address=0x40, pines=[], minimo = 1200, freq=60, debug=False):
        try:
          PWM.__init__(self, address=address, debug=debug)
          self.real = True
        except IOError:
          self.real = False
        self.desc = hex(self.address)
        self.pines = pines
        self.minimo = minimo
        self.maximo = 4095
        self.setPWMFreq(freq)

        for n in range(len(pines)):
            if pines[n]:
                pines[n].inv.registrar_chip_vias(self,n)
                pines[n].registrar_chip_vias(self,n)

        Maqueta.chips_vias.append(self)

    def stop(self, pin):
        print("**** STOP **** " + str(self) + " --> "+str(self.pines[pin]))
        pin_f = pin * 2
        pin_r = pin_f + 1
        self.setPWM(pin_f, 0, 4096)
        self.setPWM(pin_r, 0, 4096)

    def poner_velocidad(self, pin, polaridad, val, minimo=None):
        if val < -100:
          val = -100
        if val > 100:
          val = 100
        if val < 0:
          val = -val
          polaridad = -polaridad

        pin_f = pin * 2
        pin_r = pin_f + 1
        if (polaridad<0):
            pin_act = pin_r
            pin_des = pin_f
        else:
            pin_act = pin_f
            pin_des = pin_r

        mi = self.minimo
        if minimo!=None:
            mi = int(minimo)
        valor = int((self.maximo - mi) * val / 100.0)
        if valor > 0:
            valor = valor + mi
        else:
            # valor = 4096 # Realmente apagado
            valor = 1 # Pulsos muy estrechos para permitir la deteccion
        if(self.debug):
            print("Pin: " + str(pin) + "    Polaridad: " + str(polaridad))
            print("chip: " + str(self) + "    pin_act: " + str(pin_act) + " - pin_des: " + str(pin_des))
            print("Val: " + str(val) + "    Valor: " + str(valor))
        self.setPWM(pin_des, 0, 4096)
        self.setPWM(pin_act, 0, valor)


