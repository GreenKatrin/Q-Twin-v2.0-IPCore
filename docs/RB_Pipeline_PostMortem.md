# Q-Twin — Digital Twin HIL para Control Cuántico: Resumen de Pipeline y Post-Mortem de Depuración

**Alcance:** Vector 1 del proyecto Q-Twin (Digital Twin Hardware-in-the-Loop para control de cúbits superconductores).  
**Objetivo:** Cuantificar la brecha Sim2Real entre el firmware de control (FPGA/RFSoC) y la física real del cúbit, y validar el pipeline completo con un benchmark de algoritmo (Randomized Benchmarking).

---

## 1. Arquitectura Final

El flujo de simulación opera de manera secuencial a través de cuatro etapas interconectadas:

*   **Módulo B (`drag_pulse_engine.py`):** Síntesis de pulso DRAG ($X_\pi$, $X_{\pi/2}$). Genera formas de onda `PulseWaveform` ($I(t)$, $Q(t)$ en rad/s) para compuertas de un cúbit con corrección DRAG. Estándar canónico establecido: $10\text{ GSa/s}$, $\lambda = 1.0$.
*   **Módulo A (`sim2real_channel.py`):** Canal físico no ideal. Aplica desbalance IQ/skew, cuantización DAC de 14 bits, jitter de apertura, y filtro coaxial paso-bajo de $350\text{ MHz}$. Opera en dos modos: `run_channel` (pulso aislado, filtrado offline) y `run_channel_sequence` (secuencia continua, filtrado causal con estado persistente para RB).
*   **Módulo C (`transmon_simulator.py`):** Emulador de transmón de 3 niveles. Resuelve el hamiltoniano de Duffing en el subespacio $\{|0\rangle, |1\rangle, |2\rangle\}$ bajo la RWA (aproximación de onda rotatoria), calculando tanto la evolución unitaria (fidelidad coherente) como la disipación de Lindblad ($T_1$, $T_2^*$).
*   **RB (`rb_core.py`, `run_rb.py`):** Módulo de Randomized Benchmarking. Genera el grupo de Clifford de 1 cúbit (24 elementos) descompuesto en fases virtuales $Z$ y pulsos físicos $X_{\pi/2}$. Construye secuencias aleatorias, calcula el canal de inversión y ejecuta el ajuste de decaimiento exponencial.

---

## 2. Resultados Finales Validados

| Métrica / Parámetro | Valor Obtenido |
| :--- | :--- |
| **Fidelidad $X_\pi$ ideal (coherente)** | $0.999985$ |
| **Fidelidad $X_\pi$ HIL (canal degradado)** | $0.999984$ |
| **Fuga $L_2$ ideal / HIL** | $1.46 \times 10^{-7}$ / $1.80 \times 10^{-7}$ |
| **Fidelidad $X_{\pi/2}$ ideal** | $0.9999997$ |
| **Sim2Real Gap, compuerta única ($X_\pi$)** | $\sim 1 \times 10^{-6}$ |
| **$r_{\text{Clifford}}$ ideal (RB)** | $4.166 \times 10^{-4} \pm 3.3 \times 10^{-6}$ |
| **$r_{\text{Clifford}}$ HIL (RB)** | $4.491 \times 10^{-4} \pm 7.7 \times 10^{-6}$ |
| **Sim2Real Gap, nivel algoritmo (RB)** | $\mathbf{3.25 \times 10^{-5} \pm 8.4 \times 10^{-6}}$ ($3.89\sigma$, $K=10$, $m \in \{1..64\}$) |

**Lectura Física:** A nivel de compuerta única, el error coherente de forma de pulso ya calibrado es del orden de $10^{-7}$ a $10^{-6}$. A nivel de secuencia de Clifford ($40\text{ ns}$ por compuerta), la decoherencia $T_1/T_2^*$ domina absolutamente y eleva el error por compuerta a $\sim 4 \times 10^{-4}$. Este es exactamente el comportamiento esperado de un RB real bien calibrado: el límite lo impone la decoherencia ambiental, no la imperfección residual del pulso.

