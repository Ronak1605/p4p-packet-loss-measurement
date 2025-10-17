import asyncio
import pickle
import pyvisa
from packet_loss_tester import PacketLossTester
from bleak import BleakServer, BleakGATTCharacteristic, BleakGATTService
from bleak.backends.characteristic import BleakGATTCharacteristicProperties

scope_usb_address = 'USB0::10893::5990::MY58493325::INSTR'
num_tests = 100
timeout_sec = 2000  # ms

# Custom UUIDs for our service
SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
DATA_CHARACTERISTIC_UUID = "12345678-1234-1234-1234-123456789abd"
COMMAND_CHARACTERISTIC_UUID = "12345678-1234-1234-1234-123456789abe"

class OscilloscopeBluetoothServer:
    def __init__(self):
        self.rm = None
        self.scope = None
        self.tester = None
        self.client_connected = False
        self.current_test = 0
        self.data_characteristic = None
        
    def setup_instruments(self):
        """Initialize oscilloscope connection"""
        self.rm = pyvisa.ResourceManager()
        self.scope = self.rm.open_resource(scope_usb_address)
        self.scope.timeout = timeout_sec
        self.tester = PacketLossTester(self.scope, "USB", num_tests)
        print("Instruments initialized")
        
    def cleanup_instruments(self):
        """Clean up instrument connections"""
        if self.scope:
            self.scope.close()
        if self.rm:
            self.rm.close()
            
    async def command_handler(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        """Handle commands from client"""
        try:
            command = data.decode('utf-8').strip()
            print(f"Received command: {command}")
            
            if command == "START":
                self.client_connected = True
                self.current_test = 0
                print("Client connected and ready to receive data")
                
            elif command == "GET_NEXT" and self.client_connected:
                if self.current_test < num_tests:
                    self.current_test += 1
                    print(f"Running test {self.current_test}/{num_tests}")
                    
                    # Run the test
                    result = self.tester._run_single_test(self.current_test)
                    
                    # Serialize the result
                    data = pickle.dumps(result)
                    
                    # Send length first (4 bytes) then data
                    length_bytes = len(data).to_bytes(4, 'big')
                    await self.data_characteristic.write_value(length_bytes + data)
                    
                    print(f"Sent test {self.current_test} result")
                else:
                    # All tests complete
                    await self.data_characteristic.write_value(b"COMPLETE")
                    print("All tests completed")
                    
        except Exception as e:
            print(f"Error handling command: {e}")

async def main():
    server = OscilloscopeBluetoothServer()
    
    try:
        # Setup instruments
        server.setup_instruments()
        
        # Create BLE characteristics
        data_char = BleakGATTCharacteristic(
            DATA_CHARACTERISTIC_UUID,
            properties=BleakGATTCharacteristicProperties.read | 
                      BleakGATTCharacteristicProperties.write |
                      BleakGATTCharacteristicProperties.notify,
            value=None,
            descriptors=[]
        )
        
        command_char = BleakGATTCharacteristic(
            COMMAND_CHARACTERISTIC_UUID,
            properties=BleakGATTCharacteristicProperties.write,
            value=None,
            descriptors=[]
        )
        
        # Store reference for sending data
        server.data_characteristic = data_char
        
        # Create service
        service = BleakGATTService(SERVICE_UUID, [data_char, command_char])
        
        # Start BLE server
        async with BleakServer(
            name="OscilloscopeServer",
            services=[service],
        ) as ble_server:
            
            # Set up command handler
            command_char.add_write_handler(server.command_handler)
            
            print("Bluetooth LE Server started")
            print(f"Device name: OscilloscopeServer")
            print(f"Service UUID: {SERVICE_UUID}")
            print("Waiting for client connection...")
            
            # Keep server running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down server...")
                
    finally:
        server.cleanup_instruments()

if __name__ == "__main__":
    """Bluetooth server to be run on the Pi connected to the oscilloscope."""
    asyncio.run(main())