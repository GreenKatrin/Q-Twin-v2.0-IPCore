"""
Q-Twin -- Randomized Benchmarking (cierre del Vector 1)
========================================================
Los modulos originales (drag_pulse_engine.py, sim2real_channel.py, transmon_simulator.py,
clifford_decomposition.py, rb_core.py, run_rb.py) descritos en docs/RB_Pipeline_PostMortem.md
NO estan presentes en el repositorio (se verifico en todo el historial de git); solo el
postmortem y los resultados quedaron documentados. Este script los reconstruye desde cero en
un solo archivo, incorporando explicitamente cada correccion de bug documentada:

  3.1 Signo del termino DRAG en el Hamiltoniano:      -i/2 * Omega_Q(t) * (a - a_dag)
  3.2 Factor 2 en Omega_Q(t):                          Omega_Q = -lambda * dOmega_I/dt / (2*alpha)
  3.3 Tasa de muestreo convergida:                     10 GSa/s
  3.5 Filtrado causal con estado persistente:          scipy.signal.lfilter con zi propagado
  3.6 Full-scale fijo (no recalculado por pulso):      atado al pico de amplitud de X_pi/2
  3.7 Semilla independiente por repeticion:            SEED + 1000*m + k
  3.8 Ajuste ponderado, B=0.5 fijo:                    pesos = sigma/sqrt(K)

Transparencia metodologica: cada numero que este script imprime proviene de una integracion
real de la ecuacion maestra de Lindblad para cada secuencia. No hay resultados precalculados
ni hardcodeados en ninguna rama del codigo.

Parametros fisicos NO documentados explicitamente en el postmortem (T1, T2*, ancho de banda del
filtro coaxial, desbalance IQ) se fijan aqui a valores representativos de un transmon moderno y
se declaran explicitamente abajo -- son una eleccion de este script, no un hecho verificado del
proyecto.
"""

import numpy as np
from scipy.integrate import solve_ivp
from scipy.signal import butter, lfilter, lfilter_zi
from scipy.interpolate import interp1d
from scipy.optimize import minimize, minimize_scalar
from scipy.spatial.transform import Rotation
from itertools import permutations, product
import json
import time

# =====================================================================
# 0. PARAMETROS
# =====================================================================
TWO_PI = 2 * np.pi

ALPHA_MHZ = -300.0          # anarmonicidad (misma convencion que two_qubit/two_qubit_hil_dcg.py)
T1_US = 150.0                # supuesto: transmon moderno de alta coherencia (NO documentado en el postmortem)
T2S_US = 100.0                # supuesto (T2* <= 2*T1, se verifica abajo)
T_GATE_US = 0.020            # 20 ns por pulso fisico X_pi/2  -> 40 ns por Clifford (consistente con el postmortem)

SAMPLE_RATE_GSPS = 10.0       # estandar canonico (bug 3.3)
DAC_BITS = 14
JITTER_RMS_PS = 1.5
COAX_FC_MHZ = 350.0
IQ_GAIN_IMBAL = 0.02          # 2% de desbalance de ganancia I/Q (supuesto)
IQ_SKEW_DEG = 1.0             # skew de fase I/Q, referido a un LO de 5 GHz (supuesto, ver nota en Canal)
LAMBDA_DRAG = 1.0             # optimo canonico tras la correccion del factor 2 (seccion 3.2 del postmortem)

M_LIST = [1, 2, 4, 8, 16, 32, 64]
K_REPS = 20
BASE_SEED = 20260919

assert 1.0 / T2S_US >= 1.0 / (2 * T1_US), "T2* no puede exceder 2*T1"

DIM = 3


def annihilation(dim=DIM):
    a = np.zeros((dim, dim))
    for n in range(1, dim):
        a[n - 1, n] = np.sqrt(n)
    return a


a_op = annihilation()
a_dag = a_op.conj().T
n_op = a_dag @ a_op
anharm_op = 0.5 * (n_op @ (n_op - np.eye(DIM)))

H_static = TWO_PI * ALPHA_MHZ * anharm_op  # rad/us, marco rotante resonante con el drive

Tphi_US = 1.0 / (1.0 / T2S_US - 1.0 / (2 * T1_US))
c1 = np.sqrt(1.0 / T1_US) * a_op          # relajacion T1
c2 = np.sqrt(2.0 / Tphi_US) * n_op        # defasaje puro T_phi

print(f"[Parametros derivados] T_phi = {Tphi_US:.3f} us "
      f"(de T1={T1_US} us, T2*={T2S_US} us)")

