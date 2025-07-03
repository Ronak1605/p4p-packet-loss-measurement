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
RECONNECT_DELAY = 5  # seconds

def log_packet_loss_event(reason: str):
    """Logs a timestamped error or packet loss event."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    # If the reason is a keyboard interrupt, log it differently
    if reason == "Logging interrupted by user.":
        entry = f"{timestamp} - Logging interrupted by user."
        print(entry)
        with open(ERROR_LOG_FILE, "a") as f:
            f.write(entry + "\n")
        return
    
    # For actual errors, log accordingly
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

def connect_to_scope():
    """Try to connect to the oscilloscope. Retry loop if not found."""
    while not os.path.exists(SCOPE_DEVICE):
        log_packet_loss_event("Oscilloscope not connected. Retrying...")
        time.sleep(RECONNECT_DELAY)
    try:
        scope = open(SCOPE_DEVICE, "wb+", buffering=0)
        scope.write(b"*IDN?\n")
        idn = scope.read(100)
        print("Connected to:", idn.decode().strip())
        return scope
    except Exception as e:
        log_packet_loss_event(f"Failed to initialize communication: {e}")
        time.sleep(RECONNECT_DELAY)
        return connect_to_scope()

def log_scope_measurements():
    """Continuously logs oscilloscope measurements to file."""
    try:
        with open(LOG_FILE, "a") as log_file:
            scope = connect_to_scope()

            while True:
                try:
                    # Read Vpp from Channel 1
                    scope.write(b":MEASure:VPP? CHAN1\n")
                    vpp_ch1 = scope.read(100).decode().strip()

                    # Read AC RMS from CHAN2
                    scope.write(b":MEASure:ACRMS? CHAN2\n")
                    acrms_ch2 = scope.read(100).decode().strip()
                    # current_ch2 = convert_vrms_to_current(vrms_ch2, PROBE_GAIN_MV_PER_A["CHAN2"], "CHAN2")

                    # Read AC RMS from CHAN3
                    scope.write(b":MEASure:ACRMS? CHAN3\n")
                    acrms_ch3 = scope.read(100).decode().strip()
                    # current_ch3 = convert_vrms_to_current(vrms_ch3, PROBE_GAIN_MV_PER_A["CHAN3"], "CHAN3")

                    # Log
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    log_entry = (
                        f"{timestamp} - Vpp CH1: {vpp_ch1} V, "
                        f"AC RMS CH2: {acrms_ch2} A, "
                        f"AC RMS CH3: {acrms_ch3} A"
                    )
                    print(log_entry)
                    log_file.write(log_entry + "\n")

                except (OSError, IOError) as io_err:
                    log_packet_loss_event(f"Communication lost: {io_err}")
                    scope.close()
                    time.sleep(RECONNECT_DELAY)
                    scope = connect_to_scope()

                except Exception as unknown_err:
                    log_packet_loss_event(f"Unexpected error: {unknown_err}")
                    scope.close()
                    break

                time.sleep(1)

    except KeyboardInterrupt:
        log_packet_loss_event("Logging interrupted by user.")
    except Exception as outer_err:
        log_packet_loss_event(f"Logger crashed: {outer_err}")

if __name__ == "__main__":
    log_scope_measurements()
