"""
Simulasi output kode main.cpp (ESP32 JXK Current Reader)
Meniru logika pembacaan ADC, filter, kalibrasi, dan format JSON serial.
"""

import random
import json

# --- Konfigurasi (sama dengan main.cpp) ---
ADC_PIN = 34
V_REF = 3.3
ADC_MAX = 4095
R_TOP = 15.0
R_BOTTOM = 10.0
dividerRatio = R_BOTTOM / (R_TOP + R_BOTTOM)  # 0.4

sensorOutputMaxV = 5.0
sensorFullScaleA = 150.0
sensorSensitivity_VperA = sensorOutputMaxV / sensorFullScaleA  # 5/150 = 0.0333 V/A

SAMPLES = 100
FILTER_ALPHA = 0.2
CURRENT_DEADBAND_A = 0.40

# State variabel (mirip variabel global di C++)
zeroOffsetSensorV = 0.0
zeroOffsetAdcRaw = 0.0
zeroOffsetAdcVoltage = 0.0
filteredSensorV = 0.0
zeroOffsetCurrentA = 0.0


def read_sensor_simulated():
    """Simulasi analogRead dengan noise acak + offset tegangan sensor"""
    # Simulasikan nilai ADC mentah (0-4095) dengan noise kecil
    raw_values = []
    for _ in range(SAMPLES):
        # Nilai baseline ~2048 (1.65V) + noise acak +/- 20
        raw = 2048 + random.randint(-20, 20)
        raw_values.append(raw)
        pass  # simulate delayMicroseconds(100)

    raw_min = min(raw_values)
    raw_max = max(raw_values)
    avg_raw = sum(raw_values) / len(raw_values)

    v_adc = (avg_raw / ADC_MAX) * V_REF
    sensor_voltage = v_adc / dividerRatio  # pembalik divider

    return {
        "rawAdc": avg_raw,
        "rawAdcMin": raw_min,
        "rawAdcMax": raw_max,
        "adcVoltage": v_adc,
        "sensorVoltage": sensor_voltage,
    }


def calibrate_zero():
    global zeroOffsetSensorV, zeroOffsetAdcRaw, zeroOffsetAdcVoltage, \
           zeroOffsetCurrentA, filteredSensorV

    cal_loops = 20
    sum_v = 0.0
    sum_raw = 0.0
    sum_adc_v = 0.0

    for _ in range(cal_loops):
        reading = read_sensor_simulated()
        sum_v += reading["sensorVoltage"]
        sum_raw += reading["rawAdc"]
        sum_adc_v += reading["adcVoltage"]
        pass  # simulate delay(20)

    zeroOffsetSensorV = sum_v / cal_loops
    zeroOffsetAdcRaw = sum_raw / cal_loops
    zeroOffsetAdcVoltage = sum_adc_v / cal_loops

    if zeroOffsetSensorV < 0.0:
        zeroOffsetSensorV = 0.0

    zeroOffsetCurrentA = zeroOffsetSensorV / sensorSensitivity_VperA
    filteredSensorV = zeroOffsetSensorV

    print("=== Kalibrasi Titik Nol Selesai ===")
    print(f"Zero Offset Sensor Voltage: {zeroOffsetSensorV:.4f} V")
    print(f"Zero Offset Current:        {zeroOffsetCurrentA:.4f} A")
    print(f"Zero Offset ADC Raw:        {zeroOffsetAdcRaw:.1f}")
    print(f"Zero Offset ADC Voltage:    {zeroOffsetAdcVoltage:.4f} V")
    print("--------------------------------------")


def loop_iteration():
    global filteredSensorV

    reading = read_sensor_simulated()
    raw_v_sensor = reading["sensorVoltage"]

    # Low-pass filter
    filteredSensorV = (FILTER_ALPHA * raw_v_sensor) + \
                      ((1.0 - FILTER_ALPHA) * filteredSensorV)

    delta_sensor_v = raw_v_sensor - zeroOffsetSensorV
    delta_adc_raw = reading["rawAdc"] - zeroOffsetAdcRaw
    raw_current_a = (raw_v_sensor - zeroOffsetSensorV) / sensorSensitivity_VperA
    filtered_current_a = (filteredSensorV - zeroOffsetSensorV) / sensorSensitivity_VperA
    current_before_deadband_a = filtered_current_a

    negative_current = current_before_deadband_a < 0.0
    threshold_active = (current_before_deadband_a < CURRENT_DEADBAND_A) or negative_current
    current_a = 0.0 if threshold_active else current_before_deadband_a

    signal_changed = (delta_adc_raw > 5.0) or (delta_adc_raw < -5.0)
    adc_saturated = (reading["rawAdc"] >= ADC_MAX) or (reading["adcVoltage"] >= V_REF)

    output = {
        "adc_raw": round(reading["rawAdc"], 1),
        "adc_min": reading["rawAdcMin"],
        "adc_max": reading["rawAdcMax"],
        "adc_span": reading["rawAdcMax"] - reading["rawAdcMin"],
        "adc_zero_raw": round(zeroOffsetAdcRaw, 1),
        "v_adc": round(reading["adcVoltage"], 4),
        "v_adc_zero": round(zeroOffsetAdcVoltage, 4),
        "v_sensor_raw": round(raw_v_sensor, 4),
        "v_sensor_filtered": round(filteredSensorV, 4),
        "v_sensor": round(filteredSensorV, 4),
        "v_zero": round(zeroOffsetSensorV, 4),
        "delta_v": round(delta_sensor_v, 4),
        "delta_raw": round(delta_adc_raw, 1),
        "zero_offset_a": round(zeroOffsetCurrentA, 4),
        "current_raw_a": round(raw_current_a, 3),
        "current_filtered_a": round(filtered_current_a, 3),
        "current_before_deadband_a": round(current_before_deadband_a, 3),
        "current_a": round(current_a, 3),
        "threshold_a": round(CURRENT_DEADBAND_A, 3),
        "threshold_active": threshold_active,
        "negative_current": negative_current,
        "signal_changed": signal_changed,
        "adc_saturated": adc_saturated,
    }

    return output


# --- Jalankan simulasi ---
if __name__ == "__main__":
    print("ESP32 JXK-7202308 Current Reader (Simulasi)\n")
    calibrate_zero()
    print("\nMemulai pembacaan data (simulasi 5 baris JSON):\n")

    for i in range(5):
        data = loop_iteration()
        print(json.dumps(data))
        pass  # simulate delay(1000)