import pyvisa
import time
from datetime import datetime

LOG_FILE = "scope_log.txt"

def log_scope_measurements():
    try:
        rm = pyvisa.ResourceManager('@py')  # use pyvisa-py backend
        instruments = rm.list_resources()

        print("Found resources:", instruments)

        # Try to find the scope by checking for USB instruments
        scope_resource = None
        for res in instruments:
            if "USB" in res:
                scope_resource = res
                break

        if not scope_resource:
            print("No USB oscilloscope found.")
            return

        scope = rm.open_resource(scope_resource)
        scope.timeout = 3000  # ms

        print(f"Connected to: {scope.query('*IDN?').strip()}")
        print(f"Logging Vpp from CH1 every second... (Log: {LOG_FILE})")

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
