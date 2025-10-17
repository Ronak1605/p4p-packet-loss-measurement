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

"""Simple Bluetooth server using rfcomm bind (no pybluez required)"""

def setup_bluetooth():
    """Setup Bluetooth using system tools"""
    print("Setting up Bluetooth...")
    
    try:
        # Enable Bluetooth and make discoverable
        subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], check=False)
        subprocess.run(['sudo', 'hciconfig', 'hci0', 'piscan'], check=False)
        
        # Get Bluetooth address
        result = subprocess.run(['hciconfig'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'BD Address:' in line:
                addr = line.split('BD Address: ')[1].split()[0]
                print(f"Pi Bluetooth Address: {addr}")
                break
        
        # Set up RFCOMM listening on channel 1
        print("Setting up RFCOMM server on channel 1...")
        
        # Kill any existing RFCOMM connections
        subprocess.run(['sudo', 'pkill', '-f', 'rfcomm'], capture_output=True)
        subprocess.run(['sudo', 'rfcomm', 'release', 'all'], capture_output=True)
        
        # Bind RFCOMM channel 1 to listen for connections
        bind_result = subprocess.run(['sudo', 'rfcomm', 'listen', '/dev/rfcomm0', '1'], 
                                   capture_output=True, text=True, timeout=2)
        
        print("✓ Bluetooth setup complete - listening on RFCOMM channel 1")
        print("Pi is discoverable and ready for connection")
        return True
        
    except Exception as e:
        print(f"Bluetooth setup error: {e}")
        return False

def wait_for_bluetooth_connection():
    """Wait for RFCOMM connection from Mac client"""
    print("\n=== Waiting for Bluetooth RFCOMM Connection ===")
    print("On your Mac:")
    print("1. Pair with this Pi in System Preferences > Bluetooth (if not already paired)")
    print("2. Run the Bluetooth client script")
    print("3. Client will create RFCOMM connection on channel 1")
    
    # Start RFCOMM server in background
    print("Starting RFCOMM server...")
    
    try:
        # Use rfcomm to wait for incoming connection
        proc = subprocess.Popen(['sudo', 'rfcomm', 'watch', '/dev/rfcomm0', '1'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for /dev/rfcomm0 to become available
        for attempt in range(300):  # 5 minutes
            if os.path.exists('/dev/rfcomm0'):
                # Try to open the connection
                try:
                    time.sleep(1)  # Let connection stabilize
                    ser = serial.Serial('/dev/rfcomm0', 115200, timeout=10)
                    print(f"✓ RFCOMM client connected via /dev/rfcomm0")
                    return ser, proc
                except serial.SerialException as e:
                    print(f"RFCOMM device exists but can't open: {e}")
                    continue
            
            if attempt % 30 == 0:
                remaining_min = (300 - attempt) // 60
                print(f"Still waiting for RFCOMM connection... ({remaining_min} minutes remaining)")
            
            time.sleep(1)
        
        # Timeout
        proc.terminate()
        return None, None
        
    except Exception as e:
        print(f"Error setting up RFCOMM server: {e}")
        return None, None

def main():
    print("=== Bluetooth Server (Pi) - Simple RFCOMM ===")
    
    # Connect to oscilloscope first (same as TCP)
    print("Connecting to oscilloscope...")
    try:
        rm = pyvisa.ResourceManager()
        scope = rm.open_resource(scope_usb_address)
        scope.timeout = timeout_sec
        print("✓ Oscilloscope connected")
    except Exception as e:
        print(f"❌ Failed to connect to oscilloscope: {e}")
        return

    tester = PacketLossTester(scope, "USB", num_tests)

    # Setup Bluetooth
    if not setup_bluetooth():
        print("❌ Bluetooth setup failed")
        scope.close()
        rm.close()
        return

    # Wait for client connection
    ser, proc = wait_for_bluetooth_connection()
    
    if not ser:
        print("❌ No Bluetooth client connected")
        scope.close()
        rm.close()
        return

    try:
        print("✓ Client connected! Starting tests...")
        
        # Send tests exactly like TCP server
        for n in range(num_tests):
            print(f"Running test {n+1}/{num_tests}...")
            result = tester._run_single_test(n + 1)
            
            # Send data using same protocol as TCP
            data = pickle.dumps(result)
            ser.write(len(data).to_bytes(4, 'big'))  # Length first
            ser.write(data)                          # Then data
            ser.flush()                              # Ensure sent
            
        print("✓ All tests completed and sent")
        
    except Exception as e:
        print(f"❌ Error during tests: {e}")
    finally:
        print("Closing connections...")
        if ser:
            ser.close()
        if proc:
            proc.terminate()
        # Clean up RFCOMM
        subprocess.run(['sudo', 'rfcomm', 'release', '/dev/rfcomm0'], capture_output=True)
        scope.close()
        rm.close()

if __name__ == "__main__":
    main()