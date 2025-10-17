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

def setup_bluetooth_simple():
    """Simplified Bluetooth setup using bluetoothctl"""
    print("Setting up Bluetooth using bluetoothctl...")
    
    try:
        # Use bluetoothctl commands
        commands = [
            "power on",
            "discoverable on", 
            "pairable on",
            "agent NoInputNoOutput",
            "default-agent"
        ]
        
        for cmd in commands:
            result = subprocess.run(['bluetoothctl'], input=f"{cmd}\nquit\n", 
                                  text=True, capture_output=True, timeout=5)
            print(f"Command '{cmd}': {result.stdout.strip()}")
            
        print("✓ Bluetooth configured successfully")
        print("Pi is now discoverable and pairable")
        
        # Get Pi's Bluetooth address
        result = subprocess.run(['bluetoothctl', 'show'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'Controller' in line:
                bt_addr = line.split()[1]
                print(f"Pi Bluetooth address: {bt_addr}")
                break
                
    except Exception as e:
        print(f"Bluetooth setup error: {e}")
        
def wait_for_serial_connection():
    """Wait for any serial connection that might be created by pairing"""
    print("\nWaiting for Bluetooth serial connection...")
    print("Please pair and connect from your Mac now:")
    print("1. Go to System Preferences > Bluetooth")
    print("2. Find and pair with this Pi")
    print("3. After pairing, try to connect")
    
    # Check multiple possible serial devices
    possible_devices = [
        '/dev/rfcomm0',
        '/dev/ttyS0', 
        '/dev/ttyAMA0',
        '/dev/serial0'
    ]
    
    for attempt in range(120):  # Wait up to 2 minutes
        # Check for RFCOMM devices
        for device in possible_devices:
            if os.path.exists(device):
                try:
                    ser = serial.Serial(device, 115200, timeout=10)
                    print(f"✓ Connected via {device}")
                    return ser
                except serial.SerialException:
                    continue
        
        # Also check for any new tty devices
        try:
            devices = os.listdir('/dev/')
            bt_devices = [d for d in devices if 'rfcomm' in d or 'bluetooth' in d.lower()]
            for device in bt_devices:
                device_path = f'/dev/{device}'
                try:
                    ser = serial.Serial(device_path, 115200, timeout=10)
                    print(f"✓ Connected via {device_path}")
                    return ser
                except serial.SerialException:
                    continue
        except:
            pass
            
        if attempt % 10 == 0:
            print(f"Still waiting... ({120-attempt}s remaining)")
        time.sleep(1)
    
    return None

def main():
    print("=== Bluetooth Server (Pi) ===")
    
    # Setup Bluetooth
    setup_bluetooth_simple()
    
    # Connect to oscilloscope
    try:
        rm = pyvisa.ResourceManager()
        scope = rm.open_resource(scope_usb_address)
        scope.timeout = timeout_sec
        print("✓ Oscilloscope connected")
    except Exception as e:
        print(f"❌ Failed to connect to oscilloscope: {e}")
        print("Make sure oscilloscope is connected and powered on")
        return

    tester = PacketLossTester(scope, "USB", num_tests)

    # Wait for Bluetooth connection
    ser = wait_for_serial_connection()
    
    if not ser:
        print("❌ No Bluetooth connection established")
        scope.close()
        rm.close()
        return

    try:
        print("✓ Bluetooth client connected, starting tests...")
        
        # Send tests exactly like TCP server
        for n in range(num_tests):
            print(f"Running test {n+1}/{num_tests}...")
            result = tester._run_single_test(n + 1)
            # Send result as pickled object (same as TCP)
            data = pickle.dumps(result)
            # Send length first (4 bytes, same as TCP)
            ser.write(len(data).to_bytes(4, 'big'))
            ser.write(data)
            ser.flush()
            
        print("✓ All tests sent. Closing connection.")
        
    except Exception as e:
        print(f"❌ Error during communication: {e}")
    finally:
        if ser:
            ser.close()
        scope.close()
        rm.close()

if __name__ == "__main__":
    main()