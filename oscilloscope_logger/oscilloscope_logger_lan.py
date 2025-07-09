import pyvisa
import time
import csv
from statistics import mean, median
from datetime import datetime
from test_config import PROBE_GAIN_MV_PER_A, get_next_test_filepath

# === VISA & Test Settings ===
scope_ip = '169.254.212.203'
num_tests = 50
command = '*IDN?'
timeout_sec = 2

# === Output Path ===
full_path = get_next_test_filepath("lan_test_results")

# === SCPI Current Conversion (not used for now)
def convert_vrms_to_current(vrms_str, gain_mV_per_A, channel):
    try:
        vrms = float(vrms_str)
        return round(vrms / (gain_mV_per_A / 1000.0), 6)
    except ValueError:
        return float("nan")

# === Connect and Test ===
rm = pyvisa.ResourceManager()
scope = rm.open_resource(f'TCPIP0::{scope_ip}::INSTR')
scope.timeout = timeout_sec * 1000

results, response_times = [], []
success_count = 0

start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
test_start = time.time()
print(f"Starting LAN test, saving to: {full_path}")

for n in range(num_tests):
    t0 = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        response = scope.query(command).strip()
        elapsed = round((time.time() - t0) * 1000, 2)

        if response == "KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614":
            response_times.append(elapsed)
            v_rms = scope.query(":MEASure:VRMS? CHAN1").strip()
            acrms_ch2 = scope.query(":MEASure:ACRMS? CHAN2").strip()
            acrms_ch3 = scope.query(":MEASure:ACRMS? CHAN3").strip()

            results.append([n+1, timestamp, "Success", elapsed, response, v_rms, acrms_ch2, acrms_ch3])
            print(f"[{n+1}] {elapsed} ms | VRMS CH1: {v_rms} V | CH2: {acrms_ch2} A | CH3: {acrms_ch3} A")
            success_count += 1
        else:
            results.append([n+1, timestamp, "Unexpected Response", elapsed, response, "", "", ""])
    except Exception as err:
        results.append([n+1, timestamp, "Timeout", "", str(err), "", "", ""])

    time.sleep(1)

# === Summary ===
test_end = time.time()
loss = num_tests - success_count
stats = {
    "Start Time": start_time_str,
    "End Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    "Success Count": success_count,
    "Loss Count": loss,
    "Loss %": round((loss / num_tests) * 100, 2),
    "Mean": round(mean(response_times), 2) if response_times else "N/A",
    "Median": round(median(response_times), 2) if response_times else "N/A",
    "Min": round(min(response_times), 2) if response_times else "N/A",
    "Max": round(max(response_times), 2) if response_times else "N/A",
    "Total Duration (s)": round(test_end - test_start, 2)
}

# === Write CSV ===
with open(full_path, 'w', newline='') as f:
    writer = csv.writer(f)
    for k, v in stats.items():
        writer.writerow([k, v])
    writer.writerow([])
    writer.writerow(["Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
                     "VRMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)"])
    writer.writerows(results)

print("Test complete. File saved:", full_path)
