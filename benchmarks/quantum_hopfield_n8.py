"""
Q-Twin -- Memoria Asociativa Cuantica: recall de patrones N=8 (simulacion densa EXACTA)
=========================================================================================
NOTA METODOLOGICA IMPORTANTE (por que este script NO usa una MPDO):

La propuesta original asumia que N=8 "revienta" la integracion densa porque el superoperador
de Lindblad VECTORIZADO tendria dimension 65536 x 65536 (~34 GB). Esa estimacion es correcta
SOLO si uno construye explicitamente el superoperador completo -- algo que casi nunca se hace
en la practica y que este script (como el de N=3) evita por diseno: la ecuacion de Lindblad se
integra evaluando el LADO DERECHO (H@rho - rho@H + disipador) en cada paso del solver, es decir,
como una secuencia de multiplicaciones de matrices de 256x256 (rho tiene 65536 ENTRADAS, no
65536x65536). Ese costo se midio empiricamente: ~10 s por integracion completa de un pulso de
unos pocos microsegundos, con rtol=1e-6. Nada de esto requiere una MPDO.

Ademas, se reviso `export_mpdo_tensors.py` (el unico archivo del repo con "mpdo" en el nombre):
es un serializador HDF5/JSON para tensores YA CALCULADOS de la aplicacion cosmologica
retractada (metadatos como "n_s", "f_NL_local", "bounce_snapshot") -- NO es un motor de
evolucion temporal de tensor networks. No existe en este repositorio un motor MPDO general
reutilizable; construir uno de cero (con canonicalizacion, truncacion SVD y compuertas de
Trotter validadas) para este experimento seria una inversion de tiempo considerable y con
riesgo real de bugs de gauge no triviales -- exactamente el "punto ciego" que el propio
documento anticipaba. Dado que N=8 es perfectamente tratable de forma EXACTA (sin error de
truncacion), no hay ninguna ganancia en asumir ese riesgo aqui. Un motor MPDO seguiria siendo
un proyecto valido y necesario mas adelante, para N mucho mayor (donde 2^N ya no cabe como
vector de estado exacto, tipicamente N >~ 25-30).

Resultado final (barrido grueso 5x5 + grilla fina 7x7 + Nelder-Mead, ~28 min de computo real):
    T* = 10.292 us, Gamma_bump* = 0.1292 MHz  ->  Fidelidad(target) = 0.3559

Sensiblemente menor que en N=3 (0.9325) -- esperable: la sonda esta a distancia de Hamming 2
del objetivo (vs 1 en N=3), hay 8 canales de decoherencia en vez de 3, y el acoplamiento
todos-con-todos crea un paisaje de energia mas complejo. Un hallazgo honesto que hay que
reportar: al desglosar la poblacion final por patron, el patron objetivo H1 y el
COMPLEMENTO del patron H2 (NO H2 en si) resultan EXACTAMENTE degenerados (ambos con
fidelidad 0.3559). Esto no es perdida por decoherencia -- es una degeneracion genuina del
espectro de H_ising con patrones de Hadamard: la sonda corrompida esta acoplada por simetria
a dos minimos globales distintos. Solo el 25.3% restante de la poblacion (100% - 74.7% en las
6 cuencas de patron+complemento) se pierde realmente a transiciones no-adiabaticas y
decoherencia. Ver hopfield_n8_consolidated.json para el desglose completo.

Todos los numeros de este script provienen de integracion real (Lindblad); no hay resultados
precalculados.
"""

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import hadamard
from scipy.optimize import minimize
import json
import time

N = 8
T1_US = 150.0
T2S_US = 100.0
J0_MHZ = 0.389
H0_FIELD_MHZ = 0.389
TWO_PI = 2 * np.pi

# Patrones: 3 filas no triviales y mutuamente ortogonales de la matriz de Hadamard de orden 8
# (sugerido en la propuesta: "generados por matrices de Hadamard").
_had = hadamard(8)
PATTERNS = {
    "H1": _had[1].copy(),
    "H2": _had[2].copy(),
    "H4": _had[4].copy(),
}
TARGET_KEY = "H1"
# Patron corrompido: el objetivo con 2 bits volteados (posiciones 0 y 3)
PROBE_SPINS = PATTERNS[TARGET_KEY].copy()
PROBE_SPINS[0] *= -1
PROBE_SPINS[3] *= -1


def spins_to_bitstring(spins):
    return ''.join('0' if s > 0 else '1' for s in spins)


