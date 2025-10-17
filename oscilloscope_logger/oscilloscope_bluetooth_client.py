import serial
import pickle
import csv
import test_config
import serial.tools.list_ports
import time

num_tests = 100
base_name = "usb_bt_test_results"
full_path = test_config.get_next_test_filepath(base_name)

CSV_HEADER = [
    "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
    "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)",
    "Waveform Min", "Waveform Max", "Waveform Avg"
]

def find_bluetooth_port():
    """Find Bluetooth serial port by listing all ports"""
    print("=== Available Serial Ports ===")
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No serial ports found")
        return None
    
    bluetooth_ports = []
    all_ports = []
    
    for i, port in enumerate(ports):
        all_ports.append(port)
        description = port.description.lower()
        device = port.device.lower()
        
        print(f"{i+1}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {getattr(port, 'hwid', 'Unknown')}")
        
        # Look for Bluetooth indicators
        if any(keyword in description for keyword in 
               ['bluetooth', 'bt', 'serial', 'spp', 'rfcomm']):
            bluetooth_ports.append((i+1, port))
            print("   ^ Potential Bluetooth port")
        print()
    
    if bluetooth_ports:
        print("Potential Bluetooth ports found:")
        for num, port in bluetooth_ports:
            print(f"  {num}. {port.device} - {port.description}")
        print()
    
    # Let user choose
    while True:
        if bluetooth_ports:
            print("Enter the number of the Bluetooth port to use")
            print("(or 'a' to see all ports, or 'q' to quit):")
        else:
            print("No obvious Bluetooth ports found.")
            print("Enter port number to try anyway, 'a' to see all, or 'q' to quit:")
        
        choice = input("> ").strip().lower()
        
        if choice == 'q':
            return None
        elif choice == 'a':
            print("\nAll ports:")
            for i, port in enumerate(all_ports):
                print(f"{i+1}. {port.device} - {port.description}")
            continue
        
        try:
            port_num = int(choice) - 1
            if 0 <= port_num < len(all_ports):
                return all_ports[port_num].device
            else:
                print("Invalid port number")
        except ValueError:
            print("Please enter a valid number")

def test_connection(port_path):
    """Test if we can connect to the specified port"""
    try:
        print(f"Testing connection to {port_path}...")
        ser = serial.Serial(port_path, 115200, timeout=5)
        print("✓ Port opened successfully")
        
        # Try to read a small amount of data to see if Pi is sending
        print("Checking if Pi is sending data...")
        ser.timeout = 3
        test_data = ser.read(4)  # Try to read length header
        
        if len(test_data) == 4:
            length = int.from_bytes(test_data, 'big')
            print(f"✓ Received data header, expecting {length} bytes")
            ser.close()
            return True
        elif test_data:
            print(f"✓ Received some data: {test_data}")
            ser.close()
            return True
        else:
            print("⚠ No data received, but port is accessible")
            ser.close()
            return True
            
    except serial.SerialException as e:
        print(f"✗ Cannot connect to {port_path}: {e}")
        return False

def main():
    print("=== Bluetooth Client (Mac) ===")
    print("Make sure:")
    print("1. Pi server is running")
    print("2. Devices are paired in System Preferences > Bluetooth")
    print("3. You've tried connecting to the Pi in Bluetooth settings")
    print()
    
    # Find available ports
    port_path = find_bluetooth_port()
    if not port_path:
        print("No port selected. Exiting.")
        return
    
    # Test the connection first
    if not test_connection(port_path):
        retry = input("Connection test failed. Try anyway? (y/n): ")
        if retry.lower() != 'y':
            return
    
    try:
        print(f"\n✓ Connecting to {port_path} for data transfer...")
        ser = serial.Serial(port_path, 115200, timeout=30)
        
        print(f"✓ Connected! Receiving {num_tests} tests...")
        
        # Receive data exactly like TCP client
        with open(full_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["USB Test with Measurement Logging (Bluetooth)"])
            writer.writerow(CSV_HEADER)
            
            for i in range(num_tests):
                print(f"Test {i+1}/{num_tests}...", end=' ')
                
                # Read length first (4 bytes) - same as TCP
                length_bytes = ser.read(4)
                if len(length_bytes) != 4:
                    print(f"Failed to read length (got {len(length_bytes)} bytes)")
                    break
                length = int.from_bytes(length_bytes, 'big')
                
                # Read the actual data - same as TCP
                data = b''
                while len(data) < length:
                    remaining = length - len(data)
                    packet = ser.read(remaining)
                    if not packet:
                        print(f"Connection lost (expected {remaining} more bytes)")
                        break
                    data += packet
                
                if len(data) == length:
                    result = pickle.loads(data)
                    writer.writerow(result)
                    print(f"✓ {result[2]}")
                else:
                    print(f"Incomplete data ({len(data)}/{length} bytes)")
                    break
                
        print(f"\n✓ All tests completed!")
        print(f"Results saved to {full_path}")
        
    except serial.SerialException as e:
        print(f"\n❌ Serial connection error: {e}")
    except Exception as e:
        print(f"\n❌ Error during data transfer: {e}")
    finally:
        try:
            ser.close()
            print("Connection closed")
        except:
            pass

if __name__ == "__main__":
    main()