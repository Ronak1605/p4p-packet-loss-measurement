import pyvisa
import time
import csv
from statistics import mean, median
from datetime import datetime

import test_config  # your config file

# Use config vars
cable_type = test_config.cable_type
position = test_config.position
power_state = test_config.power_state
conduction_angle = test_config.conduction_angle
PROBE_GAIN_MV_PER_A = test_config.PROBE_GAIN_MV_PER_A

# USB VISA address (replace with actual scope USB VISA address)
scope_usb_address = 'USB0::10893::5990::MY58493325::INSTR'

# Test parameters
num_tests = 50
timeout_sec = 2000  # ms

# Get output file path
base_name = "usb_test_results"
full_path = test_config.get_next_test_filepath(base_name)

def convert_vrms_to_current(vrms_str, gain_mV_per_A, channel):
    try:
        vrms = float(vrms_str)
        sensitivity_V_per_A = gain_mV_per_A / 1000.0
        return round(vrms / sensitivity_V_per_A, 6)
    except ValueError:
        print(f"Invalid VRMS value from {channel}: '{vrms_str}'")
        return float("nan")

# Connect to scope
rm = pyvisa.ResourceManager()
scope = rm.open_resource(scope_usb_address)
scope.timeout = timeout_sec

results = []
response_times = []
success_count = 0

print(f"Starting USB + measurement test: {full_path}")
start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
test_start = time.time()

for n in range(num_tests):
    t0 = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        response = scope.query('*IDN?').strip()
        elapsed = round((time.time() - t0) * 1000, 2)

        if response == "KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614":
            response_times.append(elapsed)

            v_rms = scope.query(":MEASure:VRMS? CHAN1").strip()
            acrms_ch2 = scope.query(":MEASure:ACRMS? CHAN2").strip()
            acrms_ch3 = scope.query(":MEASure:ACRMS? CHAN3").strip()

            results.append([
                n + 1,
                timestamp,
                "Success",
                elapsed,
                response,
                v_rms,
                acrms_ch2,
                acrms_ch3,
            ])
            success_count += 1

            print(f"[{n+1}/{num_tests}] {elapsed} ms | V RMS CH1: {v_rms} V | CH2: {acrms_ch2} A | CH3: {acrms_ch3} A")

        else:
            print(f"[{n+1}/{num_tests}] Unexpected response: {response}")
            results.append([
                n + 1,
                timestamp,
                "Unexpected Response",
                elapsed,
                response,
                "", "", ""
            ])

    except Exception as err:
        elapsed = round((time.time() - t0) * 1000, 2)
        results.append([
            n + 1,
            timestamp,
            "Timeout/Error",
            elapsed,
            str(err),
            "", "", ""
        ])
        print(f"[{n+1}/{num_tests}] Timeout/Error after {elapsed} ms: {err}")

    time.sleep(1)

# Summary Stats
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

# Write to CSV
with open(full_path, 'w', newline='') as f:
    writer = csv.writer(f)

    writer.writerow(["USB Test with Measurement Logging"])
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

    writer.writerow([
        "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
        "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)"
    ])
    writer.writerows(results)

print("\nTest completed.")
print(f"File saved to: {full_path}")
print(f"Start time: {start_time_str}")
print(f"End time: {end_time_str}")
print(f"Successful responses: {success_count}")
print(f"Lost packets: {loss} ({loss_percent:.2f}%)")
print(f"Mean: {mean_time} ms | Median: {median_time} ms | Min: {min_time} ms | Max: {max_time} ms")
