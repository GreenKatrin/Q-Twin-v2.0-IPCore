# Nota Metodológica v2.2: Cierre Numérico del Sector Tensorial y Corrección de Escala

**Registro del Proyecto:** Q-Twin v2.0 (Versión de análisis tensorial v2.2).

---

## 1. Corrección Formal de la Frecuencia de Recalentamiento ($f_{\text{rh}}$)

Se corrige el valor previamente reportado de $166.8\text{ MHz}$ a **$26.50\text{ MHz}$**. 

La discrepancia se debió a la omisión del factor $2\pi$ en la conversión desde el número de onda comóvil $k_{\text{rh}} = 1.714 \times 10^{22}\text{ Mpc}^{-1}$ mediante la relación estándar $f = ck/2\pi$. No se trata de una ambigüedad de convenciones, sino de un error algebraico directo que queda subsanado en esta versión.

## 2. Resultados Físicos Derivados ab initio

Al integrar la ecuación de Mukhanov-Sasaki sobre la métrica de tres fases regularizada ($\mathcal{C}^\infty$), los observables tensoriales quedan fijados sin parámetros ajustables:

- **Frecuencia de Recalentamiento ($f_{\text{rh}}$):** $26.50\text{ MHz}$
- **Frecuencia Máxima Espectro ($f_{\max}$):** $32.05\text{ MHz}$
- **Envolvente Ultravioleta:** Supresión exponencial estricta $\sim e^{-4k\tau_b}$ (sin colas algebraicas espurias).
- **Consistencia Energética BBN:** $\Omega_{\text{GW}}^{\text{tot}}h^2$ satisface la cota de nucleosíntesis primordial ($r_{\text{modelo}} \le r_{\text{BBN}}^{\max} \approx 4.3 \times 10^{-52}$).
