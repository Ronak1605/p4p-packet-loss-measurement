import pyvisa
import socket
import pickle
from packet_loss_tester import PacketLossTester

scope_usb_address = 'USB0::10893::5990::MY58493325::INSTR'
num_tests = 100
timeout_sec = 2000  # ms

HOST = '0.0.0.0'
PORT = 5005

"""TCP server to be run on the Pi connected to the oscilloscope."""
def main():
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource(scope_usb_address)
    scope.timeout = timeout_sec

    tester = PacketLossTester(scope, "USB", num_tests)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"Waiting for PC connection on {HOST}:{PORT}...")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            for n in range(num_tests):
                result = tester._run_single_test(n + 1)
                # Send result as a pickled object for reliability
                data = pickle.dumps(result)
                # Send length first (fixed 4 bytes, network order)
                conn.sendall(len(data).to_bytes(4, 'big'))
                conn.sendall(data)
            print("All tests sent. Closing connection.")
    scope.close()
    rm.close()

if __name__ == "__main__":
    main()