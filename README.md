# Q-Twin: Hardware-in-the-Loop Digital Twin para Control Cuántico

> **⚠️ AVISO DE RETRACCIÓN Y PIVOTE ARQUITECTÓNICO (Versiones < v2.3)**
> Las iteraciones iniciales de este repositorio (incluyendo la publicación v2.0 en Zenodo) documentaban el uso del sistema como un "emulador analógico de gravedad cuántica" comparando resultados numéricos con datos observacionales del satélite Planck. Tras una rigurosa auditoría interna, **todas las afirmaciones cosmológicas y ab-initio han sido retractadas y marcadas como [DEPRECATED]**. Se hallaron patologías numéricas en las condiciones iniciales y errores de ponderación estadística que invalidan dichas conclusiones teóricas. Q-Twin opera exclusivamente como una plataforma de ingeniería de control cuántico.

## Descripción del Proyecto

Q-Twin es un marco de emulación *Hardware-in-the-Loop* (HIL) y un firmware/IP-Core SystemVerilog diseñado para evaluar, depurar y caracterizar sistemas de control de cúbits superconductores antes de su despliegue en refrigeradores de dilución. 

El objetivo central de la arquitectura es cuantificar la **brecha Sim2Real** (la diferencia entre un pulso de microondas ideal y su versión degradada físicamente) permitiendo a los ingenieros cuánticos probar algoritmos de calibración y corrección de errores en un entorno virtual validado estadísticamente.

## Arquitectura del Simulador

El motor de simulación opera mediante un pipeline de cuatro módulos interconectados, calibrado a una tasa de muestreo nativa de **10 GSa/s**:

*   **Módulo B (Drag Pulse Engine):** Sintetizador analítico de formas de onda (I/Q) para compuertas de un cúbit ($X_\pi$, $X_{\pi/2}$) implementando correcciones DRAG (Derivative Removal by Adiabatic Gate) de primer orden para mitigar fugas a estados superiores.
*   **Módulo A (Physical Channel):** Emulador del canal físico no ideal. Modela imperfecciones del hardware de control incluyendo desbalance IQ, cuantización de convertidores digital-analógicos (DAC de 14 bits), jitter de apertura y filtrado coaxial causal paso-bajo (**350 MHz**).
*   **Módulo C (Transmon Simulator):** Solucionador cuántico de dinámica abierta. Integra el hamiltoniano de Duffing en un subespacio de 3 niveles ($|0\rangle, |1\rangle, |2\rangle$) bajo la aproximación de onda rotatoria (RWA), acoplado a un disipador de Lindblad para modelar tiempos de relajación térmica ($T_1$) y desfase ($T_2^*$).
*   **RB (Randomized Benchmarking):** Motor de validación estadística basado en secuencias aleatorias del grupo de Clifford. Realiza *frame tracking* de fases virtuales para aislar el error coherente del pulso frente a la decoherencia ambiental.

## Validación de Referencia (Vector 1)

El pipeline actual ha sido auditado utilizando un protocolo de *Randomized Benchmarking* de un cúbit con $K=10$ repeticiones y profundidades de secuencia $m \in \{1..64\}$. Los resultados demuestran que el sistema modela de forma precisa el límite de decoherencia del hardware real:

| Métrica de Benchmark | Valor HIL Medido |
| :--- | :--- |
| Fidelidad compuerta aislada $X_\pi$ | $0.999984$ |
| Fuga al estado no computacional $|2\rangle$ | $1.80 \times 10^{-7}$ |
| Tasa de error de Clifford ($r_{\text{Clifford}}$) | $4.491 \times 10^{-4} \pm 7.7 \times 10^{-6}$ |
| **Sim2Real Gap (Desviación vs. Ideal)** | **$3.25 \times 10^{-5}$** ($3.89\sigma$) |

## Compatibilidad de Hardware

El núcleo digital de Q-Twin está diseñado para integrarse como un IP-Core en la plataforma **AMD Xilinx ZCU216 RFSoC**, utilizando registros AXI4-Lite (`0xA000_0000` - `0xA000_0300`) para la parametrización en tiempo real del modelo de ruido y canal físico. El proyecto no requiere hardware de circuito impreso (PCB) personalizado y se compila sobre placas de desarrollo comerciales.

## Documentación y Metodología

Para un desglose técnico de la validación del simulador, la corrección de errores numéricos y el proceso de calibración, consulte el reporte maestro de depuración: `docs/RB_Pipeline_PostMortem.md`.
