import argparse
import time
import test_config
from packet_loss_tester import PacketLossTester

def main():
    parser = argparse.ArgumentParser(description='Run packet loss test with router communication')
    parser.add_argument('router_ip', type=str, help='IP address of the router (e.g., 192.168.1.1)')
    parser.add_argument('-p', '--port', type=int, default=80, 
                        help='Port to use (default: 80 for HTTP)')
    parser.add_argument('-n', '--num-tests', type=int, default=100, 
                        help='Number of test packets to send (default: 100)')
    parser.add_argument('-d', '--delay', type=float, default=0.0, 
                        help='Delay between tests in seconds (default: 0.0s)')
    parser.add_argument('-t', '--timeout', type=float, default=2.0,
                        help='Request timeout in seconds (default: 2.0s)')
    parser.add_argument('-c', '--connection', type=str, default='LAN',
                        help='Connection type (for reporting)')
    parser.add_argument('--tcp', action='store_true',
                        help='Use TCP instead of HTTP')
    parser.add_argument('--udp', action='store_true',
                        help='Use UDP protocol (requires echo server)')
    parser.add_argument('--dynamic-http', action='store_true',
                        help='Use dynamic HTTP test with TCP link check before requests')
    
    args = parser.parse_args()
    
    # Determine protocol to use
    use_http = not (args.tcp or args.udp)
    use_tcp = args.tcp and not args.udp
    use_udp = args.udp
    
    # Create tester instance
    tester = PacketLossTester(
        router_address=args.router_ip,
        connection_type=args.connection,
        num_tests=args.num_tests,
        port=args.port,
        timeout=args.timeout,
        use_http=use_http
    )
    
    # Set protocol flag for UDP
    if use_udp:
        tester.use_udp = True
    
    # Enable dynamic HTTP check if flag is set
    tester.use_dynamic_http_check = args.dynamic_http
    
    # Determine protocol label for printing
    if use_udp:
        protocol = "UDP"
    elif use_tcp:
        protocol = "TCP"
    else:
        protocol = "Dynamic HTTP" if tester.use_dynamic_http_check else "HTTP"
    
    print(f"Starting router packet loss test to {args.router_ip}:{args.port}")
    print(f"Testing {args.num_tests} packets with {args.delay}s delay between each")
    print(f"Using {protocol} protocol")
    
    # Run the test
    stats = tester.run_test(delay_between_tests=args.delay)
    
    # Save results
    file_path = test_config.get_next_test_filepath(f"router_{protocol.lower().replace(' ', '_')}_test")
    tester.save_results_to_csv(file_path, stats)
    tester.print_summary(stats, file_path)
    
    # Close HTTP session and other persistent resources
    tester.close()


if __name__ == "__main__":
    main()