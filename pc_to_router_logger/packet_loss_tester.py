import time
import csv
import socket
import requests
from statistics import mean, median
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import test_config

class PacketLossTester:
    def __init__(self, router_address: str, connection_type: str, num_tests: int = 200, 
                port: int = 80, timeout: float = 2.0, use_http: bool = True, use_dynamic_http_check: bool = False):
        self.router_address = router_address  # IP address of the router
        self.connection_type = connection_type
        self.num_tests = num_tests
        self.port = port  # Port to use for communication (80 for HTTP)
        self.timeout = timeout  # Socket/request timeout in seconds
        self.use_http = use_http  # Whether to use HTTP or raw TCP
        self.use_udp = False  # Whether to use UDP instead of TCP
        self.results = []
        self.response_times = []
        self.success_count = 0
        # Test data to send
        self.test_message = "Test_packetloss_test_!@#$%^&*()KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614Test_packetloss_test_!@#$%^&*()KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614KEYSIGHT TECHNOLOGIES,DSO-X 3024T,MY58493325,07.20.2017102614"
        
        # For HTTP store first successful response for comparison
        self.reference_response: Optional[bytes] = None

        # Set flag for dynamic HTTP reconnection test
        self.use_dynamic_http_check = use_dynamic_http_check
        
        # Session for keep-alive in dynamic HTTP test
        self.session = requests.Session()
        
    def run_test(self, delay_between_tests: float = 0) -> Dict[str, Any]:
        """Run the packet loss test and return results
        Args:
            delay_between_tests (float): Delay in seconds between each test attempt.
        Returns:
            Dict[str, Any]: Summary statistics including success count, loss count, and response times.
        """
        print(f"Starting {self.connection_type} test with {self.num_tests} attempts to router at {self.router_address}")
        
        start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        test_start = time.time()
        
        for n in range(self.num_tests):
            result = self._run_single_test(n + 1)
            self.results.append(result)
            
            if result[2] == "Success":  # Status field
                self.success_count += 1
                self.response_times.append(result[3])  # Response time field
                
            time.sleep(delay_between_tests)
        
        test_end = time.time()
        
        return self._calculate_summary_stats(start_time_str, test_start, test_end)
    
    def _run_single_test(self, attempt_num: int) -> List:
        """Run a single test attempt by sending data to router and waiting for response"""
        t0 = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        if self.use_http:
            if self.use_dynamic_http_check:
                return self._run_http_test_dynamic(attempt_num, t0, timestamp)
            else:
                return self._run_http_test(attempt_num, t0, timestamp)
        elif self.use_udp:
            return self._run_udp_test(attempt_num, t0, timestamp)
        else:
            return self._run_tcp_test(attempt_num, t0, timestamp)
    
    def _run_http_test(self, attempt_num: int, t0: float, timestamp: str) -> List:
        """Send HTTP request to router and analyze response character by character"""
        try:
            # Create HTTP request to router
            url = f"http://{self.router_address}"
            response = requests.get(url, timeout=self.timeout)
            
            # Calculate elapsed time
            elapsed = round((time.time() - t0) * 1000, 2)
            
            # Get response status and content (with safety checks)
            status_code = response.status_code
            
            # Safety check - ensure content exists
            if not hasattr(response, 'content') or response.content is None:
                print(f"[{attempt_num}/{self.num_tests}] Response content is None")
                return [attempt_num, timestamp, "Error", elapsed, "Response content is None"]
            
            content = response.content
            
            # Store the first successful response as reference if not already set
            if status_code == 200 and self.reference_response is None:
                self.reference_response = content
                print(f"[{attempt_num}/{self.num_tests}] Captured reference response, size: {len(content)} bytes")
                # Include the actual response content in the CSV record
                return [attempt_num, timestamp, "Success", elapsed, 
                        f"HTTP {status_code} | Size: {len(content)} bytes | Reference captured | Content: {content}"]
            
            # For subsequent requests, validate character by character against reference
            if status_code == 200 and self.reference_response is not None:
                # Check if sizes match first (quick check)
                if len(content) != len(self.reference_response):
                    mismatch = f"Size mismatch: got {len(content)} bytes, expected {len(self.reference_response)} bytes"
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Content Error | {mismatch}")
                    # Include the actual response content in the CSV record
                    return [attempt_num, timestamp, "Content Error", elapsed, 
                            f"HTTP {status_code} | {mismatch} | Content: {content}"]
                
                # Character by character comparison
                mismatches = []
                for i, (c1, c2) in enumerate(zip(content, self.reference_response)):
                    if c1 != c2:
                        # Record position and character difference
                        mismatches.append((i, c1, c2))
                        # Limit to first 5 mismatches to avoid huge logs
                        if len(mismatches) >= 5:
                            break
                
                if mismatches:
                    # Format mismatch details for logging
                    mismatch_details = "; ".join([f"Pos {pos}: {chr(c1) if c1 < 128 else hex(c1)} != {chr(c2) if c2 < 128 else hex(c2)}" 
                                                for pos, c1, c2 in mismatches])
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Character Mismatch | {len(mismatches)} differences")
                    # Include the actual response content in the CSV record
                    return [attempt_num, timestamp, "Character Mismatch", elapsed, 
                            f"HTTP {status_code} | {len(mismatches)} character differences: {mismatch_details} | Content: {content}"]
                else:
                    # Perfect match, character by character
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Perfect match")
                    # Include the actual response content in the CSV record
                    return [attempt_num, timestamp, "Success", elapsed, 
                            f"HTTP {status_code} | Size: {len(content)} bytes | Perfect character match | Content: {content}"]
            else:
                # Either no reference response yet or non-200 status code
                content_size = len(content) if content else 0
                print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Unexpected Response | HTTP {status_code}")
                # Include the actual response content in the CSV record
                return [attempt_num, timestamp, "Unexpected Response", elapsed, 
                        f"HTTP {status_code} | Size: {content_size} bytes | No reference to compare against | Content: {content}"]
                
        except requests.exceptions.Timeout:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] HTTP Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed, "HTTP request timed out"]
            
        except requests.exceptions.ConnectionError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Connection error after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed, "Connection error"]
            
        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, str(err)]
    
    def _run_tcp_test(self, attempt_num: int, t0: float, timestamp: str) -> List:
        """Send TCP data to router and analyze response"""
        try:
            # Create socket for this test
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                
                # Connect to router
                sock.connect((self.router_address, self.port))
                
                # Send test message
                sock.sendall(self.test_message.encode('utf-8'))
                
                # Receive response
                response_bytes = sock.recv(4096)
                response_text = response_bytes.decode('utf-8', errors='ignore').strip()
                
                # Calculate elapsed time
                elapsed = round((time.time() - t0) * 1000, 2)
                
                # For TCP communication, any response indicates success
                if response_bytes:
                    # Create a truncated version for console (to prevent terminal flooding)
                    console_response = response_text[:50] + "..." if len(response_text) > 50 else response_text
                    
                    # Successful response - show response preview in console
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Response size: {len(response_bytes)} bytes | Content: {console_response}")
                    
                    # For CSV, include the full response content
                    return [attempt_num, timestamp, "Success", elapsed, f"Size: {len(response_bytes)} bytes | Content: {response_text}"]
                else:
                    print(f"[{attempt_num}/{self.num_tests}] Empty response")
                    return [attempt_num, timestamp, "Empty Response", elapsed, "No data received"]

        except socket.timeout:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed, "Connection timed out"]
            
        except ConnectionRefusedError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Connection refused after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed, "Connection refused"]
            
        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, str(err)]
        
    def _run_udp_test(self, attempt_num: int, t0: float, timestamp: str) -> List:
        """Send UDP data to router and analyze response (no automatic retransmission)"""
        try:
            # Create UDP socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout)
                
                # Generate sequence number and add to test message
                seq_num = attempt_num
                test_data = f"SEQ:{seq_num}|" + self.test_message
                
                # Send test message
                sock.sendto(test_data.encode('utf-8'), (self.router_address, self.port))
                
                # Try to receive response
                try:
                    response_bytes, addr = sock.recvfrom(4096)
                    elapsed = round((time.time() - t0) * 1000, 2)
                    
                    # Check if we received our own sequence number back
                    response_text = response_bytes.decode('utf-8', errors='ignore')
                    if f"SEQ:{seq_num}|" in response_text:
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Correct sequence")
                        return [attempt_num, timestamp, "Success", elapsed, 
                                f"Size: {len(response_bytes)} bytes | Correct sequence | Content: {response_text[:100]}"]
                    else:
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Wrong Sequence | Expected {seq_num}")
                        return [attempt_num, timestamp, "Wrong Sequence", elapsed, 
                                f"Expected SEQ:{seq_num} | Received: {response_text[:100]}"]
                
                except socket.timeout:
                    elapsed = round((time.time() - t0) * 1000, 2)
                    print(f"[{attempt_num}/{self.num_tests}] UDP Timeout after {elapsed} ms")
                    return [attempt_num, timestamp, "Timeout", elapsed, "UDP response timed out"]
                    
        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, str(err)]
        
    
    def is_tcp_port_open(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Check if TCP port is open (for dynamic HTTP test)"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            try:
                sock.connect((ip, port))
                return True
            except:
                return False
    
    def _run_http_test_dynamic(self, attempt_num: int, t0: float, timestamp: str) -> List:
        """HTTP test with dynamic TCP link check before request to preemptively reconnect"""
        if not self.is_tcp_port_open(self.router_address, self.port, timeout=1.0):
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] TCP port {self.port} not open before HTTP request, skipping attempt.")
            return [attempt_num, timestamp, "TCP Port Closed", elapsed, f"TCP port {self.port} closed; skipping HTTP request"]

        try:
            url = f"http://{self.router_address}"
            # Use the persistent session for keep-alive
            response = self.session.get(url, timeout=self.timeout)
            elapsed = round((time.time() - t0) * 1000, 2)
            status_code = response.status_code

            if not hasattr(response, 'content') or response.content is None:
                print(f"[{attempt_num}/{self.num_tests}] Response content is None")
                return [attempt_num, timestamp, "Error", elapsed, "Response content is None"]

            content = response.content

            if status_code == 200 and self.reference_response is None:
                self.reference_response = content
                print(f"[{attempt_num}/{self.num_tests}] Captured reference response, size: {len(content)} bytes")
                return [attempt_num, timestamp, "Success", elapsed,
                        f"HTTP {status_code} | Size: {len(content)} bytes | Reference captured | Content: {content}"]

            if status_code == 200 and self.reference_response is not None:
                if len(content) != len(self.reference_response):
                    mismatch = f"Size mismatch: got {len(content)} bytes, expected {len(self.reference_response)} bytes"
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Content Error | {mismatch}")
                    return [attempt_num, timestamp, "Content Error", elapsed,
                            f"HTTP {status_code} | {mismatch} | Content: {content}"]

                mismatches = []
                for i, (c1, c2) in enumerate(zip(content, self.reference_response)):
                    if c1 != c2:
                        mismatches.append((i, c1, c2))
                        if len(mismatches) >= 5:
                            break

                if mismatches:
                    mismatch_details = "; ".join([f"Pos {pos}: {chr(c1) if c1 < 128 else hex(c1)} != {chr(c2) if c2 < 128 else hex(c2)}"
                                                for pos, c1, c2 in mismatches])
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Character Mismatch | {len(mismatches)} differences")
                    return [attempt_num, timestamp, "Character Mismatch", elapsed,
                            f"HTTP {status_code} | {len(mismatches)} character differences: {mismatch_details} | Content: {content}"]
                else:
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Perfect match")
                    return [attempt_num, timestamp, "Success", elapsed,
                            f"HTTP {status_code} | Size: {len(content)} bytes | Perfect character match | Content: {content}"]
            else:
                content_size = len(content) if content else 0
                print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Unexpected Response | HTTP {status_code}")
                return [attempt_num, timestamp, "Unexpected Response", elapsed,
                        f"HTTP {status_code} | Size: {content_size} bytes | No reference to compare against | Content: {content}"]

        except requests.exceptions.Timeout:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] HTTP Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed, "HTTP request timed out"]

        except requests.exceptions.ConnectionError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Connection error after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed, "Connection error"]

        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, str(err)]
            
    def _calculate_summary_stats(self, start_time_str: str, test_start: float, test_end: float) -> Dict[str, Any]:
        """Calculate summary statistics"""
        end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_duration = round(test_end - test_start, 2)
        loss = self.num_tests - self.success_count
        loss_percent = round((loss / self.num_tests) * 100, 2)
        
        if self.response_times:
            stats = {
                "mean_time": round(mean(self.response_times), 2),
                "median_time": round(median(self.response_times), 2),
                "min_time": round(min(self.response_times), 2),
                "max_time": round(max(self.response_times), 2)
            }
        else:
            stats = {
                "mean_time": "N/A",
                "median_time": "N/A", 
                "min_time": "N/A",
                "max_time": "N/A"
            }
        
        return {
            "start_time": start_time_str,
            "end_time": end_time_str,
            "total_duration": total_duration,
            "success_count": self.success_count,
            "loss_count": loss,
            "loss_percent": loss_percent,
            **stats
        }
    
    def save_results_to_csv(self, file_path: str, stats: Dict[str, Any]):
        """Save test results to CSV file"""
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header and metadata
            writer.writerow([f"{self.connection_type.upper()} Test with Router Communication"])
            writer.writerow(["Start Time", stats["start_time"]])
            writer.writerow(["End Time", stats["end_time"]])
            writer.writerow(["Cable Type", test_config.cable_type])
            writer.writerow(["Position", test_config.antenna_position])
            writer.writerow(["Power State", test_config.power_state])
            writer.writerow(["Conduction Angle", test_config.conduction_angle])
            writer.writerow(["Router Address", self.router_address])
            writer.writerow(["Protocol", "HTTP" if self.use_http else "TCP"])
            writer.writerow(["Port", self.port])
            writer.writerow(["Total Attempts", self.num_tests])
            writer.writerow(["Successful Responses", stats["success_count"]])
            writer.writerow(["Lost Packets", stats["loss_count"]])
            writer.writerow(["Loss %", stats["loss_percent"]])
            writer.writerow(["Mean Response Time (ms)", stats["mean_time"]])
            writer.writerow(["Median Response Time (ms)", stats["median_time"]])
            writer.writerow(["Min Response Time (ms)", stats["min_time"]])
            writer.writerow(["Max Response Time (ms)", stats["max_time"]])
            writer.writerow(["Total Duration (s)", stats["total_duration"]])
            writer.writerow([])
            
            # Write data headers and results
            writer.writerow([
                "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response",
            ])
            writer.writerows(self.results)
    
    def print_summary(self, stats: Dict[str, Any], file_path: str):
        """Print test summary to console"""
        print("\nTest completed.")
        print(f"File saved to: {file_path}")
        print(f"Start time: {stats['start_time']}")
        print(f"End time: {stats['end_time']}")
        print(f"Protocol: {'HTTP' if self.use_http else 'TCP'} to {self.router_address}:{self.port}")
        print(f"Successful responses: {stats['success_count']}")
        print(f"Lost packets: {stats['loss_count']} ({stats['loss_percent']:.2f}%)")
        print(f"Mean: {stats['mean_time']} ms | Median: {stats['median_time']} ms | Min: {stats['min_time']} ms | Max: {stats['max_time']} ms")
        
    def close(self):
        """Close any persistent resources like HTTP session"""
        if self.session:
            self.session.close()
