import socket
import pickle
import csv
import test_config

num_tests = 100
base_name = "usb_tcp_test_results"
full_path = test_config.get_next_test_filepath(base_name)
PI_IP = '192.168.0.50'  # Replace Raspberry Pi's IP address as necessary
PORT = 5005

CSV_HEADER = [
    "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
    "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)",
    "Waveform Min", "Waveform Max", "Waveform Avg"
]

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Connecting to Pi at {PI_IP}:{PORT} ...")
        s.connect((PI_IP, PORT))
        with open(full_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write metadata (same as save_results_to_csv)
            writer.writerow(["USB Test with Measurement Logging"])
            # You can add more metadata rows here if needed, e.g.:
            # writer.writerow(["Start Time", ...])
            writer.writerow(CSV_HEADER)
            for _ in range(num_tests):
                # Read length first (4 bytes)
                length_bytes = s.recv(4)
                if not length_bytes:
                    break
                length = int.from_bytes(length_bytes, 'big')
                # Read the actual data
                data = b''
                while len(data) < length:
                    packet = s.recv(length - len(data))
                    if not packet:
                        break
                    data += packet
                result = pickle.loads(data)
                writer.writerow(result)
                print(f"Logged: {result}")
        print(f"Results saved to {full_path}")

if __name__ == "__main__":
    main()