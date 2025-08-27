import pyvisa
import test_config
from packet_loss_tester import PacketLossTester

# LAN settings
scope_ip = '192.168.0.102'
num_tests = 100
timeout_sec = 2

# Get output file path
full_path = test_config.get_next_test_filepath("lan_test_results")

def main():
    # Connect to scope
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource(f'TCPIP0::{scope_ip}::INSTR')
    scope.timeout = timeout_sec * 1000
    
    # Create tester and run test
    tester = PacketLossTester(scope, "LAN", num_tests)
    stats = tester.run_test(delay_between_tests=0)  # Reduced delay for faster testing
    
    # Save results and print summary
    tester.save_results_to_csv(full_path, stats)
    tester.print_summary(stats, full_path)
    
    # Close connection
    scope.close()
    rm.close()

if __name__ == "__main__":
    main()