---

## 3. Post-Mortem: Bugs Reales Encontrados y Depurados

### 3.1 Signo invertido en el acoplamiento DRAG del hamiltoniano (Módulo C)
*   **Síntoma:** Con la corrección DRAG activada, la población transferida a $|1\rangle$ empeoró respecto a no aplicar DRAG (de $99.26\%$ a $93.58\%$), y la fuga a $|2\rangle$ aumentó.
*   **Diagnóstico:** El término $+\frac{i}{2}\Omega_Q(t)(a-a^\dagger)$ tenía el signo opuesto a la convención requerida por $\Omega_Q(t)=-\lambda\dot{\Omega}_I/\alpha$ del Módulo B. Si una corrección de segundo orden empeora el resultado de primer orden, es un error de signo matemático, no un efecto físico genuino.
*   **Solución:** Cambiado a $-\frac{i}{2}\Omega_Q(t)(a-a^\dagger)$ en `build_hamiltonian_fn`.

### 3.2 Factor 2 faltante en la fórmula de $\Omega_Q(t)$ (Módulo B)
*   **Síntoma:** El óptimo empírico de $\lambda$ quedó fijo en $0.50$ para $X_\pi$. Se atribuyó erróneamente a un efecto físico de "fast gate" (Stark-shift dinámico).
*   **Diagnóstico:** Un efecto de segundo orden debe escalar como $\epsilon^2 = (\Omega/\alpha)^2$ y desaparecer para pulsos débiles. Al barrer amplitudes (desde $X_\pi$ hasta $X_{\pi/64}$), el óptimo no se movió. Esta invariancia de amplitud es la firma de un factor sistemático faltante.
*   **Solución:** La fórmula teórica correcta es $\Omega_Q(t)=-\lambda\dot{\Omega}_I(t)/(2\alpha)$. Al agregar el factor 2, el óptimo regresó a $\lambda \approx 1.0$ para todas las amplitudes.

### 3.3 Tasa de muestreo no convergida en Módulo B ($1\text{ GSa/s}$)
*   **Síntoma:** Con solo 20 muestras sobre un pulso de $20\text{ ns}$, la fuga $L_2$ ($10^{-6}$) era dos órdenes de magnitud mayor al valor convergido continuo ($10^{-8}$).
*   **Solución:** Se estableció $10\text{ GSa/s}$ como estándar canónico, verificado por convergencia cruzada contra $20\text{ GSa/s}$ y alineado con la tasa nativa de los DAC RFSoC Gen3 ($\sim 9.85\text{ GSa/s}$).

### 3.4 Rejilla de calibración de $\lambda$ demasiado gruesa
*   **Síntoma:** Un barrido grueso ($\Delta\lambda=0.2$) reportó un falso óptimo en $\lambda=0.60$ (infidelidad $1.8 \times 10^{-4}$). El óptimo real era $\lambda=0.50$ (infidelidad $1.5 \times 10^{-5}$, 12 veces mejor).
*   **Solución:** Refinar numéricamente la búsqueda antes de declarar un óptimo paramétrico.

### 3.5 Filtrado no causal en Módulo A para secuencias continuas
*   **Síntoma:** El uso de `sosfiltfilt` (fase cero) en secuencias RB "veía el futuro", filtrando hacia adelante y hacia atrás, eliminando incorrectamente la interferencia entre símbolos (ISI) física de un cable real.
*   **Solución:** Implementación de filtrado estrictamente causal `apply_coax_filter_causal()` con propagación de estado interno `zi` entre las compuertas de la secuencia continua.

### 3.6 Full-scale del DAC recalculado dinámicamente por pulso
*   **Síntoma:** `run_channel` recalculaba el fondo de escala de cuantización para cada compuerta individual, provocando inconsistencia de rango dinámico en secuencias RB con amplitudes mixtas.
*   **Solución:** Se parametrizó un `fixed_full_scale` global atado al pico de máxima amplitud teórica del experimento.

