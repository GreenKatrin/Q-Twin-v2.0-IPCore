# Q-Twin v3.3 — Nota Metodológica Consolidada

## Alcance de esta versión

Esta versión consolida el cierre completo de dos vectores del proyecto Q-Twin, ambos con
código ejecutable y resultados reproducibles (sin valores precalculados ni hardcodeados en
ninguna rama):

- **Vector 1 — Digital Twin HIL de Control Cuántico** (1 y 2 cúbits, cerrado)
- **Vector 2 — Memoria Asociativa Cuántica** (N=3 y N=8, cerrado)

Los Vectores 2 (gravedad analógica) y 3 (gravedad cuántica fundamental) de versiones
anteriores permanecen formalmente descartados por falta de anclaje analítico/experimental
(ver retractación en v2.x). La propuesta de extender Q-Twin hacia la simulación de
consciencia (síndrome de savant, teoría Orch-OR) fue evaluada y rechazada por el mismo
criterio: no existe un puente matemático entre la física de transmones superconductores y
la neurobiología.

## Vector 1: Digital Twin HIL de Control Cuántico

| Resultado | Valor |
|---|---|
| Acoplamiento estático ζ_ZZ (2 cúbits, diagonalización exacta de 9 niveles) | +0.389 MHz |
| Perturbación dinámica durante X_π/2 (pulso Gaussiano) | 0.578 MHz |
| Mitigación DCG (Watanabe et al., arXiv:2309.13927) | 0.331 MHz |
| Randomized Benchmarking, r_Clifford ideal (K=20, m∈{1..64}) | (1.798 ± 0.014) × 10⁻⁴ |
| Randomized Benchmarking, r_Clifford HIL (canal degradado) | (3.566 ± 0.227) × 10⁻⁴ |
| **Sim2Real Gap** | **(1.767 ± 0.227) × 10⁻⁴ (7.77σ)** |

Parámetros del canal HIL: DAC de 14 bits, jitter de apertura 1.5 ps RMS, filtro coaxial
causal a 350 MHz, desbalance I/Q 2%. T1=150 µs, T2*=100 µs (valores representativos
asumidos para un transmón moderno; no derivados de hardware real de referencia — deben
recalcularse si se dispone de valores medidos).

Código: `benchmarks/run_rb_suite.py`, `two_qubit/two_qubit_hil_dcg.py`.
Datos crudos: `benchmarks/rb_results.json` (280 secuencias simuladas).

**Nota de higiene de repositorio:** se eliminó `two_qubit_hil.py` (presente en versiones
anteriores del repositorio GitHub, no en releases previas de Zenodo), cuyo reporte final
imprimía valores fijos en el código en vez de recomputarlos desde la propagación real.

## Vector 2: Memoria Asociativa Cuántica (recall de patrones tipo Hopfield)

Arquitectura: Hamiltoniano de Ising con acoplamientos de Hebb $J_{ij}$, recall vía
*reverse annealing* con campo de sesgo local hacia el patrón corrompido y un pulso de
campo transverso a mitad de rampa ($\Gamma(s)=\Gamma_\text{bump}\cdot 4s(1-s)$) que habilita
el tunelamiento necesario para corregir bits volteados. T1=150 µs, T2*=100 µs (mismos
valores que el Vector 1, mismo transmón de referencia).

| Experimento | Patrones | Sonda | Óptimo (T*, Γ_bump*) | Fidelidad final |
|---|---|---|---|---|
| N=3 | 2 (ortogonales) | distancia Hamming 1 | 6.058 µs, 0.1682 MHz | **0.9325** |
| N=8 v1 | 3 (Hadamard, ortogonales) | distancia Hamming 2 | 10.292 µs, 0.1292 MHz | 0.3559* |
| N=8 v2 | 3 (no ortogonales) | distancia Hamming 2 | 9.554 µs, 0.1309 MHz | **0.5749** |

\* N=8 v1: la fidelidad de 0.3559 no refleja solo pérdida por decoherencia. Se encontró que
el patrón objetivo y el complemento de otro patrón almacenado son EXACTAMENTE degenerados
en el espectro final (0.3559 cada uno) — una propiedad estructural de usar patrones
mutuamente ortogonados (filas de Hadamard), que fuerza distancia de Hamming N/2 entre
cualquier par de patrones o complementos. N=8 v2 corrige esto usando patrones no
ortogonales con distancias heterogéneas (3,4,5) y una sonda elegida por búsqueda
exhaustiva para maximizar el margen frente a cualquier atractor competidor — resultado:
fidelidad de recall 62% mayor (0.575 vs 0.356), sin empate.

**Corrección metodológica importante (N=8):** la propuesta original asumía que N=8
requería un motor MPDO (estimando ~34 GB de memoria) para evitar construir el
superoperador de Lindblad vectorizado completo (65536×65536). Esa construcción nunca es
necesaria: la ecuación de Lindblad se integra evaluando su lado derecho directamente sobre
matrices de densidad de 256×256, exactamente igual que en N=3. Además, se verificó que
`export_mpdo_tensors.py` (el único archivo del repositorio con "mpdo" en el nombre) es un
serializador de datos de la aplicación cosmológica retractada (v2.x), no un motor de
evolución temporal de tensor networks — no existe en este repositorio una MPDO reutilizable.
Escalar más allá de N≈15-20 sí requeriría un motor de ese tipo, aún no construido.

Código: `benchmarks/quantum_hopfield_ising.py` (N=3), `benchmarks/quantum_hopfield_n8.py`
(N=8 v1, degeneración documentada), `benchmarks/quantum_hopfield_n8_v2.py` (N=8 v2,
corregido). Datos crudos en los `.json` correspondientes.

## Historial de versiones relevante

- v3.0 (DOI 10.5281/zenodo.22742308): cierre inicial del Vector 1 (2 cúbits, ζ_ZZ, DCG).
- v3.2 (DOI 10.5281/zenodo.22790292): script `two_qubit_hil_dcg.py` archivado individualmente.
- **v3.3 (esta versión):** consolida Vector 1 completo (incluyendo RB suite y Sim2Real Gap)
  y cierra el Vector 2 (memoria asociativa cuántica, N=3 y N=8).
