import numpy
import pyaudio

import time
from timed import timed_avg, timed_avg_and_freq
from singleton import singleton
from os import walk
from functools import reduce # compatibilidad con python 3, no molesta en 2.7
import os.path

from canales import *
from fuente_sonido import *
from mixer import Mixer

@singleton
class AudioSystem(object):
    filtrado = []

    def __init__(self):
        self.fuentes = []
        self.sonidos = { "gen": { "gen": None } }
        self.buscar_sonidos()

        self.p = pyaudio.PyAudio()

        apis = [ self.p.get_host_api_info_by_index(i) for i in range(self.p.get_host_api_count()) ]
        default_devices = [ a["defaultOutputDevice"] for a in apis if a["defaultOutputDevice"]>=0 ]

        dispositivos = [ self.p.get_device_info_by_index(i) for i in range(self.p.get_device_count()) ]
        filtros = (
            [ lambda d: d["maxOutputChannels"] >= Canales.NUM_CANALES ] +
            AudioSystem.filtrado +
            [ lambda d: d["index"] in default_devices ]
        )

        for f in filtros:
           tentativo = list(filter(f, dispositivos))
           if tentativo:
               dispositivos = tentativo


        if dispositivos:
            print("Dispositivo de sonido seleccionado: "+ str(dispositivos[0]))
        else:
            print("No hay dispositivos de sonido disponibles")

        try:
            self.stream = self.p.open(format=pyaudio.paFloat32,
                                 frames_per_buffer=2048,
                                 channels=Canales.NUM_CANALES,
                                 rate=FuenteSonido.RATE, output=1,
                                 output_device_index=dispositivos[0]["index"],
                                 stream_callback=self.callback)
            self.stream.start_stream()
        except:
            self.stream = None

        # Inicializar mixer
        Mixer()

        FuenteSonido.AUDIO_SYSTEM=self



    def terminate(self):
        self.p.terminate()

    def nueva_fuente(self, fuente):
        print("nueva_fuente "+str(fuente))
        if self.stream:
            print("hay stream:")
            print(self.stream)
            print(self.stream.__dict__)
            self.fuentes.append(fuente)
            if self.stream.is_stopped():
                print("arrancando stream")
                self.stream.start_stream()

    def quitar_fuente(self, fuente):
        print("quitando fuente "+str(fuente))
        self.fuentes.remove(fuente)
        # No paramos el stream porque al pararlo se cuelga... por que?
        #if not len(self.fuentes):
        #    self.stream.stop_stream()

    def fast_concatenate(self,input):
        # Esta funcion solo es apropiada para convertir una matriz en vector, por filas
        # pero es mucho mas rapida (10x) que numpy.concatenate
        return input.reshape(input.shape[0]*input.shape[1])

    @timed_avg_and_freq(1000)
    def callback(self, in_data, frame_count, time_info, status):
        data = [ self.fast_concatenate(f.readframes(frame_count)) for f in self.fuentes ]
        data = reduce(lambda x,y: x+y, data, numpy.zeros(frame_count*Canales.NUM_CANALES))
        return (data.astype(numpy.float32).tostring(), pyaudio.paContinue)

    def sonido(self, clase, nombre, gen=True):
        if clase in self.sonidos and nombre in self.sonidos[clase]:
            return self.sonidos[clase][nombre]
        if gen and nombre in self.sonidos["gen"]:
            return self.sonidos["gen"][nombre]
        if gen:
            return self.sonidos["gen"]["gen"]
        return None

    def registrar_sonido(self, clase, nombre, path):
        if clase not in self.sonidos:
            self.sonidos[clase] = {}
        self.sonidos[clase][nombre] = path

    def buscar_sonidos(self):
        for (dirpath, dirnames, filenames) in walk("sonidos"):
            # print(dirpath, dirnames, filenames)
            for fn in filenames:
                self.registrar_sonido(os.path.basename(dirpath), fn.split(".",1)[0], os.path.join(dirpath, fn) )


if __name__ == '__main__':
    AudioSystem.filtrado.append( lambda d: "USB" in d["name"] )
    s = AudioSystem()
    print( "=============" )
    print( s.sonidos )
    print( "=============" )

    f1=RepeatingWav("/usr/share/skype/sounds/VoicemailReceived.wav")
    f2=Sin(329.63*2)
    f1.canales=Fader()
    f2.canales=UnCanal(0)
    f2.canales.phase=3.14/4
    f2.amp = 0.2
    f2.fade_in(1000)
    f3=NoHaySonidoPara("mi")
    s.nueva_fuente(f1)
    s.nueva_fuente(f2)
    s.nueva_fuente(f3)

    n=0

    # wait for stream to finish
    while s.stream.is_active():
        print("Cambiando a canal "+str(n))
        f1.canales.nuevo(UnCanal(n))
        n = (n+1)%Canales.NUM_CANALES
        time.sleep(5)
        if n==5:
           f2.fade_out(100)

    # stop stream
    s.stream.stop_stream()
    s.stream.close()

    s.terminate()