### 3.7 Semilla de ruido de canal fija en repeticiones Monte Carlo
*   **Síntoma:** En el bucle de RB, las $K$ repeticiones compartían la misma semilla para el jitter/ruido del canal, anulando el promedio estadístico sobre las imperfecciones del hardware.
*   **Solución:** Se inyectó una semilla de alcance independiente (`SEED + 1000*m + k`) por repetición.

### 3.8 Ponderación estadística errónea en el ajuste RB
*   **Síntoma:** El ajuste $P_0(m) = A p^m + B$ usando la desviación estándar cruda ($\sigma$) como peso generó un "gap negativo" artificial.
*   **Solución:** Se fijó la asíntota en $B=0.5$ (fuga a $|2\rangle$ despreciable) y se utilizó el error estándar de la media ($\sigma/\sqrt{K}$) para los pesos del ajuste de mínimos cuadrados, revelando el gap físico real.

### 3.9 Divergencia de SINAD por asunciones semánticas
*   **Síntoma:** Dos implementaciones de canal idénticas reportaron SNR con $40\text{ dB}$ de diferencia.
*   **Diagnóstico:** Definiciones operativas distintas para la métrica de "ruido" (piso de cuantización teórico LSB²/12 frente a residuo total real-menos-ideal). Ninguna divergencia arquitectónica puede darse por sentada sin una conciliación matemática explícita.

---

## 4. Lección Metodológica Transversal

Cada uno de los *bugs* críticos (especialmente los problemas de factor de escala y de signo) sobrevivió a revisiones iniciales porque poseían una **explicación física teóricamente plausible** (como el corrimiento Stark o los efectos de compuerta rápida). 

La vulnerabilidad fue superada exigiendo sistemáticamente una **predicción falsable**: comprobar el escalado con la amplitud del pulso, forzar convergencias asintóticas o requerir consistencia de signos. La verdadera auditoría técnica de un Digital Twin se basa en interrogar las predicciones diferenciales del código, no en la plausibilidad literaria de sus ecuaciones.

---

## 5. Manifiesto de Archivos del Pipeline

| Archivo | Función / Contenido |
| :--- | :--- |
| `drag_pulse_engine.py` | **Módulo B:** Síntesis y optimización analítica de pulso DRAG. |
| `sim2real_channel.py` | **Módulo A:** Simulador de imperfecciones de canal físico (aislado y continuo). |
| `transmon_simulator.py` | **Módulo C:** Integrador de hamiltoniano de 3 niveles y disipador de Lindblad. |
| `clifford_decomposition.py` | Generador del grupo de Clifford (24 elementos) y rutinas de compilación a pulsos físicos $Z - X_{\pi/2} - Z$. |
| `rb_core.py` | Motor criptográfico de RB: *frame tracking*, ensamblaje y simulador de secuencia. |
| `run_rb.py` | Orquestador de Monte Carlo con checkpointing para inferencia estadística del gap HIL. |
| `rb_results.json` | Base de datos cruda con las $K=10$ repeticiones para cada $m \in \{1, 2, 4, 8, 16, 32, 64\}$. |

---

## 6. Próximos Pasos Sugeridos

*   **Expansión Multicúbit:** Extender el par generador a dos cúbits integrando compuertas de acoplamiento (ej. *Cross-Resonance* o *CZ*) y la diafonía paramétrica ($J_{13}$, $J_{24}$) proyectada originalmente en el Módulo A.
*   **Refinamiento Estadístico (Opcional):** Ampliar las repeticiones $K$ de Monte Carlo si en el futuro se requiere reducir el margen de error sobre la brecha Sim2Real actual ($3.89\sigma$).
*   **Validación Física HIL:** Confrontar las métricas de $r_{\text{Clifford}}$ extraídas del Gemelo Digital contra la caracterización RB real de una QPU conectada físicamente a las interfaces DAC/ADC de la tarjeta AMD RFSoC ZCU216.
