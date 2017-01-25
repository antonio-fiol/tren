#include <avr/pgmspace.h>
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <EEPROM.h>

#define PIN0 2
#define STATUS 13

#define NUM_LEDS_ADDR 255
#define REMAINING_STEPS 254
#define ACTIVE_STRIP 253
#define FLASH_TIME 252

// Cada LED adicional implica 6 bytes
// La maxima longitud viene dada tambien por la direccion fija mas baja
#define MAX_STRIP_LENGTH 252

// Cada tira adicional implica 29 bytes de memoria en compilacion
#define MAX_TIRAS 2

//#define PRINTRAM

uint8_t ledNum = 0;
uint8_t stripNum = 0;
uint8_t numLeds[MAX_TIRAS];
uint8_t remainingSteps[MAX_TIRAS];
uint8_t flashTime[MAX_TIRAS];
bool flashStart[MAX_TIRAS];

uint8_t mem[MAX_STRIP_LENGTH*3];

Adafruit_NeoPixel strip[MAX_TIRAS];

unsigned long prevMillis[MAX_TIRAS];

void setup()
{
  Serial.begin(9600);
  Serial.println(F("Setup"));
  // Aunque no haya configuracion, al menos una tira deberia crearse
  numLeds[0] = 16;

  // Leer la configuracion del numero de leds por tira
  readConfig();

  // Inicializar las tiras necesarias
  for(int i = 0; i<MAX_TIRAS; i++) {
     if(numLeds[i]>0) {
        prevMillis[i] = millis();
        remainingSteps[i] = 1;
        strip[i] = Adafruit_NeoPixel(numLeds[i], PIN0 + i, NEO_GRB + NEO_KHZ800);
        strip[i].begin();
        strip[i].show();
        Serial.println(i);
        printRam();
     }
  }
  pinMode(STATUS, OUTPUT);
  digitalWrite(STATUS, !digitalRead(STATUS));

  Wire.begin(4);                // join i2c bus with address #4
  Wire.onReceive(receiveEvent); // register event
  
  for(int i = 0; i < MAX_STRIP_LENGTH * 3; i++)
  {
    mem[i]=(uint8_t)0;
  }
  
  // Ejecutar una secuencia de test de arco iris en toda la longitud de la
  // primera tira
  rainbowCycle(0,20);

  Serial.println(F("Ready"));
  printRam();

}

void loop()
{
  unsigned long now = millis();
  
  for(int i = 0; i < 1; i++)
  {
    // Iniciar flash si esta pendiente para esta tira
    if(flashStart[i])
    {
      Serial.println(flashTime[i], DEC);
      flashStart[i] = false;
      uint32_t blanco = strip[i].Color(255,255,255);
      for(uint8_t led = 0; led < numLeds[i]; led++)
      {
        strip[i].setPixelColor(led, blanco);
      }
      strip[i].show();
      digitalWrite(STATUS, !digitalRead(STATUS));
      prevMillis[i] = now;
    }
    // Terminar flash si hay un flash pendiente para esta tira
    if(flashTime[i])
    {
      // ... si ya ha pasado el tiempo
      if((now - prevMillis[i]) > (unsigned long)(flashTime[i]))
      {
        flashTime[i] = 0;
        // El final del flash consisten en volver a poner
        // el color "final" a la tira, en un solo paso
        remainingSteps[i] = 1;
        doTransition(i);
        digitalWrite(STATUS, !digitalRead(STATUS));
        prevMillis[i] = now;
      }
    }
    // Si no ha terminado la transicion...
    if(remainingSteps[i])
    {
      // ...y ya toca el siguiente paso
      if((now - prevMillis[i]) > 50L)
      {
        doTransition(i);
        digitalWrite(STATUS, !digitalRead(STATUS));
        prevMillis[i] = now;
      }
    }
  }
}

// Avanza un paso en la transicion de colores de la tira hacia el color final
void doTransition(int num)
{
  remainingSteps[num]--;
  uint8_t stripStart = 0;
  if(num == 1) // FIXME: Para soportar mas de 2 tiras hay que cambiar este bloque
  {
    stripStart += numLeds[0];
  }
  for(uint8_t led = 0; led < numLeds[num]; led++)
  {
    //           Actual * pasos_que_quedan + Objetivo
    // Nuevo = ----------------------------------------
    //                  pasos_que_quedan + 1

    // De este modo, en el ultimo paso (quedan 0)
    //        Nuevo = Objetivo

    // Proviene de la formula:
    //           Original * pasos_que_quedan + Objetivo * pasos_dados
    // Nuevo = --------------------------------------------------------
    //                    pasos_que_quedan + pasos_dados

    // asumiendo que no conocemos el color original, pero conocemos el actual,
    // siendo el actual el que resultaria de aplicar la formula para el paso
    // anterior de la iteracion.

    uint32_t cc = strip[num].getPixelColor(led);
    uint32_t cr = (cc >> 16)&0xff;
    uint32_t cg = (cc >>  8)&0xff;
    uint32_t cb = (cc      )&0xff;

    cr*=remainingSteps[num];
    cg*=remainingSteps[num];
    cb*=remainingSteps[num];

    cr += mem[3*(led+stripStart)];
    cg += mem[3*(led+stripStart)+1];
    cb += mem[3*(led+stripStart)+2];

    cr /= (1+remainingSteps[num]);
    cg /= (1+remainingSteps[num]);
    cb /= (1+remainingSteps[num]);
    
    strip[num].setPixelColor(led, strip[num].Color(cr,cg,cb));
  }
  strip[num].show();
}


