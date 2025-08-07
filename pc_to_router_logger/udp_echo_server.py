import socket
import threading
import argparse
import time

def start_udp_echo_server(host='0.0.0.0', port=5000):
    """Start a UDP echo server that returns any data it receives"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"UDP echo server listening on {host}:{port}")
    
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            print(f"Received {len(data)} bytes from {addr}")
            # Echo the exact data back to sender
            sock.sendto(data, addr)
    except KeyboardInterrupt:
        print("Shutting down UDP echo server")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start a UDP echo server')
    parser.add_argument('-p', '--port', type=int, default=5000,
                        help='Port to listen on (default: 5000)')
    args = parser.parse_args()
    
    start_udp_echo_server(port=args.port)