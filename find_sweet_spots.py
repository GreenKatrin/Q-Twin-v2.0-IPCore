import requests
import numpy as np

API_URL = "http://localhost:8000/environment/simulate"

print("🔍 [SWEET SPOT DETECTOR] Escaneando la topografía de coherencia del transmón...\n")

pressures = np.linspace(0.0, 5.0, 11)
temperatures = np.linspace(10.0, 50.0, 9)

grid = []

for t in temperatures:
    row = []
    for p in pressures:
        payload = {"pressure_mpa": float(p), "temperature_mk": float(t)}
        res = requests.post(API_URL, json=payload).json()
        
        drift = res.get("mechanical_drift_hz", 0.0)
        noise = res.get("thermal_noise_rate", 0.0)
        
        # Métrica de sensibilidad
        sensitivity = abs(drift) + (noise * 1e5)
        row.append((p, t, sensitivity, res["prob_one"]))
    grid.append(row)

# Buscar el mínimo global de sensibilidad (Sweet Spot)
flat_grid = [item for sublist in grid for item in sublist]
flat_grid.sort(key=lambda x: x[2])

best_p, best_t, min_sens, p1 = flat_grid[0]

print("🎯 [RESULTADO DEL ESCANEO]")
print(f"📍 Sweet Spot Mecánico/Térmico Encontrado:")
print(f"   • Presión Óptima (P*):     {best_p:.2f} MPa")
print(f"   • Temperatura Óptima (T*): {best_t:.2f} mK")
print(f"   • Fidelidad Resultante:    P(|1>) = {p1:.4f}")
print(f"   • Sensibilidad Mínima:     {min_sens:.4f}")
