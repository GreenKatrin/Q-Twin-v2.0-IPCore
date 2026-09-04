import os
import sys
import struct

AXI_BASE_ADDR = 0xA0000000
MAP_SIZE = 4096

class AXI4LiteDriver:
    """
    Controlador de registros AXI4-Lite para entorno simulado y físico.
    """
    def __init__(self, base_addr=AXI_BASE_ADDR):
        self.base_addr = base_addr
        self.emulated = True
        
        # Intentar acceder a hardware real si el archivo de dispositivo existe
        if os.path.exists("/dev/mem"):
            try:
                import mmap
                self.f = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
                self.mem = mmap.mmap(self.f, MAP_SIZE, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=self.base_addr)
                self.emulated = False
                print(f"📟 [AXI HARDWARE] Conectado exitosamente al bus AXI físico en 0x{self.base_addr:08X}")
            except Exception as e:
                print(f"⚠️ [AXI HARDWARE] No se obtuvo acceso directo. Usando RAM emulada.")
        
        if self.emulated:
            print("💡 [AXI VIRTUAL] Entorno de simulación detectado. Inicializando bus AXI4-Lite en RAM virtual...")
            self.mem = bytearray(MAP_SIZE)

    def write_phase_register(self, phase_hex_val):
        """Escribe la corrección calculada por la IA en el registro offset 0x00"""
        data = struct.pack("<I", phase_hex_val & 0xFFFF)
        if self.emulated:
            self.mem[0:4] = data
        else:
            self.mem.seek(0)
            self.mem.write(data)
        print(f"🚀 [AXI WRITE] Coeficiente 0x{phase_hex_val:04X} inyectado directamente al bus AXI4-Lite [Offset +0x00]")

    def read_status(self):
        """Lee el estado desde el registro offset 0x00"""
        if self.emulated:
            val = struct.unpack("<I", self.mem[0:4])[0]
        else:
            self.mem.seek(0)
            val = struct.unpack("<I", self.mem.read(4))[0]
        return val

if __name__ == "__main__":
    driver = AXI4LiteDriver()
    driver.write_phase_register(0x10E0)
    print(f"✅ [AXI STATUS] Lectura de verificación de bus: 0x{driver.read_status():04X}")