# =====================================================================
# 1. MODULO B: SINTESIS DE PULSO DRAG
# =====================================================================

def gaussian_envelope(t, T, amp):
    """Gaussiana truncada con pedestal restado (borde en cero)."""
    sigma = T / 6.0
    tc = T / 2.0
    g = np.exp(-(t - tc) ** 2 / (2 * sigma ** 2))
    g0 = np.exp(-(tc ** 2) / (2 * sigma ** 2))
    return amp * (g - g0) / (1 - g0)


def gaussian_envelope_deriv(t, T, amp):
    """Derivada analitica exacta de gaussian_envelope (evita diferencias finitas -> mas rapido)."""
    sigma = T / 6.0
    tc = T / 2.0
    g = np.exp(-(t - tc) ** 2 / (2 * sigma ** 2))
    g0 = np.exp(-(tc ** 2) / (2 * sigma ** 2))
    dg_dt = -(t - tc) / sigma ** 2 * g
    return amp * dg_dt / (1 - g0)


def drag_quadratures(t, T, amp):
    """Omega_I(t), Omega_Q(t) en rad/us. Signo y factor 2 corregidos (bugs 3.1, 3.2)."""
    OmI = gaussian_envelope(t, T, amp)
    dOmI_dt = gaussian_envelope_deriv(t, T, amp)
    alpha_ang = TWO_PI * ALPHA_MHZ
    OmQ = -LAMBDA_DRAG * dOmI_dt / (2 * alpha_ang)
    return OmI, OmQ


def rotated_quadratures(t, T, amp, phase):
    OmI, OmQ = drag_quadratures(t, T, amp)
    OmI_r = OmI * np.cos(phase) - OmQ * np.sin(phase)
    OmQ_r = OmI * np.sin(phase) + OmQ * np.cos(phase)
    return OmI_r, OmQ_r


def H_from_quadratures(OmI, OmQ):
    return 0.5 * OmI * (a_op + a_dag) - 0.5j * OmQ * (a_op - a_dag) + H_static


def ideal_H_of_t(amp, T, phase):
    def H_of_t(t):
        OmI_r, OmQ_r = rotated_quadratures(t, T, amp, phase)
        return H_from_quadratures(OmI_r, OmQ_r)
    return H_of_t


# ---- calibracion de amplitud (poblacion final exacta, sin decoherencia) ----

def unitary_rhs(t, psi, H_of_t):
    return -1j * (H_of_t(t) @ psi)


def simulate_unitary_population1(amp, T):
    psi0 = np.array([1, 0, 0], dtype=complex)
    H_of_t = ideal_H_of_t(amp, T, 0.0)
    sol = solve_ivp(unitary_rhs, [0, T], psi0, args=(H_of_t,), method='RK45',
                     rtol=1e-10, atol=1e-12)
    return np.abs(sol.y[1, -1]) ** 2


def calibrate_amp_x90(T):
    target_pop = np.sin(np.pi / 4) ** 2  # 0.5, para X_pi/2
    res = minimize_scalar(lambda amp: abs(simulate_unitary_population1(amp, T) - target_pop),
                           bounds=(1.0, 300.0), method='bounded',
                           options={'xatol': 1e-8})
    return res.x


AMP_X90 = calibrate_amp_x90(T_GATE_US)
print(f"[Calibracion] Amplitud X_pi/2 = {AMP_X90:.4f} rad/us "
      f"(poblacion final = {simulate_unitary_population1(AMP_X90, T_GATE_US):.8f})")

# full-scale fijo del DAC, atado al pico teorico de amplitud del experimento (bug 3.6)
_t_probe = np.linspace(0, T_GATE_US, 4000)
_OmI_probe, _OmQ_probe = drag_quadratures(_t_probe, T_GATE_US, AMP_X90)
FULL_SCALE = 1.15 * max(np.max(np.abs(_OmI_probe)), np.max(np.abs(_OmQ_probe)))
print(f"[Canal] Full-scale del DAC fijado a {FULL_SCALE:.4f} rad/us (14 bits)")

# =====================================================================
# 2. MODULO A: CANAL FISICO NO IDEAL (con estado causal persistente)
# =====================================================================

