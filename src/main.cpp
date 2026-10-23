#include <Arduino.h>

const int ADC_PIN = 34;               // GPIO34 (ADC1_CH6)
const float V_REF = 3.3f;             // ESP32 ADC Reference Voltage
const int ADC_MAX = 4095;             // 12-bit ADC Resolution

const float R_TOP = 10.0f;            // Resistor Pembagi Tegangan Atas (kOhm)
const float R_BOTTOM = 10.0f;         // Resistor Pembagi Tegangan Bawah (kOhm)
const float dividerRatio = R_BOTTOM / (R_TOP + R_BOTTOM); // = 0.5

const float sensorOutputMaxV = 5.0f;  // Output Maksimal Sensor (0-5V)
const float sensorFullScaleA = 150.0f;// Range Sensor JXK (misal: 0-150A)
const float sensorSensitivity_VperA = sensorOutputMaxV / sensorFullScaleA;

const int SAMPLES = 100;              // Ditingkatkan efisiensinya
const float FILTER_ALPHA = 0.2f;      // Low-pass filter coefficient

float zeroOffsetSensorV = 0.0f;
float filteredSensorV = 0.0f;
float zeroOffsetCurrentA = 0.0f;

// Fungsi membaca ADC secara cepat tanpa memblokir CPU
float getDirectSensorVoltage() {
  unsigned long sum = 0;
  for (int i = 0; i < SAMPLES; ++i) {
    sum += analogRead(ADC_PIN);
    delayMicroseconds(100); // 100us x 100 = hanya 10ms total!
  }
  float avgRaw = (float)sum / (float)SAMPLES;
  float vAdc = (avgRaw / (float)ADC_MAX) * V_REF;
  return vAdc / dividerRatio; // Konversi balik ke tegangan asli sensor (0-5V)
}

void calibrateZero() {
  float sumV = 0.0f;
  const int CAL_LOOPS = 20;
  
  for (int i = 0; i < CAL_LOOPS; ++i) {
    sumV += getDirectSensorVoltage();
    delay(20);
  }

  zeroOffsetSensorV = sumV / (float)CAL_LOOPS;
  
  // Jika sensor JXK murni 0V saat 0A, kita batasi offset yang tidak wajar
  if (zeroOffsetSensorV < 0.0f) zeroOffsetSensorV = 0.0f;
  
  zeroOffsetCurrentA = zeroOffsetSensorV / sensorSensitivity_VperA;
  filteredSensorV = zeroOffsetSensorV;
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(ADC_PIN, INPUT);
  analogSetPinAttenuation(ADC_PIN, ADC_11db);

  Serial.println("\nESP32 JXK-7202308 Current Reader");
  Serial.println("Memulai Kalibrasi Titik Nol (Pastikan Tidak Ada Arus)...");

  calibrateZero();

  Serial.print("Zero Offset Sensor Voltage: ");
  Serial.print(zeroOffsetSensorV, 4);
  Serial.println(" V");
  Serial.print("Zero Offset Current: ");
  Serial.print(zeroOffsetCurrentA, 4);
  Serial.println(" A");
  Serial.println("--------------------------------------");
}

void loop() {
  // Read & Filter Voltage
  float rawVSensor = getDirectSensorVoltage();
  filteredSensorV = (FILTER_ALPHA * rawVSensor) + ((1.0f - FILTER_ALPHA) * filteredSensorV);

  // Hitung Arus Bersih (dikurangi Offset)
  float currentA = (filteredSensorV - zeroOffsetSensorV) / sensorSensitivity_VperA;

  // Threshold / Deadband untuk menghilangkan Noise saat 0 Ampere
  if (currentA < 0.05f) { // Jika pembacaan < 0.05A (50mA), anggap murni 0A
    currentA = 0.0f;
  }

  // Kirim JSON ke Raspberry Pi
  Serial.print("{\"v_sensor\":");
  Serial.print(filteredSensorV, 4);
  Serial.print(",\"v_zero\":");
  Serial.print(zeroOffsetSensorV, 4);
  Serial.print(",\"zero_offset_a\":");
  Serial.print(zeroOffsetCurrentA, 4);
  Serial.print(",\"current_a\":");
  Serial.print(currentA, 3);
  Serial.println("}");
  
  Serial.flush(); // Memastikan transmisi serial selesai penuh
  delay(1000);   // Jeda 1 detik antar pengiriman
}