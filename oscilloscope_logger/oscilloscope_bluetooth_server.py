import pyvisa
import pickle
from packet_loss_tester import PacketLossTester
import subprocess
import serial
import time
import os

scope_usb_address = 'USB0::10893::5990::MY58493325::INSTR'
num_tests = 100
timeout_sec = 2000  # ms

"""Bluetooth server to be run on the Pi connected to the oscilloscope."""

def setup_bluetooth_rfcomm():
    """Set up Bluetooth RFCOMM server using system tools"""
    try:
        # Make Bluetooth discoverable
        subprocess.run(['sudo', 'hciconfig', 'hci0', 'piscan'], check=True)
        print("Bluetooth made discoverable")
        
        # Kill any existing rfcomm processes
        subprocess.run(['sudo', 'pkill', '-f', 'rfcomm'], capture_output=True)
        
        print("Waiting for Bluetooth RFCOMM connection on channel 1...")
        print("Connect from your Mac to complete the connection")
        
        # Wait for RFCOMM connection to be established
        for i in range(60):  # Wait up to 60 seconds
            if os.path.exists('/dev/rfcomm0'):
                try:
                    ser = serial.Serial('/dev/rfcomm0', 115200, timeout=10)
                    print("Bluetooth RFCOMM connection established")
                    return ser
                except serial.SerialException:
                    pass
            time.sleep(1)
            if i % 10 == 0:
                print(f"Still waiting for connection... ({60-i}s remaining)")
                
        return None
        
    except subprocess.CalledProcessError as e:
        print(f"Error setting up Bluetooth: {e}")
        return None

def main():
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource(scope_usb_address)
    scope.timeout = timeout_sec

    tester = PacketLossTester(scope, "USB", num_tests)

    # Set up Bluetooth connection (mirrors TCP socket setup)
    ser = setup_bluetooth_rfcomm()
    
    if not ser:
        print("Failed to establish Bluetooth connection")
        scope.close()
        rm.close()
        return

    try:
        print("Bluetooth client connected, starting tests...")
        
        # Send tests exactly like TCP server
        for n in range(num_tests):
            result = tester._run_single_test(n + 1)
            # Send result as pickled object (same as TCP)
            data = pickle.dumps(result)
            # Send length first (4 bytes, same as TCP)
            ser.write(len(data).to_bytes(4, 'big'))
            ser.write(data)
            ser.flush()
            
        print("All tests sent. Closing connection.")
        
    except Exception as e:
        print(f"Error during communication: {e}")
    finally:
        ser.close()
        scope.close()
        rm.close()
        # Clean up RFCOMM
        subprocess.run(['sudo', 'rfcomm', 'release', '/dev/rfcomm0'], capture_output=True)

if __name__ == "__main__":
    main()