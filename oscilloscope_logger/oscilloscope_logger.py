import os
import time
from datetime import datetime

# === Probe sensitivity in mV/A for each channel ===
PROBE_GAIN_MV_PER_A = {
    "CHAN2": 70,  # CH2 connected to RCP300XS
    "CHAN3": 70,  # CH3 connected to RCP300XS
}

SCOPE_DEVICE = "/dev/usbtmc0"
LOG_FILE = "scope_log.txt"
ERROR_LOG_FILE = "packet_loss_log.txt"

def log_packet_loss_event(reason: str):
    """Logs a timestamped error or packet loss event."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    entry = f"{timestamp} - PACKET LOSS or ERROR: {reason}"
    print(entry)
    with open(ERROR_LOG_FILE, "a") as f:
        f.write(entry + "\n")

def convert_vrms_to_current(vrms_str, gain_mV_per_A, channel):
    """Convert Vrms to current using probe gain (in mV/A)."""
    try:
        vrms = float(vrms_str)
        sensitivity_V_per_A = gain_mV_per_A / 1000.0  # Convert mV to V
        current = vrms / sensitivity_V_per_A
        return current
    except ValueError:
        log_packet_loss_event(f"Invalid VRMS value from {channel}: '{vrms_str}'")
        return float("nan")

def log_scope_measurements():
    """Continuously logs oscilloscope measurements to file."""
    if not os.path.exists(SCOPE_DEVICE):
        log_packet_loss_event("Oscilloscope not connected at startup.")
        return

    try:
        with open(SCOPE_DEVICE, "wb+", buffering=0) as scope, open(LOG_FILE, "a") as log_file:
            scope.write(b"*IDN?\n")
            idn = scope.read(100)
            print("Connected to:", idn.decode().strip())

            while True:
                try:
                    # Read Vpp from Channel 1
                    scope.write(b":MEASure:VPP? CHAN1\n")
                    vpp_ch1 = scope.read(100).decode().strip()

                    # Read Vrms from CHAN2
                    scope.write(b":MEASure:VRMS? CHAN2\n")
                    vrms_ch2 = scope.read(100).decode().strip()
                    current_ch2 = convert_vrms_to_current(vrms_ch2, PROBE_GAIN_MV_PER_A["CHAN2"], "CHAN2")
                    ch2_range_estimate = "approx. –75 mA to +5 mA"

                    # Read Vrms from CHAN3
                    scope.write(b":MEASure:VRMS? CHAN3\n")
                    vrms_ch3 = scope.read(100).decode().strip()
                    current_ch3 = convert_vrms_to_current(vrms_ch3, PROBE_GAIN_MV_PER_A["CHAN3"], "CHAN3")

                    # Timestamp and log
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    log_entry = (
                        f"{timestamp} - Vpp CH1: {vpp_ch1} V, "
                        f"Vrms CH2: {vrms_ch2} V → RMS Current: {current_ch2:.3f} A ({ch2_range_estimate}), "
                        f"Vrms CH3: {vrms_ch3} V → Current: {current_ch3:.3f} A"
                    )
                    print(log_entry)
                    log_file.write(log_entry + "\n")

                except Exception as inner_err:
                    log_packet_loss_event(f"Measurement read error: {inner_err}")
                    break

                time.sleep(1)

    except Exception as outer_err:
        log_packet_loss_event(f"Failed to open oscilloscope device: {outer_err}")

if __name__ == "__main__":
    log_scope_measurements()
