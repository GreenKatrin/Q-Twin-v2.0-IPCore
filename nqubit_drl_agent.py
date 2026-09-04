import time
import grpc
import numpy as np

import quantum_engine_pb2
import quantum_engine_pb2_grpc
from axi_hardware_driver import AXI4LiteDriver

class MultiQubitDRLAgent:
    def __init__(self, num_qubits=2):
        self.num_qubits = num_qubits
        self.driver = AXI4LiteDriver()
        self.channel = grpc.insecure_channel('localhost:50052')
        self.stub = quantum_engine_pb2_grpc.QuantumEngineStub(self.channel)

    def run_control_loop(self, steps=5):
        print(f"\n🌌 [DRL MULTI-QUBIT] Iniciando bucle de control para N = {self.num_qubits} Qubits...")
        print("----------------------------------------------------------------------------------")
        
        for step in range(1, steps + 1):
            drives = [np.random.uniform(0.1, 1.0) for _ in range(self.num_qubits)]
            
            for idx, drive_val in enumerate(drives):
                reg_val = int(drive_val * 0xFFFF)
                self.driver.write_phase_register(reg_val)
            
            signals = [quantum_engine_pb2.ControlSignals(qubit_id=i, i_amplitude=drives[i], q_amplitude=0.0) for i in range(self.num_qubits)]
            req = quantum_engine_pb2.SimulationRequest(
                delta_t_ns=2.0,
                temperature_mk=10.0,
                pressure_mpa=0.0,
                drive_signals=signals
            )
            
            res = self.stub.SimulateStep(req)
            
            print(f"Paso {step:02d} | Dim Hilbert: {res.tensor_shape[0]}x{res.tensor_shape[1]} | "
                  f"Fidelidad Promedio: {res.average_fidelity:.4f} | Error Crosstalk: {res.total_crosstalk_error:.4f}")
            time.sleep(0.4)

if __name__ == "__main__":
    agent = MultiQubitDRLAgent(num_qubits=2)
    agent.run_control_loop()
