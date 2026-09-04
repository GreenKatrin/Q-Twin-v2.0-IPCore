import time
import numpy as np
from concurrent import futures
import grpc
import q_twin_pb2
import q_twin_pb2_grpc

class COMSOLSurrogateModel:
    def __init__(self):
        self.lut = {0.0: 0.0, 1.0: 1000.0, 2.0: 2000.0, 2.5: 2500.0, 3.0: 3000.0}
    def get_thermal_decoherence(self, temp_mK):
        base = 0.001
        return base * (temp_mK / 15.0)**2 if temp_mK > 15.0 else base
    def get_mechanical_drift(self, pressure_MPa):
        return float(np.interp(pressure_MPa, list(self.lut.keys()), list(self.lut.values())))

class QuantumEngineServicer(q_twin_pb2_grpc.QuantumEngineServiceServicer):
    def __init__(self):
        self.comsol = COMSOLSurrogateModel()
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)

    def EvolveQubit(self, request, context):
        drift_hz = self.comsol.get_mechanical_drift(request.pressure_mpa)
        thermal_noise = self.comsol.get_thermal_decoherence(request.temperature_mk)
        
        # Simulación tensorial del Hamiltoniano EGRO v2.0
        dt = 2e-9
        omega_ctrl = request.phase_pulse_rad / dt
        omega_drift = 2 * np.pi * drift_hz
        H = (omega_ctrl * self.X) + (omega_drift * self.Z)
        
        eigvals, eigvecs = np.linalg.eigh(H)
        U = eigvecs @ np.diag(np.exp(-1j * eigvals * dt)) @ eigvecs.conj().T
        
        state = np.array([1, 0], dtype=complex)
        new_state = U @ state
        if np.random.rand() < thermal_noise:
            new_state = self.Z @ new_state
        new_state /= np.linalg.norm(new_state)
        
        p1 = float(np.abs(new_state[1])**2)
        p0 = float(np.abs(new_state[0])**2)
        
        return q_twin_pb2.StateResponse(
            qubit_id=request.qubit_id,
            prob_zero=p0,
            prob_one=p1,
            mechanical_drift_hz=drift_hz,
            thermal_noise_rate=thermal_noise
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    q_twin_pb2_grpc.add_QuantumEngineServiceServicer_to_server(QuantumEngineServicer(), server)
    server.add_insecure_port('[::]:50051')
    print("🚀 Motor Cuántico gRPC activo en puerto 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
