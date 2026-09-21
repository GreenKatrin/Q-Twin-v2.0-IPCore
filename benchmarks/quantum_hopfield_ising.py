"""
Q-Twin -- Memoria Asociativa Cuantica: recall de patrones via reverse-annealing (N=3)
======================================================================================
HISTORIA DE ESTE SCRIPT (transparencia metodologica):

Intento 1 (protocolo tal como se propuso originalmente): "forward annealing" puro,
H(t) = H_ising - Gamma(t) * sum_i X_i, partiendo de un estado inicial producto de |+>/|-> en
la base X codificando el patron corrompido, con Gamma(t) decreciendo linealmente de Gamma_max
a 0. Resultado real obtenido: fidelidad final con el patron objetivo NUNCA supero ~10%, y
EMPEORaba al alargar el tiempo de quench (de 0.10 a T=0.5us hasta ~0.0000 a T=200us) --
justo lo opuesto de lo que predice el teorema adiabatico si el protocolo fuera correcto. El
diagnostico: el estado inicial |+/-> especificado no es el estado fundamental del Hamiltoniano
inicial dominado por el campo transverso (ese estado fundamental es unico y NO depende del
patron: es |+++>); es una autoenergia EXCITADA de sum_i X_i, por lo que la evolucion adiabatica
lo conecta a un estado excitado de H_ising, no al minimo global. El protocolo tal como se penso
NO puede funcionar independientemente de la velocidad del quench.

Intento 2 (protocolo corregido, el que efectivamente se ejecuta abajo): "reverse annealing"
con campo de sesgo local hacia el patron corrompido --
    H(s) = -(1-s) * sum_i h_i Z_i  -  Gamma(s) * sum_i X_i  -  s * sum_ij J_ij Z_i Z_j
En s=0, el campo de sesgo domina y el estado fundamental ES EXACTAMENTE el patron corrompido
(overlap = 1.0, verificado numericamente); en s=1, H(s) = H_ising puro, cuyo estado fundamental
es el subespacio degenerado {patron objetivo, patron espurio}. Gamma(s) es un "bache" de campo
transverso en medio de la rampa (Gamma(s) = Gamma_bump * 4s(1-s), nulo en los extremos) que
habilita el tunelamiento necesario para corregir el bit volteado. Este es el protocolo estandar
en la literatura de recall de patrones con annealers cuanticos (reverse annealing).

Con este protocolo se escaneo T (tiempo total de rampa) y Gamma_bump; el mejor punto encontrado
en el canal IDEAL (sin decoherencia) fue Gamma_bump=0.5 MHz, T=100us, con fidelidad=0.9528.
Al incluir decoherencia real (T1=150us, T2*=100us, reutilizados de benchmarks/run_rb_suite.py),
la fidelidad a T=100us cae a solo 0.324 -- el tiempo de rampa ya es una fraccion apreciable de
T1/T2*. Se re-escaneo T con decoherencia (T=10us dio 0.677), y luego se hizo un barrido fino de
Gamma_bump en [0.02, 1.5] MHz a T=10us: aparece un pico limpio y unimodal en Gamma_bump~0.15 MHz
(no en 0.5 MHz como se conjeturo inicialmente). Una optimizacion conjunta final de (T, Gamma_bump)
con Nelder-Mead da el optimo GLOBAL real de este experimento:
    T* = 6.058 us, Gamma_bump* = 0.1682 MHz  ->  Fidelidad(target) = 0.9325, Fidelidad(espurio) = 0.0201
Es decir: con la optimizacion conjunta correcta, la penalidad por decoherencia se reduce
drasticamente frente al primer intento ingenuo (0.677 -> 0.933) simplemente por operar en el
regimen de acoplamiento Gamma_bump correcto y un tiempo de rampa mas corto que el "optimo ideal"
ingenuamente extrapolado del caso sin decoherencia.

Todos los numeros de este script provienen de integracion real (Schrodinger/Lindblad); no hay
resultados precalculados.
"""

import numpy as np
from scipy.integrate import solve_ivp
import json

# =====================================================================
# 0. PARAMETROS
# =====================================================================
N = 3
T1_US = 150.0
T2S_US = 100.0
J0_MHZ = 0.389
H0_FIELD_MHZ = 0.389
GAMMA_BUMP_MHZ = 0.5              # optimo del canal IDEAL (T=100us, sin decoherencia)
GAMMA_BUMP_LINDBLAD_MHZ = 0.1682   # optimo CONJUNTO (T, Gamma_bump) tras barrido fino con T1/T2*
T_OPTIMAL_IDEAL_US = 100.0
T_OPTIMAL_LINDBLAD_US = 6.058       # optimo conjunto con decoherencia (T1=150us, T2*=100us)

PATTERNS = {"001": np.array([+1, +1, -1]), "110": np.array([-1, -1, +1])}
PROBE_STATE = "011"
TARGET_PATTERN = "001"
SPURIOUS_PATTERN = "110"

TWO_PI = 2 * np.pi


