#include <Arduino.h>
// ===== Wiring =====
// D9 -> 220Ω -> Red   |  D10 -> 220Ω -> Green  |  D11 -> 220Ω -> Blue
// Common pin: CC -> GND  |  CA -> +5V

const uint8_t PIN_B1 = 2;
const uint8_t PIN_R1 = 3;
const uint8_t PIN_G1 = 4;
const uint8_t PIN_Y = 5;
const uint8_t PIN_W = 6;
const uint8_t PIN_B2 = 7;
const uint8_t PIN_R2 = 8;
const uint8_t PIN_G2 = 9;

const uint8_t LED_PINS[] = {PIN_B1, PIN_R1, PIN_G1, PIN_Y, PIN_W, PIN_B2, PIN_R2, PIN_G2};
const uint8_t NUM_LEDS = sizeof(LED_PINS) / sizeof(LED_PINS[0]);

const byte START = 0xAA;
unsigned long offAt[8] = {0};

const bool ACTIVE_LOW = true;

// helper to write logical on/off regardless of wiring
inline void ledWrite(uint8_t pin, bool on)
{
  // if ACTIVE_LOW, ON = LOW; if active-high, ON = HIGH
  digitalWrite(pin, (on ^ ACTIVE_LOW) ? HIGH : LOW);
}

enum ParseState
{
  WAIT,
  NOTE,
  VEL
};
ParseState st = WAIT;
uint8_t curNote = 0, curVel = 0;

int8_t noteToPin(uint8_t note)
{
  switch (note)
  {
  case 36:
    return PIN_W; // Kick
  case 38:
  case 40:
    return PIN_R1; // Snare
  case 42:
  case 44:
  case 46:
    return PIN_B1; // Hi-hat
  case 43:
  case 58:
    return PIN_G2; // floor tom
  case 49:
    return PIN_Y; // Crash
  case 51:
    return PIN_R2; // Ride
  case 48:
  case 50:
    return PIN_G1; // Tom 1
  case 45:
  case 47:
    return PIN_B2; // Tom 2
  default:
    return -1;
  }
}

void flashPin(uint8_t pin, uint16_t durationMs)
{
  ledWrite(pin, true);
  for (uint8_t i = 0; i < NUM_LEDS; ++i)
  {
    if (LED_PINS[i] == pin)
    {
      offAt[i] = millis() + durationMs;
      break;
    }
  }
}

void setup()
{
  for (uint8_t i = 0; i < NUM_LEDS; ++i)
  {
    pinMode(LED_PINS[i], OUTPUT);
    ledWrite(LED_PINS[i], false); // ensure all off at boot
  }
  Serial.begin(115200);
}

static inline uint16_t velToMs(uint8_t vel)
{
  if (vel == 0)
    return 0;
  uint16_t ms = 50 + (uint16_t)vel; // simple, feels snappy
  if (ms > 160)
    ms = 160;
  return ms;
}

void triggerNote(uint8_t note, uint8_t vel)
{
  if (vel == 0)
  {
    return;
  }
  int8_t pin = noteToPin(note);
  if (pin < 0)
  {
    return; // not mapped
  }
  flashPin((uint8_t)pin, velToMs(vel));
}

void loop()
{
  // ---- Parse [START, note, velocity] coming from Python ----
  while (Serial.available())
  {
    uint8_t b = (uint8_t)Serial.read();
    switch (st)
    {
    case WAIT:
      if (b == START)
        st = NOTE;
      break;
    case NOTE:
      curNote = b & 0x7F;
      st = VEL;
      break;
    case VEL:
      curVel = b & 0x7F;
      st = WAIT;
      triggerNote(curNote, curVel);
      break;
    }
  }

  // ---- Turn off LEDs  ----
  unsigned long now = millis();
  for (uint8_t i = 0; i < NUM_LEDS; ++i)
  {
    if (offAt[i] && now >= offAt[i])
    {
      ledWrite(LED_PINS[i], false);
      offAt[i] = 0;
    }
  }
}