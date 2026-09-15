# Anexo: Extensión a 2 Cúbits
## Hamiltoniano Acoplado, Línea de Base $\zeta_{ZZ}$, y Error de Espectador Dinámico

**Alcance:** primera extensión del Vector 1 (Digital Twin HIL) de 1 a 2 cúbits, arquitectura de frecuencia fija con acoplamiento capacitivo estático y control Cross-Resonance (CR).

### 1. Arquitectura y verificación de base
* **Espacio de Hilbert:** $9\times9$, producto tensorial de dos transmones (Control $A$, Target $B$) truncados a 3 niveles cada uno. Operadores extendidos vía Kronecker: $a=a_3\otimes I_3$, $b=I_3\otimes a_3$.
* **Marco de trabajo:** rotante local de cada transmón (a su propia frecuencia $\omega_A,\omega_B$), con $\Delta=\omega_A-\omega_B$. El acoplamiento estático $J(a^\dagger b+ab^\dagger)$ del marco de laboratorio se transforma en $J(a^\dagger b e^{i\Delta t}+ab^\dagger e^{-i\Delta t})$; el drive CR (aplicado a $A$ a la frecuencia de $B$) adquiere la fase complementaria $\frac{1}{2}[\Omega(t)a^\dagger e^{-i\Delta t}+\Omega^*(t)a e^{i\Delta t}]$. Ambas fórmulas se rederivaron de forma independiente antes de implementarse y coincidieron exactamente.
* **Verificación decisiva:** swap vacuum-Rabi resonante ($\Delta=0$, sin drive) contra la solución analítica cerrada $P_{|1,0\rangle}(t)=\sin^2(Jt)$. Error máximo: $1.06\times10^{-10}$. El hamiltoniano de 9 niveles reproduce la física exacta conocida sin ambigüedad.
* **Costo computacional:** un gate CR de 200 ns con detuning realista ($\Delta/2\pi=250$ MHz) corre en 0.9-1.7 s por trayectoria (RK45, rtol $10^{-8}$ a $10^{-10}$) — no fue necesario un solver rígido (BDF/LSODA).

**Archivos:** `two_qubit_hamiltonian.py`, `two_qubit_simulator.py` (clase `TwoQubitSimulator`, con enrutamiento multicanal `port_A/port_B/port_CR`).

### 2. Línea de base: acoplamiento $ZZ$ estático
Medido ajustando la fase acumulada del Target (drive apagado, solo $J$) vs. tiempo, condicionada al estado del Control, para $J=3$ MHz, $\Delta/2\pi=250$ MHz, $\alpha_A=-300$ MHz, $\alpha_B=-320$ MHz:

$$ \zeta_{ZZ} = -0.39\text{ MHz} \quad (-0.3986\text{ MHz en ventana [0,60]ns}, \ -0.3879\text{ MHz en ventana [0,300]ns} \text{ — consistente al }3\%) $$

Se confirmó el origen microscópico correcto: la extracción muestra una fuga real de $\sim 1.4\%$ hacia estados tipo $|2,0\rangle$ para el caso Control=1 — exactamente el mecanismo de hibridación dispersiva vía la anarmonicidad que genera $ZZ$ en transmones reales.
**Archivo:** `extract_zz_rate.py`.

### 3. Hallazgo principal: error de espectador dinámico durante $X_\pi$

#### 3.1 Observación
Al medir el Target condicionado al Control usando un pulso CR desnudo, la rotación observada resultó ser casi enteramente $ZZ$ estático, no $ZX$ inducido por el drive. Al construir un eco ($CR_+ \to X_\pi \to CR_- \to X_\pi$) para aislar el $ZX$, el residuo falló en cancelarse.

#### 3.2 Diagnóstico por traza temporal continua
Se extrajo $Y(t)$ del Target y $P_2(t)$ del Control (fuga transitoria), sobre el experimento "eco de la nada" (solo $J$, drive CR apagado):

| Tramo | Comportamiento de $Y(t)$ | Fuga transitoria $P_2$ (Control) |
| :--- | :--- | :--- |
| **Espera 1 (0-96 ns)** | Crecimiento lineal, lento: $\sim 2.3\times10^{-4}$/ns | 0 |
| **$X_\pi$ #1 (100-120 ns)** | Oscilación abrupta $0.024\to0.103\to-0.037$ (amplitud $\sim 0.14$) | pico $0.89\%$ |
| **Espera 2 (128-221 ns)**| Lineal, pero $\sim 3\times$ más rápido (Control ya volteado) | 0 |
| **$X_\pi$ #2 (220-240 ns)** | Oscilación abrupta $+0.122\to-0.235$ (amplitud $\sim 0.36$) | pico $1.95\%$ |

Los saltos ocurren exclusivamente dentro de las ventanas de los pulsos $X_\pi$, son 6-15x más rápidos que la deriva de fondo, y no se cancelan entre sí.

#### 3.3 DRAG no es suficiente
Se reemplazó el $X_\pi$ ad-hoc por el $X_\pi$ real verificado (Módulo B, $\lambda=1.0$, fuga aislada $\sim 10^{-7}$). El resultado fue idéntico:

| Métrica | $X_\pi$ sin DRAG | $X_\pi$ con DRAG (verificado) |
| :--- | :--- | :--- |
| $Y$ final, Control $=0$ | $-0.2349$ | $-0.2366$ |
| $Y$ final, Control $=1$ | $-0.2583$ | $-0.2558$ |
| $P_2$(Control) pico | $1.95\%$ | $2.4\%$ (mayor, no menor) |

**Interpretación:** DRAG suprime la fuga de un cúbit *aislado* al final del pulso. El Target sigue entrelazado con la trayectoria instantánea del Control (que atraviesa una superposición no trivial incluso con DRAG) durante los 20 ns completos. 

#### 3.4 Validación externa
Watanabe et al. (arXiv:2309.13927) miden exactamente este efecto en hardware real, encontrando que la tasa de error por compuerta de un pulso Gaussiano+DRAG estándar empeora $\sim 4\times$ cuando un espectador está activo ($\zeta_{ZZ}=0.73$ MHz). Confirman que DRAG estándar no ofrece protección contra este mecanismo.

### 4. Estado del hallazgo
Esto no es un bug del código. Es la manifestación correcta, dentro del modelo de 9 niveles, de una limitación física real de las arquitecturas de frecuencia fija. Se decidió consolidar el hallazgo en lugar de desarrollar pulsos "ZZ-interaction-free" avanzados en esta fase.

### 5. Manifiesto de archivos
| Archivo | Contenido |
| :--- | :--- |
| `two_qubit_hamiltonian.py` | Hamiltoniano $9\times9$ base, verificado analíticamente |
| `two_qubit_simulator.py` | Clase multicanal y ensamblador de eco |
| `cr_timing_benchmark.py` | Benchmark de costo de integración para CR |
| `extract_zz_rate.py` | Extracción de $\zeta_{ZZ}=-0.39$ MHz |
| `trace_echo_null.py` | Traza temporal que aisló el error de espectador |

### 6. Direcciones futuras (no exploradas en esta fase)
* Implementar un pulso robusto a $ZZ$ (optimización semi-analítica vía expansión de Magnus).
* Evaluar mitigaciones activas (ej. tonos siZZle) o replantear la topología a acopladores sintonizables.
