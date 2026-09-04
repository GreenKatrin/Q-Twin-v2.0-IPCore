import requests
import time
from fpga_bridge import update_fpga_phase

API_URL = "http://localhost:8000/environment/simulate"

print("🚨 [PRUEBA DE FALLO] Iniciando simulación de choque térmico stocástico...")

# 1. Estado nominal
payload_normal = {"pressure_mpa": 0.0, "temperature_mk": 10.0}
res_normal = requests.post(API_URL, json=payload_normal).json()
print(f"🟢 Estado Nominal -> Temp: {payload_normal['temperature_mk']} mK | Drift: {res_normal['mechanical_drift_hz']} Hz | P(|1>): {res_normal['prob_one']}")

time.sleep(1)

# 2. Inyección de pico térmico
payload_fault = {"pressure_mpa": 3.5, "temperature_mk": 48.0}
print(f"\n🔥 [EVENTO DETECTADO] Inyectando alteración extrema: Temp: {payload_fault['temperature_mk']} mK | Presión: {payload_fault['pressure_mpa']} MPa")
res_fault = requests.post(API_URL, json=payload_fault).json()
print(f"🔴 Estado Perturbado -> Drift: {res_fault['mechanical_drift_hz']} Hz | Tasa Ruido: {res_fault['thermal_noise_rate']}")

# 3. Recálculo y mitigación del Agente hacia la FPGA
drift_detected = res_fault['mechanical_drift_hz']
# Algoritmo de compensación: Convertir la deriva de frecuencia a un registro de fase de 16 bits
compensation_reg = int((drift_detected / 3000.0) * 0xFFFF) & 0xFFFF

print(f"\n⚡ [REACCIÓN AUTÓNOMA] Agente calcula registro de mitigación: 0x{compensation_reg:04X}")
update_fpga_phase(compensation_reg)

print("\n✅ [RESULTADO] Mitigación inyectada en el pipeline Verilator exitosamente.")
