import pyvisa
import pickle
from packet_loss_tester import PacketLossTester
import subprocess
import serial
import time
import os
import socket

scope_usb_address = 'USB0::10893::5990::MY58493325::INSTR'
num_tests = 100
timeout_sec = 2000  # ms

"""Bluetooth server using RFCOMM socket (compatible with macOS client)"""

def setup_bluetooth_rfcomm():
    """Setup Bluetooth RFCOMM server socket"""
    print("Setting up Bluetooth RFCOMM server...")
    
    try:
        # Make Bluetooth discoverable
        subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], check=False)
        subprocess.run(['sudo', 'hciconfig', 'hci0', 'piscan'], check=False)
        
        # Get Bluetooth address
        result = subprocess.run(['hciconfig'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'BD Address:' in line:
                addr = line.split('BD Address: ')[1].split()[0]
                print(f"Pi Bluetooth Address: {addr}")
                break
        
        # Create RFCOMM socket (like TCP socket but for Bluetooth)
        import bluetooth
        
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", bluetooth.PORT_ANY))
        server_sock.listen(1)
        
        port = server_sock.getsockname()[1]
        print(f"✓ Bluetooth RFCOMM server listening on channel {port}")
        
        # Advertise service
        bluetooth.advertise_service(
            server_sock, "Pi Oscilloscope Server",
            service_id="00001101-0000-1000-8000-00805F9B34FB",  # Serial Port Profile UUID
            service_classes=[bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE]
        )
        
        return server_sock
        
    except ImportError:
        print("❌ Python bluetooth library not installed")
        print("Install with: sudo apt install python3-bluetooth")
        return None
    except Exception as e:
        print(f"❌ Bluetooth setup error: {e}")
        return None

def main():
    print("=== Bluetooth RFCOMM Server (Pi) ===")
    
    # Connect to oscilloscope first
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

    # Setup Bluetooth RFCOMM server
    server_sock = setup_bluetooth_rfcomm()
    if not server_sock:
        scope.close()
        rm.close()
        return

    try:
        print("\nWaiting for Bluetooth client connection...")
        print("On your Mac, run the client and it should find this service")
        
        # Wait for client connection (like TCP accept())
        client_sock, client_info = server_sock.accept()
        print(f"✓ Client connected from {client_info}")
        
        # Convert socket to file-like object for easier data handling
        client_file = client_sock.makefile('wb')
        
        print("Starting tests...")
        
        # Send tests exactly like TCP server
        for n in range(num_tests):
            print(f"Running test {n+1}/{num_tests}...")
            result = tester._run_single_test(n + 1)
            
            # Send data using same protocol as TCP
            data = pickle.dumps(result)
            client_file.write(len(data).to_bytes(4, 'big'))  # Length first
            client_file.write(data)                          # Then data
            client_file.flush()                              # Ensure sent
            
        print("✓ All tests completed and sent")
        
    except Exception as e:
        print(f"❌ Error during tests: {e}")
    finally:
        print("Closing connections...")
        try:
            client_sock.close()
        except:
            pass
        try:
            server_sock.close()
        except:
            pass
        scope.close()
        rm.close()

if __name__ == "__main__":
    main()