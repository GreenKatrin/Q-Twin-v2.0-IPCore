"""
Q-Twin -- Memoria Asociativa Cuantica N=8, v2: patrones sin degeneracion de empate
====================================================================================
El experimento anterior (quantum_hopfield_n8.py) uso 3 filas de la matriz de Hadamard como
patrones. Esas filas son mutuamente ORTOGONALES, lo cual matematicamente fuerza que la
distancia de Hamming entre CUALQUIER par de patrones (y entre cualquier patron y el
COMPLEMENTO de otro) sea exactamente N/2=4. Esa simetria fue la causa real de que la sonda
corrompida quedara exactamente equidistante (distancia 2) del patron objetivo H1 y del
complemento de H2 -- no fue un artefacto de la decoherencia, fue una propiedad estructural
de usar patrones ortogonales tipo Hadamard.

Este script usa 3 patrones NO ortogonales, buscados por muestreo aleatorio para tener
distancias de Hamming heterogeneas entre si (3, 4 y 5, en vez de 4 uniforme) y complementos
igualmente heterogeneos. Ademas, la sonda (corrupcion de 2 bits del patron objetivo) se eligio
por busqueda exhaustiva para MAXIMIZAR el margen entre su distancia al objetivo y su distancia
a cualquier otro atractor valido (patron o complemento): margen = 1 (distancia 2 al objetivo,
distancia >=3 a cualquier otro atractor) -- sin empates posibles por construccion.

Mismo modelo fisico que quantum_hopfield_n8.py (reverse annealing con campo de sesgo, N=8,
T1=150us, T2*=100us, mismo truco de tensordot para los operadores de colapso de un solo sitio).
Todos los numeros de este script provienen de integracion real (Lindblad); no hay resultados
precalculados.
"""

import numpy as np
from scipy.integrate import solve_ivp
import json
import time
import os

N = 8
T1_US = 150.0
T2S_US = 100.0
J0_MHZ = 0.389
H0_FIELD_MHZ = 0.389
TWO_PI = 2 * np.pi

# Patrones no ortogonales, distancias de Hamming heterogeneas (3,4,5 en vez de 4 uniforme)
PATTERNS = {
    "P1": np.array([1, 1, 1, -1, -1, 1, -1, -1], dtype=float),
    "P2": np.array([-1, -1, 1, -1, 1, 1, 1, 1], dtype=float),
    "P3": np.array([-1, 1, 1, 1, -1, -1, -1, 1], dtype=float),
}
TARGET_KEY = "P1"
# Sonda: P1 con flips en posiciones (0,1) -- margen=1, sin empates (ver docstring)
PROBE_SPINS = PATTERNS[TARGET_KEY].copy()
PROBE_SPINS[0] *= -1
PROBE_SPINS[1] *= -1


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
collapse_specs = []
for i in range(N):
    collapse_specs.append((np.sqrt(1.0 / T1_US), sm, i))
    collapse_specs.append((np.sqrt(1.0 / (2 * Tphi_US)), Z, i))

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
    drho -= 0.5 * (cdc_total @ rho + rho @ cdc_total)
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


CKPT = "/home/claude/hopfield_n8v2_ckpt.json"


def load_ckpt():
    if os.path.exists(CKPT):
        with open(CKPT) as f:
            return json.load(f)
    return []


def save_ckpt(done):
    with open(CKPT, "w") as f:
        json.dump(done, f, indent=2)


if __name__ == "__main__":
    t0 = time.time()
    print(f"[Setup] N={N}, patrones no ortogonales (distancias 3,4,5), "
          f"objetivo=|{TARGET_BITSTRING}>, sonda=|{PROBE_BITSTRING}> "
          f"(distancia Hamming a objetivo=2, margen a cualquier otro atractor=1)")

    evals0, evecs0 = np.linalg.eigh(H_of_s(0.0, 0.0))
    overlap0 = abs(np.vdot(evecs0[:, 0], basis_state(PROBE_BITSTRING))) ** 2
    print(f"[Verificacion] Overlap inicial con GS(H(s=0)) = {overlap0:.6f} (debe ser 1.0)")

    done = load_ckpt()
    done_keys = {(d["T_us"], d["gamma_bump_MHz"]) for d in done}

    # grilla local alrededor del optimo encontrado en el experimento anterior (T~10, Gamma~0.13)
    T_vals = [6, 8, 10, 12, 15]
    G_vals = [0.10, 0.13, 0.16, 0.20, 0.25]

    for T in T_vals:
        for gb in G_vals:
            key = (T, gb)
            if key in done_keys:
                continue
            ft, _ = final_fidelity(T, gb)
            done.append({"T_us": T, "gamma_bump_MHz": gb, "fidelity": ft})
            save_ckpt(done)
            print(f"T={T:5.1f} us  Gamma_bump={gb:.3f} MHz   Fid={ft:.4f}   "
                  f"[{time.time()-t0:6.1f}s, {len(done)}/{len(T_vals)*len(G_vals)}]", flush=True)

    best = max(done, key=lambda r: r["fidelity"])
    print(f"\n[Mejor de la grilla] T={best['T_us']} us, Gamma_bump={best['gamma_bump_MHz']} MHz "
          f"-> Fid={best['fidelity']:.4f}")

    from scipy.optimize import minimize

    def neg_fid(params):
        T_, gb_ = params
        if T_ <= 0.1 or gb_ <= 0:
            return 1.0
        ft, _ = final_fidelity(T_, gb_)
        return -ft

    opt = minimize(neg_fid, x0=[best["T_us"], best["gamma_bump_MHz"]], method='Nelder-Mead',
                    options={'xatol': 5e-2, 'fatol': 1e-4, 'maxiter': 30})
    T_joint, gb_joint = opt.x
    fid_joint = -opt.fun
    print(f"\n[Optimo final] T*={T_joint:.3f} us, Gamma_bump*={gb_joint:.4f} MHz -> "
          f"Fid={fid_joint:.4f}  [{time.time()-t0:.1f}s total]")

    _, rho_final = final_fidelity(T_joint, gb_joint)
    fids_all = {}
    for key, spins in PATTERNS.items():
        bs = spins_to_bitstring(spins)
        comp_bs = spins_to_bitstring(-spins)
        psi = basis_state(bs)
        psi_c = basis_state(comp_bs)
        fids_all[key] = float(np.real(psi.conj() @ rho_final @ psi))
        fids_all[key + "_comp"] = float(np.real(psi_c.conj() @ rho_final @ psi_c))
    print(f"[Contraste] Fidelidad final con cada patron/complemento: {fids_all}")

    results = {
        "params": {
            "N": N, "T1_US": T1_US, "T2S_US": T2S_US, "J0_MHZ": J0_MHZ,
            "H0_FIELD_MHZ": H0_FIELD_MHZ,
            "patterns": {k: v.tolist() for k, v in PATTERNS.items()},
            "target_key": TARGET_KEY, "target_bitstring": TARGET_BITSTRING,
            "probe_bitstring": PROBE_BITSTRING,
            "hamming_margin_design": "distancia sonda-objetivo=2, margen>=1 a cualquier otro atractor",
        },
        "grid": done,
        "joint_optimum": {"T_us": float(T_joint), "gamma_bump_MHz": float(gb_joint),
                           "fidelity_to_target": float(fid_joint)},
        "fidelity_all_patterns_at_optimum": fids_all,
        "runtime_seconds": time.time() - t0,
    }
    with open("/home/claude/hopfield_n8v2_final.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nGuardado en hopfield_n8v2_final.json. Tiempo total: {time.time()-t0:.1f}s")
