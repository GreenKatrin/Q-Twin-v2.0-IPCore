# Q-Twin v2.3 Technical Addendum: Scalar Sector & Master Calibration

**Document Status:** Public Technical Addendum (v2.3 Release)  
**Parent DOI:** 10.5281/zenodo.22694596  

---

### 1. Falsification of Free Uncoupled BKO Exponentials
Numerical integration of $V(\phi_1, \phi_2) = -V_1 e^{-c_1 \phi_1} - V_2 e^{-c_2 \phi_2}$ on the physical attractor confirms a mild turn ($|\dot{\theta}/H|_{\text{peak}} \approx 0.396$) and $m_s^2/H^2 \approx -1.73$. The uncoupled model is formally ruled out as a source for scale-invariant scalar perturbations ($n_s = 0.963$).

### 2. Ridge Potential Benchmark & AXI4-Lite Mapping
The scalar sector adopts $V(\sigma, s) = -V_0 e^{-c\sigma}(1 + \frac{1}{2}M^2 s^2)$ as a benchmark. The entropic mass $m_{s,\text{eff}}^2/H^2 = -50.65$ ($n_s = 0.963 \pm 0.004$) is sustained with $M^2 \approx 18.2523$.

| Theoretical Parameter | Símbolo Cosmológico | Registro AXI4-Lite | Dirección Base | Configuración Firmware |
| :--- | :--- | :--- | :--- | :--- |
| **Rigidez de Fondo** | $c = \sqrt{11.55} \approx 3.3985$ | `Qn_PHASE_CTRL` | `0xA000_0000` | NCO $\varepsilon_{\text{NL}} = 12.5\text{ MHz}$ |
| **Masa de Cresta** | $M^2 \approx 18.2523$ | `CROSSTALK_COMP` | `0xA000_0100` | Matriz $C^{-1}$ + $J_{12}$ |
| **Saturación Cuártica** | $\varepsilon_{\text{sat}} = 0.140$ | `SMC_SAT_EPSILON` | `0xA000_0200` | Capa límite de Fock |
| **Disipación Lindblad** | $\kappa_{\text{eff}} = 1.0\text{ MHz}$ | `KAPPA_EFF_DISP` | `0xA000_0300` | Tasa de extracción de traza |
