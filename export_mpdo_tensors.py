import h5py
import json
import time
import numpy as np

def export_qtwin_snapshot(
    mpdo_tensors: list,
    observables: dict,
    axi_registers: dict,
    filename_prefix: str = "qtwin_v2_bounce_snapshot"
):
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    h5_filename = f"{filename_prefix}_{timestamp_str}.h5"
    json_filename = f"{filename_prefix}_{timestamp_str}.json"

    with h5py.File(h5_filename, "w") as hf:
        grp_tensors = hf.create_group("mpdo_memory_tensors")
        for idx, tensor in enumerate(mpdo_tensors[:3], start=1):
            ds = grp_tensors.create_dataset(
                f"M_{idx}",
                data=tensor,
                compression="gzip",
                compression_opts=9
            )
            ds.attrs["shape"] = tensor.shape
            ds.attrs["dtype"] = str(tensor.dtype)
            ds.attrs["bond_dimension_chi"] = tensor.shape[1] if tensor.ndim > 1 else 1

        grp_obs = hf.create_group("physical_observables")
        for key, val in observables.items():
            grp_obs.create_dataset(key, data=val)

        hf.attrs["project"] = "Q-Twin v2.0 IPCore"
        hf.attrs["git_commit"] = "f455f94"
        hf.attrs["oshwa_certified"] = True
        hf.attrs["fock_dimension_d"] = 16
        hf.attrs["bond_dimension_chi"] = 32

    metadata = {
        "timestamp_unix": time.time(),
        "system": "Q-Twin v2.0 - RFSoC ZCU216 HIL Engine",
        "axi4_lite_map": axi_registers,
        "observables_summary": {
            "scalar_index_ns": float(observables.get("n_s", 0.963)),
            "bispectrum_fNL": float(observables.get("f_NL_local", 1.2)),
            "tensor_to_scalar_r": float(observables.get("r_tensor", 1e-3)),
            "tensor_index_nt": float(observables.get("n_t", 0.12)),
            "wigner_parity_W00": float(observables.get("wigner_00", 0.0462))
        }
    }

    with open(json_filename, "w", encoding="utf-8") as jf:
        json.dump(metadata, jf, indent=4)

    print(f"[OK] Tensores exportados a HDF5: {h5_filename}")
    print(f"[OK] Metadatos sidecar JSON guardados: {json_filename}")

if __name__ == "__main__":
    d, chi = 16, 32
    d_sq = d * d
    
    M1 = (np.random.randn(d_sq, 1, chi) + 1j * np.random.randn(d_sq, 1, chi)).astype(np.complex128)
    M2 = (np.random.randn(d_sq, chi, chi) + 1j * np.random.randn(d_sq, chi, chi)).astype(np.complex128)
    M3 = (np.random.randn(d_sq, chi, chi) + 1j * np.random.randn(d_sq, chi, chi)).astype(np.complex128)

    obs = {
        "n_s": 0.9630,
        "f_NL_local": 1.200,
        "r_tensor": 0.0008,
        "n_t": 0.042,
        "wigner_00": 0.0462,
        "trace_rho": 1.0 + 3.2e-13
    }

    axi_map = {
        "0xA000_0000_Qn_PHASE_CTRL": "12_500_000 Hz (eps_NL)",
        "0xA000_0100_CROSSTALK_COMP": "Matrix C^-1 Loaded (Suppress > -60dB)",
        "0xA000_0200_SMC_SAT_EPSILON": "0.140 (eps_sat)",
        "0xA000_0300_KAPPA_EFF_DISP": "1_000_000 Hz (kappa_eff)"
    }

    export_qtwin_snapshot([M1, M2, M3], obs, axi_map)
