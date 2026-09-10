# Nota Metodológica y Estado de Ecuaciones (v2.1 — Errata)

**Registro Zenodo v2.1:** [DOI 10.5281/zenodo.22694596](https://doi.org/10.5281/zenodo.22694596).

---

## Reclasificación del proyecto

**Título anterior:** "Q-Twin v2.0: Arquitectura Hardware-in-the-Loop para Emulación Cosmológica Cuántica — Documento Técnico Integrado de Especificación, Validación Física y Producción"

**Título corregido (v2.1):** "Q-Twin v2.0: Arquitectura de Referencia y Simulador de Gemelo Digital para Control Cuántico Hardware-in-the-Loop (Modelo Virtual, sin QPU física)"

## Qué cambia respecto a la v2.0

1. **No existe hardware cuántico físico.** El proyecto es un simulador de gemelo digital que corre sobre una FPGA comercial (AMD Xilinx RFSoC ZCU216) y un motor tensorial en Numba JIT. No hay criostato de dilución, chip superconductor fabricado, ni transmones físicos. Todas las referencias a "temperatura de 15 mK", "ocupación térmica medida" o "chip criogénico" en la v2.0 describen una variable de estado dentro de la simulación, no una medición física.

2. **Se retira la reclamación de certificación OSHWA.** La Open Source Hardware Association certifica diseños de hardware físico publicados bajo licencia abierta; no aplica a software o simulación virtual. El badge "OSHWA Certified" y las frases de aprobación se retiran de forma permanente, no se dejan como "pendiente".

3. **Los observables cosmológicos son salidas de un modelo calibrado, no predicciones independientes ni mediciones.** En particular:
   - n_s = 0.963 ± 0.004 depende de fijar el parámetro β≈1.70 por inversión para reproducir ese valor objetivo — no es una predicción ab initio.
   - El índice tensorial n_t = 2.4188 y el corte exponencial, usados para derivar f_rh, f_max y r_BBN^max, se sometieron a integración numérica directa de la ecuación de modos de Mukhanov. Esa integración **no reproduce** ninguno de los dos valores.
   - r_modelo nunca se calculó desde la cuantización de modos; solo se fijó una cota superior de consistencia (r_BBN^max).
   - En consecuencia, f_rh, f_max y r_BBN^max deben leerse como **condiciones de contorno bajo un ansatz no verificado**, no como resultados cerrados.

4. **Los archivos de código fuente que usen lenguaje no académico** (`trascendent_rl_agent.py`) se renombran y reescriben con terminología técnica estándar (optimización multiobjetivo de Pareto, control de disipación lindbladiana homeostática) en el repositorio asociado.

## Qué se mantiene válido de la v2.0

- La arquitectura de firmware AXI4-Lite, la topología en serpentín y la precodificación C⁻¹ como diseño de instrumentación para control de qubits sobre RFSoC.
- El motor tensorial MPDO como método de simulación de sistemas cuánticos abiertos.
- El cálculo de ocupación térmica de fotones a 15 mK / 8 GHz es una aplicación correcta de la estadística de Bose-Einstein estándar — válido como cálculo de referencia para el diseño, no como medición.

## Siguiente hito para una v3.0 con reclamos físicos

Antes de reintroducir cualquier reclamo de predicción cosmológica cerrada, se requiere: (a) resolver la ecuación de modos sobre una métrica de rebote empalmada físicamente consistente; (b) calcular r_modelo como salida de esa solución; y (c), si se construye hardware físico real, solicitar la certificación OSHWA correspondiente.
