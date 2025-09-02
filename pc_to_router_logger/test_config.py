import os

# === Configurable Test Info (CHANGE FOR EACH TEST) ===
communication_type = 'http_keysight'
cable_type = 'lan_cat6_https_weakened'
antenna_position = 'metal_benchtop_taped'
power_state = '100V'
conduction_angle = '120_deg'

# === Probe sensitivity in mV/A ===
PROBE_GAIN_MV_PER_A = {
    "CHAN2": 70,
    "CHAN3": 70,
}

# === Folder and Filename Convention ===
def get_next_test_filepath(base_name: str, root_folder: str = "results6_wireshark"):
    test_folder = os.path.join(root_folder, communication_type, cable_type, antenna_position, power_state, conduction_angle)
    os.makedirs(test_folder, exist_ok=True)

    i = 1
    while True:
        file_name = f"{base_name}_{communication_type}_{cable_type}_{antenna_position}_{power_state}_{conduction_angle}_test_{i:04d}.csv"
        full_path = os.path.join(test_folder, file_name)
        if not os.path.exists(full_path):
            return full_path
        i += 1
