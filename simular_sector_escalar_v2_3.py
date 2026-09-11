import numpy as np
from scipy.integrate import solve_ivp

w_eff = 2.85
c = np.sqrt(3.0 * (1.0 + w_eff))  # c ≈ 3.39853
M2 = 18.25225225
V0 = 1.0

def ridge_derivatives(t, y):
    sigma, dsigma, s, ds = y
    exp_factor = np.exp(-c * sigma)
    V_val = -V0 * exp_factor * (1.0 + 0.5 * M2 * s**2)
    dV_dsigma = c * V0 * exp_factor * (1.0 + 0.5 * M2 * s**2)
    dV_ds = -V0 * exp_factor * M2 * s
    kinetic = 0.5 * (dsigma**2 + ds**2)
    rho_total = kinetic + V_val
    H = -np.sqrt(max(rho_total, 1e-15) / 3.0)
    ddsigma = -3.0 * H * dsigma - dV_dsigma
    dds = -3.0 * H * ds - dV_ds
    return [dsigma, ddsigma, ds, dds]

t_start = -50.0
t_end = -0.05
coeff = (2.0 / (c**2 * V0)) * (1.0 - 6.0 / c**2) / (t_start**2)
sigma_0 = - (1.0 / c) * np.log(coeff)
dsigma_0 = 2.0 / (c * t_start)
s_0 = 1e-5
ds_0 = 0.0

y0 = [sigma_0, dsigma_0, s_0, ds_0]
t_eval = np.linspace(t_start, t_end, 1000)
sol = solve_ivp(ridge_derivatives, [t_start, t_end], y0, t_eval=t_eval, method='DOP853', rtol=1e-10, atol=1e-12)

sigma = sol.y[0]
dsigma = sol.y[1]
s = sol.y[2]

V_val_in = -V0 * np.exp(-c * sigma[0])
rho_in = 0.5 * (dsigma[0]**2) + V_val_in
H_in = -np.sqrt(max(rho_in, 1e-15) / 3.0)
V_ss_in = -V0 * np.exp(-c * sigma[0]) * M2

V_val_out = -V0 * np.exp(-c * sigma[-1])
rho_out = 0.5 * (dsigma[-1]**2) + V_val_out
H_out = -np.sqrt(max(rho_out, 1e-15) / 3.0)
V_ss_out = -V0 * np.exp(-c * sigma[-1]) * M2

print(f"m_s^2/H^2 inicial (t={t_start}): {V_ss_in / (H_in**2):.4f}")
print(f"m_s^2/H^2 final   (t={t_end}):  {V_ss_out / (H_out**2):.4f}")
print(f"Status DOP853: {sol.status}")
