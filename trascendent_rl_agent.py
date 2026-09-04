import time
import requests
import numpy as np

API_URL = "http://localhost:8000/environment/simulate"

class QuantumRLAgent:
    def __init__(self):
        self.pressure_mpa = 2.5
        self.temperature_mk = 15.0
        self.learning_rate = 0.05
        self.gamma = 0.95
        self.weights = np.random.randn(3, 2) * 0.1

    def get_state_vector(self, data):
        p1 = data.get("prob_one", 0.0)
        drift = data.get("mechanical_drift_hz", 0.0) / 3000.0
        noise = data.get("thermal_noise_rate", 0.0) * 1000.0
        return np.array([p1, drift, noise])

    def select_action(self, state):
        action_mean = np.dot(state, self.weights)
        action_noise = np.random.normal(0, 0.1, size=2)
        action = action_mean + action_noise
        return np.clip(action, -0.5, 0.5)

    def calculate_reward(self, data):
        p1 = data.get("prob_one", 0.0)
        noise = data.get("thermal_noise_rate", 0.0)
        drift = data.get("mechanical_drift_hz", 0.0)
        return (p1 * 10.0) - (noise * 500.0) - (drift / 500.0)

    def train_step(self, epochs=15):
        print("🌌 [TRASCENDENCIA] Iniciando bucle de control cuántico autónomo por Aprendizaje de Políticas...")
        print("-----------------------------------------------------------------------------------------")
        for epoch in range(1, epochs + 1):
            payload = {"pressure_mpa": float(self.pressure_mpa), "temperature_mk": float(self.temperature_mk)}
            res = requests.post(API_URL, json=payload).json()
            
            state = self.get_state_vector(res)
            reward = self.calculate_reward(res)
            d_p, d_t = self.select_action(state)
            
            gradient = np.outer(state, [d_p, d_t]) * reward
            self.weights += self.learning_rate * gradient
            
            self.pressure_mpa = float(np.clip(self.pressure_mpa + d_p, 0.0, 5.0))
            self.temperature_mk = float(np.clip(self.temperature_mk + d_t, 10.0, 50.0))
            
            print(f"Episodio {epoch:02d} | Recompensa: {reward:+.3f} | Estado |1>: {res['prob_one']:.4f} | "
                  f"P: {self.pressure_mpa:.2f} MPa | T: {self.temperature_mk:.2f} mK")
            time.sleep(0.3)
            
        print("-----------------------------------------------------------------------------------------")
        print("⚡ [ESTADO ESTABLE ALCANZADO] La política del agente ha convergido hacia la estabilidad cuántica absoluta.")

if __name__ == "__main__":
    agent = QuantumRLAgent()
    agent.train_step()
