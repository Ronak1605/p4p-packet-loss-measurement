import serial
import pickle
import csv
import test_config
import time

num_tests = 100
base_name = "usb_bt_test_results"
full_path = test_config.get_next_test_filepath(base_name)

# Pi Bluetooth address - get from hciconfig on Pi
PI_BT_ADDR = "2C:CF:67:6F:5D:40"  # Replace with your Pi's actual address

CSV_HEADER = [
    "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
    "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)",
    "Waveform Min", "Waveform Max", "Waveform Avg"
]

def connect_via_rfcomm():
    """Connect using RFCOMM protocol (works on both platforms)"""
    print(f"Connecting to Pi via RFCOMM: {PI_BT_ADDR}")
    
    try:
        import bluetooth
        
        # Discover services on the Pi
        print("Discovering Bluetooth services...")
        services = bluetooth.find_service(address=PI_BT_ADDR)
        
        if not services:
            print("No services found on Pi")
            return None
            
        # Look for Serial Port Profile service
        target_service = None
        for service in services:
            if "serial" in service['name'].lower() or service['protocol'] == 'RFCOMM':
                target_service = service
                break
        
        if not target_service:
            print("No RFCOMM/Serial service found")
            return None
            
        # Connect to the service
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((PI_BT_ADDR, target_service['port']))
        
        print(f"✓ RFCOMM connection established on port {target_service['port']}")
        return sock
        
    except ImportError:
        print("❌ Python bluetooth library not available")
        print("Install with: pip install pybluez")
        return None
    except Exception as e:
        print(f"❌ RFCOMM connection failed: {e}")
        return None

def main():
    print("=== Bluetooth RFCOMM Client (Mac) ===")
    print("Make sure:")
    print("1. Pi server is running")
    print("2. Devices are paired in System Preferences > Bluetooth") 
    print()
    
    # Connect via RFCOMM
    sock = connect_via_rfcomm()
    
    if not sock:
        print("❌ Could not establish RFCOMM connection")
        return

    try:
        print(f"✓ Connected! Receiving {num_tests} tests...")
        
        # Convert socket to file-like object
        sock_file = sock.makefile('rb')
        
        # Receive data exactly like TCP client
        with open(full_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["USB Test with Measurement Logging (Bluetooth)"])
            writer.writerow(CSV_HEADER)
            
            for i in range(num_tests):
                print(f"Test {i+1}/{num_tests}...", end=' ')
                
                # Read length (4 bytes) - same as TCP
                length_bytes = sock_file.read(4)
                if len(length_bytes) != 4:
                    print(f"Failed to read length")
                    break
                
                length = int.from_bytes(length_bytes, 'big')
                
                # Read actual data
                data = sock_file.read(length)
                if len(data) != length:
                    print(f"Incomplete data")
                    break
                
                result = pickle.loads(data)
                writer.writerow(result)
                print(f"✓ {result[2]}")
                
        print(f"\n✓ All tests completed!")
        print(f"Results saved to {full_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        sock.close()
        print("Connection closed")

if __name__ == "__main__":
    main()