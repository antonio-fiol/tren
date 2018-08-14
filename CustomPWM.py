#!/usr/bin/python

import time
import math
from Antonio_I2C import Adafruit_I2C

# ============================================================================
# Adafruit PCA9685 16-Channel PWM Servo Driver
# ============================================================================

class CustomPWM :
  # Registers/etc.
  __FREQ              = 0x00

  def __init__(self, address=0x40, debug=False, i2cdebug=False):
    self.i2c = Adafruit_I2C(address)
    self.i2c.debug = i2cdebug
    self.address = address
    self.debug = debug

  def setPWMFreq(self, freq, debug=False):
    "Sets the PWM frequency"
    if (self.debug or debug):
      print("Setting PWM frequency to %d Hz" % freq)
    self.i2c.write16(self.__FREQ, freq)

  def setPWM(self, channel, duty):
    "Sets a single PWM channel"
    self.i2c.write16(channel, duty)

