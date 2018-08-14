#!/usr/bin/env python3
from maqueta import *
from chips_maqueta import *
from audio_maqueta import AudioSystem, UnCanal, Mixer
from pista_medicion import PistaMedicion
from eventos import DescartarConcurrencia
import csv
import re
from collections import defaultdict

if __name__ == "__main__":

    #from change_monitor import ChangeMonitor
    #ChangeMonitor(Tren)

    DrawingHandler.name = "4x1concentrico.svg"

    # Preferir un dispositivo PCM conectado por USB
    AudioSystem.filtrado.append( lambda d: "USB" in d["name"] )

    # "Device" es el nombre que aparece al listar con aplay -l
    # card 1: Device [USB Sound Device], device 0: USB Audio [USB Audio]
    Mixer.nombre_tarjeta_mixer_preferida = "Device"
    #Mixer.nombre_tarjeta_mixer_preferida = "PCH"
    Mixer()


    # Listado de desvios de la maqueta. Indica a cuales se entra por el centro y a cuales por el rojo/verde (*)
    # (*) suponiendo un tren que parte hacia la izquierda desde M1 y nunca cambia de polaridad (X1-->Desvio10)
    #Desvio(1, inv=True) # (*) se entra al desvio por el rojo o el verde en lugar de por el centro
    #Desvio(6, inv=True, estado_inicial=Desvio.ROJO)

    # Comportamientos automaticos de los desvios (para cerrar las entradas de la X)
    #       Desvio   7, al ponerse  VERDE  cambiara     el desvio  11    a    ROJO    y el desvio  12    a    VERDE
    #Maqueta.desvios[ 7].auto[Desvio.VERDE].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    #Maqueta.desvios[10].auto[Desvio.ROJO ].update({Maqueta.desvios[11]:Desvio.ROJO,Maqueta.desvios[12]:Desvio.VERDE,})
    #Maqueta.desvios[11].auto[Desvio.VERDE].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})
    #Maqueta.desvios[12].auto[Desvio.ROJO ].update({Maqueta.desvios[ 7]:Desvio.ROJO,Maqueta.desvios[10]:Desvio.VERDE,})

    # ZonaRestringida( lista de combinaciones que permiten la entrada )
    # Cada combinacion: { desvio:color, ... }
    #ZonaRestringida({Maqueta.desvios[7]:Desvio.VERDE, Maqueta.desvios[10]:Desvio.ROJO},
    #                {Maqueta.desvios[11]:Desvio.VERDE, Maqueta.desvios[12]:Desvio.ROJO})

    # Semaforos
    # Se declaran igual que los tramos, pero con un parametro limites_rojo con un LimiteSemaforoRojo
    #Semaforo("S1",0.29,limites=[LimiteVelocidad(40.0)],limites_rojo=[LimiteSemaforoRojo(maximo=10.0)])
    #Semaforo("I6",0.745, limites=[LimiteVelocidad(40)],limites_rojo=[LimiteSemaforoRojo(maximo=40,porcentaje=63).inv] ),
    #Semaforo("I2", 0.62, limites_rojo=[LimiteSemaforoRojo(porcentaje=65.0,debug=True)] )
    
    #Maqueta.semaforos["I2"].inv.limites_rojo.append(LimiteSemaforoRojo(porcentaje=70.0,debug=True))
    #semaforos.update({semaforos["I2"].inv.desc:semaforos["I2"].inv})

    #lc1 = LimiteCondicional( lambda maqueta, tren: maqueta.desvios[7].estado==Desvio.VERDE, LimiteAcercamiento(100,80.0,40), LimiteVelocidad(100) )
    #lc2 = LimiteCondicional( lambda maqueta, tren: maqueta.semaforos["S1"].estado==Semaforo.ROJO, LimiteAcercamiento(100,80,10), LimiteVelocidad(100) )

    #semaforos["I6"].limites.append(lc2)
    #semaforos["I2"].limites.append(lc1)

    CONECTORES_VIAS = "ABCDEFGHJK" # Añadir siempre de 2 en 2, ordenados segun conexion a las placas
    BASE_CVD = 0x10                # Direccion base de la primera placa. Se asume que las siguientes suman 1.

    mapa={}
    ChipOffset = namedtuple("ChipOffset", [ "chip", "offset" ])
    for d,(a,b) in enumerate(re.findall(r"(..)",CONECTORES_VIAS)):
        c = ChipViasDetector(BASE_CVD+d)
        mapa[a] = ChipOffset(c,-1)
        mapa[b] = ChipOffset(c,3)

    tr = lambda ref, inv: Maqueta.tramos[ref].inv if inv else Maqueta.tramos[ref]
    with open("MaquetaTramos.csv") as csvfile:
        csvfile.readline()
        csvfile.readline()
        reader = csv.DictReader(csvfile, dialect="excel")
        for row in reader:
            print(row)
            longitud = row["Longitud\n(metros)"]
            if(longitud):
                ref = row["Ref"]
                letra, numero = ref
                t = Tramo(ref, float(longitud))
                mapa[letra].chip.registrar(int(numero) + mapa[letra].offset, t)

    with open("MaquetaTramoTramo.csv") as csvfile:
        csvfile.readline()
        csvfile.readline()
        reader = csv.DictReader(csvfile, dialect="excel")
        for row in reader:
            print(row)
            origen, destino, inv = row["Origen"], row["Destino"], row["Inv"]
            if(origen and destino):
                conexion(tr(origen,inv), tr(destino, False))

    sd = SistemaDesvios(0x20)  # Asumimos un unico sistema de desvios
    with open("MaquetaDesvios.csv") as csvfile:
        csvfile.readline()
        csvfile.readline()
        reader = csv.DictReader(csvfile, dialect="excel")
        for row in reader:
            print(row)
            ref = row["Ref"]
            centro, rojo, verde = row["Centro"], row["Rojo"], row["Verde"]
            c_inv, r_inv, v_inv = row["C\nInv"], row["R\nInv"], row["V\nInv"]
            estado_inicial = Coloreado.ROJO if row["Estado\nInicial"] == "R" else Coloreado.VERDE
            if(centro or rojo or verde):
                d=Desvio(ref, estado_inicial=estado_inicial)
                d.registrar_chip_desvios(sd, pin=SalidaRef(ref), chip_rv=sd)
                if centro: conexion(tr(centro, c_inv), d.centro)
                if rojo: conexion(d.rojo, tr(rojo, r_inv))
                if verde: conexion(d.verde, tr(verde, v_inv))

    with open("MaquetaDesvioDesvio.csv") as csvfile:
        csvfile.readline()
        csvfile.readline()
        reader = csv.DictReader(csvfile, dialect="excel")
        for row in reader:
            print(row)
            origen, rama_o, destino, rama_d = row["Origen"], row["RamaO"], row["Destino"], row["RamaD"]
            if(origen and destino and rama_o and rama_d):
                if(rama_o=="C" and rama_d=="C"): raise Error("No se pueden conectar dos desvios por sus centros sin un tramo")
                if(rama_o=="C"):
                    tmp, rama_tmp = origen, rama_o
                    origen, rama_o = destino, rama_d
                    destino, rama_d = tmp, rama_tmp
                desvio_origen = Maqueta.desvios[origen]
                desvio_destino = Maqueta.desvios[destino]
                trd = lambda d,r: d.centro if r=="C" else d.rojo if r=="R" else d.verde if r=="V" else None
                trdi = lambda d,r: trd(d,r) if r=="C" else trd(d,r).inv
                conexion(trd(desvio_origen,rama_o), trdi(desvio_destino, rama_d))

    mapa_estaciones = defaultdict(lambda:defaultdict(list))
    def crea_estacion(nombre, sentido, tramo, inv, porc, desc, asoc):
        if nombre and tramo:
            e = Estacion(nombre, sentido, tramo=tr(tramo,inv), punto_parada=float(porc), desc=desc)
            if(asoc): mapa_estaciones[asoc][sentido].append(e)
    with open("MaquetaAndenes.csv") as csvfile:
        csvfile.readline()
        csvfile.readline()
        reader = csv.DictReader(csvfile, dialect="excel")
        for row in reader:
            print(row)
            crea_estacion(row["Ref"], "cw",  row["CW\nTramo"],  row["CW\nInv"],  row["CW\n%"],  row["Descripción"], row["Estación"])
            crea_estacion(row["Ref"], "ccw", row["CCW\nTramo"], row["CCW\nInv"], row["CCW\n%"], row["Descripción"], row["Estación"])
    print(mapa_estaciones)

    with open("MaquetaEstaciones.csv") as csvfile:
        csvfile.readline()
        csvfile.readline()
        reader = csv.DictReader(csvfile, dialect="excel")
        for row in reader:
            print(row)
            ref, desc = row["Ref"], row["Descripción"]
            if ref:
                for sentido in ("cw","ccw"):
                    estaciones = mapa_estaciones[ref][sentido]
                    if estaciones:
                        AsociacionEstaciones(ref, sentido, estaciones, desc)
    
    # Listado de tramos de la maqueta (el orden no importa)
    # DESC: Tramo(DESC, longitud)
    # Puentes
    #Tramo("P1", 0.65, limites=[LimiteBajada(inicio_forzado=0, forzar_en=0)]).longitud=0.40      # Toda en bajada. Longitud de bajada corregida.
    #Tramo("P2", 1.66, limites=[LimiteBajada(inicio_forzado=80, forzar_en=95),         # 30 cm de bajada
    #                           LimiteBajada(inicio_forzado=40, forzar_en=55).inv()])  # 96 cm de bajada
    #Tramo("P3", 1.46, limites=[LimiteBajada(inicio_forzado=75, forzar_en=90)])        # 30 cm de bajada
    #Tramo("I1", 1.13,  limites=[LimiteAcercamiento(100,80.0,40).inv()] )
    #Tramo("I5", 0.46,  limites=[LimiteAcercamiento(100,80.0,40)] )
    #Tramo("I6", 0.745, limites=[LimiteVelocidad(40), lc2 ] )

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


    #PistaMedicion(tramos=[tramos[x] for x in ["E1","E2","E8","E3","E4","E5","E6"]])

    # Listado de estaciones
    #Estacion(nombre,sentido,tramo,%,desc=descripcion).controlar_tramo_previo(velocidad_de_traspaso_entre_tramos)
    #Estacion("st1","cw", Maqueta.tramos["S1"],20, desc="Salóu centro").controlar_tramo_previo(15)
    #Estacion("st1","ccw",Maqueta.tramos["I6"].inv,63, desc="Salóu centro")

    #Estacion("st1e","cw", Maqueta.tramos["E6"],70, desc="Salóu periferia")
    #Estacion("st1e","ccw",Maqueta.tramos["E6"].inv,50, desc="Salóu periferia")

    #Estacion("st2","cw", Maqueta.tramos["I2"],65, desc="Centro")
    #Estacion("st2","ccw",Maqueta.tramos["I2"].inv,70, desc="Centro")

    #AsociacionEstaciones(nombre, sentido, [ __estaciones__ ], desc=descripcion)
    #AsociacionEstaciones("detras", "cw", [
    #    Estacion("st3", "cw", Maqueta.tramos["E3"], 80),
    #    Estacion("st3e", "cw", Maqueta.tramos["E7"], 80),
    #], desc="Lejos")
    #AsociacionEstaciones("detras", "ccw", [
    #    Estacion("st3", "ccw", Maqueta.tramos["E3"].inv, 80),
    #    Estacion("st3e", "ccw", Maqueta.tramos["E7"].inv, 80),
    #], desc="Lejos")

    #Estacion("est","ccw",Maqueta.tramos["M5"].inv,90,desc="Estanteria")

    #Demo(1,"Corta",[("st1e","ccw"),("est","ccw")])
    #Demo(2,"Larga 1",[("st1e","ccw"),("st2","cw"),("detras", "ccw"),("st1","cw"),("est","ccw")])
    #Demo(3,"Larga 2",[("st1e","ccw"),("st2","cw"),("detras", "cw"),("st1","cw"),("est","ccw")])

    # Listado de zonas
    #Zona("Tunel1").incluye(tramos["E2"],desde=0,hasta=85).incluye(tramos["I1"],desde=42,hasta=73)
    #Zona("Tunel2").incluye(tramos["E4"],desde=20,hasta=87).incluye(tramos["I4"],desde=71,hasta=90)
    #pn = Zona("PasoANivel").incluye(tramos["E5"]).incluye(tramos["E4"],desde=50).incluye(tramos["I5"]).incluye(tramos["I4"],desde=75)

    # Zonas para Altavoces
    # -----------------------pared------------------------
    #     front-left         center      surround-left
    #     front-right         lfe       surround-right

    #Zona("Audio-FL").suena_por(UnCanal(0)).incluye(tramos["E2"]).incluye(tramos["I1"],desde=41).incluye(tramos["I4"],hasta=18).incluye(tramos["E7"],hasta=33).incluye(tramos["E3"],hasta=33).incluye(tramos["I2"],hasta=12).incluye(tramos["E8"]).incluye(tramos["M4"])
    #Zona("Audio-FR").suena_por(UnCanal(1)).incluye(tramos["I1"],hasta=24).incluye(tramos["E1"]).incluye(tramos["M5"])
    #Zona("Audio-SL").suena_por(UnCanal(2)).incluye(tramos["E4"]).incluye(tramos["I4"],desde=34,hasta=94).incluye(tramos["I3"],desde=24,hasta=44).incluye(tramos["E7"],desde=66).incluye(tramos["E3"],desde=66) # TODO Revisar I3
    #Zona("Audio-SR").suena_por(UnCanal(3)).incluye(tramos["I3"],hasta=24).incluye(tramos["E5"]).incluye(tramos["I5"]).incluye(tramos["X1"]).incluye(tramos["X2"])
    #Zona("Audio-CE").suena_por(UnCanal(4)).incluye(tramos["E3"],desde=33,hasta=66).incluye(tramos["E7"],desde=33,hasta=66).incluye(tramos["M2"]).incluye(tramos["M3"]).incluye(tramos["I2"],desde=12).incluye(tramos["I4"],desde=18,hasta=34).incluye(tramos["I3"],desde=44,hasta=65)
    #Zona("Audio-LF").suena_por(UnCanal(5)).incluye(tramos["I6"]).incluye(tramos["E6"],desde=15).incluye(tramos["P1"])

    farolas = Luz("farolas")
    casas = Luz("casas")
    via_estanteria_colocada = Luz("via_estanteria_colocada")

    # Listado de chips que alimentan las vias, indicando que tramo alimentan los pines de cada chip.
    # La polaridad del tramo sigue la regla (*).
    # Indicar "None" si un par de pines no alimenta ningun tramo.
    #ChipVias(0x40,[
        # Adafruit 0
        # Placa 2 (Derecha con los puentes H arriba)
    #    tramos["M3"], # Pins 0-1 => VIA2
    #    tramos["I6"], # Pins 2-3 => VIA1
    #    tramos["E6"], # Pins 4-5 => VIA4
    #    tramos["E8"], # Pins 6-7 => VIA3

        # Placa 1 (Izquierda)
    #    tramos["M2"], # Pins 8-9 => VIA2
    #    tramos["I2"], # Pins 10-11 => VIA1
    #    tramos["S1"], # Pins 12-13 => VIA4
    #    tramos["P1"], # Pins 14-15 => VIA3
    #], debug=False)

    #ChipVias(0x41,[
        # Adafruit 1
        # Placa 4
    #    tramos["P4"], # 0-1
    #    tramos["E1"],
    #    tramos["I1"],
    #    tramos["E5"],

        # Placa 3
    #    tramos["I5"],
    #    tramos["E4"],
    #    TramosConAlimentacionCompartida(tramos["X1"], tramos["X2"]),
    #    tramos["I4"],
    #], debug=False)

    # Listado de chips que detectan la presencia de trenes en las vias, indicando que tramo detectan los pines de cada chip.
    # La deteccion no tiene en cuenta la polaridad
    # Indicar "None" si un pin no detecta ningun tramo.
    #ChipDetector(0x25,[
        # A
        # A placa 4
    #    tramos["E1"],       # LSB (Arriba-izquierda en la placa, par naranja)
    #    tramos["P4"],
    #    tramos["E5"], 
    #    tramos["I1"],

        # A placa 3
    #    tramos["E4"],
    #    tramos["I5"],
    #    tramos["I4"],
    #    TramosConDeteccionCompartida(tramos["X1"], tramos["X2"]),
        #tramos["X1"],       # MSB (Abajo-izquierda en la placa, par marron)

        # B
        # A placa 2
    #    tramos["S1"],       # LSB (Abajo-derecha en la placa, par naranja) (Par naranja)
    #    tramos["P1"],
    #    tramos["M2"],
    #    tramos["I2"],       

        # A placa 1
    #    tramos["E6"],       
    #    tramos["E8"],
    #    tramos["M3"],
    #    tramos["I6"],       # MSB (Arriba-derecha en la placa, par marron)
    #])

    #chip1 = ChipDesvios(0x22, {
    #        desvios[1]:  ChipDesvios.AZUL_D1,
    #        desvios[2]:  ChipDesvios.BL_AZUL_D1,
    #        desvios[3]:  ChipDesvios.BL_VERDE_D1,
    #        desvios[4]:  ChipDesvios.VERDE_D1,
    #        desvios[5]:  ChipDesvios.BL_NARANJA_D2,
    #        desvios[6]:  ChipDesvios.NARANJA_D2,
    #        desvios[7]:  ChipDesvios.VERDE_D2,
    #        desvios[8]:  ChipDesvios.AZUL_D2,
    #        desvios[9]:  ChipDesvios.BL_VERDE_D2,
    #        desvios[10]: ChipDesvios.BL_AZUL_D2,
    #        desvios[11]: ChipDesvios.MARRON_D1,
    #        desvios[12]: ChipDesvios.BL_MARRON_D1,
    #        semaforos["S1"].luz[Semaforo.ROJO]: ChipDesvios.NARANJA_D1,
    #        semaforos["S1"].luz[Semaforo.VERDE]: ChipDesvios.BL_NARANJA_D1,
    #})
    #ChipDesvios(0x23, {
    #        farolas    :  ChipDesvios.MARRON_D1,
    #        casas      :  ChipDesvios.BL_MARRON_D1,
    #        desvios[13]:  ChipDesvios.VERDE_D2,
    #        desvios[14]:  ChipDesvios.AZUL_D2,
    #        desvios[15]:  ChipDesvios.BL_VERDE_D2,
    #        desvios[16]:  ChipDesvios.BL_AZUL_D2,
    #        desvios[17]:  ChipDesvios.BL_NARANJA_D2,
    #}, chip_rv=chip1)

    Locomotora(id="vapor", desc="Vapor", coeffs=[0.11798049502618266, 0.00304658416577914, -1.228381595259825e-05], minimo=1400, muestras_inercia=2)
    Locomotora(id="humo", desc="Humo y luz", coeffs=[0.04602868437873745, 0.0044200608178752016, -1.932449180697901e-05], minimo=1400, muestras_inercia=2)
    Locomotora(id="alco1800", desc="Alco 1800 (Diesel)", coeffs=[0.07409022857194827, 0.006888871942219088, -4.105773701684626e-05], minimo=550)
    #[0.06339493671304784, 0.006563136444433814, -3.546151812489586e-05] 700
    #Locomotora(id="talgo", desc="Talgo", coeffs=[0.0705067098, 0.0085391554, -4.4265621878004e-5  ], minimo=1000, muestras_inercia=10)
    Locomotora(id="talgo", desc="Talgo", coeffs=[0.06269762207713507, 0.006847887396690622, -4.1256003045953165e-05], minimo=320, muestras_inercia=10)
    Locomotora(id="comsa", desc="Comsa", coeffs=[0.12077762631211575, 0.003107459392643413, -1.0492061779321495e-05], minimo=1600, muestras_inercia=50)
    Locomotora(id="ef-55", desc="EF-55 (Kato)", coeffs=[0.01958548268810128, 0.00478287434306379, -2.5501116465710806e-05], minimo=780, muestras_inercia=10)
    Locomotora(id="cercanias", desc="Cercanías", coeffs=[0.031261934662692115, 0.006996998827739664, -3.528356235287542e-05], minimo=550, muestras_inercia=20)
    Locomotora(id="c61-006", desc="SNCF C61-006 V", coeffs=[0.061291493686289084, 0.005144162475490486, -3.1719614648088305e-05], minimo=1060, muestras_inercia=2) # 3N
    Locomotora(id="c61-006a",desc="SNCF C61-006 A", coeffs=[0.061291493686289084, 0.005144162475490486, -3.1719614648088305e-05], minimo=1060, muestras_inercia=2) # 3N Helena
    Locomotora(id="v200", desc="V200", coeffs=[-0.017070525390169747, 0.011210285639240654, -6.292727347601206e-05], minimo=1000, muestras_inercia=10) # 3N Helena
    #Locomotora(id="2100", desc="2100", coeffs=[0.07240401047268205, 0.0055405416238591115, -3.1329731145268906e-05], minimo=1862, muestras_inercia=2) # 3N
    Locomotora(id="2100", desc="2100", coeffs=[0.09278432010716989, 0.00548961989033292, -3.003735849905945e-05], minimo=1216, muestras_inercia=2) # 3N

    #cond1 = lambda evento: Maqueta().desvios[11].estado==Desvio.VERDE and Maqueta().desvios[12].estado==Desvio.VERDE
    #cond2 = lambda evento: Maqueta().desvios[11].estado==Desvio.VERDE and Maqueta().desvios[12].estado==Desvio.ROJO
    #cond3 = lambda evento: Maqueta().desvios[7].estado==Desvio.VERDE and Maqueta().desvios[10].estado==Desvio.VERDE
    #cond4 = lambda evento: Maqueta().desvios[7].estado==Desvio.VERDE and Maqueta().desvios[10].estado==Desvio.ROJO

    #CambiarSemaforo(semaforos["I6 invertido"], Semaforo.ROJO).si(cond1).cuando(Desvio.EventoCambiado, desvios[11])
    #CambiarSemaforo(semaforos["I6 invertido"], Semaforo.VERDE).si(cond2).cuando(Desvio.EventoCambiado, desvios[12])
    #CambiarSemaforo(semaforos["I2"], Semaforo.ROJO).si(cond3).cuando(Desvio.EventoCambiado, desvios[7])
    #CambiarSemaforo(semaforos["I2"], Semaforo.VERDE).si(cond4).cuando(Desvio.EventoCambiado, desvios[10])

    #PermitirEstado(desvios[6],Desvio.VERDE).si(via_estanteria_colocada)

    #PulsoDeLuz(flash,1).cuando(Zona.EventoEntraTren, pn)

    #EncenderLuz(farolas).cuando(Desvio.EventoCambiado).tras(3)

    #PulsoDeLuz(mi_luz, 3).cuando(Estacion.EventoTrenParado) # Encender la luz del anden durante 3 segundos cuando un tren se para en la estacion
    #PulsoDeLuz(mi_luz).cuando(Desvio.EventoCambiado)

    SonidoTren("parado").cuando(Tren.EventoVelocidadCero).si_activo_para_tren(por_defecto=False)
    #SonidoTren("silbato").cuando(Zona.EventoEntraTren, pn).si_activo_para_tren()
    #SonidoTren("arranca").cuando(Tren.EventoCambioVelocidadEfectiva).si(lambda evento: evento.anterior == 0).si_activo_para_tren(por_defecto=False)
    #SonidoTren("arranca").cuando(Estacion.EventoTrenArrancando).si_activo_para_tren(por_defecto=False)
    #SonidoTren("parado").cuando(Estacion.EventoTrenParado).si_activo_para_tren(por_defecto=False)
    DescartarConcurrencia(SonidoEstacion("Salida inmediata del tren {tren.clase} con destino {destino}.")).cuando(Estacion.EventoTrenParado).si_activo_para_tren(por_defecto=False)
    #Tramo.debug = True
    #listar_eventos_disponibles()

    #Shell(1, "Prueba", "echo hola > /tmp/hola")
    Shell(1, "Apagar el sistema", "sudo shutdown -h now")

    #Tira(desc="Ambiente", num_leds=180, dobleces=1, invirtiendo=True).weather()
    #Weather.AutoLuces.usa([farolas, casas])

    start()



