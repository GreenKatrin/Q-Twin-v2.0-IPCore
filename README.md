# Q-Twin: Hardware-in-the-Loop Quantum Emulator

**⚠️ AVISO IMPORTANTE SOBRE VERSIONES ANTERIORES (v2.x)**
Las afirmaciones previas sobre observables cosmológicos y gravedad cuántica detalladas en las ramas v2.x han sido formalmente retractadas. Tras auditorías metodológicas, se determinó que los modelos carecían de anclaje empírico riguroso. Los detalles de esta retractación están en las notas de la versión v3.2.0.

---

## Estado Actual (v3.2.0+): Emulación HIL de Control Cuántico

El enfoque del emulador se ha reestructurado por completo hacia la validación de arquitecturas de hardware cuántico real. Actualmente, Q-Twin modela Hamiltonianos a nivel de microondas para sistemas acoplados de transmones.

### Extensión a 2 Cúbits (Arquitectura de Frecuencia Fija)
El núcleo actual del repositorio contiene un simulador exacto que modela un espacio de Hilbert de 9x9 (2 transmones truncados a 3 niveles) para estudiar la diafonía estática y dinámica.

**Resultados Verificados Empíricamente:**
* **Línea Base Estática:** Extracción rigurosa del acoplamiento estático residual a +0.389 MHz.
* **Error de Espectador Dinámico:** Simulación de la fluctuación inducida por un pulso Gaussiano X_pi/2 (0.578 MHz).
* **Mitigación DCG (Watanabe et al.):** Implementación de una optimización basada en la expansión de Magnus en el marco de toggling. Usando un pulso unipolar optimizado (amplitud pico 14.43 MHz), la fluctuación del espectador se amortiguó a 0.331 MHz.

### Archivos Principales
* `two_qubit_hil.py`: Script consolidado de construcción del Hamiltoniano estático, extracción de línea base y simulación de mitigación de diafonía DCG.
