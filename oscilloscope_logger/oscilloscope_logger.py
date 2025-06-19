# scope_logger.py

import pyvisa
import time
from datetime import datetime

LOG_FILE = "scope_log.txt"
RESOURCE = '/dev/usbtmc0'  # USBTMC path

def log_scope_measurements():
    try:
        rm = pyvisa.ResourceManager('@py')
        scope = rm.open_resource(RESOURCE)
        scope.timeout = 3000  # milliseconds

        print(f"Connected to: {scope.query('*IDN?').strip()}")
        print(f" Logging Vpp from CH1 every second... (Log: {LOG_FILE})")

        with open(LOG_FILE, "a") as f:
            while True:
                try:
                    vpp = scope.query(":MEASure:VPP? CHAN1").strip()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    log_entry = f"{timestamp} - Vpp: {vpp} V"
                    print(log_entry)
                    f.write(log_entry + "\n")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Read error: {e}")
                    time.sleep(1)

    except Exception as e:
        print(f"Could not connect to oscilloscope: {e}")

if __name__ == "__main__":
    log_scope_measurements()
