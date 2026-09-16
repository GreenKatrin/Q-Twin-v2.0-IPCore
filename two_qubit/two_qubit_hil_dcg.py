"""
Q-Twin HIL: Emulador de 9 Niveles para Transmones Acoplados
============================================================
Consolida, con computo real (sin resultados fijos en el codigo):

  1. Acoplamiento estatico zeta_ZZ, via diagonalizacion exacta del Hamiltoniano de 9 niveles.
  2. Perturbacion dinamica sobre el Target durante una compuerta X_pi/2 sobre el Control,
     con un pulso Gaussiano simple, via propagacion exacta por pasos.
  3. Mitigacion DCG (Dynamically Corrected Gates, Watanabe et al., arXiv:2309.13927):
     optimizacion de la envolvente del pulso para anular las integrales de Magnus de
     primer orden en el marco de "toggling", y verificacion de que reduce la perturbacion
     medida en (2).

Cada numero impreso al final proviene de una ejecucion real de las funciones de este
archivo. No hay resultados precalculados ni hardcodeados en ninguna rama del codigo.

Limitaciones conocidas (documentadas explicitamente, no ocultas):
  - La optimizacion DCG requiere permanecer en el regimen perturbativo (Omega_max << |alpha_A|).
    Un X_pi completo en 20 ns viola esta condicion con estos parametros; por eso se usa
    X_pi/2 en 40 ns, replicando el regimen validado experimentalmente por Watanabe et al.
  - El ansatz DCG usado (2 parametros, con restriccion de positividad) no lleva las integrales
    de Magnus exactamente a cero -- las deja en el orden de ~0.02. Es una mitigacion real y
    medible, no una cancelacion perfecta.
  - Los parametros fisicos (J, Delta, alpha_A, alpha_B) son los de este modelo de trabajo;
    no han sido contrastados contra una medicion de hardware real.
"""

import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize, minimize_scalar

# =====================================================================
# 1. PARAMETROS FISICOS Y ESPACIO DE HILBERT (9 niveles = 3x3)
# =====================================================================

J = 3.0            # MHz, acoplamiento de intercambio
DELTA = 250.0       # MHz, detuning Control-Target
ALPHA_A = -300.0    # MHz, anarmonicidad del Control
ALPHA_B = -320.0    # MHz, anarmonicidad del Target
OMEGA_B = 5000.0    # MHz, frecuencia base del Target (referencia arbitraria)
OMEGA_A = OMEGA_B + DELTA

DIM = 3
TWO_PI = 2 * np.pi


def operador_aniquilacion(dim=DIM):
    a = np.zeros((dim, dim))
    for n in range(1, dim):
        a[n - 1, n] = np.sqrt(n)
    return a


def hamiltoniano_local(omega, alpha, dim=DIM):
    """H_local = 2*pi*[omega*N + (alpha/2) N(N-1)], en rad/us."""
    a = operador_aniquilacion(dim)
    n_op = a.T @ a
    return TWO_PI * (omega * n_op + (alpha / 2.0) * (n_op @ (n_op - np.eye(dim)))), a


# Construccion de operadores en el espacio conjunto (9x9)
H_A_local, a = hamiltoniano_local(OMEGA_A, ALPHA_A)
H_B_local, b = hamiltoniano_local(OMEGA_B, ALPHA_B)
I3 = np.eye(DIM)
a_dag, b_dag = a.T, b.T

A_op, A_dag = np.kron(a, I3), np.kron(a_dag, I3)
B_op, B_dag = np.kron(I3, b), np.kron(I3, b_dag)
DRIVE_OP = np.kron(a + a_dag, I3)   # cuadratura de dipolo sobre el Control

H0_STATIC = (
    np.kron(H_A_local, I3)
    + np.kron(I3, H_B_local)
    + TWO_PI * J * (A_dag @ B_op + A_op @ B_dag)
)

IDX_00, IDX_01, IDX_10, IDX_11 = 0, 1, DIM, DIM + 1


# =====================================================================
# 2. VALIDACION ESTATICA (DIAGONALIZACION EXACTA)
# =====================================================================

