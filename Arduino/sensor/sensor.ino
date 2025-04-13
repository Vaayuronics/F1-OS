#include <ArduinoJson.h>

/*
  For best accuracy, potentiometer should measure > 0 when accelerator in idle state.
  Potentiometer should also measure slightly above maxThrottle when accelerator pushed completly.
*/

//Pin values
const uint8_t analogThrottle = A0;
const uint8_t analogBreak = A1;
const int digitalSpeed = 2;  // Pin where Hall effect sensor is connected
//Saved values
unsigned long lastPulseTime = 0;
unsigned long pulseCount = 0;
float speedMph = 0;
unsigned long id = 0;
//Editable values
const int pulses = 2;
const float axleCircumference = 1.0; // In inches
const int maxThrottle = 35;
const int minThrottle = 0;

// Reads data from a given analog pin and returns it as an angle (-180, 180).
float readPedal(uint8_t analogPin)
{
  int raw = analogRead(analogPin);
  float angle = (raw * (360.0 / 1023.0)) - 180;  // Convert to degrees

  if(angle < minThrottle)
  {
    angle = minThrottle; // To cap min value of potentiometer
  }
  else if(angle > maxThrottle)
  {
    angle = maxThrottle; // To cap max value of potentiometer
  }

  return angle;
}

void setup() 
{
  Serial.begin(115200);
  pinMode(digitalSpeed, INPUT);
}

// Reads pulses from hall effect sensor and converts that to mph
float readSpeed()
{
  unsigned long time = millis();

  // Read the sensor
  if (digitalRead(digitalSpeed) == HIGH) 
  {
    pulseCount++;  // Count pulses from the sensor
    lastPulseTime = time;
  }

  // Calculate speed every second (1000 milliseconds)
  if (time - lastPulseTime >= 1000) 
  {
    // Calculate RPM, divide by 2 since we have 2 pulses per revolution
    // 2 pulses as there are 2 magnets, one on each side to balance axel
    unsigned long rpm = pulseCount / pulses;  // pulses per revolution

    // Calculate linear speed in inches per minute
    float linearSpeedInchesPerMinute = rpm * axleCircumference;

    // Convert to MPH (inches per minute to miles per hour)
    speedMph = linearSpeedInchesPerMinute / 1056;

    // Reset pulse count for the next calculation
    pulseCount = 0;
    lastPulseTime = time;
  }

  return speedMph;
}

void loop() 
{
  float throttleAngle = readPedal(analogThrottle);
  float breakAngle = readPedal(analogBreak);

  // Create a JSON document
  JsonDocument data;

  // Add data to the document
  data["throttle"] = throttleAngle;
  data["break"] = breakAngle; // If break angle is max then set throttle to 0 in main code? Cant do burn out tho :(
  data["speed"] = readSpeed();
  data["id"] = id;

  // Serialize the document to a string and send it over Serial
  serializeJson(data, Serial);
  Serial.println();
  id++;
}


