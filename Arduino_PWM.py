#!/usr/bin/python

import time
import math
from Antonio_I2C import Adafruit_I2C

# ============================================================================
# Arduino-based PWM Driver
# ============================================================================

class ArduinoPWM :
  # Registers/etc.
  __PRESCALE_FACTOR    = 0xFB
  __PRESCALE_COUNT_L   = 0xFC
  __PRESCALE_COUNT_H   = 0xFD
  __LED0_ON_L          = 0x00
  __LED0_ON_H          = 0x01
  __LED0_OFF_L         = 0x02
  __LED0_OFF_H         = 0x03
  __CHANNELS           = 4

  def __init__(self, address=0x40, debug=False, i2cdebug=False):
    self.i2c = Adafruit_I2C(address)
    self.i2c.debug = i2cdebug
    self.address = address
    self.debug = debug
    if (self.debug):
      print("Reseting Arduino PWM")
    self.setAllPWM(0, 0)

  def setPWMFreq(self, freq, debug=False):
    "Sets the PWM frequency"
    prescaleval = 25000000.0    # 25MHz
    prescaleval /= 4096.0       # 12-bit
    prescaleval /= float(freq)
    prescaleval -= 1.0
    if (self.debug or debug):
      print("Setting PWM frequency to %d Hz" % freq)
      print("Estimated pre-scale: %d" % prescaleval)
    prescale = math.floor(prescaleval + 0.5)
    if (self.debug or debug):
      print("Final pre-scale: %d" % prescale)

    prescalers_available = [ 1, 8, 64, 256, 1024 ]
    for (prescale, factor) in enumerate(prescalers_available):
      if(self.debug or debug):
        print("For frequency %f Trying prescaler %d factor %d" % (freq, prescale, factor) )
        # compare match register = [ 16,000,000Hz/ (prescaler * desired interrupt frequency) ] - 1
        compare_match_register = int( 16000000.0 / (factor * 4096.0 * freq) ) + 1
        print("compare_match_register = %d" % compare_match_register)
    # ticks = 1/freq (s) * ticks/s
    #self.i2c.write8(self.__PRESCALE, int(math.floor(prescale)))
    #self.i2c.write8(self.__PRESCALE_COUNT_L, int(math.floor(prescale)) & 0xFF)
    #self.i2c.write8(self.__PRESCALE_COUNT_H, int(math.floor(prescale)) >> 8)

  def setPWM(self, channel, on, off):
    "Sets a single PWM channel"
    self.i2c.write8(self.__LED0_ON_L+4*channel, on & 0xFF)
    self.i2c.write8(self.__LED0_ON_H+4*channel, on >> 8)
    self.i2c.write8(self.__LED0_OFF_L+4*channel, off & 0xFF)
    self.i2c.write8(self.__LED0_OFF_H+4*channel, off >> 8)

  def setAllPWM(self, on, off):
    "Sets all PWM channels"
    for c in range(self.__CHANNELS): self.setPWM(c, on, off)

if __name__=="__main__":
  ap=ArduinoPWM(debug=True)
  for f in range(2,100,2):
    ap.setPWMFreq(f)