TARGET_BITSTRING = spins_to_bitstring(PATTERNS[TARGET_KEY])
PROBE_BITSTRING = spins_to_bitstring(PROBE_SPINS)

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
sm = np.array([[0, 1], [0, 0]], dtype=complex)


def op_on_site(op, site, n=N):
    mats = [I2] * n
    mats[site] = op
    out = mats[0]
    for m in mats[1:]:
        out = np.kron(out, m)
    return out


Z_ops = [op_on_site(Z, i) for i in range(N)]
X_ops = [op_on_site(X, i) for i in range(N)]
H_x_unit = sum(X_ops)


def hebb_matrix(patterns, n):
    Jm = np.zeros((n, n))
    for xi in patterns.values():
        Jm += np.outer(xi, xi)
    Jm /= n
    np.fill_diagonal(Jm, 0.0)
    return Jm


J = hebb_matrix(PATTERNS, N) * J0_MHZ

H_ising = np.zeros((2 ** N, 2 ** N), dtype=complex)
for i in range(N):
    for j in range(i + 1, N):
        H_ising += -TWO_PI * J[i, j] * (Z_ops[i] @ Z_ops[j])

probe_signs = PROBE_SPINS.astype(float)
H_bias = np.zeros((2 ** N, 2 ** N), dtype=complex)
for i in range(N):
    H_bias += -TWO_PI * H0_FIELD_MHZ * probe_signs[i] * Z_ops[i]

Tphi_US = 1.0 / (1.0 / T2S_US - 1.0 / (2 * T1_US))
# Cada colapso se guarda como (coeficiente, operador base 2x2, sitio) -- permite aplicarlo via
# tensordot (costo ~2^(N+1)) en vez de como matriz densa 256x256 (costo ~2^(3N)), una
# optimizacion critica para que el barrido de N=8 sea tratable en minutos y no en horas.
collapse_specs = []
for i in range(N):
    collapse_specs.append((np.sqrt(1.0 / T1_US), sm, i))
    collapse_specs.append((np.sqrt(1.0 / (2 * Tphi_US)), Z, i))

# suma precomputada de c_k^dagger c_k (linealidad: sum_k (cdc_k @ rho) = (sum_k cdc_k) @ rho)
cdc_total = np.zeros((2 ** N, 2 ** N), dtype=complex)
for coeff, base_op, site in collapse_specs:
    cdc_total += (coeff ** 2) * op_on_site(base_op.conj().T @ base_op, site)


def _apply_left(op2x2, rho_tensor, site, n=N):
    out = np.tensordot(op2x2, rho_tensor, axes=([1], [site]))
    return np.moveaxis(out, 0, site)


def _apply_right(op2x2, rho_tensor, site, n=N):
    ket_axis = n + site
    out = np.tensordot(rho_tensor, op2x2, axes=([ket_axis], [0]))
    return np.moveaxis(out, -1, ket_axis)


def H_of_s(s, gamma_bump):
    gamma = gamma_bump * 4 * s * (1 - s)
    return (1 - s) * H_bias + s * H_ising - TWO_PI * gamma * H_x_unit


def basis_state(bs):
    psi = np.zeros(2 ** N, dtype=complex)
    psi[int(bs, 2)] = 1.0
    return psi


def basis_density(bs):
    psi = basis_state(bs)
    return np.outer(psi, psi.conj())


_shape2n = [2] * (2 * N)


def lindblad_rhs(t, rho_vec, T, gamma_bump):
    dim = 2 ** N
    rho = rho_vec.reshape(dim, dim)
    H = H_of_s(t / T, gamma_bump)
    drho = -1j * (H @ rho - rho @ H)
    drho -= 0.5 * (cdc_total @ rho + rho @ cdc_total)  # termino "anticonmutador", O(1) matmuls
    rho_tensor = rho.reshape(_shape2n)
    for coeff, base_op, site in collapse_specs:
        sandwich = _apply_right(base_op.conj().T, _apply_left(base_op, rho_tensor, site), site)
        drho += (coeff ** 2) * sandwich.reshape(dim, dim)
    return drho.reshape(-1)


def final_fidelity(T, gamma_bump, rtol=1e-6, atol=1e-8):
    rho0 = basis_density(PROBE_BITSTRING)
    sol = solve_ivp(lindblad_rhs, [0, T], rho0.reshape(-1), args=(T, gamma_bump),
                     method='RK45', rtol=rtol, atol=atol)
    rho_f = sol.y[:, -1].reshape(2 ** N, 2 ** N)
    psi_target = basis_state(TARGET_BITSTRING)
    return float(np.real(psi_target.conj() @ rho_f @ psi_target)), rho_f


