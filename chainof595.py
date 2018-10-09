from Adafruit_GPIO import SPI

MAX_CHIPS = 100

class ChainOf595:
   """ Abstraction class to drive a chain of 74xx595 shift registers using the SPI bus.
       Connect:
          MOSI --> SER of first chip.
          QH' of n-th chip --> SER of (n+1)-th chip.
          QH' of last chip --> MISO (via* a gated buffer 74xx125)

          CE0 or CE1 --> RCLK of all chips
                     --> *Gate of 74xx125

                      ____ 74xx32*
          SPI_CLOCK --\   `.
                       |    >-- SRCLK
               RCLK --/___.'
          * 74xx32 and 74xx125 are needed to support more than one
            SPI device connected to the same MOSI/MISO/SPI_CLOCK lines
            that only act if the right CEx is enabled.
   """
   def __init__(self, qty=None, bus=0, dev=0, debug=False):
       """ qty: length of the chain (default: None = auto detect)
           bus, dev: Bus and device number
           debug: Show old and new states on each change
       """
       try:
           self.spi = SPI.SpiDev(bus,dev)
           self.spi.set_mode(3) # Clock idle high, sampled on low-high
           self.spi.set_bit_order(SPI.MSBFIRST)
       except Exception as e:
           print(e)
           self.spi = None
           print("No SPI")
       self.debug = debug
       if(qty): self.set_qty(qty)
       else: self.detect()

   def set_qty(self, qty):
       """ Set the length of the chain (quantity of chips) and reset. """
       assert qty > 0, "Chain length must be positive."
       self.bytes = qty
       self.reset()

   def reset(self):
       """ Set the status to all zeros (and send to the chips). """
       self.states = [ 0x00 ] * self.bytes
       self.send()

   def set_bit(self, bit, state, send=True):
       """ Set a single bit to a specific state.
           Bit 0 is the LSB (QA) of the chip closest to MOSI.
           Bit 7 is the MSB (QH) of the chip closest to MOSI.
           BIT 8 is the LSB (QA) of the second chip.
           etc.
       """
       if(self.debug): print("OLD: "+self.binstates())
       mask = 1 << (bit & 0x7)
       b = self.bytes - (bit>>3) - 1
       if(state):
           self.states[b] |= mask
       else:
           self.states[b] &= ~mask
       if(self.debug): print("NEW: "+self.binstates())
       if(send): self.send()

   def binstates(self):
       """ Return a string of bits representing the state """
       return ("{:08b} "*self.bytes).format(*self.states)

   def send(self):
       """ Send the current state to the chips. """
       if self.spi:
           self.spi.transfer(self.states) # Ignore old data coming back

   def detect(self):
       """ Detect the length of the chain.
           QH' of the last chip must be connected to MISO.
       """
       if self.spi:
           lots_of_zeros = [0] * MAX_CHIPS
           out = self.spi.transfer(lots_of_zeros)
           out = self.spi.transfer([255]+lots_of_zeros)
           num = out.index(255)
           assert num > 0, "Chain not detected or shorted."
           out[num] = 0
           assert out == bytearray(MAX_CHIPS + 1), "Unexpected returned value. Likely chain not closed."
       else:
           num = 6 # Arbitrary number in dummy mode
       self.set_qty(num)
       return num

