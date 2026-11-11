#include <Arduino.h>

const int ADC_PIN = 34;               // GPIO34 (ADC1_CH6)
const float V_REF = 3.3f;             // ESP32 ADC Reference Voltage
const int ADC_MAX = 4095;             // 12-bit ADC Resolution

// --- Pengaturan Pembagi Tegangan ---
const float R_TOP = 15.0f;            // Resistor atas 15 kOhm
const float R_BOTTOM = 10.0f;         // Resistor bawah 10 kOhm
const float dividerRatio = R_BOTTOM / (R_TOP + R_BOTTOM); // = 0.4

// --- Pengaturan Sensor JXK ---
const float sensorOutputMaxV = 5.0f;  // Output Maksimal Sensor (0-5V)
const float sensorFullScaleA = 150.0f;// Range Sensor JXK (0-150A)
const float sensorSensitivity_VperA = sensorOutputMaxV / sensorFullScaleA;

// --- Pengaturan Pembacaan & Filter ---
const int SAMPLES = 100;              // Jumlah sampel pembacaan
const float FILTER_ALPHA = 0.2f;      // Low-pass filter coefficient
const float CURRENT_DEADBAND_A = 2.0f;// Deadband threshold 2A

// Variabel kalibrasi & filter
float zeroOffsetSensorV = 0.0f;
float zeroOffsetAdcRaw = 0.0f;
float zeroOffsetAdcVoltage = 0.0f;
float filteredSensorV = 0.0f;
float zeroOffsetCurrentA = 0.0f;

struct SensorReading {
  float rawAdc;
  int rawAdcMin;
  int rawAdcMax;
  float adcVoltage;
  float sensorVoltage;
};

SensorReading readSensor() {
  unsigned long sum = 0;
  int rawMin = ADC_MAX;
  int rawMax = 0;
  for (int i = 0; i < SAMPLES; ++i) {
    int raw = analogRead(ADC_PIN);
    sum += raw;
    if (raw < rawMin) rawMin = raw;
    if (raw > rawMax) rawMax = raw;
    delayMicroseconds(100);
  }
  float avgRaw = (float)sum / (float)SAMPLES;
  float vAdc = (avgRaw / (float)ADC_MAX) * V_REF;
  return {
    avgRaw,
    rawMin,
    rawMax,
    vAdc,
    vAdc / dividerRatio
  };
}

void calibrateZero() {
  float sumV = 0.0f;
  float sumRaw = 0.0f;
  float sumAdcV = 0.0f;
  const int CAL_LOOPS = 20;

  for (int i = 0; i < CAL_LOOPS; ++i) {
    SensorReading reading = readSensor();
    sumV += reading.sensorVoltage;
    sumRaw += reading.rawAdc;
    sumAdcV += reading.adcVoltage;
    delay(20);
  }

  zeroOffsetSensorV = sumV / (float)CAL_LOOPS;
  zeroOffsetAdcRaw = sumRaw / (float)CAL_LOOPS;
  zeroOffsetAdcVoltage = sumAdcV / (float)CAL_LOOPS;

  if (zeroOffsetSensorV < 0.0f) zeroOffsetSensorV = 0.0f;

  zeroOffsetCurrentA = zeroOffsetSensorV / sensorSensitivity_VperA;
  filteredSensorV = zeroOffsetSensorV;
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(ADC_PIN, INPUT);
  analogSetPinAttenuation(ADC_PIN, ADC_11db);

  Serial.println("\nESP32 JXK-7202308 Current Reader (15k/10k Divider)");
  Serial.println("Memulai Kalibrasi Titik Nol (Pastikan Tidak Ada Arus)...");

  calibrateZero();

  Serial.print("Zero Offset Sensor Voltage: ");
  Serial.print(zeroOffsetSensorV, 4);
  Serial.println(" V");
  Serial.print("Zero Offset Current: ");
  Serial.print(zeroOffsetCurrentA, 4);
  Serial.println(" A");
  Serial.print("Zero Offset ADC Raw: ");
  Serial.println(zeroOffsetAdcRaw, 1);
  Serial.println("--------------------------------------");
}

void loop() {
  SensorReading reading = readSensor();
  float rawVSensor = reading.sensorVoltage;

  // Low-pass filter
  filteredSensorV = (FILTER_ALPHA * rawVSensor) + ((1.0f - FILTER_ALPHA) * filteredSensorV);

  float deltaSensorV = rawVSensor - zeroOffsetSensorV;
  float deltaAdcRaw = reading.rawAdc - zeroOffsetAdcRaw;
  float rawCurrentA = (rawVSensor - zeroOffsetSensorV) / sensorSensitivity_VperA;
  float filteredCurrentA = (filteredSensorV - zeroOffsetSensorV) / sensorSensitivity_VperA;
  float currentBeforeDeadbandA = filteredCurrentA;

  bool negativeCurrent = currentBeforeDeadbandA < 0.0f;
  bool thresholdActive = (currentBeforeDeadbandA < CURRENT_DEADBAND_A) || negativeCurrent;
  float currentA = currentBeforeDeadbandA;

  if (thresholdActive) {
    currentA = 0.0f;
  }

  bool signalChanged = (deltaAdcRaw > 5.0f || deltaAdcRaw < -5.0f);
  bool adcSaturated = (reading.rawAdc >= ADC_MAX || reading.adcVoltage >= V_REF);

  // Output JSON — FIELD PENTING + ALASAN current_a = 0
  Serial.print("{");
  Serial.print("\"adc_raw\":"); Serial.print(reading.rawAdc, 1);
  Serial.print(",\"v_sensor\":"); Serial.print(filteredSensorV, 4);
  Serial.print(",\"v_zero\":"); Serial.print(zeroOffsetSensorV, 4);
  Serial.print(",\"delta_v\":"); Serial.print(deltaSensorV, 4);
  Serial.print(",\"zero_offset_a\":"); Serial.print(zeroOffsetCurrentA, 4);
  Serial.print(",\"current_a\":"); Serial.print(currentA, 3);
  Serial.print(",\"threshold_active\":"); Serial.print(thresholdActive ? "true" : "false");
  Serial.print(",\"signal_changed\":"); Serial.print(signalChanged ? "true" : "false");
  Serial.print(",\"adc_saturated\":"); Serial.print(adcSaturated ? "true" : "false");
  Serial.println("}");

  Serial.flush();
  delay(1000);
}


