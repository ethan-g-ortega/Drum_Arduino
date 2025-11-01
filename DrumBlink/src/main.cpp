#include <Arduino.h>
// ===== Wiring =====
// D9 -> 220Ω -> Red   |  D10 -> 220Ω -> Green  |  D11 -> 220Ω -> Blue
// Common pin: CC -> GND  |  CA -> +5V

const int PIN_R = 9;
const int PIN_G = 10;
const int PIN_B = 11;

// ---- Set your LED type (exactly one true) ----
const bool COMMON_CATHODE = true;
const bool COMMON_ANODE = !COMMON_CATHODE;

// Incoming packet from Python: [0xAA, note, velocity]
const byte START = 0xAA;

// Write color with auto inversion for common-anode
static inline void setColor(uint8_t r, uint8_t g, uint8_t b)
{
  if (COMMON_ANODE)
  {
    r = 255 - r;
    g = 255 - g;
    b = 255 - b;
  }
  analogWrite(PIN_R, r);
  analogWrite(PIN_G, g);
  analogWrite(PIN_B, b);
}

static inline uint8_t v2pwm(uint8_t v)
{
  // simple linear; tweak as you like
  unsigned int x = (unsigned int)v * 2;
  return (x > 255) ? 255 : x;
}

// Flash color briefly
unsigned long flashUntil = 0;
void flashColor(uint8_t r, uint8_t g, uint8_t b, uint16_t ms)
{
  setColor(r, g, b);
  flashUntil = millis() + ms;
}

void setup()
{
  pinMode(PIN_R, OUTPUT);
  pinMode(PIN_G, OUTPUT);
  pinMode(PIN_B, OUTPUT);
  setColor(0, 0, 0);

  Serial.begin(115200);
}

void triggerNote(uint8_t note, uint8_t vel)
{
  if (vel == 0)
    return;
  uint8_t p = v2pwm(vel);

  switch (note)
  {
  case 36: /* Kick  */
    flashColor(p, 0, 0, 90);
    break; // Red
  case 38: /* Snare */
    flashColor(0, 0, p, 90);
    break; // Blue
  case 42: /* HH cl */
    flashColor(0, p, 0, 80);
    break; // Green
  case 46: /* HH op */
    flashColor(0, p / 2, p, 100);
    break; // Cyan
  case 49: /* Crash */
    flashColor(p, p, 0, 120);
    break; // Yellow
  case 51: /* Ride  */
    flashColor(p, 0, p, 120);
    break; // Magenta
  case 48: /* Tom1  */
    flashColor(p, p / 3, 0, 100);
    break; // Orange
  case 47: /* Tom2  */
    flashColor(p / 2, 0, p / 2, 100);
    break; // Purple
  case 45: /* Tom3  */
    flashColor(0, p / 2, p / 4, 100);
    break; // Teal
  default:
    flashColor(p / 4, p / 4, p / 4, 70);
    break; // White-ish
  }
}

void loop()
{
  // Parse [START, note, velocity]
  static enum { WAIT,
                NOTE,
                VEL } st = WAIT;
  static uint8_t note = 0, vel = 0;

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
      note = b & 0x7F;
      st = VEL;
      break;
    case VEL:
      vel = b & 0x7F;
      st = WAIT;
      triggerNote(note, vel);
      break;
    }
  }

  // Auto-off after flash time
  if (flashUntil && millis() > flashUntil)
  {
    setColor(0, 0, 0);
    flashUntil = 0;
  }
}