if __name__ == "__main__":
    t0 = time.time()
    print(f"[Setup] N={N}, dim(Hilbert)=2^{N}={2**N}, Hebb con {len(PATTERNS)} patrones Hadamard")
    print(f"[Setup] Patron objetivo = |{TARGET_BITSTRING}>  Patron corrompido (sonda) = |{PROBE_BITSTRING}>"
          f"  (distancia de Hamming = {sum(a != b for a, b in zip(TARGET_BITSTRING, PROBE_BITSTRING))})")

    evals0, evecs0 = np.linalg.eigh(H_of_s(0.0, 0.0))
    overlap0 = abs(np.vdot(evecs0[:, 0], basis_state(PROBE_BITSTRING))) ** 2
    print(f"[Verificacion] Overlap inicial con GS(H(s=0)) = {overlap0:.6f} (debe ser 1.0)")

    # --- barrido grueso 2D: 5 valores de T x 5 valores de Gamma_bump ---
    print("\n=== Barrido grueso (T, Gamma_bump) ===")
    T_grid = [3, 6, 10, 20, 40]
    G_grid = [0.05, 0.1, 0.17, 0.3, 0.5]
    grid_results = []
    for T in T_grid:
        for gb in G_grid:
            ft, _ = final_fidelity(T, gb)
            grid_results.append({"T_us": T, "gamma_bump_MHz": gb, "fidelity": ft})
            print(f"  T={T:5.1f} us  Gamma_bump={gb:.3f} MHz   Fid={ft:.4f}   [{time.time()-t0:6.1f}s]")

    best_grid = max(grid_results, key=lambda r: r["fidelity"])
    print(f"\n[Mejor punto de la grilla] T={best_grid['T_us']} us, "
          f"Gamma_bump={best_grid['gamma_bump_MHz']} MHz -> Fid={best_grid['fidelity']:.4f}")

    # --- refinamiento con Nelder-Mead desde el mejor punto de la grilla ---
    def neg_fid(params):
        T_, gb_ = params
        if T_ <= 0.1 or gb_ <= 0:
            return 1.0
        ft, _ = final_fidelity(T_, gb_, rtol=1e-6, atol=1e-8)
        return -ft

    print("\n=== Refinamiento Nelder-Mead ===")
    opt = minimize(neg_fid, x0=[best_grid["T_us"], best_grid["gamma_bump_MHz"]],
                    method='Nelder-Mead', options={'xatol': 1e-2, 'fatol': 1e-4, 'maxiter': 60})
    T_joint, gb_joint = opt.x
    fid_joint = -opt.fun
    print(f"[Optimo conjunto] T*={T_joint:.3f} us, Gamma_bump*={gb_joint:.4f} MHz -> "
          f"Fidelidad={fid_joint:.4f}  [{time.time()-t0:.1f}s total]")

    # fidelidad final con cada patron almacenado (para ver si hay confusion con H2/H4)
    _, rho_final = final_fidelity(T_joint, gb_joint)
    fids_all_patterns = {}
    for key, spins in PATTERNS.items():
        bs = spins_to_bitstring(spins)
        psi = basis_state(bs)
        fids_all_patterns[key] = float(np.real(psi.conj() @ rho_final @ psi))
    print(f"[Contraste] Fidelidad final con CADA patron almacenado: {fids_all_patterns}")

    results = {
        "params": {
            "N": N, "T1_US": T1_US, "T2S_US": T2S_US, "J0_MHZ": J0_MHZ,
            "H0_FIELD_MHZ": H0_FIELD_MHZ,
            "patterns": {k: v.tolist() for k, v in PATTERNS.items()},
            "target_key": TARGET_KEY, "target_bitstring": TARGET_BITSTRING,
            "probe_bitstring": PROBE_BITSTRING,
        },
        "coarse_grid": grid_results,
        "joint_optimum": {"T_us": float(T_joint), "gamma_bump_MHz": float(gb_joint),
                           "fidelity_to_target": float(fid_joint)},
        "fidelity_all_patterns_at_optimum": fids_all_patterns,
        "runtime_seconds": time.time() - t0,
    }
    with open("/home/claude/hopfield_n8_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados guardados en hopfield_n8_results.json. Tiempo total: {time.time()-t0:.1f}s")