def extraer_zz_estatico(H0=H0_STATIC):
    evals, evecs = np.linalg.eigh(H0)
    idx = {
        "00": np.argmax(np.abs(evecs[IDX_00, :])),
        "01": np.argmax(np.abs(evecs[IDX_01, :])),
        "10": np.argmax(np.abs(evecs[IDX_10, :])),
        "11": np.argmax(np.abs(evecs[IDX_11, :])),
    }
    # H0 esta construido en rad/us (TWO_PI incluido, requerido por el propagador dinamico);
    # se divide entre TWO_PI aqui para reportar las energias en MHz (frecuencia ordinaria).
    E = {k: evals[i] / TWO_PI for k, i in idx.items()}
    zeta_zz = E["11"] - E["10"] - E["01"] + E["00"]
    return E, zeta_zz


# =====================================================================
# 3. PROPAGACION DINAMICA (propagador exacto por pasos)
# =====================================================================

def propagar_pulso(envolvente_fn, T, n_steps=8000, omega_drive=OMEGA_A):
    """
    Evoluciona Control=|0>, Target=(|0>+|1>)/sqrt(2) bajo H0_STATIC + drive resonante
    sobre el Control. Devuelve, en cada paso: tiempo, poblacion del Control en |1>,
    y la fase de la coherencia reducida del Target (para extraer su frecuencia
    instantanea despues).
    """
    dt = T / n_steps
    psi = np.zeros(DIM * DIM, dtype=complex)
    psi[0 * DIM + 0] = 1 / np.sqrt(2)
    psi[0 * DIM + 1] = 1 / np.sqrt(2)

    ts = np.zeros(n_steps + 1)
    fase_target = np.zeros(n_steps + 1)
    pop_control_1 = np.zeros(n_steps + 1)

    for k in range(n_steps + 1):
        t = k * dt
        ts[k] = t
        rho = np.outer(psi, psi.conj()).reshape(DIM, DIM, DIM, DIM)
        rho_B = np.einsum('ijik->jk', rho)          # traza parcial sobre el Control
        fase_target[k] = np.angle(rho_B[0, 1])
        pop_control_1[k] = np.abs(psi[DIM + 0]) ** 2 + np.abs(psi[DIM + 1]) ** 2

        if k < n_steps:
            t_mid = t + dt / 2
            omega_t = envolvente_fn(t_mid)
            H_drive = TWO_PI * omega_t * np.cos(TWO_PI * omega_drive * t_mid) * DRIVE_OP
            psi = expm(-1j * (H0_STATIC + H_drive) * dt) @ psi

    return ts, fase_target, pop_control_1


def rango_fluctuacion(ts, fase_target):
    fase_unwrapped = np.unwrap(fase_target)
    freq_inst = -np.gradient(fase_unwrapped, ts) / TWO_PI
    return freq_inst.max() - freq_inst.min()


# =====================================================================
# 4. PULSO GAUSSIANO DE REFERENCIA (calibrado a X_pi/2 por poblacion real)
# =====================================================================

def calibrar_gaussiano_xpi2(T, sigma_frac=1 / 6.0, n_steps_calib=3000):
    sigma = T * sigma_frac
    tc = T / 2

    def envolvente(t, omega0):
        return omega0 * np.exp(-(t - tc) ** 2 / (2 * sigma ** 2))

    def poblacion_final(omega0):
        ts, _, pop = propagar_pulso(lambda t: envolvente(t, omega0), T, n_steps=n_steps_calib)
        return pop[-1]

    res = minimize_scalar(lambda w: abs(poblacion_final(w) - 0.5), bounds=(1, 80), method='bounded')
    omega0_opt = res.x
    return lambda t: envolvente(t, omega0_opt), omega0_opt


# =====================================================================
# 5. PULSO DCG OPTIMIZADO (Watanabe et al.) -- ansatz unipolar
# =====================================================================