// function that executes whenever data is received from master
// this function is registered as an event, see setup()
void receiveEvent(int howMany)
{
  digitalWrite(STATUS, !digitalRead(STATUS));
  if(1 <= Wire.available())
  {
    ledNum = Wire.read();
    switch(ledNum)
    {
      case NUM_LEDS_ADDR:
      // Definir el numero de LEDs de la tira en curso, y guardar config
      renewStrip();
      break;
    
      case REMAINING_STEPS:
      // Iniciar la transicion en N pasos hacia los colores finales
      startTransition();
      break;

      case ACTIVE_STRIP:
      // Cambiar la tira activa
      changeActive();
      break;

      case FLASH_TIME:
      // Iniciar flash, con duracion N ms
      startFlash();
      break;
        
      default:
      // Guardar el color final para el LED correspondiente a la direccion usada, y siguientes
      updateLeds();
      break;
    }
  }

  // Leer informacion que pueda quedar, de una peticion mal formada
  // Necesario para evitar que queden datos para la siguiente lectura y el error sea irrecuperable
  while(0 < Wire.available())
  {
    Wire.read();
  }

  printRam();
}

void startTransition()
{
  if(1 <= Wire.available())
  {
    uint8_t newSteps = Wire.read();
    if(remainingSteps[stripNum]!=newSteps)
    {
      remainingSteps[stripNum] = newSteps;
      ledNum = 0;
    }
  }
}

void changeActive()
{
  if(1 <= Wire.available())
  {
    uint8_t newStrip = Wire.read();
    if(stripNum!=newStrip && newStrip < 2)
    {
      stripNum = newStrip;
      ledNum = 0;
    }
  }
}

void renewStrip()
{
  if(1 <= Wire.available())
  {
    uint8_t newLeds = Wire.read();
    Serial.println(F("Longitud actual"));
    Serial.println((int)(numLeds[stripNum]));
    Serial.println(F("Tira actual"));
    Serial.println((int)stripNum);
    Serial.println(F("Lectura"));
    Serial.println((int)newLeds);

    Serial.println(F("===="));
    if(numLeds[stripNum]!=newLeds)
    {
      if((((int)newLeds) + numLeds[0] + numLeds[1] - numLeds[stripNum]) < MAX_STRIP_LENGTH)
      {
        Serial.print(F("L:"));
        Serial.println((int)newLeds);
        // Grabar nueva configuracion en EEPROM
        EEPROM.write(stripNum, newLeds);
        // Reseteo chapucero del Arduino, necesario para regenerar todos los objetos
        // sin quedarnos sin memoria
        void (*softReset) (void) = 0; //declare reset function @ address 0
        softReset();
      } else {
        Serial.print(F("NoCambia"));
      }
      ledNum = 0;
    }
  }
}

void updateLeds()
{
  uint8_t stripStart = 0;
  if(stripNum == 1) // FIXME: Cambiar este bloque para soportar mas de 2 tiras
  {
    stripStart += numLeds[0];
  }
  
  // Lectura de colores de tres en tres (R, G, B).
  while(3 <= Wire.available())
  {
    char r = Wire.read();
    char g = Wire.read();
    char b = Wire.read();
    
    mem[3*(ledNum+stripStart)+0] = r;
    mem[3*(ledNum+stripStart)+1] = g;
    mem[3*(ledNum+stripStart)+2] = b;
    
    ledNum ++;
    if(ledNum > numLeds[stripNum]) ledNum=0;
  }
}

void startFlash() {
  if(1 <= Wire.available())
  {
    flashTime[stripNum] = Wire.read();
    flashStart[stripNum] = true;
    ledNum = 0;
  }
}

void readConfig() {
   int s = 0;
   for(int i = 0; i<MAX_TIRAS; i++) {
      uint8_t n = EEPROM.read(i);
      s+=n;
      if(s<MAX_STRIP_LENGTH) {
         if(n>0) {
            numLeds[i]=n;
            Serial.print(F("Tira")); Serial.println(i);
            Serial.print(F("LEDS")); Serial.println((int)(numLeds[i]));            
         } else {
            // La EEPROM no tiene una longitud para esta tira. Si la tenemos, por defecto, la sumamos.
            s+=numLeds[i];
         }
      }
   }
}

// Secuencia de test
void rainbowCycle(uint8_t num, uint8_t wait) {
  uint16_t i, j;

  for(j=0; j<256*3; j++) { // 3 cycles of all colors on wheel
    for(i=0; i< strip[num].numPixels(); i++) {
      strip[num].setPixelColor(i, Wheel(num, ((i * 256 / strip[num].numPixels()) + j) & 255));
    }
    strip[num].show();
    delay(wait);
    if(j%100 == 0) digitalWrite(STATUS, !digitalRead(STATUS));
  }
}
// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(uint8_t num, byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return strip[num].Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return strip[num].Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip[num].Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

#ifdef PRINTRAM
// Calcula la memoria libre de forma estimada y basica, viendo el espacio
// entre el heap (memoria para malloc) y el stack (memoria para las variables locales)
int freeRam () {
  extern int __heap_start, *__brkval; 
  int v; 
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval); 
}
#endif

void printRam () {
#ifdef PRINTRAM
  Serial.print(F("R:"));
  Serial.println(freeRam());
#endif
}