class Sim2RealChannel:
    """
    Desbalance IQ + skew, cuantizacion DAC de 14 bits (full-scale fijo), jitter de apertura,
    y filtro coaxial paso-bajo CAUSAL (bug 3.5: lfilter con estado zi propagado entre pulsos,
    nunca sosfiltfilt de fase cero).
    """

    def __init__(self, seed):
        self.dt_us = 1.0 / (SAMPLE_RATE_GSPS * 1e3)  # SAMPLE_RATE_GSPS GSa/s -> us por muestra
        nyq_mhz = 0.5 * SAMPLE_RATE_GSPS * 1e3
        self.b, self.a = butter(2, COAX_FC_MHZ / nyq_mhz, btype='low')
        zi0 = lfilter_zi(self.b, self.a)
        self.zi_I = zi0 * 0.0
        self.zi_Q = zi0 * 0.0
        self.rng = np.random.default_rng(seed)
        self.jitter_rms_us = JITTER_RMS_PS * 1e-6
        # Nota de convencion: el skew I/Q se especifica como fase a una LO de referencia de 5 GHz
        # (misma convencion que OMEGA_B en two_qubit_hil_dcg.py), convertido a un retardo temporal.
        self._skew_time_us = np.deg2rad(IQ_SKEW_DEG) / (TWO_PI * 5000.0)  # us

    def _quantize(self, x):
        levels = 2 ** DAC_BITS
        step = 2 * FULL_SCALE / levels
        return np.clip(np.round(x / step) * step, -FULL_SCALE, FULL_SCALE)

    def corrupted_H_of_t(self, amp, T, phase):
        n = max(int(round(T / self.dt_us)), 8)
        t_grid = np.arange(n) * self.dt_us
        OmI_r, OmQ_r = rotated_quadratures(t_grid, T, amp, phase)

        # desbalance de ganancia I/Q
        OmQ_r = OmQ_r * (1.0 + IQ_GAIN_IMBAL)
        # skew I/Q: pequeno retardo temporal de Q respecto de I
        OmQ_r = np.interp(t_grid - self._skew_time_us, t_grid, OmQ_r)

        # jitter de apertura: correccion de primer orden dx = dt_jitter * dx/dt (vectorizado, O(n))
        dOmI = np.gradient(OmI_r, self.dt_us)
        dOmQ = np.gradient(OmQ_r, self.dt_us)
        jitter = self.rng.normal(0.0, self.jitter_rms_us, size=n)
        OmI_j = OmI_r + jitter * dOmI
        OmQ_j = OmQ_r + jitter * dOmQ

        # cuantizacion DAC de 14 bits, full-scale fijo (bug 3.6)
        OmI_q = self._quantize(OmI_j)
        OmQ_q = self._quantize(OmQ_j)

        # filtro coaxial causal con estado persistente entre pulsos (bug 3.5)
        OmI_f, self.zi_I = lfilter(self.b, self.a, OmI_q, zi=self.zi_I)
        OmQ_f, self.zi_Q = lfilter(self.b, self.a, OmQ_q, zi=self.zi_Q)

        fI = interp1d(t_grid, OmI_f, kind='linear', fill_value='extrapolate', assume_sorted=True)
        fQ = interp1d(t_grid, OmQ_f, kind='linear', fill_value='extrapolate', assume_sorted=True)

        def H_of_t(t):
            return H_from_quadratures(fI(t), fQ(t))

        return H_of_t


# =====================================================================
# 3. MODULO C: TRANSMON DE 3 NIVELES (Duffing + Lindblad)
# =====================================================================

def lindblad_rhs(t, y, H_of_t):
    rho = y.reshape(DIM, DIM)
    H = H_of_t(t)
    drho = -1j * (H @ rho - rho @ H)
    for c in (c1, c2):
        drho += c @ rho @ c.conj().T - 0.5 * (c.conj().T @ c @ rho + rho @ c.conj().T @ c)
    return drho.reshape(-1)


def propagate_lindblad(rho0, H_of_t, T):
    sol = solve_ivp(lindblad_rhs, [0, T], rho0.reshape(-1), args=(H_of_t,),
                     method='RK45', rtol=1e-6, atol=1e-8)
    rho_f = sol.y[:, -1].reshape(DIM, DIM)
    return rho_f


# =====================================================================
# 4. clifford_decomposition.py: GRUPO DE CLIFFORD (24) -> Z - X_pi/2 - Z
# =====================================================================

def generate_octahedral_so3():
    mats = []
    for perm in permutations(range(3)):
        Pm = np.zeros((3, 3))
        for i, p in enumerate(perm):
            Pm[i, p] = 1.0
        for signs in product([1, -1], repeat=3):
            M = Pm @ np.diag(signs)
            if abs(np.linalg.det(M) - 1.0) < 1e-9:
                mats.append(M)
    uniq = []
    for M in mats:
        if not any(np.allclose(M, U, atol=1e-9) for U in uniq):
            uniq.append(M)
    assert len(uniq) == 24, f"Se esperaban 24 rotaciones propias, se obtuvieron {len(uniq)}"
    return uniq


