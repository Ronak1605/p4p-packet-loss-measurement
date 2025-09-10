import os

# === Configurable Test Info (CHANGE FOR EACH TEST) ===
cable_type = 'lan_cat6_unshielded_stripped_unpaused'
position = 'antenna_tuning_inverter_gap'
power_state = '60V'
conduction_angle = '120_deg'

# === Probe sensitivity in mV/A ===
PROBE_GAIN_MV_PER_A = {
    "CHAN2": 70,
    "CHAN3": 70,
}

# === Folder and Filename Convention ===
def get_next_test_filepath(base_name: str, root_folder: str = "results_6"):
    test_folder = os.path.join(root_folder, cable_type, position, power_state, conduction_angle)
    os.makedirs(test_folder, exist_ok=True)

    i = 1
    while True:
        file_name = f"{base_name}_{cable_type}_{position}_{power_state}_{conduction_angle}_test_{i:04d}.csv"
        full_path = os.path.join(test_folder, file_name)
        if not os.path.exists(full_path):
            return full_path
        i += 1