def hebb_matrix(patterns, n):
    Jm = np.zeros((n, n))
    for xi in patterns.values():
        Jm += np.outer(xi, xi)
    Jm /= n
    np.fill_diagonal(Jm, 0.0)
    return Jm


J = hebb_matrix(PATTERNS, N) * J0_MHZ

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

H_ising = np.zeros((2 ** N, 2 ** N), dtype=complex)
for i in range(N):
    for j in range(i + 1, N):
        H_ising += -TWO_PI * J[i, j] * (Z_ops[i] @ Z_ops[j])

probe_signs = np.array([+1 if b == '0' else -1 for b in PROBE_STATE], dtype=float)
H_bias = np.zeros((2 ** N, 2 ** N), dtype=complex)
for i in range(N):
    H_bias += -TWO_PI * H0_FIELD_MHZ * probe_signs[i] * Z_ops[i]

Tphi_US = 1.0 / (1.0 / T2S_US - 1.0 / (2 * T1_US))
c_ops = []
for i in range(N):
    c_ops.append(np.sqrt(1.0 / T1_US) * op_on_site(sm, i))
    c_ops.append(np.sqrt(1.0 / (2 * Tphi_US)) * op_on_site(Z, i))


def H_of_s(s, gamma_bump=GAMMA_BUMP_MHZ):
    gamma = gamma_bump * 4 * s * (1 - s)
    return (1 - s) * H_bias + s * H_ising - TWO_PI * gamma * H_x_unit


def basis_state(bs):
    psi = np.zeros(2 ** N, dtype=complex)
    psi[int(bs, 2)] = 1.0
    return psi


def basis_density(bs):
    psi = basis_state(bs)
    return np.outer(psi, psi.conj())


def schrodinger_rhs(t, psi, T, gamma_bump):
    return -1j * (H_of_s(t / T, gamma_bump) @ psi)


def lindblad_rhs(t, rho_vec, T, gamma_bump):
    dim = 2 ** N
    rho = rho_vec.reshape(dim, dim)
    H = H_of_s(t / T, gamma_bump)
    drho = -1j * (H @ rho - rho @ H)
    for c in c_ops:
        drho += c @ rho @ c.conj().T - 0.5 * (c.conj().T @ c @ rho + rho @ c.conj().T @ c)
    return drho.reshape(-1)


def von_neumann_entropy_qubit0(rho_full, n=N):
    full = rho_full.reshape(2, 2 ** (n - 1), 2, 2 ** (n - 1))
    rho_A = np.zeros((2, 2), dtype=complex)
    for a in range(2):
        for b in range(2):
            rho_A[a, b] = np.trace(full[a, :, b, :])
    eigvals = np.linalg.eigvalsh(rho_A)
    eigvals = eigvals[eigvals > 1e-12]
    return float(-np.sum(eigvals * np.log2(eigvals)))


