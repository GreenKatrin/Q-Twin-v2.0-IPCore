import numpy as np
import numba as nb
import time

@nb.njit(fastmath=True)
def run_reheating_simulation(steps=100, dt_ns=10.0):
    times_ns = np.zeros(steps)
    condensate_energy = np.zeros(steps)
    radiation_energy = np.zeros(steps)
    
    rho_condensate = 1.0
    rho_rad = 0.0
    g0 = 0.12
    gamma_decay = 0.04
    
    for t_step in range(steps):
        t_ns = t_step * dt_ns
        times_ns[t_step] = t_ns
        
        a_t = 1.0 + 0.015 * t_step
        g_eff = g0 * (1.0 / (a_t**3)) * np.exp(-0.5 * gamma_decay * t_step)
        
        transfer = g_eff * rho_condensate
        rho_condensate -= transfer
        rho_rad += transfer * (1.0 / (a_t**4))
        
        condensate_energy[t_step] = max(0.0, rho_condensate)
        radiation_energy[t_step] = max(0.0, rho_rad)
        
    return times_ns, condensate_energy, radiation_energy

if __name__ == "__main__":
    print("======================================================================")
    print("   Q-TWIN v2.0: FASE DE RECALENTAMIENTO Y NUCLEACIÓN DE MATERIA     ")
    print("======================================================================\n")
    
    t0 = time.time()
    times, e_cond, e_rad = run_reheating_simulation(100, 10.0)
    t1 = time.time()
    
    print(f"[JIT EXECUTION] 100 pasos calculados en {(t1 - t0)*1000:.2f} ms.\n")
    print("  Tiempo (ns) │  Energía Condensado  │  Energía Radiación  │ Estado")
    print(" ─────────────┼──────────────────────┼─────────────────────┼──────────────────────")
    
    indices = [0, 15, 30, 50, 70, 99]
    for idx in indices:
        status = "Transición Activa" if e_cond[idx] > 0.05 else "Dominación de Radiación"
        print(f"   {times[idx]:6.1f} ns  │       {e_cond[idx]:6.4f}         │       {e_rad[idx]:6.4f}        │ {status}")
