from pathlib import Path
import os
import matplotlib.pyplot as plt
import pandas as pd

def read_latency_from_csv(csv_file):
    # Find the header row for the data section
    with open(csv_file, 'r') as f:
        lines = f.readlines()
    for idx, line in enumerate(lines):
        if line.startswith('Attempt,'):
            data_start = idx
            break
    df = pd.read_csv(csv_file, skiprows=data_start)
    # Use 'Response Time (ms)' as latency
    return df['Response Time (ms)'].values

def compare_latency_across_types(files_dict, output_dir="oscilloscope_latency_comparison"):
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(14, 8))
    for label, (file, color) in files_dict.items():
        latency = read_latency_from_csv(file)
        plt.plot(range(1, len(latency)+1), latency, label=label, color=color, marker='o', markersize=5, linewidth=2, alpha=0.85)
    plt.xlabel("Packet Attempt", fontsize=20)
    plt.ylabel("Latency (ms)", fontsize=20)
    plt.title("Packet Response Times for 100 Tests with Oscilloscope at 60V with 120° Conduction Angle", fontsize=20)
    plt.legend(fontsize=18)
    plt.grid(True, alpha=0.3)
    plt.xticks(fontsize=18)
    plt.yticks(fontsize=18)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latency_comparison.png"), dpi=300)
    plt.close()
    print(f"Latency comparison plot saved to {output_dir}/latency_comparison.png")

if __name__ == "__main__":
    base_path = os.path.join(Path(__file__).parent)
    files = {
        "WiFi": (
            os.path.join(base_path, "results_pi_test/wireless_WiFi_Test/inverter_lcl_gap/60V/120_deg/usb_tcp_test_results_wireless_WiFi_Test_inverter_lcl_gap_60V_120_deg_test_0001.csv"),
            "purple"
        ),
        "UTP": (
            os.path.join(base_path, "results_pi_comparison_test/utp_unshielded_blue/inverter_lcl_gap/60V/120_deg/lan_test_results_utp_unshielded_blue_inverter_lcl_gap_60V_120_deg_test_0001.csv"),
            "red"
        ),
        "STP": (
            os.path.join(base_path, "results_pi_comparison_test/stp_shielded_green/inverter_lcl_gap/60V/120_deg/lan_test_results_stp_shielded_green_inverter_lcl_gap_60V_120_deg_test_0001.csv"),
            "blue"
        ),
        "Weakened UTP": (
            os.path.join(base_path, "results_7/lan_cat6_unshielded_stripped_unpaused_channel1/antenna_tuning_inverter_gap/60V/120_deg/lan_test_results_lan_cat6_unshielded_stripped_unpaused_channel1_antenna_tuning_inverter_gap_60V_120_deg_test_0001.csv"),
            "orange"
        ),
    }
    compare_latency_across_types(files)