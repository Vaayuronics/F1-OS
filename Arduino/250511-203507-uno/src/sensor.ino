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
unsigned long lastCalc = 0;
unsigned long pulseCount = 0;
float speedMph = 0;
//Editable values
const int pulses = 2;
const float wheelCircumference = 12 * PI; // In inches
const int maxThrottle = 35;
const int minThrottle = 0;
int lastButtonState = HIGH; // Last state of the button

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
  pinMode(digitalSpeed, INPUT_PULLUP);
}

// Reads pulses from hall effect sensor and converts that to mph
float readSpeed()
{
  unsigned long time = millis();

  // Read the sensor
  if (digitalRead(digitalSpeed) == LOW && lastButtonState == HIGH)
  {
    pulseCount++;  // Count pulses from the sensor
    lastButtonState = LOW;  // Update the last state
  }
  else if (digitalRead(digitalSpeed) == HIGH)
  {
    lastButtonState = HIGH;  // Update the last state
  }

  // Calculate speed every second (1000 milliseconds)
  if (time - lastCalc >= 1000) 
  {
    // Calculate RPM - use float division to maintain precision
    float rpm = (pulseCount * 60.0) / pulses; // Convert to RPM

    // Calculate linear speed in inches per hour
    float linearSpeedInchesPerHour = rpm * wheelCircumference * 60.0; // Convert to inches per hour

    // Convert to MPH (inches per hour to miles per hour)
    speedMph = linearSpeedInchesPerHour / 63360.0; // 63360 inches in a mile

    // Reset pulse count for the next calculation
    pulseCount = 0;
    lastCalc = time;
  }
  return speedMph;
}

void loop() 
{
  float throttleAngle = readPedal(analogThrottle);
  float breakAngle = readPedal(analogBreak);
  float speed = readSpeed();

  if (Serial.available() > 0) 
  {
    // Create a JSON document
    JsonDocument message;

    deserializeJson(message, Serial.readStringUntil('\n'));  // Deserialize the incoming JSON

    if(message["command"] == "poll")
    {
      // Create a JSON document
      JsonDocument data;

      // Add data to the document
      data["throttle"] = throttleAngle;
      data["break"] = breakAngle; // If break angle is max then set throttle to 0 in main code? Cant do burn out tho :(
      data["speed"] = speed;

      // Serialize the document to a string and send it over Serial
      serializeJson(data, Serial);
      Serial.println();
    }
  }
}


