# Q-Twin v2.0: Simulador de Gemelo Digital HIL para Control Cuántico y Cosmología de Juguete

**Estado del proyecto: simulación / arquitectura de referencia. No incluye ni requiere un procesador cuántico físico.**

**Q-Twin v2.0** es un simulador de gemelo digital que modela, en software, la respuesta de un sistema de control de qubits superconductores (topología de 16 transmones en serpentín) sobre una FPGA comercial AMD Xilinx RFSoC (ZCU216), usando una representación tensorial MPDO (*Matrix Product Density Operators*) para simular la ecuación maestra de Lindblad en tiempo real.

El objetivo es servir como banco de pruebas Hardware-in-the-Loop **para firmware y algoritmos de control** — de la misma forma en que un banco HIL automotriz (dSPACE) simula el motor para probar la centralita electrónica sin quemar gasolina — no como un modelo físico validado de cosmología primordial.

---

## ⚠️ Qué es y qué no es este repositorio

**Es:**
- Firmware SystemVerilog (`pulse_controller.sv`) para control de microondas en FPGAs RFSoC.
- Scripts de compilación para placas AMD Xilinx Zynq RFSoC (ZCU216 / RFSoC4x2), en la misma familia de hardware que usa QICK (Fermilab) para control real de qubits.
- Un motor de simulación de sistemas cuánticos abiertos en Python/Numba JIT (MPDO, χ = 32).
- Un banco de pruebas HIL para validar algoritmos de control antes de disponer de un circuito cuántico físico.

**No es:**
- Un refrigerador de dilución físico ni un laboratorio criogénico.
- Un chip de silicio superconductor fabricado. La "temperatura de 15 mK" es una variable de estado dentro de la simulación, no una medición.
- Una demostración observacional de cosmología ekpirótica ni del Big Bang. Los valores de n_s, f_NL y r mostrados abajo son salidas de un modelo con parámetros calibrados por inversión para acercarse a Planck, no predicciones independientes — ver limitaciones más abajo.

## 📊 Salidas del simulador (no mediciones, no predicciones cerradas)

| Observable | Salida del modelo | Referencia observacional | Estatus |
| --- | --- | --- | --- |
| Índice espectral escalar (n_s) | 0.963 ± 0.004 | 0.9649 ± 0.0042 (Planck CMB) | Calibrado: depende de fijar β por inversión |
| Bispectro local (f_NL) | 1.2 ± 2.4 | −0.9 ± 5.1 (límite Planck) | Salida del canal de desfase simulado |
| Razón tensor-a-escalar (r) | < 10⁻³ | < 0.036 (BICEP/Keck) | r_modelo no se ha calculado desde la cuantización; solo se fijó una cota |
| Índice tensorial (n_t) | 2.4188 (analítico, sin verificar numéricamente) | — | Al resolver la ecuación de modos exacta sobre la métrica del propio proyecto, no se reproduce esta ley de potencias — ver Nota Metodológica v2.1 |

Ver `Zenodo_v2.1_Nota_Metodologica.md` para el detalle completo de qué está verificado, qué está calibrado y qué sigue pendiente.

## 🗺️ Mapa de Registros AXI4-Lite (0xA000_0000)

| Dirección | Registro | Función |
| --- | --- | --- |
| 0xA000_0000 | Qn_PHASE_CTRL | Amplitud séxtica simulada ε_NL |
| 0xA000_0100 | CROSSTALK_COMP | Matriz inversa C⁻¹ (16×16) para cancelar acoplamientos capacitivos simulados |
| 0xA000_0200 | SMC_SAT_EPSILON | Capa límite sigmoidal del disipador suave simulado |
| 0xA000_0300 | KAPPA_EFF_DISP | Tasa de disipación simulada en la ecuación de Lindblad |

## 📁 Estructura del repositorio

- `simular_kasner.py` — simulación JIT del colapso de paridad de Wigner bajo cizalladura de Kasner (modelo, no medición).
- `simular_recalentamiento.py` — modelo de transferencia de energía condensado→radiación.
- `export_mpdo_tensors.py` — serialización de tensores simulados M[1,2,3] a HDF5/JSON.
- `closed_loop_drl_agent.py` — agente de optimización multiobjetivo de Pareto para el control de fase AXI4-Lite.
- `pulse_controller.sv` / `pulse_controller_axi.sv` / `pulse_controller_tb.sv` — RTL de control de pulsos y testbench.
- `build_bitstream.tcl`, `run_vivado_timing.tcl` — compilación para RFSoC ZCU216.

## ✅ Cómo verificar sin tener la placa física

Este repositorio puede clonarse y su firmware puede simularse sin poseer una tarjeta ZCU216:

```bash
# Simulación de RTL con Verilator (no requiere hardware)
verilator --cc pulse_controller.sv --exe pulse_controller_tb.sv+
# Simulación de RTL con Verilator (no requiere hardware)
verilator --cc pulse_controller.sv --exe pulse_controller_tb.sv
