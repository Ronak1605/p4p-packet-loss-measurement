import argparse
import asyncio
from packet_loss_tester import PacketLossTester
import test_config
import os

async def run_async_test(tester, delay):
    stats = await tester.run_test_async(delay_between_tests=delay)
    return stats

def main():
    parser = argparse.ArgumentParser(description='Test packet loss between PC and router')
    parser.add_argument('router_address', help='IP address of the router')
    parser.add_argument('--num-tests', type=int, default=100, help='Number of test attempts')
    parser.add_argument('--delay', type=float, default=0.00, help='Delay between tests in seconds')
    parser.add_argument('--timeout', type=float, default=2.0, help='Timeout for each request in seconds')
    parser.add_argument('--dynamic-http', action='store_true', help='Use dynamic HTTP check to verify TCP port before request')
    parser.add_argument('--async', action='store_true', help='Use asynchronous testing mode')
    parser.add_argument('--udp', action='store_true', help='Use UDP instead of TCP')
    parser.add_argument('--tcp-only', action='store_true', help='Use raw TCP instead of HTTP')
    
    args = parser.parse_args()
    
    # Set up the tester
    tester = PacketLossTester(
        router_address=args.router_address,
        connection_type=test_config.communication_type,
        num_tests=args.num_tests,
        timeout=args.timeout,
        use_http=not args.tcp_only,
        use_dynamic_http_check=args.dynamic_http
    )
    
    if args.udp:
        tester.use_udp = True
        tester.use_http = False
    
    # Determine the filename base for this test
    if tester.use_http:
        if tester.use_dynamic_http_check:
            base_name = "router_dynamic_http_test"
        else:
            base_name = "router_http_test"
    elif tester.use_udp:
        base_name = "router_udp_test"
    else:
        base_name = "router_tcp_test"
    
    # Get the next available filepath
    file_path = test_config.get_next_test_filepath(base_name)
    
    # Run the test - either sync or async
    if vars(args).get('async'):
        print("Running in ASYNC mode with dynamic HTTP checks")
        stats = asyncio.run(run_async_test(tester, args.delay))
    else:
        print("Running in SYNC mode")
        stats = tester.run_test(delay_between_tests=args.delay)
    
    # Save results and print summary
    tester.save_results_to_csv(file_path, stats)
    tester.print_summary(stats, file_path)
    tester.close()

if __name__ == "__main__":
    main()