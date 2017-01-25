# tren
Sistema de control automático de maqueta de tren

Cómo instalar los paquetes de sistema operativo necesarios para la ejecución en python 3:
sudo apt-get install python3-pip libasound2-dev libffi-dev python3-dev python3-numpy python3-pyaudio python3-tornado python3-pil

Para el módulo de text-to-speech de los mensajes de las estaciones:
sudo apt-get install libttspico-utils sox

Y además hay que instalar módulos directamente en Python3 (que no están disponibles en versiones adecuadas como paquetes de la distribución):
python3 -m pip install pyalsaaudio cffi sounddevice numpy Adafruit_PureIO --user

