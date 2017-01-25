from timed import timed_avg, timed_avg_and_freq
from representacion import Desc
from canales import OnesOutput
from wavefile import WaveReader
import numpy
import math

class FuenteSonido(object):
    """ Clase abstracta para fuentes de sonido capaces de devolver arrays de muestras mono.
        Es imprescindible reescribir el metodo muestras_mono.
    """
    RATE=44100
    FRAMES_PER_BUFFER=2048
    AUDIO_SYSTEM=None

    def __init__(self):
        self.canales = OnesOutput()
        self.nivel = 1.0
        self.fade_chunks = None

    def eof(self):
        FuenteSonido.AUDIO_SYSTEM.quitar_fuente(self)

    def muestras_mono(self, frame_count):
        raise IOError()

    @timed_avg_and_freq(1000)
    def readframes(self, frame_count):
        mm = self.muestras_mono(frame_count)

        if self.fade_chunks:
           self.nivel += 1.0 / self.fade_chunks

        if self.nivel > 1.0 and self.fade_chunks:
           self.nivel = 1.0
           self.fade_chunks = None

        if self.nivel <= 0.0:
           self.nivel = 0.0
           self.fade_chunks = None
           self.eof()

        if self.nivel != 1.0:
           mm*=self.nivel
        return self.asignar_canales(mm, self.canales.canales())

    def asignar_canales(self, mono, c):
        # En lugar de atleast_2d y .T usamos reshape, que es un poco mas rapida
        return mono.reshape(mono.shape[0],1) * numpy.atleast_2d(c)

    def fade_in(self, seg):
        self.fade_chunks = seg * FuenteSonido.RATE / FuenteSonido.FRAMES_PER_BUFFER
        self.nivel = 0.0
        return self

    def fade_out(self, seg):
        self.fade_chunks = -seg * FuenteSonido.RATE / FuenteSonido.FRAMES_PER_BUFFER
        return self

class Sin(FuenteSonido):
    def __init__(self, frequency=440):
        super(Sin,self).__init__()
        self.phase = 0
        self.frequency = frequency
        self.amp = 1.0

    @timed_avg(1000)
    def muestras_mono(self, frame_count):
        length = frame_count
        factor = float(self.frequency) * (math.pi * 2) / self.RATE
        ret = numpy.sin(numpy.arange(length) * factor + self.phase)
        self.phase += (factor*length)
        if self.amp != 1.0:
            ret *= self.amp
        return ret

    def __repr__(self):
        return type(self).__name__+" amp="+str(self.amp)+" frequency="+str(self.frequency)

class Wav(FuenteSonido, Desc):
    def __init__(self, path):
        super(Wav,self).__init__()
        self.path = self.desc = path
        self.reader = WaveReader(path)
        self.data = numpy.zeros((self.reader.channels,FuenteSonido.FRAMES_PER_BUFFER), numpy.float32, order='F')
        #nframes = r.read(data)

    @timed_avg(1000)
    def muestras_mono(self, frame_count):
        nframes = self.reader.read(self.data)
        if nframes < frame_count:
            self.action_at_end_of_stream()
            self.data[:,nframes:] = numpy.zeros((self.reader.channels,frame_count-nframes), numpy.float32, order='F')
        return self.data[0,:]

    def action_at_end_of_stream(self):
        self.reader.close()
        self.eof()

class RepeatingWav(Wav):
    def __init__(self, path):
        super(RepeatingWav,self).__init__(path)

    def action_at_end_of_stream(self):
        self.reader.seek(0)

class NoHaySonidoPara(FuenteSonido, Desc):
    def __init__(self, desc):
        super(NoHaySonidoPara,self).__init__()
        self.desc = desc
        self.nivel = 0.0

    def muestras_mono(self, frame_count):
        return numpy.zeros(frame_count, numpy.float32, order='F')

