import time
from datetime import datetime

def log_scope_vpp_directly():
    with open("/dev/usbtmc0", "wb+", buffering=0) as scope, open("scope_log.txt", "a") as log_file:
        scope.write(b"*IDN?\n")
        idn = scope.read(100)
        print("Connected to:", idn.decode().strip())

        while True:
            scope.write(b":MEASure:VPP? CHAN1\n")
            vpp = scope.read(100).decode().strip()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            log_entry = f"{timestamp} - Vpp: {vpp} V"
            print(log_entry)
            log_file.write(log_entry + "\n")
            time.sleep(1)

if __name__ == "__main__":
    log_scope_vpp_directly()
