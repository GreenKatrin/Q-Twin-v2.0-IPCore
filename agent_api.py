from fastapi import FastAPI
from pydantic import BaseModel, Field
import grpc
import q_twin_pb2
import q_twin_pb2_grpc

app = FastAPI(
    title="Q-Twin AI Gateway",
    description="Interfaz REST/OpenAPI para que Agentes de IA controlen el Gemelo Digital Cuántico.",
    version="2.0"
)

class EnvironmentParams(BaseModel):
    pressure_mpa: float = Field(2.5, description="Presión de las arandelas Belleville en MPa (0.0 a 5.0)")
    temperature_mk: float = Field(15.0, description="Temperatura del criostato en mK (10.0 a 50.0)")

@app.post("/environment/simulate", summary="Ejecutar ciclo de simulación para la IA")
def simulate(params: EnvironmentParams):
    channel = grpc.insecure_channel('quantum-engine:50051')
    stub = q_twin_pb2_grpc.QuantumEngineServiceStub(channel)
    
    req = q_twin_pb2.PulseRequest(
        qubit_id=0,
        phase_pulse_rad=1.5708,
        pressure_mpa=params.pressure_mpa,
        temperature_mk=params.temperature_mk
    )
    res = stub.EvolveQubit(req)
    return {
        "qubit_id": res.qubit_id,
        "prob_zero": round(res.prob_zero, 4),
        "prob_one": round(res.prob_one, 4),
        "mechanical_drift_hz": res.mechanical_drift_hz,
        "thermal_noise_rate": round(res.thermal_noise_rate, 5)
    }
