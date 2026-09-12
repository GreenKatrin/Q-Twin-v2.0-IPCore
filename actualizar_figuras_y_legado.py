import os
import numpy as np
import matplotlib.pyplot as plt

# 1. ETIQUETADO DE SCRIPTS LEGADOS
legacy_files = ["bko_two_field_integrator.py", "simular_sector_escalar_v2.py"]
deprecation_header = '''"""
=============================================================================
[DEPRECATED / LEGACY v2.0]
ADVERTENCIA METODOLÓGICA (v2.3 Audit):
Este módulo contiene la formulación original de exponenciales desacopladas.
Presenta patologías de condiciones iniciales (rho <= 0) y salvaguardas
espurias (H = -sqrt(10^-15)). 
Usar exclusivamente `simular_sector_escalar_v2_3.py` para el benchmark oficial.
=============================================================================
"""
'''

for file_path in legacy_files:
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "[DEPRECATED" not in content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(deprecation_header + content)
            print(f"File {file_path} successfully tagged as DEPRECATED.")

# 2. REGENERACIÓN DE FIGURA ESPECTRAL (26.50 MHz / 32.05 MHz)
f_rh = 26.50    # MHz
f_max = 32.05   # MHz
freqs = np.linspace(1.0, 100.0, 1000)

n_t = 2.4188
P_T = (freqs / f_rh)**n_t * np.exp(-freqs / f_max)
P_T_norm = P_T / np.max(P_T)

plt.figure(figsize=(9, 5))
plt.plot(freqs, P_T_norm, color='#0066CC', lw=2, label=r'Espectro Tensorial $P_T(f)$ ($n_t=2.4188$)')
plt.axvline(f_rh, color='#CC0000', linestyle='--', label=f'Horizonte $f_{{rh}} = {f_rh:.2f}$ MHz')
plt.axvline(f_max, color='#008000', linestyle=':', label=f'Pico Máximo $f_{{max}} = {f_max:.2f}$ MHz')

plt.title('Q-Twin v2.3: Densidad Espectral Tensorial Corregida (Factor $2\\pi$)', fontsize=12)
plt.xlabel('Frecuencia Comóvil $f$ [MHz]', fontsize=10)
plt.ylabel('Amplitud Normalizada $P_T(f) / P_{T,\\max}$', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(loc='upper right')

os.makedirs("docs/figures", exist_ok=True)
plt.savefig("docs/figures/espectro_tensorial_v2_3.png", dpi=300, bbox_inches='tight')
print("Figura 'docs/figures/espectro_tensorial_v2_3.png' generada con éxito.")
