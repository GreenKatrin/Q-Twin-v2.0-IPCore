import time
import grpc
import numpy as np

import quantum_engine_pb2
import quantum_engine_pb2_grpc
from axi_hardware_driver import AXI4LiteDriver

class Agent8Qubit:
    def __init__(self):
        self.num_qubits = 8
        self.driver = AXI4LiteDriver()
        self.channel = grpc.insecure_channel('localhost:50052')
        self.stub = quantum_engine_pb2_grpc.QuantumEngineStub(self.channel)

    def run_8q_cycle(self, steps=5):
        print(f"\n🌌 [DRL 8-QUBIT AGENT] Iniciando control multivariable sobre matriz 256x256...")
        print("----------------------------------------------------------------------------------")
        
        for step in range(1, steps + 1):
            drives = np.random.uniform(0.1, 1.0, size=8)
            
            # Inyección en bus AXI de 8 canales
            for q_idx in range(8):
                reg_val = int(drives[q_idx] * 0xFFFF)
                self.driver.write_phase_register(reg_val)
                
            signals = [quantum_engine_pb2.ControlSignals(qubit_id=i, i_amplitude=drives[i], q_amplitude=0.0) for i in range(8)]
            req = quantum_engine_pb2.SimulationRequest(
                delta_t_ns=2.0,
                temperature_mk=10.0,
                pressure_mpa=0.0,
                drive_signals=signals
            )
            
            t0 = time.time()
            res = self.stub.SimulateStep(req)
            elapsed_ms = (time.time() - t0) * 1000.0
            
            print(f"Paso {step:02d} | Dim Hilbert: {res.tensor_shape[0]}x{res.tensor_shape[1]} (256) | "
                  f"Fidelidad: {res.average_fidelity:.4f} | Latencia gRPC+JIT: {elapsed_ms:.2f} ms")
            time.sleep(0.3)

if __name__ == "__main__":
    agent = Agent8Qubit()
    agent.run_8q_cycle()