if __name__ == "__main__":
    psi_target = basis_state(TARGET_PATTERN)
    psi_other = basis_state(SPURIOUS_PATTERN)
    psi0 = basis_state(PROBE_STATE)

    evals0, evecs0 = np.linalg.eigh(H_of_s(0.0))
    overlap0 = abs(np.vdot(evecs0[:, 0], psi0)) ** 2
    print(f"[Verificacion] Overlap inicial con GS(H(s=0)) = {overlap0:.6f} (debe ser 1.0)")

    results = {"params": {
        "N": N, "T1_US": T1_US, "T2S_US": T2S_US, "J0_MHZ": J0_MHZ,
        "H0_FIELD_MHZ": H0_FIELD_MHZ, "GAMMA_BUMP_MHZ": GAMMA_BUMP_MHZ,
        "probe": PROBE_STATE, "target": TARGET_PATTERN, "spurious": SPURIOUS_PATTERN,
    }}

    print("\n=== Canal IDEAL (Schrodinger), T optimo ideal ===")
    n_eval = 200
    T = T_OPTIMAL_IDEAL_US
    t_eval = np.linspace(0, T, n_eval)
    sol_u = solve_ivp(schrodinger_rhs, [0, T], psi0, t_eval=t_eval, args=(T, GAMMA_BUMP_MHZ),
                       method='RK45', rtol=1e-10, atol=1e-12)
    fid_ideal_t = np.abs(sol_u.y.conj().T @ psi_target) ** 2
    S_E_ideal_t = [von_neumann_entropy_qubit0(np.outer(sol_u.y[:, k], sol_u.y[:, k].conj()))
                   for k in range(n_eval)]
    fid_ideal_other = abs(np.vdot(psi_other, sol_u.y[:, -1])) ** 2
    print(f"  T={T} us: Fid(target)={fid_ideal_t[-1]:.4f}  Fid(espurio)={fid_ideal_other:.4f}  "
          f"S_E_max={max(S_E_ideal_t):.4f} ebits")
    results["ideal_optimal"] = {
        "T_us": T, "t_eval_us": t_eval.tolist(),
        "fidelity_to_target": fid_ideal_t.tolist(), "S_E_ebits": S_E_ideal_t,
        "fidelity_to_spurious_final": float(fid_ideal_other),
    }

    print("\n=== Canal con decoherencia (Lindblad, T1/T2*), optimo conjunto (T, Gamma_bump) ===")
    T = T_OPTIMAL_LINDBLAD_US
    t_eval = np.linspace(0, T, n_eval)
    rho0 = basis_density(PROBE_STATE)
    sol_l = solve_ivp(lindblad_rhs, [0, T], rho0.reshape(-1), t_eval=t_eval,
                       args=(T, GAMMA_BUMP_LINDBLAD_MHZ), method='RK45', rtol=1e-8, atol=1e-10)
    fid_lind_t, S_E_lind_t = [], []
    for k in range(n_eval):
        rho_k = sol_l.y[:, k].reshape(2 ** N, 2 ** N)
        fid_lind_t.append(float(np.real(psi_target.conj() @ rho_k @ psi_target)))
        S_E_lind_t.append(von_neumann_entropy_qubit0(rho_k))
    fid_lind_other = float(np.real(psi_other.conj() @ sol_l.y[:, -1].reshape(8, 8) @ psi_other))
    print(f"  T={T} us, Gamma_bump={GAMMA_BUMP_LINDBLAD_MHZ} MHz: Fid(target)={fid_lind_t[-1]:.4f}  "
          f"Fid(espurio)={fid_lind_other:.4f}  S_E_max={max(S_E_lind_t):.4f} ebits")
    results["lindblad_optimal"] = {
        "T_us": T, "gamma_bump_MHz": GAMMA_BUMP_LINDBLAD_MHZ, "t_eval_us": t_eval.tolist(),
        "fidelity_to_target": fid_lind_t, "S_E_ebits": S_E_lind_t,
        "fidelity_to_spurious_final": fid_lind_other,
    }

    T = T_OPTIMAL_IDEAL_US
    rho0 = basis_density(PROBE_STATE)
    sol_l2 = solve_ivp(lindblad_rhs, [0, T], rho0.reshape(-1), args=(T, GAMMA_BUMP_MHZ),
                        method='RK45', rtol=1e-8, atol=1e-10)
    rho_f2 = sol_l2.y[:, -1].reshape(8, 8)
    fid_lind_at_100 = float(np.real(psi_target.conj() @ rho_f2 @ psi_target))
    print(f"\n[Contraste] Fid(target) con Lindblad pero a T=100us (el optimo IDEAL) = "
          f"{fid_lind_at_100:.4f}  <- decae fuerte por decoherencia a ese T")
    results["lindblad_at_ideal_T_for_contrast"] = {"T_us": T, "fidelity_to_target": fid_lind_at_100}

    print("\n=== Barrido fino de Gamma_bump a T=10us (con decoherencia) ===")
    gbumps = np.linspace(0.02, 1.5, 30)
    sweep = []
    for gb in gbumps:
        sol = solve_ivp(lindblad_rhs, [0, 10.0], basis_density(PROBE_STATE).reshape(-1),
                         args=(10.0, gb), method='RK45', rtol=1e-8, atol=1e-10)
        rho_f = sol.y[:, -1].reshape(8, 8)
        ft = float(np.real(psi_target.conj() @ rho_f @ psi_target))
        sweep.append({"gamma_bump_MHz": float(gb), "fidelity_to_target": ft})
    best_sweep = max(sweep, key=lambda r: r["fidelity_to_target"])
    print(f"  Mejor punto de la grilla: Gamma_bump={best_sweep['gamma_bump_MHz']:.4f} MHz  "
          f"Fid={best_sweep['fidelity_to_target']:.4f}")
    results["gamma_bump_sweep_T10us"] = sweep

    from scipy.optimize import minimize

    def neg_fid(params):
        T_, gb_ = params
        if T_ <= 0.1 or gb_ <= 0:
            return 1.0
        sol = solve_ivp(lindblad_rhs, [0, T_], basis_density(PROBE_STATE).reshape(-1),
                         args=(T_, gb_), method='RK45', rtol=1e-8, atol=1e-10)
        rho_f = sol.y[:, -1].reshape(8, 8)
        return -float(np.real(psi_target.conj() @ rho_f @ psi_target))

    opt = minimize(neg_fid, x0=[best_sweep["gamma_bump_MHz"] * 40, best_sweep["gamma_bump_MHz"]],
                    method='Nelder-Mead', options={'xatol': 1e-3, 'fatol': 1e-5, 'maxiter': 300})
    T_joint, gb_joint = opt.x
    print(f"\n[Optimizacion conjunta] T*={T_joint:.3f} us, Gamma_bump*={gb_joint:.4f} MHz "
          f"-> Fidelidad = {-opt.fun:.4f}")
    results["joint_optimum"] = {
        "T_us": float(T_joint), "gamma_bump_MHz": float(gb_joint), "fidelity_to_target": float(-opt.fun),
    }

    with open("/home/claude/hopfield_ising_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResultados guardados en hopfield_ising_results.json")
