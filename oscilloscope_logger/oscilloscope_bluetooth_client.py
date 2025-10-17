import asyncio
import pickle
import csv
import test_config
from bleak import BleakClient, BleakScanner

num_tests = 100
base_name = "usb_bt_test_results"
full_path = test_config.get_next_test_filepath(base_name)

# UUIDs (must match server)
SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
DATA_CHARACTERISTIC_UUID = "12345678-1234-1234-1234-123456789abd"
COMMAND_CHARACTERISTIC_UUID = "12345678-1234-1234-1234-123456789abe"

CSV_HEADER = [
    "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
    "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)",
    "Waveform Min", "Waveform Max", "Waveform Avg"
]

class OscilloscopeBluetoothClient:
    def __init__(self):
        self.results = []
        self.waiting_for_data = False
        
    async def find_oscilloscope_server(self):
        """Scan for the oscilloscope BLE server"""
        print("Scanning for Oscilloscope server...")
        devices = await BleakScanner.discover(timeout=15.0)
        
        for device in devices:
            if device.name and "OscilloscopeServer" in device.name:
                print(f"Found oscilloscope server: {device.name} ({device.address})")
                return device.address
                
        print("Available devices:")
        for device in devices:
            print(f"  {device.name} ({device.address})")
            
        return None
        
    def data_notification_handler(self, sender, data):
        """Handle incoming data from server"""
        if data == b"COMPLETE":
            print("All tests completed by server")
            self.waiting_for_data = False
            return
            
        if len(data) >= 4:
            try:
                # Extract length and data
                length = int.from_bytes(data[:4], 'big')
                if len(data) >= 4 + length:
                    # We have complete data
                    result_data = data[4:4+length]
                    result = pickle.loads(result_data)
                    self.results.append(result)
                    print(f"Received test {len(self.results)}/{num_tests}: {result[0]} - {result[2]}")
                    self.waiting_for_data = False
                    
            except (pickle.PickleError, ValueError) as e:
                print(f"Error processing data: {e}")
                self.waiting_for_data = False
            
    async def run_test_session(self, address):
        """Connect to server and collect test data"""
        async with BleakClient(address) as client:
            print(f"Connecting to Pi at {address} via Bluetooth...")
            
            # Verify we have the right service
            services = await client.get_services()
            found_service = False
            for service in services:
                if service.uuid.lower() == SERVICE_UUID.lower():
                    found_service = True
                    break
                    
            if not found_service:
                print("Could not find oscilloscope service")
                return False
            
            print("Connected and service found")
            
            # Subscribe to data notifications
            await client.start_notify(DATA_CHARACTERISTIC_UUID, self.data_notification_handler)
            
            # Send START command
            await client.write_gatt_char(COMMAND_CHARACTERISTIC_UUID, b"START")
            await asyncio.sleep(0.5)
            
            # Request each test
            for i in range(num_tests):
                self.waiting_for_data = True
                await client.write_gatt_char(COMMAND_CHARACTERISTIC_UUID, b"GET_NEXT")
                
                # Wait for response with timeout
                timeout_count = 0
                while self.waiting_for_data and timeout_count < 200:  # 20 second timeout
                    await asyncio.sleep(0.1)
                    timeout_count += 1
                    
                if timeout_count >= 200:
                    print(f"Timeout waiting for test {i+1}")
                    break
                    
            await client.stop_notify(DATA_CHARACTERISTIC_UUID)
            return True
            
    def save_results(self):
        """Save collected results to CSV"""
        with open(full_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["USB Test with Measurement Logging (Bluetooth)"])
            writer.writerow(CSV_HEADER)
            
            for result in self.results:
                writer.writerow(result)
                
        print(f"Results saved to {full_path} ({len(self.results)} tests)")

async def main():
    client = OscilloscopeBluetoothClient()
    
    # Find the server
    server_address = await client.find_oscilloscope_server()
    if not server_address:
        print("Could not find Oscilloscope server.")
        print("Make sure:")
        print("1. The Pi server is running")
        print("2. Bluetooth is enabled on both devices")
        print("3. The devices are within range")
        return
        
    try:
        # Connect and run tests
        success = await client.run_test_session(server_address)
        
        if success:
            # Save results
            client.save_results()
        else:
            print("Test session failed")
            
    except Exception as e:
        print(f"Error during test session: {e}")

if __name__ == "__main__":
    main()