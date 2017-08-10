#!/usr/bin/env python3
from maqueta import *
from chips_maqueta import *
from audio_maqueta import AudioSystem, UnCanal, Mixer
from pista_medicion import PistaMedicion

if __name__ == "__main__":

    #from change_monitor import ChangeMonitor
    #ChangeMonitor(Tren)

    DrawingHandler.name = "con-puente.svg"

    # Preferir un dispositivo PCM conectado por USB
    AudioSystem.filtrado.append( lambda d: "USB" in d["name"] )

    # "Device" es el nombre que aparece al listar con aplay -l
    # card 1: Device [USB Sound Device], device 0: USB Audio [USB Audio]
    Mixer.nombre_tarjeta_mixer_preferida = "Device"
    #Mixer.nombre_tarjeta_mixer_preferida = "PCH"
    Mixer()


    # Listado de desvios de la maqueta. Indica a cuales se entra por el centro y a cuales por el rojo/verde (*)
    # (*) suponiendo un tren que parte hacia la izquierda desde M1 y nunca cambia de polaridad (X1-->Desvio10)
    Desvio(1, inv=True) # (*) se entra al desvio por el rojo o el verde en lugar de por el centro
    Desvio(2)
    Desvio(3, inv=True)
    Desvio(4)
    Desvio(5)
    Desvio(6, inv=True, estado_inicial=Desvio.ROJO)
    Desvio(7, estado_inicial=Desvio.ROJO)
    Desvio(8, inv=True)
    Desvio(9)
    Desvio(10)
    Desvio(11, inv=True, estado_inicial=Desvio.ROJO)
    Desvio(12, inv=True)
    Desvio(13)
    Desvio(14, inv=True)
    Desvio(15)
    Desvio(16, inv=True)
    Desvio(17, inv=True)

    # Comportamientos automaticos de los desvios (para cerrar las entradas de la X)
    #       Desvio   7, al ponerse  VERDE  cambiara     el desvio  11    a    ROJO    y el desvio  12    a    VERDE
    #Maqueta.desvios[ 7].auto[Desvio.VERDE].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    #Maqueta.desvios[10].auto[Desvio.ROJO ].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    #Maqueta.desvios[11].auto[Desvio.VERDE].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})
    #Maqueta.desvios[12].auto[Desvio.ROJO ].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})

    # ZonaRestringida( lista de combinaciones que permiten la entrada )
    # Cada combinacion: { desvio:color, ... }
    ZonaRestringida({Maqueta.desvios[7]:Desvio.VERDE, Maqueta.desvios[10]:Desvio.ROJO},
                    {Maqueta.desvios[11]:Desvio.VERDE, Maqueta.desvios[12]:Desvio.ROJO})

    # Semaforos
    # Se declaran igual que los tramos, pero con un parametro limites_rojo con un LimiteSemaforoRojo
    Semaforo("S1",0.29,limites=[LimiteVelocidad(40.0)],limites_rojo=[LimiteSemaforoRojo(maximo=10.0)])
    Semaforo("I6",0.745, limites=[LimiteVelocidad(40)],limites_rojo=[LimiteSemaforoRojo(maximo=40,porcentaje=63).inv] ),
    Semaforo("I2", 0.62, limites_rojo=[LimiteSemaforoRojo(porcentaje=65.0,debug=True)] )
    
    Maqueta.semaforos["I2"].inv.limites_rojo.append(LimiteSemaforoRojo(porcentaje=70.0,debug=True))
    #semaforos.update({semaforos["I2"].inv.desc:semaforos["I2"].inv})

    lc1 = LimiteCondicional( lambda maqueta, tren: maqueta.desvios[7].estado==Desvio.VERDE, LimiteAcercamiento(100,80.0,40), LimiteVelocidad(100) )
    lc2 = LimiteCondicional( lambda maqueta, tren: maqueta.semaforos["S1"].estado==Semaforo.ROJO, LimiteAcercamiento(100,80,10), LimiteVelocidad(100) )

    #semaforos["I6"].limites.append(lc2)
    #semaforos["I2"].limites.append(lc1)

    # Listado de tramos de la maqueta (el orden no importa)
    # DESC: Tramo(DESC, longitud)
    # Puentes
    Tramo("P1", 0.65, limites=[LimiteBajada(inicio_forzado=0, forzar_en=0)]).longitud=0.40      # Toda en bajada. Longitud de bajada corregida.
    Tramo("P2", 1.66, limites=[LimiteBajada(inicio_forzado=80, forzar_en=95),         # 30 cm de bajada
                               LimiteBajada(inicio_forzado=40, forzar_en=55).inv()])  # 96 cm de bajada
    Tramo("P3", 1.46, limites=[LimiteBajada(inicio_forzado=75, forzar_en=90)])        # 30 cm de bajada
    Tramo("P4", 1.47)

    # Vias muertas
    Tramo("M2", 0.59)
    Tramo("M3", 0.64)

    # Vias muertas hacia estanteria
    Tramo("M4", 0.48)
    Tramo("M5", 0.96)

    # Circuito interior
    Tramo("I1", 1.13,  limites=[LimiteAcercamiento(100,80.0,40).inv()] )
    Tramo("I3", 1.08) # Por el lado largo, bastante mas.
    Tramo("I4", 1.63)
    Tramo("I5", 0.46,  limites=[LimiteAcercamiento(100,80.0,40)] )
    #Tramo("I6", 0.745, limites=[LimiteVelocidad(40), lc2 ] )

    # Circuito exterior
    Tramo("E1", 0.67,  limites=[LimiteAcercamiento(100,80.0,40).inv()] )
    Tramo("E2", 0.40)
    Tramo("E8", 0.3)
    Tramo("E3", 0.93)
    Tramo("E7", 0.985)
    Tramo("E4", 0.54)
    Tramo("E5", 0.67,  limites=[LimiteAcercamiento(100,80.0,40)] )
    Tramo("E6", 0.84,  limites=[LimiteVelocidad(40)] )

    # Cruce
    #TramoX("X1", 0.01, limites=[LimiteVelocidad(39)] ) # 0.12-0.305 - Limite a 39 para que no mida
    Tramo("X1", 0.01, limites=[LimiteVelocidad(39)] ) # 0.12-0.305 - Limite a 39 para que no mida
    Tramo("X2", 0.01, limites=[LimiteVelocidad(39)] ) # 0.12-0.305 - Limite a 39 para que no mida

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
    #conexion(Muerta(), tramos["M1"]), # Via muerta sin entrada
    #conexion(tramos["M1"], desvios[3].rojo)

    # Circuito exterior
    conexion(desvios[3].centro, desvios[1].verde)
    conexion(desvios[1].centro, tramos["E1"])
    conexion(tramos["E1"], tramos["E2"])

    conexion(tramos["E2"], desvios[6].rojo)
    conexion(desvios[6].centro, tramos["E8"])
    conexion(tramos["E8"], desvios[13].centro)
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
    #conexion(tramos["I3"], tramos["I4"])       ## Eliminar para activar el puente
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
    #conexion(desvios[11].verde.inv, tramos["X1"])
    #conexion(tramos["X1"], desvios[12].rojo)
    conexion(desvios[11].verde.inv, tramos["X2"])
    conexion(tramos["X2"], desvios[12].rojo)

    # Vias muertas interiores
    conexion(desvios[5].rojo, tramos["M2"])
    conexion(desvios[5].verde, tramos["M3"])
    conexion(tramos["M2"], Muerta())
    conexion(tramos["M3"], Muerta())

    # Vias muertas estanteria
    conexion(Muerta(),tramos["M5"])
    conexion(tramos["M5"],tramos["M4"])
    conexion(tramos["M4"],desvios[6].verde)

    # Puente "interior"
    conexion(desvios[4].rojo, desvios[15].centro)
    conexion(desvios[15].verde, desvios[5].centro)
    conexion(desvios[15].rojo, tramos["P2"])
    conexion(tramos["P2"], desvios[17].rojo)
    conexion(desvios[17].centro, tramos["P1"])
    conexion(tramos["P1"], desvios[3].rojo)

    # Puente original
    conexion(tramos["I3"], desvios[16].verde)
    conexion(desvios[16].centro, tramos["P4"])
    conexion(tramos["P4"], tramos["I4"])

    # Puente "exterior"
    conexion(desvios[16].rojo.inv, tramos["P3"])
    conexion(tramos["P3"], desvios[17].verde)

    PistaMedicion(tramos=[tramos[x] for x in ["E1","E2","E8","E3","E4","E5","E6"]])

    # Listado de estaciones
    #Estacion(nombre,sentido,tramo,%,desc=descripcion).controlar_tramo_previo(velocidad_de_traspaso_entre_tramos)
    Estacion("st1","cw", Maqueta.tramos["S1"],20, desc="Salóu centro").controlar_tramo_previo(15)
    Estacion("st1","ccw",Maqueta.tramos["I6"].inv,63, desc="Salóu centro")

    Estacion("st1e","cw", Maqueta.tramos["E6"],70, desc="Salóu periferia")
    Estacion("st1e","ccw",Maqueta.tramos["E6"].inv,50, desc="Salóu periferia")

    Estacion("st2","cw", Maqueta.tramos["I2"],65, desc="Centro")
    Estacion("st2","ccw",Maqueta.tramos["I2"].inv,70, desc="Centro")

    #AsociacionEstaciones(nombre, sentido, [ __estaciones__ ], desc=descripcion)
    AsociacionEstaciones("detras", "cw", [
        Estacion("st3", "cw", Maqueta.tramos["E3"], 80),
        Estacion("st3e", "cw", Maqueta.tramos["E7"], 80),
    ], desc="Lejos")
    AsociacionEstaciones("detras", "ccw", [
        Estacion("st3", "ccw", Maqueta.tramos["E3"].inv, 80),
        Estacion("st3e", "ccw", Maqueta.tramos["E7"].inv, 80),
    ], desc="Lejos")

    Estacion("est","ccw",Maqueta.tramos["M5"].inv,90,desc="Estanteria")

    Demo(1,"Corta",[("st1e","ccw"),("est","ccw")])

    # Listado de zonas
    Zona("Tunel1").incluye(tramos["E2"],desde=0,hasta=85).incluye(tramos["I1"],desde=42,hasta=73)
    Zona("Tunel2").incluye(tramos["E4"],desde=20,hasta=87).incluye(tramos["I4"],desde=71,hasta=90)
    pn = Zona("PasoANivel").incluye(tramos["E5"]).incluye(tramos["E4"],desde=50).incluye(tramos["I5"]).incluye(tramos["I4"],desde=75)

    # Zonas para Altavoces
    # -----------------------pared------------------------
    #     front-left         center      surround-left
    #     front-right         lfe       surround-right

    Zona("Audio-FL").suena_por(UnCanal(0)).incluye(tramos["E2"]).incluye(tramos["I1"],desde=41).incluye(tramos["I4"],hasta=18).incluye(tramos["E7"],hasta=33).incluye(tramos["E3"],hasta=33).incluye(tramos["I2"],hasta=12).incluye(tramos["E8"]).incluye(tramos["M4"])
    Zona("Audio-FR").suena_por(UnCanal(1)).incluye(tramos["I1"],hasta=24).incluye(tramos["E1"]).incluye(tramos["M5"])
    Zona("Audio-SL").suena_por(UnCanal(2)).incluye(tramos["E4"]).incluye(tramos["I4"],desde=34,hasta=94).incluye(tramos["I3"],desde=24,hasta=44).incluye(tramos["E7"],desde=66).incluye(tramos["E3"],desde=66) # TODO Revisar I3
    Zona("Audio-SR").suena_por(UnCanal(3)).incluye(tramos["I3"],hasta=24).incluye(tramos["E5"]).incluye(tramos["I5"]).incluye(tramos["X1"]).incluye(tramos["X2"])
    Zona("Audio-CE").suena_por(UnCanal(4)).incluye(tramos["E3"],desde=33,hasta=66).incluye(tramos["E7"],desde=33,hasta=66).incluye(tramos["M2"]).incluye(tramos["M3"]).incluye(tramos["I2"],desde=12).incluye(tramos["I4"],desde=18,hasta=34).incluye(tramos["I3"],desde=44,hasta=65)
    Zona("Audio-LF").suena_por(UnCanal(5)).incluye(tramos["I6"]).incluye(tramos["E6"],desde=15).incluye(tramos["P1"])

    farolas = Luz("farolas")
    casas = Luz("casas")
    via_estanteria_colocada = Luz("via_estanteria_colocada")

    # Listado de chips que alimentan las vias, indicando que tramo alimentan los pines de cada chip.
    # La polaridad del tramo sigue la regla (*).
    # Indicar "None" si un par de pines no alimenta ningun tramo.
    ChipVias(0x40,[
        # Adafruit 0
        # Placa 2 (Derecha con los puentes H arriba)
        tramos["M3"], # Pins 0-1 => VIA2
        tramos["I6"], # Pins 2-3 => VIA1
        tramos["E6"], # Pins 4-5 => VIA4
        tramos["E8"], # Pins 6-7 => VIA3

        # Placa 1 (Izquierda)
        tramos["M2"], # Pins 8-9 => VIA2
        tramos["I2"], # Pins 10-11 => VIA1
        tramos["S1"], # Pins 12-13 => VIA4
        tramos["P1"], # Pins 14-15 => VIA3
    ], debug=False)

    ChipVias(0x41,[
        # Adafruit 1
        # Placa 4
        tramos["P4"], # 0-1
        tramos["E1"],
        tramos["I1"],
        tramos["E5"],

        # Placa 3
        tramos["I5"],
        tramos["E4"],
        TramosConAlimentacionCompartida(tramos["X1"], tramos["X2"]),
        tramos["I4"],
    ], debug=False)

    ChipVias(0x42,[
        # Adafruit 2
        # Placa 6
        tramos["M4"],
        tramos["M5"],
        tramos["P2"],
        tramos["P3"],

        # Placa 5
        tramos["I3"],
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
        tramos["P4"],
        tramos["E5"], 
        tramos["I1"],

        # A placa 3
        tramos["E4"],
        tramos["I5"],
        tramos["I4"],
        TramosConDeteccionCompartida(tramos["X1"], tramos["X2"]),
        #tramos["X1"],       # MSB (Abajo-izquierda en la placa, par marron)

        # B
        # A placa 2
        tramos["S1"],       # LSB (Abajo-derecha en la placa, par naranja) (Par naranja)
        tramos["P1"],
        tramos["M2"],
        tramos["I2"],       

        # A placa 1
        tramos["E6"],       
        tramos["E8"],
        tramos["M3"],
        tramos["I6"],       # MSB (Arriba-derecha en la placa, par marron)
    ])

    ChipDetector(0x24,[
        # A
        tramos["M5"], # LSB (Arriba-izquierda en la placa)
        tramos["M4"],
        tramos["P3"],
        tramos["P2"],

        # A placa 5
        tramos["E7"],
        tramos["I3"],
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
        via_estanteria_colocada, # MSB (Arriba en la placa)
    ], debug=False)


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
    ChipDesvios(0x23, {
            farolas    :  ChipDesvios.MARRON_D1,
            casas      :  ChipDesvios.BL_MARRON_D1,
            desvios[13]:  ChipDesvios.VERDE_D2,
            desvios[14]:  ChipDesvios.AZUL_D2,
            desvios[15]:  ChipDesvios.BL_VERDE_D2,
            desvios[16]:  ChipDesvios.BL_AZUL_D2,
            desvios[17]:  ChipDesvios.BL_NARANJA_D2,
    }, chip_rv=chip1)

    Locomotora(id="vapor", desc="Vapor", coeffs=[0.11798049502618266, 0.00304658416577914, -1.228381595259825e-05], minimo=1400, muestras_inercia=2)
    Locomotora(id="humo", desc="Humo y luz", coeffs=[0.04602868437873745, 0.0044200608178752016, -1.932449180697901e-05], minimo=1400, muestras_inercia=2)
    Locomotora(id="alco1800", desc="Alco 1800 (Diesel)", coeffs=[0.07409022857194827, 0.006888871942219088, -4.105773701684626e-05], minimo=550)
    #Locomotora(id="talgo", desc="Talgo", coeffs=[0.0705067098, 0.0085391554, -4.4265621878004e-5  ], minimo=1000, muestras_inercia=10)
    Locomotora(id="talgo", desc="Talgo", coeffs=[0.06269762207713507, 0.006847887396690622, -4.1256003045953165e-05], minimo=320, muestras_inercia=10)
    Locomotora(id="comsa", desc="Comsa", coeffs=[0.12077762631211575, 0.003107459392643413, -1.0492061779321495e-05], minimo=1600, muestras_inercia=50)
    Locomotora(id="ef-55", desc="EF-55 (Kato)", coeffs=[0.01958548268810128, 0.00478287434306379, -2.5501116465710806e-05], minimo=780, muestras_inercia=10)
    Locomotora(id="cercanias", desc="Cercanías", coeffs=[0.031261934662692115, 0.006996998827739664, -3.528356235287542e-05], minimo=550, muestras_inercia=20)
    Locomotora(id="c61-006", desc="SNCF C61-006 V", coeffs=[0.061291493686289084, 0.005144162475490486, -3.1719614648088305e-05], minimo=1060, muestras_inercia=2) # 3N
    Locomotora(id="c61-006a",desc="SNCF C61-006 A", coeffs=[0.061291493686289084, 0.005144162475490486, -3.1719614648088305e-05], minimo=1060, muestras_inercia=2) # 3N Helena
    Locomotora(id="v200", desc="V200", coeffs=[-0.017070525390169747, 0.011210285639240654, -6.292727347601206e-05], minimo=1000, muestras_inercia=10) # 3N Helena
    Locomotora(id="2100", desc="2100", coeffs=[0.07240401047268205, 0.0055405416238591115, -3.1329731145268906e-05], minimo=1862, muestras_inercia=2) # 3N

    cond1 = lambda evento: Maqueta().desvios[11].estado==Desvio.VERDE and Maqueta().desvios[12].estado==Desvio.VERDE
    cond2 = lambda evento: Maqueta().desvios[11].estado==Desvio.VERDE and Maqueta().desvios[12].estado==Desvio.ROJO
    cond3 = lambda evento: Maqueta().desvios[7].estado==Desvio.VERDE and Maqueta().desvios[10].estado==Desvio.VERDE
    cond4 = lambda evento: Maqueta().desvios[7].estado==Desvio.VERDE and Maqueta().desvios[10].estado==Desvio.ROJO

    CambiarSemaforo(semaforos["I6 invertido"], Semaforo.ROJO).si(cond1).cuando(Desvio.EventoCambiado, desvios[11])
    CambiarSemaforo(semaforos["I6 invertido"], Semaforo.VERDE).si(cond2).cuando(Desvio.EventoCambiado, desvios[12])
    CambiarSemaforo(semaforos["I2"], Semaforo.ROJO).si(cond3).cuando(Desvio.EventoCambiado, desvios[7])
    CambiarSemaforo(semaforos["I2"], Semaforo.VERDE).si(cond4).cuando(Desvio.EventoCambiado, desvios[10])

    PermitirEstado(desvios[6],Desvio.VERDE).si(via_estanteria_colocada)

    #PulsoDeLuz(flash,1).cuando(Zona.EventoEntraTren, pn)

    #EncenderLuz(farolas).cuando(Desvio.EventoCambiado).tras(3)

    #PulsoDeLuz(mi_luz, 3).cuando(Estacion.EventoTrenParado) # Encender la luz del anden durante 3 segundos cuando un tren se para en la estacion
    #PulsoDeLuz(mi_luz).cuando(Desvio.EventoCambiado)

    SonidoTren("parado").cuando(Tren.EventoVelocidadCero).si_activo_para_tren(por_defecto=False)
    SonidoTren("silbato").cuando(Zona.EventoEntraTren, pn).si_activo_para_tren()
    #SonidoTren("arranca").cuando(Tren.EventoCambioVelocidadEfectiva).si(lambda evento: evento.anterior == 0).si_activo_para_tren(por_defecto=False)
    #SonidoTren("arranca").cuando(Estacion.EventoTrenArrancando).si_activo_para_tren(por_defecto=False)
    #SonidoTren("parado").cuando(Estacion.EventoTrenParado).si_activo_para_tren(por_defecto=False)
    SonidoEstacion("Salida inmediata del tren {tren.clase} con destino {destino}.").cuando(Estacion.EventoTrenParado).si_activo_para_tren(por_defecto=False)
    #Tramo.debug = True
    #listar_eventos_disponibles()

    #Shell(1, "Prueba", "echo hola > /tmp/hola")
    Shell(1, "Apagar el sistema", "sudo shutdown -h now")

    Tira(desc="Ambiente", num_leds=180, dobleces=1, invirtiendo=True).weather()
    Weather.AutoLuces.usa([farolas, casas])

    start()

      #680362647



