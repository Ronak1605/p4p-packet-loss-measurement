import time
from datetime import datetime

def log_scope_vpp_and_current_probes():
    probe_sensitivity_mV_per_A = 100  # Replace with your probe's actual sensitivity

    with open("/dev/usbtmc0", "wb+", buffering=0) as scope, open("scope_log.txt", "a") as log_file:
        scope.write(b"*IDN?\n")
        idn = scope.read(100)
        print("Connected to:", idn.decode().strip())

        while True:
            scope.write(b":MEASure:VPP? CHAN1\n")
            vpp_ch1 = scope.read(100).decode().strip()

            scope.write(b":MEASure:VRMS? CHAN2\n")
            vrms_ch2 = scope.read(100).decode().strip()

            scope.write(b":MEASure:VRMS? CHAN3\n")
            vrms_ch3 = scope.read(100).decode().strip()

            try:
                current_ch2 = float(vrms_ch2) / (probe_sensitivity_mV_per_A / 1000)
                current_ch3 = float(vrms_ch3) / (probe_sensitivity_mV_per_A / 1000)
            except ValueError:
                current_ch2 = current_ch3 = float('nan')

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            log_entry = (f"{timestamp} - Vpp CH1: {vpp_ch1} V, "
                         f"Current CH2: {current_ch2:.3f} A, Current CH3: {current_ch3:.3f} A")
            print(log_entry)
            log_file.write(log_entry + "\n")
            time.sleep(1)

if __name__ == "__main__":
    log_scope_vpp_and_current_probes()
