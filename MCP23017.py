from Antonio_I2C import Adafruit_I2C
from representacion import Desc

class MCP23017(Desc, object):
    __IODIRA = 0x00
    __IODIRB = 0x01
    __IPOLA  = 0x02
    __IPOLB  = 0x03
    __GPPUA  = 0x0c
    __GPPUB  = 0x0d
    GPIOA  = 0x12
    GPIOB  = 0x13
    DIRA = __IODIRA
    DIRB = __IODIRB

    OUT        = [ 0x00, 0x00 ]
    IN_NO_PULL = [ 0xff, 0x00 ]
    IN_PULL_UP = [ 0xff, 0xff ]
    POL_NORMAL = 0x00
    POL_INVERT = 0xff

    def __init__(self, address=0x40, i2cdebug=False):
        self.i2c = Adafruit_I2C(address)
        self.i2c.debug = i2cdebug
        self.address = address
        self.desc = hex(address)

    def inicializar(self, dir=IN_NO_PULL, pol=POL_NORMAL):
        if self.i2c:
            # Todo entradas (es el valor por defecto)
            # IODIR=1 - Apartado 1.6.1 - pagina 12
            self.i2c.write8(self.__IODIRA, dir[0])
            self.i2c.write8(self.__IODIRB, dir[0])
            # Activar pull-up en todas las entradas
            # GPPU=1 - Apartado 1.6.7 - pagina 19
            self.i2c.write8(self.__GPPUA, dir[1])
            self.i2c.write8(self.__GPPUB, dir[1])
            # Invertir polaridad (los optoacopladores hacen que la entrada este baja cuando hay continuidad)
            # IPOL=1 - Apartado 1.6.2 - pagina 13
            self.i2c.write8(self.__IPOLA, pol)
            self.i2c.write8(self.__IPOLB, pol)

