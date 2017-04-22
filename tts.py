import tornado.process
import tornado.ioloop
from tornado.gen import Task, Return, coroutine
import os.path

STREAM = tornado.process.Subprocess.STREAM

class TTS(object):
    def tts(self, texto, callback_reproducir, callback_fin=None):
        # Para poder ejecutar el proceso y en paralelo seguir procesando el ioloop,
        # creo una coroutine y la lanzo como un callback del ioloop.
        tornado.ioloop.IOLoop.current().add_callback(self.tts_cor, texto, callback_reproducir, callback_fin)

    @coroutine
    def tts_cor(self, texto, callback_reproducir, callback_fin):
        print("TTS.tts_cor("+str(texto)+","+str(callback_reproducir)+","+str(callback_fin)+")")
        fn="/tmp/"+str(hash(texto))
        print("TTS.tts_cor: fn="+str(fn))
        print("TTS.tts_cor: isfile="+str(os.path.isfile(fn+".44100.wav")))
        # /tmp nos hace de cache simple. Si hubiera mucha variabilidad, eso no bastaria.
        if not os.path.isfile(fn+".44100.wav"):
            cmd = ['/usr/bin/pico2wave','-w',fn+".wav",'-l','es-ES',texto]
            cs = self.call_subprocess(cmd)
            print("TTS.tts_cor: cs="+str(cs))
            result, error = yield cs
            print("TTS.tts_cor: result="+str(result))
            print("TTS.tts_cor: error="+str(error))
            cmd = ['/usr/bin/sox',fn+".wav",fn+".44100.wav","channels","1","rate","44100"]
            cs = self.call_subprocess(cmd)
            print("TTS.tts_cor: cs="+str(cs))
            result, error = yield cs
            print("TTS.tts_cor: result="+str(result))
            print("TTS.tts_cor: error="+str(error))
        print("TTS.tts_cor: callback_reproducir")
        callback_reproducir(fn+".44100.wav", callback=callback_fin)

    @coroutine
    def call_subprocess(self, args):
        print("TTS.call_subprocess "+str(args))
        sub_process = tornado.process.Subprocess(
            args, stdin=STREAM, stdout=STREAM, stderr=STREAM
        )
        print("TTS.call_subprocess "+str(sub_process))
        #yield Task(sub_process.stdin.write, "")
        result, error = yield [
            Task(sub_process.stdout.read_until_close),
            Task(sub_process.stderr.read_until_close)
        ]
        raise Return((result, error))

