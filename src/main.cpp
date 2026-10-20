#include <Arduino.h>

// JXK-7202308 example config
// Sensor output: 0–5V DC proportional to current
// Recommended wiring for ESP32 ADC safety:
// SENSOR OUT -> 10k -> ADC GPIO34
// ADC GPIO34 -> 10k -> GND
// Divider ratio = 10k / (10k + 10k) = 0.5
// So 5V sensor output becomes 2.5V at ADC, safely below 3.3V

const int ADC_PIN = 34;              // ADC1 channel (GPIO34)
const float V_REF = 3.3f;            // ESP32 ADC reference voltage
const int ADC_MAX = 4095;            // 12-bit ADC resolution

const float R_TOP = 10.0f;           // Upper resistor to sensor output
const float R_BOTTOM = 10.0f;         // Lower resistor to GND
const float dividerRatio = R_BOTTOM / (R_TOP + R_BOTTOM); // = 0.5

const float sensorOutputMaxV = 5.0f; // Sensor full-scale output voltage
const float sensorFullScaleA = 150.0f; // <-- update if your exact JXK-7202308 range differs
const float sensorSensitivity_VperA = sensorOutputMaxV / sensorFullScaleA;

const int SAMPLES = 200;
const float FILTER_ALPHA = 0.15f;  // smoothing factor for low-pass filter

float zeroOffsetSensorV = 0.0f;
float filteredSensorV = 0.0f;
float zeroOffsetCurrentA = 0.0f;

void calibrateZero() {
  unsigned long sum = 0;
  const int CAL_SAMPLES = 200;

  for (int i = 0; i < CAL_SAMPLES; ++i) {
    sum += analogRead(ADC_PIN);
    delay(5);
  }

  float avgRaw = (float)sum / (float)CAL_SAMPLES;
  float vAdc = (avgRaw / ADC_MAX) * V_REF;
  zeroOffsetSensorV = vAdc / dividerRatio;
  zeroOffsetCurrentA = zeroOffsetSensorV / sensorSensitivity_VperA;
  filteredSensorV = zeroOffsetSensorV;
}

float readFilteredSensorVoltage() {
  unsigned long sum = 0;

  for (int i = 0; i < SAMPLES; ++i) {
    sum += analogRead(ADC_PIN);
    delay(5);
  }

  float avgRaw = (float)sum / (float)SAMPLES;
  float vAdc = (avgRaw / ADC_MAX) * V_REF;
  float vSensor = vAdc / dividerRatio;

  // First-order low-pass filter to reduce ADC noise
  filteredSensorV = (FILTER_ALPHA * vSensor) + ((1.0f - FILTER_ALPHA) * filteredSensorV);
  return filteredSensorV;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(ADC_PIN, INPUT);
  analogSetPinAttenuation(ADC_PIN, ADC_11db);

  Serial.println("ESP32 JXK-7202308 Current Reader");
  Serial.println("Make sure no current flows during calibration.");

  calibrateZero();

  Serial.print("Zero offset sensor voltage: ");
  Serial.print(zeroOffsetSensorV, 4);
  Serial.println(" V");
  Serial.print("Zero offset current: ");
  Serial.print(zeroOffsetCurrentA, 4);
  Serial.println(" A");
  Serial.println("--------------------------------------");
}

void loop() {
  float vSensor = readFilteredSensorVoltage();
  float currentA = (vSensor - zeroOffsetSensorV) / sensorSensitivity_VperA;

  if (currentA < 0.0f) {
    currentA = 0.0f;
  }

  // Send JSON line to Raspberry Pi for database logging
  Serial.print("{\"v_sensor\":");
  Serial.print(vSensor, 4);
  Serial.print(",\"v_zero\":");
  Serial.print(zeroOffsetSensorV, 4);
  Serial.print(",\"zero_offset_a\":");
  Serial.print(zeroOffsetCurrentA, 4);
  Serial.print(",\"current_a\":");
  Serial.print(currentA, 3);
  Serial.println("}");

  delay(1000);
}
