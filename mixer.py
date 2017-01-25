from singleton import singleton
from parametros import expuesto, Parametros, EventoParametros
from eventos import GestorEventos
import alsaaudio

@singleton
class Mixer(object):
    nombre_tarjeta_mixer_preferida = None
    nombre_mixer_preferido = None

    def __init__(self):
        try:
            cards = alsaaudio.cards()
            cardindex = 0
            if Mixer.nombre_tarjeta_mixer_preferida and Mixer.nombre_tarjeta_mixer_preferida in cards:
                cardindex = cards.index(Mixer.nombre_tarjeta_mixer_preferida)
            mixers = alsaaudio.mixers(cardindex)
            mixername = mixers[0]
            if Mixer.nombre_mixer_preferido and Mixer.nombre_mixer_preferido in mixers:
                mixername = Mixer.nombre_mixer_preferido
            self.mixer = alsaaudio.Mixer(mixername, cardindex=cardindex)
            print("Mixer inicializado")
            print("Mixer getvolume()="+str(self.mixer.getvolume()))
            Parametros().set("Mixer", "PORCENTAJE_VOLUMEN", self.mixer.getvolume()[0])
            GestorEventos().suscribir_evento(EventoParametros, self.ajustar_volumen, Parametros().d["Mixer"])
        except:
            self.mixer = None
            print("ERROR: Imposible inicializar mixer")
            raise

    def ajustar_volumen(self, evento):
        print("Mixer ajustando volumen")
        print("Mixer: PORCENTAJE_VOLUMEN="+str(Mixer.PORCENTAJE_VOLUMEN))
        self.mixer.setvolume(int(Mixer.PORCENTAJE_VOLUMEN))

    @expuesto
    def PORCENTAJE_VOLUMEN():
        """Volumen del sistema de sonido."""
        return 0


