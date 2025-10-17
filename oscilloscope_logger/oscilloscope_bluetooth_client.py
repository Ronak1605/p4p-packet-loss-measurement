import serial
import pickle
import csv
import test_config
import subprocess
import time
import os

num_tests = 100
base_name = "usb_bt_test_results"
full_path = test_config.get_next_test_filepath(base_name)

# Pi Bluetooth address - get from hciconfig on Pi
PI_BT_ADDR = "2C:CF:67:6F:5D:40"

CSV_HEADER = [
    "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
    "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)",
    "Waveform Min", "Waveform Max", "Waveform Avg"
]

def create_rfcomm_connection():
    """Create RFCOMM connection using system rfcomm command"""
    print(f"=== Connecting to Pi via RFCOMM: {PI_BT_ADDR} ===")
    
    print("Step 1: Make sure devices are paired in System Preferences > Bluetooth")
    input("Press Enter when Pi and Mac are paired...")
    
    print("Step 2: Creating RFCOMM connection...")
    
    # Try to create RFCOMM connection to Pi on channel 1
    try:
        # Use rfcomm to connect to Pi
        print(f"Connecting to {PI_BT_ADDR} on RFCOMM channel 1...")
        
        # Create RFCOMM connection
        rfcomm_cmd = ['rfcomm', 'connect', '/dev/rfcomm0', PI_BT_ADDR, '1']
        print(f"Running: {' '.join(rfcomm_cmd)}")
        
        # Start rfcomm connection in background
        proc = subprocess.Popen(rfcomm_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for connection to be established
        print("Waiting for RFCOMM connection...")
        time.sleep(5)
        
        # Check if /dev/rfcomm0 was created
        if os.path.exists('/dev/rfcomm0'):
            try:
                ser = serial.Serial('/dev/rfcomm0', 115200, timeout=30)
                print("✓ RFCOMM connection established")
                return ser, proc
            except Exception as e:
                print(f"RFCOMM device created but can't open: {e}")
                proc.terminate()
        else:
            print("❌ RFCOMM device not created")
            proc.terminate()
    
    except Exception as e:
        print(f"RFCOMM connection failed: {e}")
    
    return None, None

def try_manual_connection():
    """Try manual connection using available serial ports"""
    print("\n=== Manual Connection Attempt ===")
    print("Looking for available serial ports...")
    
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No serial ports found")
        return None
    
    print("Available ports:")
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device} - {port.description}")
    
    while True:
        choice = input("Enter port number to try (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return None
        
        try:
            port_idx = int(choice) - 1
            if 0 <= port_idx < len(ports):
                port_device = ports[port_idx].device
                print(f"Trying {port_device}...")
                
                ser = serial.Serial(port_device, 115200, timeout=30)
                print(f"✓ Connected to {port_device}")
                return ser
            else:
                print("Invalid selection")
        except ValueError:
            print("Please enter a number")
        except Exception as e:
            print(f"Connection to {port_device} failed: {e}")

def main():
    print("=== Bluetooth Client (Mac) - Simple RFCOMM ===")
    
    # Try RFCOMM connection first
    ser, proc = create_rfcomm_connection()
    
    # If RFCOMM fails, try manual connection
    if not ser:
        print("RFCOMM connection failed, trying manual connection...")
        ser = try_manual_connection()
        proc = None
    
    if not ser:
        print("❌ Could not establish any Bluetooth connection")
        print("\nRecommendation: Use the working TCP connection instead")
        print("TCP is more reliable for data transfer")
        return

    try:
        print(f"\n✓ Connected! Receiving {num_tests} tests...")
        
        # Receive data exactly like TCP client
        with open(full_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["USB Test with Measurement Logging (Bluetooth)"])
            writer.writerow(CSV_HEADER)
            
            tests_received = 0
            
            for i in range(num_tests):
                print(f"Test {i+1}/{num_tests}...", end=' ')
                
                # Read length (4 bytes) - same as TCP
                length_bytes = ser.read(4)
                if len(length_bytes) != 4:
                    print(f"Failed to read length (got {len(length_bytes)} bytes)")
                    break
                
                length = int.from_bytes(length_bytes, 'big')
                
                # Read actual data
                data = b''
                while len(data) < length:
                    remaining = length - len(data)
                    packet = ser.read(remaining)
                    if not packet:
                        print("Connection lost")
                        break
                    data += packet
                
                if len(data) == length:
                    result = pickle.loads(data)
                    writer.writerow(result)
                    tests_received += 1
                    print(f"✓ {result[2]}")
                else:
                    print(f"Incomplete data ({len(data)}/{length} bytes)")
                    break
                
        print(f"\n✓ Received {tests_received}/{num_tests} tests")
        print(f"Results saved to {full_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if ser:
            ser.close()
        if proc:
            proc.terminate()
        # Clean up RFCOMM
        subprocess.run(['rfcomm', 'release', '/dev/rfcomm0'], capture_output=True)
        print("Connection closed")

if __name__ == "__main__":
    main()