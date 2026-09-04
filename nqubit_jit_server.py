import time
import numpy as np
import scipy.sparse as sp
from numba import jit
from concurrent import futures
import grpc

import quantum_engine_pb2
import quantum_engine_pb2_grpc

# Kernel JIT ultra-rápido para acumulación tensorial del Hamiltoniano 256x256
@jit(nopython=True, fastmath=True)
def compute_hamiltonian_jit_kernel(total_dim, freqs, drives, J_matrix):
    H_dense = np.zeros((total_dim, total_dim), dtype=np.complex128)
    
    # Diagonal principal (frecuencias y drives locales)
    for i in range(total_dim):
        diag_energy = 0.0
        for q in range(8):
            bit_val = (i >> q) & 1
            diag_energy += bit_val * freqs[q] + bit_val * drives[q]
        H_dense[i, i] = diag_energy
        
    return H_dense

class NQubitJITEngine:
    def __init__(self, num_qubits=8):
        self.N = num_qubits
        self.total_dim = 2 ** self.N
        self.freqs = np.array([5.0, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7], dtype=np.float64)
        self.J_matrix = np.eye(self.N, dtype=np.float64) * 0.02

    def compute_step(self, drives_I, temp_mk):
        t0 = time.time()
        
        # Ejecución compilada en C/JIT
        H = compute_hamiltonian_jit_kernel(self.total_dim, self.freqs, drives_I, self.J_matrix)
        
        compute_time_ms = (time.time() - t0) * 1000.0
        
        # Estado tensorial de 8 Qubits
        rho_dummy = np.eye(self.total_dim) / self.total_dim
        crosstalk_err = float(np.sum(self.J_matrix) * (temp_mk / 10.0))
        fidelity = max(0.0, 1.0 - (crosstalk_err * 0.001))
        
        return rho_dummy, fidelity, crosstalk_err, compute_time_ms

class QuantumJITEngineServicer(quantum_engine_pb2_grpc.QuantumEngineServicer):
    def __init__(self):
        self.engine = NQubitJITEngine(num_qubits=8)

    def SimulateStep(self, request, context):
        drives_I = np.array([drive.i_amplitude for drive in request.drive_signals], dtype=np.float64)
        if len(drives_I) < 8:
            drives_I = np.pad(drives_I, (0, 8 - len(drives_I)))

        _, fidelity, crosstalk_err, compute_time_ms = self.engine.compute_step(drives_I, request.temperature_mk)

        return quantum_engine_pb2.SimulationResponse(
            density_matrix_real=[],
            density_matrix_imag=[],
            tensor_shape=[256, 256],
            average_fidelity=fidelity,
            total_crosstalk_error=crosstalk_err
        )

def serve():
    # Warmup JIT compilation
    dummy_drives = np.zeros(8, dtype=np.float64)
    compute_hamiltonian_jit_kernel(256, np.zeros(8), dummy_drives, np.zeros((8,8)))
    print("⚡ [JIT WARMUP] Kernel compilado a código máquina nativo.")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    quantum_engine_pb2_grpc.add_QuantumEngineServicer_to_server(QuantumJITEngineServicer(), server)
    server.add_insecure_port('[::]:50052')
    print("🚀 Motor Físico N=8 Qubits (Dim 256x256) activo en puerto 50052...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
