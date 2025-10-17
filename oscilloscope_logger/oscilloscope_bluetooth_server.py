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

def wait_for_bluetooth_connection():
    """Wait for ACTUAL Bluetooth client connection (not built-in serial ports)"""
    print("\nWaiting for Bluetooth client connection...")
    print("Please connect from your Mac:")
    print("1. Pair with this Pi in System Preferences > Bluetooth")
    print("2. Run the client script on your Mac")
    print("3. Select the Bluetooth port when prompted")
    
    # Only check for RFCOMM devices (actual Bluetooth connections)
    # Exclude built-in serial ports that always exist
    bluetooth_only_devices = [
        '/dev/rfcomm0',
        '/dev/rfcomm1', 
        '/dev/rfcomm2',
        '/dev/rfcomm3',
        '/dev/rfcomm4'
    ]
    
    print("Monitoring for RFCOMM Bluetooth connections only...")
    print("(Ignoring built-in serial ports like /dev/serial0, /dev/ttyS0, etc.)")
    
    # Track which devices existed before we started waiting
    initial_devices = set()
    try:
        initial_devices = set(os.listdir('/dev/'))
    except:
        pass
    
    for attempt in range(600):  # Wait up to 10 minutes
        
        # Only check RFCOMM devices (real Bluetooth connections)
        for device in bluetooth_only_devices:
            if os.path.exists(device):
                try:
                    print(f"Found RFCOMM device: {device}")
                    # Try to open it - if it fails, no client is connected
                    ser = serial.Serial(device, 115200, timeout=2)
                    
                    # Test if there's actually a client by trying to read
                    # If no client, this will timeout quickly
                    print(f"Testing if {device} has an active client...")
                    test_read = ser.read(1)  # Try to read 1 byte with 2-second timeout
                    
                    if test_read or True:  # Accept connection even if no immediate data
                        print(f"✓ Bluetooth client connected via {device}")
                        return ser
                    else:
                        print(f"No active client on {device}")
                        ser.close()
                        
                except serial.SerialException as e:
                    print(f"Cannot open {device}: {e}")
                    continue
        
        # Check for any NEW devices that appeared (might be Bluetooth-related)
        try:
            current_devices = set(os.listdir('/dev/'))
            new_devices = current_devices - initial_devices
            
            for device_name in new_devices:
                if 'bluetooth' in device_name.lower() or 'bt' in device_name.lower():
                    device_path = f'/dev/{device_name}'
                    try:
                        ser = serial.Serial(device_path, 115200, timeout=2)
                        print(f"✓ New Bluetooth device connected: {device_path}")
                        return ser
                    except serial.SerialException:
                        continue
        except:
            pass
            
        if attempt % 30 == 0:  # Print every 30 seconds
            minutes_remaining = (600 - attempt) // 60
            print(f"Still waiting for RFCOMM connection... ({minutes_remaining} minutes remaining)")
            print("Make sure to:")
            print("  - Pair devices in System Preferences > Bluetooth")
            print("  - Run the client script which will create the RFCOMM connection")
            
        time.sleep(1)
    
    print("❌ Timeout waiting for Bluetooth client connection")
    return None

def main():
    print("=== Bluetooth Server (Pi) ===")
    
    # Connect to oscilloscope FIRST (same as TCP server)
    print("Connecting to oscilloscope...")
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

    # Setup Bluetooth
    setup_bluetooth_simple()
    
    # WAIT for ACTUAL client connection (not built-in serial ports)
    ser = wait_for_bluetooth_connection()
    
    if not ser:
        print("❌ No Bluetooth client connection established")
        scope.close()
        rm.close()
        return

    try:
        print("✓ Real Bluetooth client connected, starting tests...")
        
        # NOW run tests (same as TCP server - ONLY after client connects)
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
        print(f"❌ Error during communication: {e}")
    finally:
        if ser:
            ser.close()
        scope.close()
        rm.close()

if __name__ == "__main__":
    main()