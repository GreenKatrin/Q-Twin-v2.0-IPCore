# RB Pipeline — Postmortem v2 (cierre del Vector 1)

## 0. Contexto y alcance de este documento

El postmortem original (`RB_Pipeline_PostMortem.md`) documentaba un pipeline modular
(`drag_pulse_engine.py`, `sim2real_channel.py`, `transmon_simulator.py`,
`clifford_decomposition.py`, `rb_core.py`, `run_rb.py`) y una tabla de resultados. Al revisar
todo el historial de git de este repositorio se confirmó que **esos archivos nunca llegaron a
comitearse** — solo el documento y los números quedaron públicos.

Este v2 reconstruye el pipeline completo desde cero, en un único archivo autocontenido
(`benchmarks/run_rb_suite.py`), e incorpora explícitamente las correcciones de bug ya
documentadas en v1. Los resultados de este documento provienen de una ejecución real de ese
script (Monte Carlo completo, K=20, m∈{1,2,4,8,16,32,64}); no hay números precalculados ni
copiados de v1.

## 1. Correcciones de v1 incorporadas explícitamente

| # | Corrección | Dónde se aplica en `run_rb_suite.py` |
|---|---|---|
| 3.1 | Signo del término DRAG en el Hamiltoniano: `-i/2 · Ω_Q(t) · (a - a†)` | `H_from_quadratures` |
| 3.2 | Factor 2 en `Ω_Q(t) = -λ · dΩ_I/dt / (2α)` | `drag_quadratures` |
| 3.3 | Tasa de muestreo convergida a 10 GSa/s | `SAMPLE_RATE_GSPS` |
| 3.5 | Filtrado causal con estado persistente (nunca `filtfilt`) | `Sim2RealChannel` (`zi_I`, `zi_Q` propagados entre pulsos) |
| 3.6 | Full-scale del DAC fijo, no recalculado por pulso | `FULL_SCALE`, atado al pico de amplitud de X_π/2 |
| 3.7 | Semilla independiente por repetición | `seed = BASE_SEED + 1000*m + k` |
| 3.8 | Ajuste ponderado, B=0.5 fijo | `fit_rb` (pesos = SEM, `exp_decay_fixed_B`) |

Las secciones 3.4 (resolución de la grilla de calibración) y 3.9 (ambigüedad de definición de
SNR) del postmortem v1 no aplican directamente a este script: la calibración usa optimización
continua (`minimize_scalar`) en vez de grilla, y no se calcula ningún SINAD en este pipeline.

## 2. Parámetros físicos — cuáles estaban documentados y cuáles se asumieron aquí

**Ya establecidos en el repo** (reutilizados para consistencia):
- Anarmonicidad α = −300 MHz (misma convención que `ALPHA_A` en `two_qubit/two_qubit_hil_dcg.py`)

**Asumidos en este script** (no había un valor de referencia documentado en v1 ni en otro
archivo del repo — quedan declarados explícitamente en el encabezado de
`run_rb_suite.py` para que puedan corregirse si hay datos de hardware real):
- T1 = 150 µs, T2* = 100 µs (transmón moderno de alta coherencia)
- Desbalance de ganancia I/Q = 2%, skew I/Q ≈ 0.56 ps (referido a un LO de 5 GHz)
- Jitter de apertura = 1.5 ps RMS, DAC de 14 bits, filtro coaxial causal a 350 MHz

Si se dispone de valores medidos de T1/T2* del hardware de referencia del proyecto, el
Sim2Real Gap reportado abajo debe recalcularse con esos valores.

## 3. Arquitectura de la compilación de Clifford

El grupo de Clifford de un cúbit (24 elementos) se genera como el grupo de rotaciones propias
del octaedro (SO(3), orden 24) y se levanta a SU(2) vía la representación de cuaterniones. Cada
elemento se decompone numéricamente en la forma canónica

```
C = Rz(φ2) · X_π/2 · Rz(θ) · X_π/2 · Rz(φ0)
```

con `Rz` puramente virtual (sin costo de tiempo ni acción física — es diagonal en la base Z, por
lo que no afecta P₀) y exactamente 2 pulsos físicos X_π/2 por Clifford. La decomposición se
resuelve por optimización no lineal (Nelder-Mead, 10 reinicios aleatorios); el residuo máximo de
fidelidad sobre los 24 elementos fue **2.2 × 10⁻¹⁶** (precisión de máquina).

Una secuencia RB de longitud m se compone de m Cliffords aleatorios más el Clifford de
inversión (calculado como la transpuesta del producto acumulado en SO(3), que por cierre de
grupo es siempre uno de los 24 elementos) → 2(m+1) pulsos físicos concatenados, con el frame de
fase Z acumulado de forma continua a lo largo de toda la secuencia.

## 4. Resultados (Monte Carlo real, K=20, m∈{1,2,4,8,16,32,64})

| Canal | A | p | r_Clifford |
|---|---|---|---|
| Ideal (software) | 0.49989 | 0.99964033 | (1.798 ± 0.014) × 10⁻⁴ |
| HIL (degradado) | 0.49984 | 0.99928689 | (3.566 ± 0.227) × 10⁻⁴ |

**Sim2Real Gap = Δr_Clifford = (1.767 ± 0.227) × 10⁻⁴ — significancia 7.77σ**

La tasa de error por compuerta de Clifford prácticamente se duplica al pasar del canal ideal al
canal HIL degradado (jitter de apertura, cuantización de 14 bits, desbalance I/Q y memoria del
filtro coaxial causal de 350 MHz), con una diferencia estadísticamente inequívoca.

Los datos crudos de las 280 secuencias simuladas (140 por canal) y los parámetros completos del
Monte Carlo están en `benchmarks/rb_results.json`.

## 5. Nota de higiene del repositorio

`two_qubit_hil.py` (raíz del repositorio) fue eliminado en el mismo commit que este documento:
su función de reporte final imprimía valores fijos en el código en vez de recomputarlos desde la
propagación real, contradiciendo la disciplina de verificación del resto del proyecto. El motor
canónico para el sistema de dos cúbits acoplados sigue siendo
`two_qubit/two_qubit_hil_dcg.py`, que sí deriva cada número reportado de una ejecución real.

## 6. Estado del Vector 1

Con este resultado, el Vector 1 (digital twin HIL de control cuántico, 1 y 2 cúbits) queda
cerrado: pipeline de calibración DRAG, canal Sim2Real, emulador de transmón con Lindblad,
extensión a 2 cúbits con crosstalk ZZ, y ahora el Randomized Benchmarking con Sim2Real Gap
medido y estadísticamente significativo.
