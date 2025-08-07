import socket
import threading
import time
import argparse
import sys
import os
import test_config
from packet_loss_tester import PacketLossTester

def start_echo_server(host='0.0.0.0', port=12345):
    """Start a simple echo server that returns any data it receives"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Echo server listening on {host}:{port}")
        
        def handle_client(client_socket, addr):
            """Handle a client connection by echoing back the data"""
            try:
                data = client_socket.recv(4096)
                if data:
                    print(f"Echo server received {len(data)} bytes from {addr}")
                    # Echo the exact data back
                    client_socket.sendall(data)
            except Exception as e:
                print(f"Error handling client: {e}")
            finally:
                client_socket.close()
        
        # Accept connections in a separate thread
        def accept_connections():
            while True:
                try:
                    client, addr = server_socket.accept()
                    print(f"Accepted connection from {addr}")
                    client_thread = threading.Thread(target=handle_client, args=(client, addr))
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    print(f"Error accepting connection: {e}")
                    break
        
        # Start accepting connections
        accept_thread = threading.Thread(target=accept_connections)
        accept_thread.daemon = True
        accept_thread.start()
        
        return server_socket
        
    except Exception as e:
        print(f"Error starting echo server: {e}")
        return None

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Create a socket to determine the IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually connect but gets the route
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return '127.0.0.1'  # Fallback

def main():
    parser = argparse.ArgumentParser(description='Run wired two-way communication test')
    parser.add_argument('router_ip', type=str, help='IP address of the router (e.g., 192.168.0.1)')
    parser.add_argument('-p', '--port', type=int, default=12345, help='Port to use for echo server')
    parser.add_argument('-n', '--num-tests', type=int, default=100, help='Number of tests')
    parser.add_argument('-d', '--delay', type=float, default=0.1, help='Delay between tests')
    parser.add_argument('-t', '--timeout', type=float, default=2.0, help='Timeout in seconds')
    parser.add_argument('--external', action='store_true', 
                        help='Test external loopback (requires port forwarding)')
    
    args = parser.parse_args()
    
    # Get local IP address
    local_ip = get_local_ip()
    print(f"Local IP address: {local_ip}")
    
    # Start echo server
    print("Starting local echo server...")
    server = start_echo_server(port=args.port)
    if not server:
        print("Failed to start echo server")
        sys.exit(1)
    
    try:
        if args.external:
            # Testing via external port forwarding
            print("\n=== EXTERNAL LOOPBACK TEST ===")
            print("IMPORTANT: This test requires port forwarding configuration on your router.")
            print(f"You must set up port forwarding for TCP port {args.port} to {local_ip}:{args.port}")
            print("This creates a loop: Your PC → Router → Your PC\n")
            
            # For external test, we connect to router's WAN IP
            target_ip = args.router_ip
            print(f"Testing external loopback via router WAN IP: {target_ip}")
        else:
            # Testing direct loopback
            print("\n=== DIRECT LOOPBACK TEST ===")
            print("This test uses a local echo server and connects directly to it.")
            print("This tests the reliability of the wired connection to your router.")
            
            # For direct test, we connect to localhost
            target_ip = local_ip
            print(f"Testing direct loopback to local IP: {target_ip}")
        
        # Create tester
        tester = PacketLossTester(
            router_address=target_ip,
            connection_type="WiredLoopback",
            num_tests=args.num_tests,
            port=args.port,
            timeout=args.timeout,
            use_http=False  # Use TCP
        )
        
        print(f"Testing {args.num_tests} packets with {args.delay}s delay between each")
        
        # Run the test
        stats = tester.run_test(delay_between_tests=args.delay)
        
        # Save results
        test_type = "external" if args.external else "direct"
        file_path = test_config.get_next_test_filepath(f"wired_{test_type}_loopback_test")
        tester.save_results_to_csv(file_path, stats)
        tester.print_summary(stats, file_path)
        
    except Exception as e:
        print(f"Error during test: {e}")
    
    finally:
        # Clean up
        if server:
            server.close()
            print("Echo server stopped")

if __name__ == "__main__":
    main()