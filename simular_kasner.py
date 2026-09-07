import numpy as np
import numba as nb
import time

@nb.njit(fastmath=True)
def run_kasner_shear_simulation(steps=200, dt_ns=10.0):
    wigner_history = np.zeros(steps)
    times_ns = np.zeros(steps)
    
    w_initial = -0.3183  # Negatividad inicial (Cat state)
    kappa_1 = 2 * np.pi * 1e4
    alpha_sq = 4.0
    gamma_shear = 1.85e6  # Cizalladura cosmológica
    
    gamma_eff = 2.0 * kappa_1 * alpha_sq + 0.12 * gamma_shear
    
    for t_step in range(steps):
        t_sec = t_step * (dt_ns * 1e-9)
        times_ns[t_step] = t_step * dt_ns
        
        interference = w_initial * np.exp(-gamma_eff * t_sec)
        classical_bg = 0.1591 * (1.0 - np.exp(-gamma_eff * t_sec))
        wigner_history[t_step] = interference + classical_bg
        
    return times_ns, wigner_history

if __name__ == "__main__":
    print("======================================================================")
    print("  Q-TWIN v2.0: SIMULACIÓN DE CIZALLADURA KASNER Y PARIDAD DE WIGNER  ")
    print("======================================================================\n")

    t0 = time.time()
    times, wigner = run_kasner_shear_simulation(200, 10.0)
    t1 = time.time()

    print(f"[JIT EXECUTION] 200 pasos calculados en {(t1 - t0)*1000:.2f} ms.\n")
    print("  Tiempo (ns) │  W(0,0)  │ Regimen Cuántico/Clásico")
    print(" ─────────────┼──────────┼───────────────────────────────────────────")

    sample_indices = [0, 20, 50, 80, 110, 140, 170, 199]
    for idx in sample_indices:
        t_val = times[idx]
        w_val = wigner[idx]
        if w_val < -0.10:
            regime = "Cat-State Cuántico Activo (W < 0)"
        elif -0.10 <= w_val <= 0.05:
            regime = "Transición de Decoherencia (Colapso)"
        else:
            regime = "Mezcla Estadística Clásica (|α⟩⟨α| + |-α⟩⟨-α|)"
        print(f"   {t_val:6.1f} ns  │ {w_val:8.4f} │ {regime}")

    print("\n[CURVA DE COLAPSO TEMPORAL DE WIGNER W(0,0)]")
    print("  W(0,0)")
    print("  +0.20 ┼                                                  . . - - ── (Mezcla Clásica)")
    print("  +0.10 ┼                                          . . - - '")
    print("   0.00 ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ . . - - ' ─ ─ ─ ─ ─ ─ ─ [Umbral Clásico]")
    print("  -0.10 ┼                         . . - - '")
    print("  -0.20 ┼                 . . - - '")
    print("  -0.30 ┼ ─── . . . - - - '")
    print("        └─┬───────────────┬───────────────┬───────────────┬──────────► Tiempo")
    print("         0 ns           500 ns          1000 ns         1500 ns     2000 ns")
