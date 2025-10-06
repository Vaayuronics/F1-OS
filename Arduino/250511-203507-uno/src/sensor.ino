#include <ArduinoJson.h>
#include <avr/wdt.h>  // Include watchdog timer library for reset functionality

/*
  For best accuracy, potentiometer should measure > 0 when accelerator in idle state.
  Potentiometer should also measure slightly above maxThrottle when accelerator pushed completly.
*/

//Pin values
const uint8_t analogThrottle = A0;
const uint8_t analogBrake = A1;
const int digitalSpeed = 2;  // Pin where Hall effect sensor is connected (speed sensor)
//Saved values
unsigned long lastCalc = 0;
unsigned long pulseCount = 0;
float speedMph = 0;
//Editable values
const int pulses = 2;
const float wheelCircumference = 12 * PI; // In inches
const int maxThrottle = 135; // Max angle of the potentiometer
const int minThrottle = 0; // Min angle of the potentiometer
int lastButtonState = HIGH; // Last state of the button
int tareThrottle = 0; // Angle to subtract from potentiometer reading to calibrate 0 point
int tareBrake = 0; // Angle to subtract from potentiometer reading to calibrate 0 point

// Reads data from a given analog pin and returns it as an angle (-180, 180).
float readPedal(uint8_t analogPin, int tareAngle)
{
  int raw = analogRead(analogPin);
  //Serial.print("Raw Value: ");
  //Serial.println(raw);
  float angle = ((raw * (360.0 / 1023.0)) - 180) - tareAngle;  // Convert to degrees
  //Serial.print("Angle: ");
  //Serial.println(angle);
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

void sendAnalog(uint8_t pin, float voltage)
{
  // Convert the voltage (0.0 - 5.0) to a value between 0 and 255
  int analogValue = (int)(voltage * 255.0 / 5.0);
  analogWrite(pin, analogValue); // Send the value to the specified pin
}

void setup() 
{
  Serial.begin(115200);
  pinMode(digitalSpeed, INPUT_PULLUP);
}

// Reads pulses from hall effect sensor and converts that to mph
// Only needed if cannot decipher CANBUS from Motor controller
// CANBUS should provide speed data directly
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
  float throttleAngle = readPedal(analogThrottle, tareThrottle);
  float brakeAngle = readPedal(analogBrake, tareBrake);
  float speed = readSpeed();
  //Serial.print("Throttle Angle: ");
  //Serial.println(throttleAngle);

  if (Serial.available() > 0) 
  {
    // Create a JSON document
    JsonDocument message;
    String incoming = Serial.readStringUntil('\n');
    // Deserialize the incoming JSON
    deserializeJson(message, incoming);  // Deserialize the incoming JSON

    const char* command = message["command"];
    if (command != nullptr && strcmp(command, "poll") == 0)
    {
      // Create a JSON document
      JsonDocument data;

      // Add data to the document
      data["Throttle"] = throttleAngle;
      data["Brake"] = brakeAngle; // If brake angle is max then set throttle to 0 in main code? Cant do burn out tho :(
      data["Speed"] = speed;
      data["Status"] = "Polled";

      // Serialize the document to a string and send it over Serial
      serializeJson(data, Serial);
      Serial.print('\n');  // Send newline immediately after JSON
      Serial.flush();      // Force transmission
    }
    else if (command != nullptr && strcmp(command, "tare") == 0)
    {
      // Tare the throttle and brake angles
      throttleAngle = readPedal(analogThrottle, 0);
      brakeAngle = readPedal(analogBrake, 0);
      tareThrottle = throttleAngle;
      tareBrake = brakeAngle;

      // // Create a JSON document for response
      // JsonDocument response;
      // response["Status"] = "Tared";
      // response["TareThrottle"] = tareThrottle;
      // response["TareBrake"] = tareBrake;

      // // Serialize the document to a string and send it over Serial
      // serializeJson(response, Serial);
      // Serial.print('\n');  // Send newline immediately after JSON
      // Serial.flush();      // Force transmission
    }
    else if (command != nullptr && strcmp(command, "reset") == 0)
    {
      // Reset the arduino as if it were powercycled
      wdt_enable(WDTO_15MS);  // Enable watchdog timer with 15ms timeout
      while(1) {}             // Wait for watchdog to reset the system
    }
  }
  //delay(100); // Small delay to avoid overwhelming the serial communication
}


