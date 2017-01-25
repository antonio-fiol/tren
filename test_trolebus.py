#!/usr/bin/env python
from maqueta import *
from chips_maqueta import *

if __name__ == "__main__":

    # Definimos dos tramos.
    # La "via" no esta cortada, pero simulamos los cortes con dos sensores magneticos de paso.
    Tramo("T1", 0.59)
    Tramo("T2", 0.64)

    # "alias" para escribir menos en las siguientes lineas
    tramos = Maqueta.tramos

    conexion(tramos["T1"], tramos["T2"])
    conexion(tramos["T2"], tramos["T1"])

    # Listado de estaciones
    #Estacion(nombre,sentido,tramo,%),

    # La estacion del trolebus se encuentra a la mitad del tramo T1.
    Estacion("sttr","cw", Maqueta.tramos["T1"],50)

    # En el chip de vias, declaramos que ambos tramos comparten un canal
    ChipVias(0x7f,[
        TramosConAlimentacionCompartida(tramos["T1"], tramos["T2"]),
        None,
        None,
        None,

        None,
        None,
        None,
        None,
    ], debug=False)

    
    # El chip de detectores va a llevar tanto la deteccion de continuidad...
    tdc = TramosConDeteccionCompartida(tramos["T1"], tramos["T2"])
    # como los dos sensores de paso.
    # Uno de los sensores detecta el paso de T1 a T2.
    sensor1 = SensorDePaso(tramos["T1"], tramos["T2"])
    # Y el otro detecta el paso de T2 a T1.
    sensor2 = SensorDePaso(tramos["T2"], tramos["T1"])

    # Los he declarado arriba para poder usarlos despues en las pruebas, abajo,
    # pero se podrian poner igual que el "TramosConAlimentacionCompartida" de arriba.
    ChipDetector(0x7e,[
        tdc,
        None,
        None,
        None,

        None,
        None,
        None,
        None,

        sensor1,
        sensor2,
        None,
        None,

        None,
        None,
        None,
        None,
    ])

    ### CODIGO PARA PRUEBAS ###
    print("===== PREPARACION DE MAQUETA ======")
    Tramo.debug = True
    setup()
    print("===== PONEMOS TENSION ======")
    tramos["T1"].poner_velocidad(0)
    tramos["T2"].poner_velocidad(0)
    print("===== APARECE UN TREN ======")
    tdc.tiene_tren(True)
    print("===== EL TREN PASA POR UN SENSOR ======")
    sensor1.tiene_tren(True)
    print("----- Y LO ABANDONA ------")
    sensor1.tiene_tren(False)
    print("===== PASA POR EL OTRO ======")
    sensor2.tiene_tren(True)
    print("----- Y LO ABANDONA ------")
    sensor2.tiene_tren(False)
    print("===== FIN DE LA PRUEBA ======")
    ###########################

    start()

