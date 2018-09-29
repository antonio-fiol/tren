from Adafruit_GPIO import SPI

class ChainOf595:
   """ Abstraction class to drive a chain of 74xx595 shift registers using the SPI bus. """
   def __init__(self, qty=1, bus=0, dev=0):
       """ qty: length of the chain """
       try:
           self.spi = SPI.SpiDev(bus,dev)
           self.spi.set_mode(3) # Clock idle high, sampled on low-high
       except:
           self.spi = None
       self.bytes = qty
       self.states = [ 0x00 ] * qty

   def set_bit(self, bit, state):
       """ Set a single bit to a specific state. """
       print("OLD: "+self.binstates())
       mask = 1 << (bit & 0x7)
       if(state):
           self.states[bit>>3] |= mask
       else:
           self.states[bit>>3] &= ~mask
       print("NEW: "+self.binstates())
       self.send()

   def binstates(self):
       """ Return a string of bits representing the state """
       return ("{:08b} "*self.bytes).format(*self.states)

   def send(self):
       """ Send the current state to the chips. """
       if self.spi:
           self.spi.transfer(self.states) # Ignore old data coming back

