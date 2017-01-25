#!/usr/bin/env python
from maqueta import *
from chips_maqueta import *

if __name__ == "__main__":

    DrawingHandler.name = "drawing.svg"


    # Listado de desvios de la maqueta. Indica a cuales se entra por el centro y a cuales por el rojo/verde (*)
    # (*) suponiendo un tren que parte hacia la izquierda desde M1 y nunca cambia de polaridad (X1-->Desvio10)
    Desvio(1, inv=True) # (*) se entra al desvio por el rojo o el verde en lugar de por el centro
    Desvio(2)
    Desvio(3, inv=True)
    Desvio(4)
    Desvio(5)
    Desvio(6)
    Desvio(7, estado_inicial=Desvio.ROJO)
    Desvio(8, inv=True)
    Desvio(9)
    Desvio(10)
    Desvio(11, inv=True, estado_inicial=Desvio.ROJO)
    Desvio(12, inv=True)
    Desvio(13)
    Desvio(14, inv=True)
    #Desvio(15)
    #Desvio(16)
    #Desvio(17, inv=True)

    # Comportamientos automaticos de los desvios (para cerrar las entradas de la X)
    #       Desvio   7, al ponerse  VERDE  cambiara     el desvio  11    a    ROJO    y el desvio  12    a    VERDE
    Maqueta.desvios[ 7].auto[Desvio.VERDE].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    Maqueta.desvios[10].auto[Desvio.ROJO ].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    Maqueta.desvios[11].auto[Desvio.VERDE].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})
    Maqueta.desvios[12].auto[Desvio.ROJO ].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})

    # Semaforos
    # Se declaran igual que los tramos, pero con un parametro limites_rojo con un LimiteSemaforoRojo
    Semaforo("S1",0.29,limites=[LimiteVelocidad(40.0)],limites_rojo=[LimiteSemaforoRojo(maximo=10.0)])
    Semaforo("I6",0.745, limites=[LimiteVelocidad(40)],limites_rojo=[LimiteSemaforoRojo(maximo=40,porcentaje=30).inv] ),
    Semaforo("I2", 0.62, limites_rojo=[LimiteSemaforoRojo(porcentaje=80.0,debug=True)] )
    
    Maqueta.semaforos["I2"].inv.limites_rojo.append(LimiteSemaforoRojo(porcentaje=80.0,debug=True))
    #semaforos.update({semaforos["I2"].inv.desc:semaforos["I2"].inv})

    lc1 = LimiteCondicional( lambda maqueta, tren: maqueta.desvios[7].estado==Desvio.VERDE, LimiteAcercamiento(100,80.0,40), LimiteVelocidad(100) )
    lc2 = LimiteCondicional( lambda maqueta, tren: maqueta.semaforos["S1"].estado==Semaforo.ROJO, LimiteAcercamiento(100,80,10), LimiteVelocidad(100) )

    #semaforos["I6"].limites.append(lc2)
    #semaforos["I2"].limites.append(lc1)

    # Listado de tramos de la maqueta (el orden no importa)
    # DESC: Tramo(DESC, longitud)
    # Vias muertas
    Tramo("M1", 0.77)
    # Tramo("P1", 1.00000000) # Medir
    # Tramo("P2", 1.00000000) # Medir
    # Tramo("P3", 1.00000000) # Medir
    # Tramo("P4", 1.00000000) # Medir

    Tramo("M2", 0.59)
    Tramo("M3", 0.45)
    Tramo("M4", 0.45)
    # Circuito interior
    Tramo("I1", 1.13,  limites=[LimiteAcercamiento(100,80.0,40).inv()] )
    Tramo("I3", 2.75) # 2.90 por el lado largo, 2.66 por el tramo corto 
    Tramo("I4", 1.63)
    Tramo("I5", 0.46,  limites=[LimiteAcercamiento(100,80.0,40)] )
    #Tramo("I6", 0.745, limites=[LimiteVelocidad(40), lc2 ] )
    #semaforos["I6"]
    ##semaforos["S1"]
    # Circuito exterior
    Tramo("E1", 0.67,  limites=[LimiteAcercamiento(100,80.0,40).inv()] )
    Tramo("E2", 0.71)
    Tramo("E3", 0.93)
    Tramo("E7", 0.985)
    Tramo("E4", 0.54)
    Tramo("E5", 0.67,  limites=[LimiteAcercamiento(100,80.0,40)] )
    Tramo("E6", 0.84,  limites=[LimiteVelocidad(40)] )
    # Cruce
    TramoX("X1", 0.01, limites=[LimiteVelocidad(39)] ) # 0.12-0.305 - Limite a 39 para que no mida

    # Listado de todos los objetos (tramos) de la maqueta que estan conectados.
    #
    # Se especifica segun un tren podria ir saltando de tramo a tramo (*)
    #
    # Los desvios tienen tres tramos (centro, rojo, verde), ya conectados internamente entre ellos,
    # de modo que aqui solo hay que indicar a que tramo (u otro desvio) estan conectados por fuera.
    #
    # Las vias muertas empiezan o acaban en "Muerta()", que representa el final de la via.
    #
    # Todos los objetos de la maqueta deben estar conectados entre ellos (logicamente, o un tren se
    # saldria de la via).

    # "alias" para escribir menos en las siguientes lineas
    desvios = Maqueta.desvios
    tramos = Maqueta.tramos
    semaforos = Maqueta.semaforos

    # Via muerta exterior
    conexion(Muerta(), tramos["M1"]), # Via muerta sin entrada
    conexion(tramos["M1"], desvios[3].rojo)

    # Circuito exterior
    conexion(desvios[3].centro, desvios[1].verde)
    conexion(desvios[1].centro, tramos["E1"])
    conexion(tramos["E1"], tramos["E2"])

    #conexion(tramos["E2"], tramos["E3"])
    #conexion(tramos["E3"], tramos["E4"])
    conexion(tramos["E2"], desvios[13].centro)
    conexion(desvios[13].verde, tramos["E3"])
    conexion(desvios[13].rojo, tramos["E7"])
    conexion(tramos["E3"], desvios[14].verde)
    conexion(tramos["E7"], desvios[14].rojo)
    conexion(desvios[14].centro, tramos["E4"])

    conexion(tramos["E4"], tramos["E5"])
    conexion(tramos["E5"], desvios[9].centro)
    conexion(desvios[9].verde, tramos["E6"])
    conexion(tramos["E6"], desvios[3].verde)

    # Entre circuitos (desvios 1,2,8,9)
    conexion(desvios[2].rojo, desvios[1].rojo)
    conexion(desvios[9].rojo, desvios[8].rojo)

    # Circuito interior
    conexion(desvios[2].verde, tramos["I1"])
    conexion(tramos["I1"], desvios[4].centro)
    conexion(desvios[4].verde, tramos["I2"])
    conexion(tramos["I2"], desvios[7].centro)
    conexion(desvios[7].rojo, desvios[12].verde)
    conexion(desvios[12].centro, tramos["I3"])
    conexion(tramos["I3"], tramos["I4"])       ## Eliminar para activar el puente
    conexion(tramos["I4"], tramos["I5"])
    conexion(tramos["I5"], desvios[10].centro)
    conexion(desvios[10].verde, desvios[8].verde)
    conexion(desvios[8].centro, desvios[11].rojo)
    conexion(desvios[11].centro, tramos["I6"])
    conexion(tramos["I6"], tramos["S1"])
    conexion(tramos["S1"], desvios[2].centro)

    # Cruce
    conexion(desvios[7].verde, tramos["X1"])
    conexion(tramos["X1"], desvios[10].rojo.inv) # .inv para indicar el cambio de polaridad
    conexion(desvios[11].verde.inv, tramos["X1"])
    conexion(tramos["X1"], desvios[12].rojo)

    # Vias muertas interiores
    conexion(desvios[4].rojo, desvios[5].centro)  ## Eliminar para activar el puente
    conexion(desvios[5].rojo, tramos["M2"])
    conexion(desvios[5].verde, desvios[6].centro)
    conexion(desvios[6].rojo, tramos["M3"])
    conexion(desvios[6].verde, tramos["M4"])
    conexion(tramos["M2"], Muerta())
    conexion(tramos["M4"], Muerta())
    conexion(tramos["M3"], Muerta())

    # Puente "sin inversion"
    #conexion(desvios[4].rojo, desvios[15].centro)
    #conexion(desvios[15].verde, desvios[5].centro)
    #conexion(desvios[15].rojo, tramos["P2"])
    #conexion(tramos["P2"], desvios[17].rojo)
    #conexion(desvios[17].centro, tramos["P1"])
    #conexion(tramos["P1"], desvios[3].rojo)

    # Puente "invertido"
    #conexion(tramos["I3"], desvios[16].verde)
    #conexion(desvios[16].centro, tramos["P4"])
    #conexion(tramos["P4"], tramos["I4"])
    #conexion(desvios[16].rojo.inv, tramos["P3"])
    #conexion(tramos["P3"], desvios[17].verde)



    # Listado de estaciones
    #Estacion(nombre,sentido,tramo,%),
    Estacion("st1","cw", Maqueta.tramos["S1"],20).controlar_tramo_previo(20)
    Estacion("st1","ccw",Maqueta.tramos["I6"].inv,30)

    Estacion("st1e","cw", Maqueta.tramos["E6"],70)
    Estacion("st1e","ccw",Maqueta.tramos["E6"].inv,50)

    Estacion("st2","cw", Maqueta.tramos["I2"],70)
    Estacion("st2","ccw",Maqueta.tramos["I2"].inv,70)

    # Listado de zonas
    #Zona("Tunel1").incluye(tramos["E2"],desde=20).incluye(tramos["I1"],desde=40,hasta=60)
    #Zona("Tunel2").incluye(tramos["E4"]).incluye(tramos["I4"],desde=80)
    #pn = Zona("PasoANivel").incluye(tramos["E5"],desde=40,hasta=70).incluye(tramos["I5"],desde=40,hasta=70)

    # Zonas para Altavoces
    # -----------------------pared------------------------
    #     surround-left       lfe       surround-right
    #     front-left         center        front-right
    #Zona("Audio-SL").incluye(tramos["E2"]).incluye(tramos["E1"],desde=80).incluye(tramos["I1"],desde=30).incluye(tramos["I3"],desde=60).incluye(tramos["I4"],hasta=20)
    #Zona("Audio-LF").incluye(tramos["E3"]).incluye(tramos["E7"]).incluye(tramos["M2"]).incluye(tramos["M3"]).incluye(tramos["M4"]).incluye(tramos["I2"]).incluye(tramos["I4"],desde=10,hasta=80).incluye(tramos["I3"],desde=30,hasta=60)
    #Zona("Audio-SR").incluye(tramos["E4"]).incluye(tramos["I4"],desde=70).incluye(tramos["I3"],desde=20,hasta=40)
    #Zona("Audio-FL").incluye(tramos[""])
    #Zona("Audio-CE").incluye(tramos[""])
    #Zona("Audio-FR").incluye(tramos[""])

    # Listado de zonas
    Zona("Tunel1").incluye(tramos["E2"],desde=0,hasta=85).incluye(tramos["I1"],desde=42,hasta=73)
    Zona("Tunel2").incluye(tramos["E4"],desde=20,hasta=87).incluye(tramos["I4"],desde=71,hasta=90)
    pn = Zona("PasoANivel").incluye(tramos["E5"],desde=30,hasta=60).incluye(tramos["I5"],desde=22,hasta=54)

    # Zonas para Altavoces
    # -----------------------pared------------------------
    #     surround-left       lfe       surround-right
    #     front-left         center        front-right
    Zona("Audio-SL").incluye(tramos["E2"]).incluye(tramos["I1"],desde=41).incluye(tramos["I3"],desde=92).incluye(tramos["I4"],hasta=18).incluye(tramos["E7"],hasta=33).incluye(tramos["E3"],hasta=33).incluye(tramos["I2"],hasta=12)
    Zona("Audio-LF").incluye(tramos["E3"],desde=33,hasta=66).incluye(tramos["E7"],desde=33,hasta=66).incluye(tramos["M2"]).incluye(tramos["M3"]).incluye(tramos["M4"]).incluye(tramos["I2"],desde=12).incluye(tramos["I4"],desde=18,hasta=34).incluye(tramos["I3"],desde=44,hasta=65)
    Zona("Audio-SR").incluye(tramos["E4"]).incluye(tramos["I4"],desde=34,hasta=94).incluye(tramos["I3"],desde=24,hasta=44).incluye(tramos["E7"],desde=66).incluye(tramos["E3"],desde=66)
    Zona("Audio-FL").incluye(tramos["I1"],hasta=24).incluye(tramos["E1"]).incluye(tramos["I3"],desde=65,hasta=92)
    Zona("Audio-CE").incluye(tramos["I6"]).incluye(tramos["E6"],desde=15).incluye(tramos["M1"])
    Zona("Audio-FR").incluye(tramos["I3"],hasta=24).incluye(tramos["E5"]).incluye(tramos["I5"]). incluye(tramos["X1"])


    # Listado de chips que alimentan las vias, indicando que tramo alimentan los pines de cada chip.
    # La polaridad del tramo sigue la regla (*).
    # Indicar "None" si un par de pines no alimenta ningun tramo.
    ChipVias(0x40,[
        # Adafruit 0
        # Placa 2 (Derecha con los puentes H arriba)
        tramos["M3"], # Pins 0-1 => VIA2
        tramos["I6"], # Pins 2-3 => VIA1
        tramos["E6"], # Pins 4-5 => VIA4
        tramos["M4"], # Pins 6-7 => VIA3

        # Placa 1 (Izquierda)
        tramos["M2"], # Pins 8-9 => VIA2
        tramos["I2"], # Pins 10-11 => VIA1
        tramos["S1"], # Pins 12-13 => VIA4
        tramos["M1"], # Pins 14-15 => VIA3
    ], debug=False)

    ChipVias(0x41,[
        # Adafruit 1
        # Placa 4
        tramos["I3"], # 0-1
        tramos["E1"],
        tramos["I1"],
        tramos["E5"],

        # Placa 3
        tramos["I5"],
        tramos["E4"], 
        tramos["X1"],
        tramos["I4"],
    ], debug=False)

    ChipVias(0x42,[
        # Adafruit 2
        # Placa 6 (inexistente)
        None,
        None,
        None,
        None,

        # Placa 5
        None,
        tramos["E7"],
        tramos["E3"], # 12-13
        tramos["E2"], # 14-15
    ], debug=False)

    # Listado de chips que detectan la presencia de trenes en las vias, indicando que tramo detectan los pines de cada chip.
    # La deteccion no tiene en cuenta la polaridad
    # Indicar "None" si un pin no detecta ningun tramo.
    ChipDetector(0x25,[
        # A
        # A placa 4
        tramos["E1"],       # LSB (Arriba-izquierda en la placa, par naranja)
        tramos["I3"],
        tramos["E5"], 
        tramos["I1"],

        # A placa 3
        tramos["E4"],
        tramos["I5"],
        tramos["I4"],
        tramos["X1"],       # MSB (Abajo-izquierda en la placa, par marron)

        # B
        # A placa 2
        tramos["S1"],       # LSB (Abajo-derecha en la placa, par naranja) (Par naranja)
        tramos["M1"],
        tramos["M2"],
        tramos["I2"],       

        # A placa 1
        tramos["E6"],       
        tramos["M4"],
        tramos["M3"],
        tramos["I6"],       # MSB (Arriba-derecha en la placa, par marron)
    ])

    ChipDetector(0x24,[
        # A
        None, # LSB (Arriba-izquierda en la placa)
        None,
        None,
        None,

        # A placa 5
        tramos["E7"],
        None,
        tramos["E2"],
        tramos["E3"], # MSB (Abajo-izquierda en la placa, par marron)

        # B (Derecha en la placa)
        None, # LSB (Abajo en la placa)
        None,
        None,
        None,

        None,
        None,
        None,
        None, # MSB (Arriba en la placa)
    ])


    chip1 = ChipDesvios(0x22, {
            desvios[1]:  ChipDesvios.AZUL_D1,
            desvios[2]:  ChipDesvios.BL_AZUL_D1,
            desvios[3]:  ChipDesvios.BL_VERDE_D1,
            desvios[4]:  ChipDesvios.VERDE_D1,
            desvios[5]:  ChipDesvios.BL_NARANJA_D2,
            desvios[6]:  ChipDesvios.NARANJA_D2,
            desvios[7]:  ChipDesvios.VERDE_D2,
            desvios[8]:  ChipDesvios.AZUL_D2,
            desvios[9]:  ChipDesvios.BL_VERDE_D2,
            desvios[10]: ChipDesvios.BL_AZUL_D2,
            desvios[11]: ChipDesvios.MARRON_D1,
            desvios[12]: ChipDesvios.BL_MARRON_D1,
            semaforos["S1"].luz[Semaforo.ROJO]: ChipDesvios.NARANJA_D1,
            semaforos["S1"].luz[Semaforo.VERDE]: ChipDesvios.BL_NARANJA_D1,
    })
    flash=Luz("flash")
    ChipDesvios(0x23, {
            flash: ChipDesvios.MARRON_D1,
            desvios[13]:  ChipDesvios.VERDE_D2,
            desvios[14]:  ChipDesvios.AZUL_D2,
    }, chip_rv=chip1)

    Locomotora(id="vapor", desc="Vapor", coeffs=[0.030598368520900296, 0.006112721300524377, -3.525936355581414e-05], minimo=1400)
    Locomotora(id="humo", desc="Humo y luz", coeffs=[0.04602868437873745, 0.0044200608178752016, -1.932449180697901e-05], minimo=1400)
    Locomotora(id="diesel", desc="Diesel", coeffs=[0.07409022857194827, 0.006888871942219088, -4.105773701684626e-05], minimo=550)
    Locomotora(id="talgo", desc="Talgo", coeffs=[0.0705067098, 0.0085391554, -4.4265621878004e-5  ], minimo=1000)
    Locomotora(id="comsa", desc="Comsa", coeffs=[0.04874525776472234, 0.003503784264754981, -1.2409169341061733e-05], minimo=1600)


    cond1 = lambda evento: Maqueta().desvios[11].estado==Desvio.VERDE and Maqueta().desvios[12].estado==Desvio.VERDE
    cond2 = lambda evento: Maqueta().desvios[11].estado==Desvio.VERDE and Maqueta().desvios[12].estado==Desvio.ROJO
    cond3 = lambda evento: Maqueta().desvios[7].estado==Desvio.VERDE and Maqueta().desvios[10].estado==Desvio.VERDE
    cond4 = lambda evento: Maqueta().desvios[7].estado==Desvio.VERDE and Maqueta().desvios[10].estado==Desvio.ROJO

    CambiarSemaforo(semaforos["I6 invertido"], Semaforo.ROJO).si(cond1).cuando(Desvio.EventoCambiado, desvios[11])
    CambiarSemaforo(semaforos["I6 invertido"], Semaforo.VERDE).si(cond2).cuando(Desvio.EventoCambiado, desvios[12])
    CambiarSemaforo(semaforos["I2"], Semaforo.ROJO).si(cond3).cuando(Desvio.EventoCambiado, desvios[7])
    CambiarSemaforo(semaforos["I2"], Semaforo.VERDE).si(cond4).cuando(Desvio.EventoCambiado, desvios[10])

    PulsoDeLuz(flash,1).cuando(Zona.EventoEntraTren, pn)


    #PulsoDeLuz(mi_luz, 3).cuando(Estacion.EventoTrenParado) # Encender la luz del anden durante 3 segundos cuando un tren se para en la estacion
    #PulsoDeLuz(mi_luz).cuando(Desvio.EventoCambiado)

    #SonidoTren("parado").cuando(Tren.EventoVelocidadCero)   # Esto aun no funciona, pero se declararia asi

    #Tramo.debug = True
    #listar_eventos_disponibles()
    start()


