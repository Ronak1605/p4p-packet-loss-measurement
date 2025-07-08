import pyvisa
import time
import csv
import os
from statistics import mean, median
from datetime import datetime

# === Configurable Test Info (change for each test) ===
cable_type = 'cat_5_utp'
position = 'test_switches'
power_state = 'no_power'
conduction_angle = 'mc_off'
test_folder = f'results/{cable_type}/{position}/{power_state}/{conduction_angle}'

# === Measurement Conversion Constants ===
PROBE_GAIN_MV_PER_A = {
    "CHAN2": 70,
    "CHAN3": 70,
}

# === VISA & Test Settings ===
scope_ip = '169.254.60.80'
num_tests = 50
command = '*IDN?'
timeout_sec = 2

# === Generate Output File Path with Auto-Increment ===
base_name = f"lan_test_results_{cable_type}_{position}_{power_state}_{conduction_angle}"
i = 1
os.makedirs(test_folder, exist_ok=True)

while True:
    file_name = f"{base_name}_test_{i:04d}.csv"
    full_path = os.path.join(test_folder, file_name)
    if not os.path.exists(full_path):
        break
    i += 1

# === Function to convert Vrms to current ===
def convert_vrms_to_current(vrms_str, gain_mV_per_A, channel):
    try:
        vrms = float(vrms_str)
        sensitivity_V_per_A = gain_mV_per_A / 1000.0
        return round(vrms / sensitivity_V_per_A, 6)
    except ValueError:
        print(f"Invalid VRMS value from {channel}: '{vrms_str}'")
        return float("nan")

# === Connect to Scope ===
rm = pyvisa.ResourceManager()
scope = rm.open_resource(f'TCPIP0::{scope_ip}::INSTR')
scope.timeout = timeout_sec * 1000

# === Results Logging ===
results = []
response_times = []
success_count = 0

print(f"Starting LAN + measurement test: {file_name}")
start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
test_start = time.time()

for n in range(num_tests):
    t0 = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    try:
        response = scope.query(command).strip()
        elapsed = round((time.time() - t0) * 1000, 2)
        response_times.append(elapsed)

        # === Measurement Queries ===
        vpp_ch1 = scope.query(":MEASure:VPP? CHAN1").strip()
        acrms_ch2 = scope.query(":MEASure:ACRMS? CHAN2").strip()
        acrms_ch3 = scope.query(":MEASure:ACRMS? CHAN3").strip()

        # === Current Conversion ===
        """  current_ch2 = convert_vrms_to_current(acrms_ch2, PROBE_GAIN_MV_PER_A["CHAN2"], "CHAN2")
        current_ch3 = convert_vrms_to_current(acrms_ch3, PROBE_GAIN_MV_PER_A["CHAN3"], "CHAN3") """

        results.append([
            n + 1,
            timestamp,
            "Success",
            elapsed,
            response,
            vpp_ch1,
            acrms_ch2,
            acrms_ch3,
        ])
        success_count += 1

        print(f"[{n+1}/{num_tests}] {elapsed} ms | Vpp CH1: {vpp_ch1} V | CH2: {acrms_ch2} A | CH3: {acrms_ch3} A")

    except Exception as err:
        elapsed = round((time.time() - t0) * 1000, 2)
        results.append([
            n + 1,
            timestamp,
            "Timeout",
            elapsed,
            str(err),
            "", "", "", "", ""
        ])
        print(f"[{n+1}/{num_tests}] Timeout after {elapsed} ms: {err}")

    time.sleep(1)

# === Summary Stats ===
test_end = time.time()
end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
total_duration = round(test_end - test_start, 2)

loss = num_tests - success_count
loss_percent = round((loss / num_tests) * 100, 2)
if response_times:
    mean_time = round(mean(response_times), 2)
    median_time = round(median(response_times), 2)
    min_time = round(min(response_times), 2)
    max_time = round(max(response_times), 2)
else:
    mean_time = median_time = min_time = max_time = "N/A"

# === Write to CSV ===
with open(full_path, 'w', newline='') as f:
    writer = csv.writer(f)

    # Header info
    writer.writerow(["LAN Test with Measurement Logging"])
    writer.writerow(["Start Time", start_time_str])
    writer.writerow(["End Time", end_time_str])
    writer.writerow(["Cable Type", cable_type])
    writer.writerow(["Position", position])
    writer.writerow(["Power State", power_state])
    writer.writerow(["Conduction Angle", conduction_angle])
    writer.writerow(["Total Attempts", num_tests])
    writer.writerow(["Successful Responses", success_count])
    writer.writerow(["Lost Packets", loss])
    writer.writerow(["Loss %", loss_percent])
    writer.writerow(["Mean Response Time (ms)", mean_time])
    writer.writerow(["Median Response Time (ms)", median_time])
    writer.writerow(["Min Response Time (ms)", min_time])
    writer.writerow(["Max Response Time (ms)", max_time])
    writer.writerow(["Total Duration (s)", total_duration])
    writer.writerow([])

    # Data header
    writer.writerow([
        "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
        "Vpp CH1 (V)", "Current CH2 (A)", "AC RMS CH3 (A)"
    ])
    writer.writerows(results)

# === Print Summary ===
print("\nTest completed.")
print(f"File saved to: {full_path}")
print(f"Start time: {start_time_str}")
print(f"End time: {end_time_str}")
print(f"Successful responses: {success_count}")
print(f"Lost packets: {loss} ({loss_percent:.2f}%)")
print(f"Mean: {mean_time} ms | Median: {median_time} ms | Min: {min_time} ms | Max: {max_time} ms")
