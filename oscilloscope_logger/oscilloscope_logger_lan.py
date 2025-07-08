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

# === Other Settings ===
scope_ip = '169.254.173.152'  # Replace with the oscilloscope IP
num_tests = 1000
command = '*IDN?'
timeout_sec = 2

# === Setup Output Path with Auto-Increment ===
base_name = f"lan_test_results_{cable_type}_{position}_{power_state}_{conduction_angle}"
i = 1
os.makedirs(test_folder, exist_ok=True)

while True:
    file_name = f"{base_name}_test_{i:04d}.csv"
    full_path = os.path.join(test_folder, file_name)
    if not os.path.exists(full_path):
        break
    i += 1

# === Set up VISA ===
rm = pyvisa.ResourceManager()
scope = rm.open_resource(f'TCPIP0::{scope_ip}::INSTR')
scope.timeout = timeout_sec * 1000  # ms

# === Logging Results ===
results = []
response_times = []
success_count = 0

print(f"Starting LAN test: {file_name}")
start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
test_start = time.time()

for i in range(num_tests):
    t0 = time.time()
    try:
        response = scope.query(command).strip()
        elapsed = round((time.time() - t0) * 1000, 2)
        
        ## Check if the response matches the expected result
        if response == "KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614":
            results.append((i + 1, "Success", elapsed, response))
            response_times.append(elapsed)
            success_count += 1
            print(f"[{i+1}/{num_tests}] Response in {elapsed} ms: {response}")
        else:
            results.append((i + 1, "Mismatch", elapsed, response))
            print(f"[{i+1}/{num_tests}] Mismatch: Expected response not received.")
    except pyvisa.errors.VisaIOError:
        elapsed = round((time.time() - t0) * 1000, 2)
        results.append((i + 1, "Timeout", elapsed, ""))
        print(f"[{i+1}/{num_tests}] Timeout after {elapsed} ms")

test_end = time.time()
end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
total_duration = round(test_end - test_start, 2)

# === Stats Calculation ===
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

    # Header
    writer.writerow(["LAN Communication Test Log"])
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

    # Data
    writer.writerow(["Attempt", "Status", "Response Time (ms)", "Response"])
    writer.writerows(results)

# === Print Summary ===
print("\nTest completed.")
print(f"File saved to: {full_path}")
print(f"Start time: {start_time_str}")
print(f"End time: {end_time_str}")
print(f"Total attempts: {num_tests}")
print(f"Successful responses: {success_count}")
print(f"Lost packets: {loss} ({loss_percent:.2f}%)")
print(f"Mean response time: {mean_time} ms")
print(f"Median response time: {median_time} ms")
print(f"Fastest response time: {min_time} ms")
print(f"Slowest response time: {max_time} ms")
