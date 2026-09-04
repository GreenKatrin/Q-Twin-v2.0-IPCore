import time
import numpy as np
import scipy.sparse as sp
from concurrent import futures
import grpc

import quantum_engine_pb2
import quantum_engine_pb2_grpc

class NQubitHamiltonianEngine:
    def __init__(self, num_qubits: int, cutoff_dim: int = 2):
        self.N = num_qubits
        self.dim_per_qubit = cutoff_dim
        self.total_dim = self.dim_per_qubit ** self.N
        
        self.a_base = np.diag(np.sqrt(np.arange(1, self.dim_per_qubit)), 1)
        self.I_base = np.eye(self.dim_per_qubit)
        
        self.a_ops = [self._build_single_mode_op(self.a_base, i) for i in range(self.N)]
        self.number_ops = [a.conj().T @ a for a in self.a_ops]

    def _build_single_mode_op(self, op: np.ndarray, target_qubit: int) -> sp.csr_matrix:
        op_list = [self.I_base] * self.N
        op_list[target_qubit] = op
        result = op_list[0]
        for next_op in op_list[1:]:
            result = sp.kron(result, next_op, format='csr')
        return result

    def compute_hamiltonian(self, freqs: np.ndarray, J_matrix: np.ndarray, drives_I: np.ndarray) -> sp.csr_matrix:
        H = sp.csr_matrix((self.total_dim, self.total_dim), dtype=np.complex128)
        for i in range(self.N):
            H += freqs[i] * self.number_ops[i]
        for i in range(self.N):
            for j in range(i + 1, self.N):
                if J_matrix[i, j] != 0:
                    exchange_term = (self.a_ops[i].conj().T @ self.a_ops[j]) + (self.a_ops[i] @ self.a_ops[j].conj().T)
                    H += J_matrix[i, j] * exchange_term
        for i in range(self.N):
            drive_term = drives_I[i] * (self.a_ops[i] + self.a_ops[i].conj().T)
            H += drive_term
        return H

class QuantumEngineServicer(quantum_engine_pb2_grpc.QuantumEngineServicer):
    def __init__(self):
        self.num_qubits = 2
        self.engine = NQubitHamiltonianEngine(num_qubits=self.num_qubits)
        self.J_matrix = np.array([[0.0, 0.05], [0.05, 0.0]])

    def SimulateStep(self, request, context):
        freqs = np.array([5.0, 5.2])
        # Corrección: Referencia correcta a los elementos del mensaje
        drives_I = np.array([drive.i_amplitude for drive in request.drive_signals])
        if len(drives_I) < self.num_qubits:
            drives_I = np.pad(drives_I, (0, self.num_qubits - len(drives_I)))

        H = self.engine.compute_hamiltonian(freqs, self.J_matrix, drives_I)
        
        rho_dummy = np.eye(self.engine.total_dim) / self.engine.total_dim
        crosstalk_err = float(np.sum(np.abs(self.J_matrix)) * (request.temperature_mk / 10.0))
        fidelity = max(0.0, 1.0 - (crosstalk_err * 0.01))

        return quantum_engine_pb2.SimulationResponse(
            density_matrix_real=rho_dummy.real.flatten().tolist(),
            density_matrix_imag=rho_dummy.imag.flatten().tolist(),
            tensor_shape=[self.engine.total_dim, self.engine.total_dim],
            average_fidelity=fidelity,
            total_crosstalk_error=crosstalk_err
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    quantum_engine_pb2_grpc.add_QuantumEngineServicer_to_server(QuantumEngineServicer(), server)
    server.add_insecure_port('[::]:50052')
    print("🚀 Motor Físico N-Qubit activo en el puerto 50052...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
