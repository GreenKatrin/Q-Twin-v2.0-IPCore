# Q-Twin v2.3 Technical Addendum: Scalar Sector & Master Calibration

**Document Status:** Public Technical Addendum (v2.3 Release)  
**Parent DOI:** 10.5281/zenodo.22694596  

---

### 1. Estado del Modelo BKO de Exponenciales Libres
El análisis numérico del potencial de dos exponenciales desacopladas $V(\phi_1, \phi_2) = -V_1 e^{-c_1 \phi_1} - V_2 e^{-c_2 \phi_2}$ se clasifica formalmente como **inconcluso / no verificado**. Las formulaciones del script de integración iniciales presentaron inconsistencias energéticas en las condiciones iniciales ($\rho_{\text{total}} \le 0$), impidiendo extraer un perfil numérico convergente sobre el atractor.

### 2. Adopción del Potencial de Cresta como Modelo de Referencia
Ante la ausencia de un cálculo cerrado para el modelo libre, el sector escalar adopta el potencial de cresta inestable $V(\sigma, s) = -V_0 e^{-c\sigma}(1 + \frac{1}{2}M^2 s^2)$ como un **benchmark calibrado por software** para emulación HIL.

- **Parámetro de Cresta:** $M^2 \approx 18.2523$ (obtenido por inversión para $n_s = 0.963 \pm 0.004$).
- **Masa Entrópica Verificada:** $m_{s,\text{eff}}^2/H^2 = -50.65$ (integración continua y estable con `DOP853`, status 0).
- **Mapeo AXI4-Lite:** El parámetro $M^2$ y la saturación cuártica se controlan mediante los registros `CROSSTALK_COMP` (`0xA000_0100`) y `SMC_SAT_EPSILON` (`0xA000_0200`).