def so3_to_su2(M):
    q = Rotation.from_matrix(M).as_quat()  # x,y,z,w
    x, y, z, w = q
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    return w * np.eye(2) - 1j * (x * X + y * Y + z * Z)


X90_SU2 = (1 / np.sqrt(2)) * np.array([[1, -1j], [-1j, 1]], dtype=complex)


def Rz(theta):
    return np.array([[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=complex)


def zxzxz_unitary(phi0, theta, phi2):
    return Rz(phi2) @ X90_SU2 @ Rz(theta) @ X90_SU2 @ Rz(phi0)


def decompose_to_zxzxz(U_target, n_restarts=10, seed=0):
    rng = np.random.default_rng(seed)

    def cost(params):
        U = zxzxz_unitary(*params)
        overlap = np.trace(U_target.conj().T @ U) / 2.0
        return 1.0 - np.abs(overlap)

    best = None
    for _ in range(n_restarts):
        x0 = rng.uniform(-np.pi, np.pi, 3)
        res = minimize(cost, x0, method='Nelder-Mead',
                        options={'xatol': 1e-12, 'fatol': 1e-14, 'maxiter': 8000})
        if best is None or res.fun < best.fun:
            best = res
        if best.fun < 1e-12:
            break
    return best.x, best.fun


print("[Clifford] Generando grupo octaedral (24 elementos) y decomposicion Z-X_pi/2-Z ...")
SO3_LIST = generate_octahedral_so3()
SU2_LIST = [so3_to_su2(M) for M in SO3_LIST]
DECOMP_LIST = []
max_residual = 0.0
for i, U in enumerate(SU2_LIST):
    angles, residual = decompose_to_zxzxz(U, seed=1000 + i)
    DECOMP_LIST.append(angles)
    max_residual = max(max_residual, residual)
print(f"[Clifford] {len(SU2_LIST)} elementos decompuestos. "
      f"Residuo maximo de fidelidad = {max_residual:.3e}")
assert max_residual < 1e-8, "La decomposicion Z-X_pi/2-Z no convergio para todos los elementos"

IDENTITY_SO3 = np.eye(3)


def find_so3_index(M, tol=1e-6):
    for i, U in enumerate(SO3_LIST):
        if np.allclose(M, U, atol=tol):
            return i
    raise ValueError("Matriz no encontrada en el grupo de 24 elementos (cierre de grupo violado)")


# =====================================================================
# 5. rb_core.py: ENSAMBLAJE Y SIMULACION DE UNA SECUENCIA RB
# =====================================================================

def run_one_sequence(m, seed, channel):
    """channel=None -> canal ideal (software). channel=Sim2RealChannel -> canal HIL degradado.
    Devuelve P0 = <0|rho_f|0> tras aplicar m Cliffords aleatorios + su inversion."""
    rng = np.random.default_rng(seed)
    idx_seq = rng.integers(0, 24, size=m)

    # Clifford de inversion: producto acumulado en SO(3), luego transpuesta (inversa ortogonal)
    P = IDENTITY_SO3.copy()
    for idx in idx_seq:
        P = SO3_LIST[idx] @ P
    P_inv = P.T
    inv_idx = find_so3_index(P_inv)

    full_idx_seq = list(idx_seq) + [inv_idx]

    rho = np.zeros((DIM, DIM), dtype=complex)
    rho[0, 0] = 1.0
    frame_phase = 0.0

    def physical_x90(phase):
        if channel is None:
            H_of_t = ideal_H_of_t(AMP_X90, T_GATE_US, phase)
        else:
            H_of_t = channel.corrupted_H_of_t(AMP_X90, T_GATE_US, phase)
        return propagate_lindblad(rho, H_of_t, T_GATE_US)

    for cidx in full_idx_seq:
        phi0, theta, phi2 = DECOMP_LIST[cidx]
        # Rz(phi0): virtual, sin costo fisico -- solo actualiza el marco
        frame_phase += phi0
        # X_pi/2 fisico #1, a la fase de marco actual
        rho = physical_x90(frame_phase)
        # Rz(theta): virtual
        frame_phase += theta
        # X_pi/2 fisico #2
        rho = physical_x90(frame_phase)
        # Rz(phi2): virtual -- no afecta P0 (diagonal en base Z), solo importa para el marco
        # de los pulsos fisicos de un Clifford futuro
        frame_phase += phi2

    return np.real(rho[0, 0])


# =====================================================================
# 6. run_rb.py: MONTE CARLO + AJUSTE
# =====================================================================

def exp_decay_fixed_B(m, A, p):
    return A * p ** m + 0.5


def fit_rb(m_arr, p0_mean, p0_sem):
    from scipy.optimize import curve_fit
    popt, pcov = curve_fit(exp_decay_fixed_B, m_arr, p0_mean, p0=[0.5, 0.999],
                            sigma=p0_sem, absolute_sigma=True, maxfev=20000)
    A, p = popt
    perr = np.sqrt(np.diag(pcov))
    r_clifford = (1 - p) / 2
    r_clifford_err = perr[1] / 2
    return A, p, perr[0], r_clifford, r_clifford_err


if __name__ == "__main__":
    t0 = time.time()
    results = {"ideal": {}, "hil": {}}

    for label, use_channel in (("ideal", False), ("hil", True)):
        print(f"\n=== Canal: {label.upper()} ===")
        for m in M_LIST:
            p0_vals = []
            for k in range(K_REPS):
                seed = BASE_SEED + 1000 * m + k
                channel = Sim2RealChannel(seed=seed + 500000) if use_channel else None
                p0 = run_one_sequence(m, seed, channel)
                p0_vals.append(p0)
            p0_vals = np.array(p0_vals)
            mean = p0_vals.mean()
            sem = p0_vals.std(ddof=1) / np.sqrt(K_REPS)
            results[label][m] = {"mean": mean, "sem": sem, "raw": p0_vals.tolist()}
            print(f"  m={m:>3d}  P0_mean={mean:.6f}  SEM={sem:.2e}  "
                  f"[{time.time()-t0:6.1f}s]")

    m_arr = np.array(M_LIST, dtype=float)

    A_i, p_i, pA_i, r_i, r_i_err = fit_rb(
        m_arr, np.array([results["ideal"][m]["mean"] for m in M_LIST]),
        np.array([results["ideal"][m]["sem"] for m in M_LIST]))

    A_h, p_h, pA_h, r_h, r_h_err = fit_rb(
        m_arr, np.array([results["hil"][m]["mean"] for m in M_LIST]),
        np.array([results["hil"][m]["sem"] for m in M_LIST]))

    gap = r_h - r_i
    gap_err = np.sqrt(r_i_err ** 2 + r_h_err ** 2)
    sigma_gap = gap / gap_err if gap_err > 0 else float('nan')

    print("\n" + "=" * 70)
    print("RESULTADOS FINALES (K={}, m in {})".format(K_REPS, M_LIST))
    print("=" * 70)
    print(f"Canal IDEAL : A={A_i:.5f}  p={p_i:.8f}  r_Clifford = {r_i:.4e} +/- {r_i_err:.2e}")
    print(f"Canal HIL   : A={A_h:.5f}  p={p_h:.8f}  r_Clifford = {r_h:.4e} +/- {r_h_err:.2e}")
    print(f"Sim2Real Gap (nivel algoritmo) = {gap:.4e} +/- {gap_err:.2e}  ({sigma_gap:.2f} sigma)")
    print(f"\nTiempo total de ejecucion: {time.time()-t0:.1f} s")

    with open("/home/claude/rb_results.json", "w") as f:
        json.dump({
            "params": {
                "ALPHA_MHZ": ALPHA_MHZ, "T1_US": T1_US, "T2S_US": T2S_US,
                "T_GATE_US": T_GATE_US, "SAMPLE_RATE_GSPS": SAMPLE_RATE_GSPS,
                "DAC_BITS": DAC_BITS, "JITTER_RMS_PS": JITTER_RMS_PS,
                "COAX_FC_MHZ": COAX_FC_MHZ, "IQ_GAIN_IMBAL": IQ_GAIN_IMBAL,
                "IQ_SKEW_DEG": IQ_SKEW_DEG, "LAMBDA_DRAG": LAMBDA_DRAG,
                "AMP_X90_rad_per_us": AMP_X90, "FULL_SCALE": FULL_SCALE,
                "M_LIST": M_LIST, "K_REPS": K_REPS, "BASE_SEED": BASE_SEED,
            },
            "results": results,
            "fit_ideal": {"A": A_i, "p": p_i, "r_Clifford": r_i, "r_Clifford_err": r_i_err},
            "fit_hil": {"A": A_h, "p": p_h, "r_Clifford": r_h, "r_Clifford_err": r_h_err},
            "sim2real_gap": {"value": gap, "err": gap_err, "sigma": sigma_gap},
        }, f, indent=2)
    print("Resultados guardados en rb_results.json")
