import serial
import pickle
import csv
import test_config
import subprocess

num_tests = 100
base_name = "usb_bt_test_results"
full_path = test_config.get_next_test_filepath(base_name)

# Hardcoded Pi Bluetooth address - find this by running "bluetoothctl show" on the Pi
PI_BT_ADDR = "2C:CF:67:6F:5D:40"  # Replace with your Pi's actual Bluetooth MAC address

CSV_HEADER = [
    "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
    "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)",
    "Waveform Min", "Waveform Max", "Waveform Avg"
]

def setup_bluetooth_connection():
    """Set up Bluetooth connection to Pi"""
    try:
        print(f"Connecting to Pi at {PI_BT_ADDR} via Bluetooth...")
        
        # Try to bind RFCOMM (requires pairing first)
        cmd = ['sudo', 'rfcomm', 'connect', '/dev/rfcomm0', PI_BT_ADDR, '1']
        print("Establishing RFCOMM connection...")
        
        # This will block until connection is established
        proc = subprocess.Popen(cmd)
        
        # Wait a moment for connection to establish
        import time
        time.sleep(3)
        
        if proc.poll() is None:  # Process is still running (good)
            try:
                ser = serial.Serial('/dev/rfcomm0', 115200, timeout=30)
                print("Bluetooth serial connection established")
                return ser, proc
            except serial.SerialException as e:
                print(f"Failed to open serial port: {e}")
                proc.terminate()
                return None, None
        else:
            print("RFCOMM connection failed")
            return None, None
            
    except Exception as e:
        print(f"Error setting up Bluetooth: {e}")
        return None, None

def main():
    # Set up Bluetooth connection (mirrors TCP connect)
    ser, rfcomm_proc = setup_bluetooth_connection()
    
    if not ser:
        print("Failed to establish Bluetooth connection")
        print("Make sure:")
        print("1. Devices are paired in System Preferences > Bluetooth") 
        print("2. Pi server is running")
        print("3. Bluetooth is enabled on both devices")
        return

    try:
        print("Connected, receiving data...")
        
        # Receive data exactly like TCP client
        with open(full_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["USB Test with Measurement Logging (Bluetooth)"])
            writer.writerow(CSV_HEADER)
            
            for _ in range(num_tests):
                # Read length first (4 bytes) - same as TCP
                length_bytes = ser.read(4)
                if len(length_bytes) != 4:
                    break
                length = int.from_bytes(length_bytes, 'big')
                
                # Read the actual data - same as TCP
                data = b''
                while len(data) < length:
                    packet = ser.read(length - len(data))
                    if not packet:
                        break
                    data += packet
                
                result = pickle.loads(data)
                writer.writerow(result)
                print(f"Logged: {result}")
                
        print(f"Results saved to {full_path}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if ser:
            ser.close()
        if rfcomm_proc:
            rfcomm_proc.terminate()
        # Clean up
        subprocess.run(['sudo', 'rfcomm', 'release', '/dev/rfcomm0'], capture_output=True)

if __name__ == "__main__":
    main()