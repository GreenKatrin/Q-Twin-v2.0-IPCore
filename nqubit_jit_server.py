import numpy as np
import numba as nb
import time

# --- PARÁMETROS FÍSICOS Y DE TRUNCAMIENTO ---
FOCK_DIM = 16          # Truncamiento de Fock (Error < 3.1e-7)
DT_NS = 1e-8           # Paso de tiempo RK4 (10 ns)
N_TH = 7.6e-12         # Ocupación térmica a 15 mK
EPSILON_SAT = 0.05     # Capa límite sigmoidal
KAPPA_EFF = 1.0e6      # Tasa de disipación de entropía (1 MHz)
KAPPA_1 = 2 * np.pi * 1e4 # Tasa de pérdida de un fotón (10 kHz)

@nb.njit(fastmath=True)
def build_fock_operators(dim=16):
    a = np.zeros((dim, dim), dtype=np.complex128)
    for n in range(1, dim):
        a[n - 1, n] = np.sqrt(n)
    a_dag = a.conj().T
    parity = np.zeros((dim, dim), dtype=np.complex128)
    for n in range(dim):
        parity[n, n] = (-1.0) ** n
    return a, a_dag, parity

@nb.njit(fastmath=True)
def compute_smc_lindblad_step(rho, a_op, S_val, kappa_eff, epsilon, dt):
    sat_factor = np.tanh(S_val / epsilon)
    L_smc = np.sqrt(kappa_eff) * sat_factor * a_op
    L_dag = L_smc.conj().T
    L_dag_L = np.dot(L_dag, L_smc)
    anticommutator = np.dot(L_dag_L, rho) + np.dot(rho, L_dag_L)
    d_rho_smc = np.dot(L_smc, np.dot(rho, L_dag)) - 0.5 * anticommutator
    return rho + d_rho_smc * dt

@nb.njit(fastmath=True)
def compute_wigner_parity_origin(rho, parity_op):
    trace_val = np.real(np.trace(np.dot(parity_op, rho)))
    return (2.0 / np.pi) * trace_val

@nb.njit(fastmath=True)
def run_simulation_loop(steps=200):
    a, a_dag, parity_op = build_fock_operators(FOCK_DIM)
    rho = np.zeros((FOCK_DIM, FOCK_DIM), dtype=np.complex128)
    rho[0, 0] = 0.5
    rho[4, 0] = 0.5
    rho[0, 4] = 0.5
    rho[4, 4] = 0.5
    wigner_history = np.zeros(steps)
    for t_step in range(steps):
        S_val = np.real(np.trace(np.dot(rho, rho))) - 1.0
        rho = compute_smc_lindblad_step(rho, a, S_val, KAPPA_EFF, EPSILON_SAT, DT_NS)
        wigner_history[t_step] = compute_wigner_parity_origin(rho, parity_op)
    return wigner_history

if __name__ == "__main__":
    print("[Q-TWIN JIT] Compilando e iniciando simulación en espacio de Fock d=16...")
    t0 = time.time()
    res = run_simulation_loop(200)
    t1 = time.time()
    print(f"[Q-TWIN SUCCESS] 200 pasos completados en {t1 - t0:.4f} s.")
    print(f"W(0,0) inicial (Cat-State) : {res[0]:.4f}")
    print(f"W(0,0) final (t = 2.0 µs)  : {res[-1]:.4f}")
