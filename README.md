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

Para que el software tenga acceso al bus I2C, es necesario tenerlo activado. En Raspbian se puede utilizar el comando `raspi-config` y habilitar I2C desde ahí. En distribuciones que no tienen `raspi-config`, como OSMC, simplemente se añade una línea al fichero `/boot/config.txt` y se reinicia:
```
[...]
dtparam=i2c_arm=on
```

Asimismo, nos aseguraremos de que en el fichero `/etc/modules` haya una línea con:
```
i2c-dev
```

Cómo instalar los paquetes de sistema operativo necesarios para la ejecución en python 3:
```
sudo apt-get update
sudo apt-get install python3-pip libasound2-dev libffi-dev python3-dev python3-numpy python3-pyaudio python3-tornado python3-pil gcc i2c-tools
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

En la distribución OSMC (no es aplicable a Raspbian) es conveniente desactivar el servicio "mediacenter":
```
sudo service mediacenter stop
sudo systemctl disable mediacenter
```

Si se va a clonar el repositorio desde github, se necesitará también el "git". Instalación y clonado, en dos comandos:
```
sudo apt-get install git
git clone https://github.com/antonio-fiol/tren.git
```
de lo contrario, se puede descargar el fichero ZIP desde github y descomprimirlo directamente en la raspberry. Recomiendo, por facilidad de actualización, clonar el repositorio.

Para evitar que el log se escriba en la tarjeta SD, y con ello se reduzca su vida útil, podemos redirigir el log a algún directorio montado en un tmpfs. En OSMC, el directorio /run está montado en tmpfs y tiene permisos de escritura para cualquier usuario. Así pues:
```
ln -s /run/tren.log ~/tren/tren.log
```

## Personalización

El software en este repositorio permite controlar cualquier maqueta, pero no tiene forma de conocer cómo es esa maqueta. Para que la conozca, habrá que personalizar varios ficheros.

### Configuración de la maqueta

La configuración de la maqueta se realiza en el fichero `.py` que se utiliza para arrancar el sistema. Como ejemplo, el fichero utilizado para arrancar mi maqueta es `con_puente.py`. Si se crea un fichero nuevo, habrá que apuntar a él desde el `start.sh`, o crear un nuevo `.sh` y apuntar a él desde el `tren.service` que se instalará más abajo para el autoarranque.

Para probar, en lugar de arrancar la maqueta como servicio, es recomendable arrancar directamente ese `.py` y ver el log en consola.

```
./con_puente.py
```

En este fichero hay que indicar todos los tramos que conforman la maqueta, los desvíos, y las conexiones entre ellos. Además, se pueden definir estaciones, zonas, locomotoras, eventos, etc. En el fichero de ejemplo se muestran usos de las diferentes capacidades.

### Dibujo

Todo el control de la maqueta se realiza desde el navegador, y la visualización de la misma es un fichero SVG en el que cada elemento tiene un identificador que corresponde con el identificador indicado en la configuración. El `static/drawing.svg` es un ejemplo de ello.

### Fotos y sonidos

Cada locomotora puede tener una foto y sonidos personalizados.

Las estaciones pueden tener fotos.

## Autoarranque

Para que arranque automáticamente (después de cambiar `osmc` por el usuario correcto y revisar las rutas en el `tren.service` si procede):
```
sudo cp tren/tren.service /lib/systemd/system
sudo systemctl enable tren
sudo service tren start
```


