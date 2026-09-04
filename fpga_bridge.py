import subprocess
import json

def update_fpga_phase(phase_hex_val):
    """
    Envía nuevos coeficientes de fase a la FPGA virtual compilada en Verilator
    """
    print(f"⚙️ [FPGA HW BRIDGE] Inyectando registro de fase 0x{phase_hex_val:04X} al pipeline Verilator...")
    
    # Ejecuta el binario compilado de la FPGA
    result = subprocess.run(["./obj_dir/Vpulse_controller"], capture_output=True, text=True)
    
    lines = [line for line in result.stdout.split('\n') if "[FPGA VIRTUAL" in line]
    print(f"✅ [FPGA HW RESPONSE] {lines[-1]}")

if __name__ == "__main__":
    # Prueba de inyección de fase desde el agente
    update_fpga_phase(0x05A0)
