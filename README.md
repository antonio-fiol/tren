# tren
Sistema de control automático de maqueta de tren


## Descripción

Este proyecto es el resultado del desarrollo de un sistema avanzado de control para una maqueta de tren completamente analógica.

Partiendo de la premisa de no modificar el material rodante en absoluto, y de no introducir elementos visibles en la maqueta para permitir el control, tales como barreras ópticas o similares, surgió el reto de detectar con cierta precisión la posición de un tren en la propia maqueta, cómo controlar su velocidad de manera fiable (sobre todo a velocidades bajas), y cómo automatizar el funcionamiento, al mismo nivel que las instalaciones digitales o mejor.

A lo largo del tiempo el proyecto ha dado respuesta a esos retos y a otros nuevos, tales como la posibilidad de que un tren, siempre avanzando, pase por un tramo de vía en sentido contrario al que pasó anteriormente (inversión de polaridad en la vía para mantener el avance), o la ambientación de la maqueta con luz (tiras de LED direccionables individualmente) y sonido.

El proyecto ha tenido como frutos:
- Diseño de placa electrónica para el control de velocidad, ampliada posteriormente para control de luces.
- Diseño de placa electrónica para el control de desvíos.
- Diseño de placa electrónica para la detección de trenes.
- Driver software para el control de las placas.
- Abstracciones software de los conceptos básicos de la maqueta (Tren, Tramo, Desvío, Estación, ...).
- Código para funcionalidades básicas de control (presencia, velocidad, ...) y avanzadas (detección/prevención de colisiones en manual, límites de velocidad).
- Código para la automatización (rutas, optimización, prevención de bloqueo, ...)
- Sistema flexible basado en eventos que permite configurar acciones a ejecutar en determinadas circunstancias.
- Abstracciones de conceptos más avanzados (Weather, Zonas, ...) que dan riqueza al funcionamiento de la maqueta.
- Sistema de sonidos que "sigue" al tren (altavoces por zonas) y funcionalidad de texto-a-voz en las estaciones.


## Hardware

El controlador principal del sistema es una Raspberry Pi 2 (o superior) ejecutando un sistema operativo Linux y Python 3.

Dicho controlador principal se comunica con las diferentes placas desarrolladas a medida mediante el bus I2C. Un arduino, también conectado al bus I2C, controla hasta 2 tiras de LEDs.

Es posible utilizar varias placas de cada tipo (en algunos casos hasta un máximo de 8), lo que permite controlar maquetas de complejidad significativa.


## Instalación del Software

Cómo instalar los paquetes de sistema operativo necesarios para la ejecución en python 3:
```
sudo apt-get update
sudo apt-get install python3-pip libasound2-dev libffi-dev python3-dev python3-numpy python3-pyaudio python3-tornado python3-pil
```

Para el módulo de text-to-speech de los mensajes de las estaciones:
```
sudo apt-get update
sudo apt-get install libttspico-utils sox
```

Y además hay que instalar módulos directamente en Python3 (que no están disponibles en versiones adecuadas como paquetes de la distribución):
```
python3 -m pip install pyalsaaudio cffi sounddevice numpy Adafruit_PureIO --user
```

