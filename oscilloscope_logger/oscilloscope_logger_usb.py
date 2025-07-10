import pyvisa
import test_config
from packet_loss_tester import PacketLossTester

# USB VISA address
scope_usb_address = 'USB0::10893::5990::MY58493325::INSTR'

# Test parameters
num_tests = 50
timeout_sec = 2000  # ms

# Get output file path
base_name = "usb_test_results"
full_path = test_config.get_next_test_filepath(base_name)

def main():
    # Connect to scope
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource(scope_usb_address)
    scope.timeout = timeout_sec
    
    # Create tester and run test
    tester = PacketLossTester(scope, "USB", num_tests)
    stats = tester.run_test(delay_between_tests=1.0)
    
    # Save results and print summary
    tester.save_results_to_csv(full_path, stats)
    tester.print_summary(stats, full_path)
    
    # Close connection
    scope.close()
    rm.close()

if __name__ == "__main__":
    main()