def optimizar_dcg_xpi2(T, target_theta=np.pi / 2, n_pts=2000):
    ts_fit = np.linspace(0, T, n_pts)

    def omega_x(t, a0, a2):
        tc = t - T / 2
        return (a0 + a2 * tc ** 2) * np.cos(np.pi * tc / T) ** 2

    def costo(params):
        a0, a2 = params
        Ox = omega_x(ts_fit, a0, a2)
        Theta = TWO_PI * np.concatenate([[0], np.cumsum((Ox[1:] + Ox[:-1]) / 2 * np.diff(ts_fit))])
        c_fid = abs(Theta[-1] - target_theta)
        c_rob = (1 / T) * (
            abs(np.trapezoid(np.cos(Theta), ts_fit)) + abs(np.trapezoid(np.sin(Theta), ts_fit))
        )
        c_pos = np.sum(np.clip(-Ox, 0, None) ** 2) * 50.0   # fuerza envolvente >= 0 (pulso fisico)
        w = 0.998
        return w * c_fid + (1 - w) * c_rob + c_pos

    x0 = [target_theta / (TWO_PI * T), 0.0]
    res = minimize(costo, x0=x0, method='Nelder-Mead',
                    options={'xatol': 1e-9, 'fatol': 1e-14, 'maxiter': 10000})
    a0_opt, a2_opt = res.x

    Ox_final = omega_x(ts_fit, a0_opt, a2_opt)
    Theta_final = TWO_PI * np.concatenate([[0], np.cumsum((Ox_final[1:] + Ox_final[:-1]) / 2 * np.diff(ts_fit))])
    diagnostico = {
        "a0": a0_opt, "a2": a2_opt,
        "omega_min": Ox_final.min(), "omega_max": Ox_final.max(),
        "theta_final": Theta_final[-1],
        "int_cos": np.trapezoid(np.cos(Theta_final), ts_fit),
        "int_sin": np.trapezoid(np.sin(Theta_final), ts_fit),
    }
    return lambda t: omega_x(t, a0_opt, a2_opt), diagnostico


# =====================================================================
# 6. PIPELINE PRINCIPAL
# =====================================================================

def main():
    print("=" * 70)
    print("[1] LINEA BASE ESTATICA (diagonalizacion exacta, 9 niveles)")
    print("=" * 70)
    E, zeta_zz_static = extraer_zz_estatico()
    for k, v in E.items():
        print(f"  E_{k} = {v:.4f} MHz")
    print(f"  --> zeta_ZZ (estatico) = {zeta_zz_static:+.4f} MHz\n")

    T_PULSE = 0.040  # 40 ns, regimen validado (Watanabe et al. usan el mismo orden de magnitud)

    print("=" * 70)
    print(f"[2] PULSO GAUSSIANO SIMPLE (X_pi/2, T={T_PULSE*1000:.0f} ns)")
    print("=" * 70)
    env_gauss, omega0_gauss = calibrar_gaussiano_xpi2(T_PULSE)
    ts_g, fase_g, pop_g = propagar_pulso(env_gauss, T_PULSE)
    rango_g = rango_fluctuacion(ts_g, fase_g)
    print(f"  Amplitud calibrada: {omega0_gauss:.3f} MHz")
    print(f"  Poblacion final Control en |1> (esperado ~0.5): {pop_g[-1]:.4f}")
    print(f"  --> Fluctuacion del Target: {rango_g:.4f} MHz\n")

    print("=" * 70)
    print(f"[3] MITIGACION DCG (Watanabe et al., arXiv:2309.13927)")
    print("=" * 70)
    env_dcg, diag = optimizar_dcg_xpi2(T_PULSE)
    ts_d, fase_d, pop_d = propagar_pulso(env_dcg, T_PULSE)
    rango_d = rango_fluctuacion(ts_d, fase_d)
    print(f"  Coeficientes optimizados: a0={diag['a0']:.4f} MHz, a2={diag['a2']:.4f}")
    print(f"  Omega_x: min={diag['omega_min']:.4f} MHz, max={diag['omega_max']:.4f} MHz "
          f"(|alpha_A|={abs(ALPHA_A):.0f} MHz)")
    print(f"  Theta(T) = {diag['theta_final']:.5f} rad (objetivo pi/2={np.pi/2:.5f})")
    print(f"  Integrales de Magnus residuales: cos={diag['int_cos']:.4f}, sin={diag['int_sin']:.4f}")
    print(f"  Poblacion final Control en |1> (esperado ~0.5): {pop_d[-1]:.4f}")
    print(f"  --> Fluctuacion del Target: {rango_d:.4f} MHz\n")

    print("=" * 70)
    print("[4] RESUMEN")
    print("=" * 70)
    print(f"  zeta_ZZ estatico:              {zeta_zz_static:+.4f} MHz")
    print(f"  Fluctuacion dinamica (Gauss):  {rango_g:.4f} MHz")
    print(f"  Fluctuacion dinamica (DCG):    {rango_d:.4f} MHz")
    mitigado = rango_d < rango_g
    print(f"  DCG reduce la perturbacion respecto al Gaussiano: {mitigado}")
    print(f"  DCG lleva la perturbacion por debajo del zeta_ZZ estatico: {rango_d < zeta_zz_static}")


if __name__ == "__main__":
    main()
