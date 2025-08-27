import time
import csv
import socket
import requests
import aiohttp
import asyncio
import time
from typing import List
from statistics import mean, median
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import test_config

# Temporary Classes for now
class _CountingRetry(Retry):
    """Retry that counts how many times we retried for the *current* request."""
    def __init__(self, *args, counter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._counter_ref = counter or {"count": 0, "last": None}

    def new(self, **kw):
        # Preserve the same counter dict across cloned Retry instances
        new_retry = super().new(**kw)
        new_retry._counter_ref = self._counter_ref
        return new_retry

    def increment(self, *args, **kwargs):
        # Count every retry attempt and remember the last reason/url if available
        self._counter_ref["count"] = self._counter_ref.get("count", 0) + 1
        self._counter_ref["last"] = {
            "error": str(kwargs.get("error")),
            "method": kwargs.get("method"),
            "url": kwargs.get("url"),
        }
        return super().increment(*args, **kwargs)


class _LoggingHTTPAdapter(HTTPAdapter):
    """HTTPAdapter that exposes per-request retry count and logs attempts."""
    def __init__(self, total_retries=3, backoff_factor=0.2):
        self.retry_counter = {"count": 0, "last": None}
        retry = _CountingRetry(
            total=total_retries,
            connect=total_retries,
            read=total_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "HEAD"]),
            raise_on_status=False,
            counter=self.retry_counter,
        )
        super().__init__(max_retries=retry)

    def send(self, request, **kwargs):
        # Reset per-request counter before each send
        self.retry_counter["count"] = 0
        self.retry_counter["last"] = None
        logging.getLogger("urllib3").debug(f"[HTTPAdapter] -> {request.method} {request.url}")
        resp = super().send(request, **kwargs)
        # Attach retry info to the response so callers can read it
        setattr(resp, "_retry_count", self.retry_counter["count"])
        setattr(resp, "_last_retry", self.retry_counter["last"])
        logging.getLogger("urllib3").debug(
            f"[HTTPAdapter] <- {resp.status_code} | retries={self.retry_counter['count']}"
        )
        return resp


class PacketLossTester:
    def __init__(self, router_address: str, connection_type: str, num_tests: int = 100, 
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
        
        self._http_adapter = _LoggingHTTPAdapter(total_retries=3, backoff_factor=0.2)
        self.session.mount("http://", self._http_adapter)
        self.session.mount("https://", self._http_adapter)

        # Optional: turn on debug logs from urllib3 to see low-level retry messages
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)
                
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
    
    async def run_test_async(self, delay_between_tests: float = 0.0) -> dict:
        """
        Run dynamic HTTP tests asynchronously with TCP port check before each request.
        Args:
            delay_between_tests (float): Delay between test attempts in seconds.
        Returns:
            Dict[str, Any]: Summary statistics.
        """

        self.results = []
        self.response_times = []
        self.success_count = 0
        
        # Track when async requests are processed to detect out-of-order completions
        self.start_order = []
        self.completion_order = []
        self.tcp_port_closed_timestamps = []
        self.expected_completion_order = []  # Store the expected order

        start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        test_start = time.time()

        # Create async session
        async with aiohttp.ClientSession() as self.aiohttp_session:
            tasks = []
            
            # First, create all the tasks (this is where async really happens)
            for n in range(self.num_tests):
                # Record the order in which we start tests
                self.start_order.append(n + 1)
                self.expected_completion_order.append(n + 1)  # The expected completion order
                
                # Create the task with timestamp info
                t0 = time.time()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                
                # Create a task for this request and add to list
                task = asyncio.create_task(self._run_http_test_dynamic_async(n + 1, t0, timestamp))
                tasks.append(task)
                
                # Add delay between creating tasks if specified
                if delay_between_tests > 0:
                    await asyncio.sleep(delay_between_tests)
            
            # Now wait for all tasks to complete (they may complete in any order)
            for task in asyncio.as_completed(tasks):
                result = await task
                self.results.append(result)
                
                # Record the order in which tasks complete
                attempt_num = result[0]
                self.completion_order.append(attempt_num)
                
                # Track TCP port closures with timestamps
                if result[2] == "TCP Port Closed":
                    self.tcp_port_closed_timestamps.append((attempt_num, result[1]))

                if result[2] == "Success":
                    self.success_count += 1
                    self.response_times.append(result[3])

        test_end = time.time()
        stats = self._calculate_summary_stats(start_time_str, test_start, test_end)
        
        # Calculate comprehensive out-of-order metrics
        # 1. Simple count: Completions that finished out of sequence
        simple_out_of_order_count = 0
        for i, completion in enumerate(self.completion_order):
            if i+1 != completion:  # If completion order doesn't match position in list
                simple_out_of_order_count += 1
        
        # 2. Sequence Deviation: Measure how far each completion is from its expected position
        sequence_deviations = []
        for i, attempt_num in enumerate(self.completion_order):
            expected_pos = self.expected_completion_order.index(attempt_num) + 1
            actual_pos = i + 1
            deviation = abs(expected_pos - actual_pos)
            sequence_deviations.append(deviation)
        
        # 3. Inversion Count: A formal measure of disorder in a sequence
        # (counts pairs of elements that are out of order)
        inversion_count = 0
        for i in range(len(self.completion_order)):
            for j in range(i+1, len(self.completion_order)):
                if self.completion_order[i] > self.completion_order[j]:
                    inversion_count += 1
        
        # 4. Longest Increasing Subsequence (LIS) analysis
        # The LIS represents the longest portion that is in correct order
        # The difference between total length and LIS length gives another disorder measure
        def longest_increasing_subsequence(arr):
            if not arr:
                return []
            lis = [1] * len(arr)
            for i in range(1, len(arr)):
                for j in range(0, i):
                    if arr[i] > arr[j] and lis[i] < lis[j] + 1:
                        lis[i] = lis[j] + 1
            return max(lis)
        
        lis_length = longest_increasing_subsequence(self.completion_order)
        disorder_by_lis = len(self.completion_order) - lis_length
        
        # Add all async-specific stats
        stats["simple_out_of_order_count"] = simple_out_of_order_count
        stats["simple_out_of_order_percent"] = round((simple_out_of_order_count / len(self.completion_order)) * 100, 2) if self.completion_order else 0
        stats["max_sequence_deviation"] = max(sequence_deviations) if sequence_deviations else 0
        stats["avg_sequence_deviation"] = round(sum(sequence_deviations) / len(sequence_deviations), 2) if sequence_deviations else 0
        stats["inversion_count"] = inversion_count
        stats["inversion_percent"] = round((inversion_count / (len(self.completion_order) * (len(self.completion_order) - 1) / 2)) * 100, 2) if len(self.completion_order) > 1 else 0
        stats["disorder_by_lis"] = disorder_by_lis
        stats["tcp_port_closed_timestamps"] = self.tcp_port_closed_timestamps
        stats["completion_order"] = self.completion_order
        stats["start_order"] = self.start_order
    
        return stats
    
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
            # For raw TCP tests
            if self.use_dynamic_http_check:
                return self._run_tcp_test_dynamic(attempt_num, t0, timestamp)
            else:
                return self._run_tcp_test(attempt_num, t0, timestamp)
    
    def _run_http_test(self, attempt_num: int, t0: float, timestamp: str) -> List:
        """Send HTTP request to router and analyze response character by character"""
        try:
            # Create HTTP request to router
            url = f"http://{self.router_address}"
            # Note use of session, didn't use it before
            response = self.session.get(url, timeout=self.timeout)
            
            retry_count = getattr(response, "_retry_count", 0)

            
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
                        f"HTTP {status_code} | Size: {len(content)} bytes | Reference captured | Retries: {retry_count} | Content: {content}"]
            
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
                            f"HTTP {status_code} | Size: {len(content)} bytes | Perfect character match |  Retries: {retry_count} | Content: {content}"]
            else:
                # Either no reference response yet or non-200 status code
                content_size = len(content) if content else 0
                print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Unexpected Response | HTTP {status_code}")
                # Include the actual response content in the CSV record
                return [attempt_num, timestamp, "Unexpected Response", elapsed, 
                        f"HTTP {status_code} | Size: {content_size} bytes | No reference to compare against | Content: {content}"]
                
        except requests.exceptions.Timeout:
            elapsed = round((time.time() - t0) * 1000, 2)
            retries_attempted = self._http_adapter.retry_counter.get("count", 0)
            print(f"[{attempt_num}/{self.num_tests}] HTTP Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed, "HTTP request timed out | Retries attempted:", retries_attempted]
            
        except requests.exceptions.ConnectionError:
            elapsed = round((time.time() - t0) * 1000, 2)
            retries_attempted = self._http_adapter.retry_counter.get("count", 0)
            print(f"[{attempt_num}/{self.num_tests}] Connection error after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed, "Connection error | Retries attempted:", retries_attempted]
            
        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            retries_attempted = self._http_adapter.retry_counter.get("count", 0)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, str(err), "Retries attempted:", {retries_attempted} ]
    
    def _run_tcp_test(self, attempt_num: int, t0: float, timestamp: str) -> List:
        """Send a raw-socket HTTP GET (same as HTTP test) and analyze response."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.router_address, self.port))

                # Build a simple HTTP/1.1 GET like requests would, but force identity encoding.
                req = (
                    f"GET / HTTP/1.1\r\n"
                    f"Host: {self.router_address}\r\n"
                    f"User-Agent: PacketLossTester/1.0\r\n"
                    f"Accept: */*\r\n"
                    f"Accept-Encoding: identity\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                ).encode("ascii", errors="ignore")

                sock.sendall(req)

                # Read until the server closes (Connection: close) or we hit timeout.
                chunks = []
                while True:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            break
                        chunks.append(data)
                    except socket.timeout:
                        # Stop reading on timeout; treat whatever we have as the response.
                        break

                raw = b"".join(chunks)
                elapsed = round((time.time() - t0) * 1000, 2)

                if not raw:
                    print(f"[{attempt_num}/{self.num_tests}] Empty response")
                    return [attempt_num, timestamp, "Empty Response", elapsed, "No data received", 0]

                # Separate headers/body
                header_end = raw.find(b"\r\n\r\n")
                if header_end == -1:
                    # Not a valid HTTP response; still report bytes we saw
                    preview = raw[:80].decode("utf-8", errors="ignore")
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Non-HTTP response")
                    return [attempt_num, timestamp, "Error", elapsed, f"Non-HTTP response: {preview}", 0]

                headers = raw[:header_end].decode("iso-8859-1", errors="ignore")
                body = raw[header_end + 4 :]

                # Parse status code
                first_line = headers.split("\r\n", 1)[0]
                try:
                    parts = first_line.split()
                    status_code = int(parts[1]) if len(parts) > 1 else 0
                except Exception:
                    status_code = 0

                # Mirror your HTTP-test logic: capture/compare the BODY only
                if status_code == 200 and self.reference_response is None:
                    self.reference_response = body
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Captured reference (size {len(body)} bytes)")
                    return [
                        attempt_num,
                        timestamp,
                        "Success",
                        elapsed,
                        f"HTTP {status_code} | Size: {len(body)} bytes | Reference captured",
                        0,
                    ]

                if status_code == 200 and self.reference_response is not None:
                    if len(body) != len(self.reference_response):
                        mismatch = f"Size mismatch: got {len(body)} bytes, expected {len(self.reference_response)} bytes"
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Content Error | {mismatch}")
                        return [attempt_num, timestamp, "Content Error", elapsed, f"HTTP {status_code} | {mismatch}", 0]

                    mismatches = []
                    for i, (c1, c2) in enumerate(zip(body, self.reference_response)):
                        if c1 != c2:
                            mismatches.append((i, c1, c2))
                            if len(mismatches) >= 5:
                                break

                    if mismatches:
                        mismatch_details = "; ".join(
                            [
                                f"Pos {pos}: {chr(c1) if c1 < 128 else hex(c1)} != {chr(c2) if c2 < 128 else hex(c2)}"
                                for pos, c1, c2 in mismatches
                            ]
                        )
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Character Mismatch | {len(mismatches)} differences")
                        return [
                            attempt_num,
                            timestamp,
                            "Character Mismatch",
                            elapsed,
                            f"HTTP {status_code} | {len(mismatches)} character differences: {mismatch_details}",
                            0,
                        ]
                    else:
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Perfect character match")
                        return [
                            attempt_num,
                            timestamp,
                            "Success",
                            elapsed,
                            f"HTTP {status_code} | Size: {len(body)} bytes | Perfect character match",
                            0,
                        ]

                # Non-200 response
                print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Unexpected Response | HTTP {status_code}")
                return [
                    attempt_num,
                    timestamp,
                    "Unexpected Response",
                    elapsed,
                    f"HTTP {status_code} | Size: {len(body)} bytes",
                    0,
                ]

        except socket.timeout:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed, "Connection timed out", 0]

        except ConnectionRefusedError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Connection refused after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed, "Connection refused", 0]

        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, str(err), 0]
        
    def _run_tcp_test_dynamic(self, attempt_num: int, t0: float, timestamp: str) -> List:
        """Raw TCP test with dynamic TCP port check before request (similar to HTTP dynamic)."""
        # 1. TCP pre-check
        tcp_check_start = time.time()
        port_open = self.is_tcp_port_open(self.router_address, self.port, timeout=1.0)
        tcp_check_elapsed = round((time.time() - tcp_check_start) * 1000, 2)
        tcp_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        if not port_open:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] TCP port {self.port} not open before TCP request, skipping attempt. (TCP check: {tcp_check_elapsed} ms)")
            return [attempt_num, timestamp, "TCP Port Closed", elapsed,
                    f"TCP port {self.port} closed at {tcp_check_time}; TCP check took {tcp_check_elapsed}ms; skipping raw TCP request"]

        try:
            # 2. Open socket & send HTTP GET
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.router_address, self.port))

                req = (
                    f"GET / HTTP/1.1\r\n"
                    f"Host: {self.router_address}\r\n"
                    f"User-Agent: PacketLossTester/1.0\r\n"
                    f"Accept: */*\r\n"
                    f"Accept-Encoding: identity\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                ).encode("ascii", errors="ignore")

                http_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                sock.sendall(req)

                # 3. Read response
                chunks = []
                while True:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            break
                        chunks.append(data)
                    except socket.timeout:
                        break

                http_complete_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                raw = b"".join(chunks)
                elapsed = round((time.time() - t0) * 1000, 2)
                tcp_info = f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | HTTP:{http_start_time}->{http_complete_time}"

                if not raw:
                    print(f"[{attempt_num}/{self.num_tests}] Empty response")
                    return [attempt_num, timestamp, "Empty Response", elapsed, f"{tcp_info} | No data received"]

                # Separate headers/body
                header_end = raw.find(b"\r\n\r\n")
                if header_end == -1:
                    preview = raw[:80].decode("utf-8", errors="ignore")
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Non-HTTP response")
                    return [attempt_num, timestamp, "Error", elapsed, f"{tcp_info} | Non-HTTP response: {preview}"]

                headers = raw[:header_end].decode("iso-8859-1", errors="ignore")
                body = raw[header_end + 4 :]

                # Parse status code
                first_line = headers.split("\r\n", 1)[0]
                try:
                    parts = first_line.split()
                    status_code = int(parts[1]) if len(parts) > 1 else 0
                except Exception:
                    status_code = 0

                # Reference capture/compare (same as base TCP test)
                if status_code == 200 and self.reference_response is None:
                    self.reference_response = body
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Reference captured (size {len(body)} bytes)")
                    return [attempt_num, timestamp, "Success", elapsed,
                            f"{tcp_info} | HTTP {status_code} | Size: {len(body)} bytes | Reference captured"]

                if status_code == 200 and self.reference_response is not None:
                    if len(body) != len(self.reference_response):
                        mismatch = f"Size mismatch: got {len(body)} bytes, expected {len(self.reference_response)} bytes"
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Content Error | {mismatch}")
                        return [attempt_num, timestamp, "Content Error", elapsed,
                                f"{tcp_info} | HTTP {status_code} | {mismatch}"]

                    mismatches = []
                    for i, (c1, c2) in enumerate(zip(body, self.reference_response)):
                        if c1 != c2:
                            mismatches.append((i, c1, c2))
                            if len(mismatches) >= 5:
                                break

                    if mismatches:
                        mismatch_details = "; ".join(
                            [f"Pos {pos}: {chr(c1) if c1 < 128 else hex(c1)} != {chr(c2) if c2 < 128 else hex(c2)}"
                            for pos, c1, c2 in mismatches]
                        )
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Character Mismatch | {len(mismatches)} diffs")
                        return [attempt_num, timestamp, "Character Mismatch", elapsed,
                                f"{tcp_info} | HTTP {status_code} | {len(mismatches)} character differences: {mismatch_details}"]
                    else:
                        print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Perfect match")
                        return [attempt_num, timestamp, "Success", elapsed,
                                f"{tcp_info} | HTTP {status_code} | Size: {len(body)} bytes | Perfect character match"]

                print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Unexpected Response | HTTP {status_code}")
                return [attempt_num, timestamp, "Unexpected Response", elapsed,
                        f"{tcp_info} | HTTP {status_code} | Size: {len(body)} bytes"]

        except socket.timeout:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] TCP Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed,
                    f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | Connection timed out"]

        except ConnectionRefusedError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Connection refused after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed,
                    f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | Connection refused"]

        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed,
                    f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | {err}"]


        
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
        # Track when TCP check starts
        tcp_check_start = time.time()
        port_open = self.is_tcp_port_open(self.router_address, self.port, timeout=1.0)
        tcp_check_elapsed = round((time.time() - tcp_check_start) * 1000, 2)
        tcp_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        if not port_open:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] TCP port {self.port} not open before HTTP request, skipping attempt. (TCP check: {tcp_check_elapsed} ms)")
            return [attempt_num, timestamp, "TCP Port Closed", elapsed, 
                    f"TCP port {self.port} closed at {tcp_check_time}; TCP check took {tcp_check_elapsed}ms; skipping HTTP request"]

        try:
            http_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            url = f"http://{self.router_address}"
            # Use the persistent session for keep-alive
            response = self.session.get(url, timeout=self.timeout)
            elapsed = round((time.time() - t0) * 1000, 2)
            status_code = response.status_code
            http_complete_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            
            # Create detailed TCP check info for response
            tcp_info = f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | HTTP:{http_start_time}->{http_complete_time}"

            if not hasattr(response, 'content') or response.content is None:
                print(f"[{attempt_num}/{self.num_tests}] Response content is None")
                return [attempt_num, timestamp, "Error", elapsed, f"{tcp_info} | Response content is None"]

            content = response.content

            if status_code == 200 and self.reference_response is None:
                self.reference_response = content
                print(f"[{attempt_num}/{self.num_tests}] Captured reference response, size: {len(content)} bytes")
                return [attempt_num, timestamp, "Success", elapsed,
                        f"{tcp_info} | HTTP {status_code} | Size: {len(content)} bytes | Reference captured"]

            if status_code == 200 and self.reference_response is not None:
                if len(content) != len(self.reference_response):
                    mismatch = f"Size mismatch: got {len(content)} bytes, expected {len(self.reference_response)} bytes"
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Content Error | {mismatch}")
                    return [attempt_num, timestamp, "Content Error", elapsed,
                            f"{tcp_info} | HTTP {status_code} | {mismatch}"]

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
                            f"{tcp_info} | HTTP {status_code} | {len(mismatches)} character differences: {mismatch_details}"]
                else:
                    print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Success | Perfect match (TCP check: {tcp_check_elapsed} ms)")
                    return [attempt_num, timestamp, "Success", elapsed,
                            f"{tcp_info} | HTTP {status_code} | Size: {len(content)} bytes | Perfect character match"]
            else:
                content_size = len(content) if content else 0
                print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | Unexpected Response | HTTP {status_code}")
                return [attempt_num, timestamp, "Unexpected Response", elapsed,
                        f"{tcp_info} | HTTP {status_code} | Size: {content_size} bytes | No reference to compare against"]

        except requests.exceptions.Timeout:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] HTTP Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed, f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | HTTP request timed out"]

        except requests.exceptions.ConnectionError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Connection error after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed, f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | Connection error"]

        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, f"TCP:{tcp_check_time} ({tcp_check_elapsed}ms) | {str(err)}"]
        
    async def is_tcp_port_open_async(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Asynchronously check if TCP port is open, safe resource handling with async context."""
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            # Properly close the writer to avoid resource leaks
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
        except Exception:
            return False

    async def _run_http_test_dynamic_async(self, attempt_num: int, t0: float, timestamp: str) -> list:
        """Asynchronous HTTP test with dynamic TCP link check before request (non-blocking)"""
        # Add async request identification and tracking
        async_id = f"async-{attempt_num}"
        queued_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        # Check if TCP port is open
        tcp_check_start = time.time()
        port_open = await self.is_tcp_port_open_async(self.router_address, self.port, timeout=1.0)
        tcp_check_elapsed = round((time.time() - tcp_check_start) * 1000, 2)
        tcp_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        if not await self.is_tcp_port_open_async(self.router_address, self.port, timeout=1.0):
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] TCP port {self.port} not open, skipping attempt.")
            return [attempt_num, timestamp, "TCP Port Closed", elapsed, 
                    f"[ASYNC:{async_id}] TCP port {self.port} closed; Queued:{queued_time}; TCP check:{tcp_check_time} ({tcp_check_elapsed}ms)"]

        url = f"http://{self.router_address}"
        http_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        try:
            async with self.aiohttp_session.get(url, timeout=self.timeout) as response:
                content = await response.read()
                elapsed = round((time.time() - t0) * 1000, 2)  # response time in ms
                status_code = response.status
                http_complete_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                
                # Create detailed async info for response
                async_info = f"[ASYNC:{async_id}] Queued:{queued_time} | TCP:{tcp_check_time} | HTTP:{http_start_time}->{http_complete_time}"

                if not content:
                    print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] Response content is None")
                    return [attempt_num, timestamp, "Error", elapsed, f"{async_info} | Response content is None"]

                if status_code == 200 and self.reference_response is None:
                    self.reference_response = content
                    print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] Captured reference response, size: {len(content)} bytes")
                    return [attempt_num, timestamp, "Success", elapsed,
                            f"{async_info} | HTTP {status_code} | Size: {len(content)} bytes | Reference captured"]

                if status_code == 200 and self.reference_response is not None:
                    if len(content) != len(self.reference_response):
                        mismatch = f"Size mismatch: got {len(content)} bytes, expected {len(self.reference_response)} bytes"
                        print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] {elapsed} ms | Content Error | {mismatch}")
                        return [attempt_num, timestamp, "Content Error", elapsed, f"{async_info} | {mismatch}"]

                    mismatches = [(i, c1, c2) for i, (c1, c2) in enumerate(zip(content, self.reference_response)) if c1 != c2]
                    if mismatches:
                        mismatch_details = "; ".join([f"Pos {pos}: {chr(c1) if c1 < 128 else hex(c1)} != {chr(c2) if c2 < 128 else hex(c2)}"
                                                    for pos, c1, c2 in mismatches[:5]])
                        print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] {elapsed} ms | Character Mismatch | {len(mismatches)} differences")
                        return [attempt_num, timestamp, "Character Mismatch", elapsed, f"{async_info} | {mismatch_details}"]
                    else:
                        print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] {elapsed} ms | Success | Perfect match")
                        return [attempt_num, timestamp, "Success", elapsed, f"{async_info} | Perfect match"]

                else:
                    content_size = len(content) if content else 0
                    print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] {elapsed} ms | Unexpected Response | HTTP {status_code}")
                    return [attempt_num, timestamp, "Unexpected Response", elapsed,
                            f"{async_info} | HTTP {status_code} | Size: {content_size} bytes"]

            # Rest of error handling cases with async info added
        except asyncio.TimeoutError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] HTTP Timeout after {elapsed} ms")
            return [attempt_num, timestamp, "Timeout", elapsed, f"[ASYNC:{async_id}] HTTP request timed out | Queued:{queued_time}"]

        except aiohttp.ClientConnectionError:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] Connection error after {elapsed} ms")
            return [attempt_num, timestamp, "Error", elapsed, f"[ASYNC:{async_id}] Connection error | Queued:{queued_time}"]

        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] [ASYNC:{async_id}] Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Error", elapsed, f"[ASYNC:{async_id}] {str(err)} | Queued:{queued_time}"]

    
    def save_results_to_csv(self, file_path: str, stats: Dict[str, Any]):
        """Save test results to CSV file"""
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Metadata (unchanged)
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
            writer.writerow(["Test Mode", stats["test_mode"]])
            writer.writerow(["Dynamic TCP Check", "Yes" if self.use_dynamic_http_check else "No"])
            writer.writerow(["Total Attempts", self.num_tests])
            writer.writerow(["Successful Responses", stats["success_count"]])
            writer.writerow(["Lost Packets", stats["loss_count"]])
            writer.writerow(["Loss %", stats["loss_percent"]])
            writer.writerow(["Total Retries", stats["total_retries"]])
            writer.writerow(["Mean Retries", stats["mean_retries"]])

            # TCP-specific stats
            writer.writerow(["TCP Port Closed Count", stats["tcp_port_closed_count"]])
            writer.writerow(["TCP Port Closed %", stats["tcp_port_closed_percent"]])

            # Latency stats
            writer.writerow(["Mean Response Time (ms)", stats["mean_time"]])
            writer.writerow(["Median Response Time (ms)", stats["median_time"]])
            writer.writerow(["Min Response Time (ms)", stats["min_time"]])
            writer.writerow(["Max Response Time (ms)", stats["max_time"]])
            writer.writerow(["Total Duration (s)", stats["total_duration"]])
            writer.writerow([])

            # Results rows (added "Retries")
            writer.writerow([
                "Attempt", "Timestamp", "Status", "Response Time (ms)", "Response", "Retries"
            ])
            writer.writerows(self.results)



    def _calculate_summary_stats(self, start_time_str: str, test_start: float, test_end: float) -> Dict[str, Any]:
        """Calculate summary statistics"""
        end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_duration = round(test_end - test_start, 2)
        loss = self.num_tests - self.success_count
        loss_percent = round((loss / self.num_tests) * 100, 2)

        # Calculate TCP port closed stats
        tcp_port_closed_count = sum(1 for result in self.results if result[2] == "TCP Port Closed")
        tcp_port_closed_percent = round((tcp_port_closed_count / self.num_tests) * 100, 2) if self.num_tests > 0 else 0

        # Retry tracking
        retry_counts = [result[5] for result in self.results if len(result) > 5]  # assuming 6th column = retries
        total_retries = sum(retry_counts) if retry_counts else 0
        mean_retries = round(mean(retry_counts), 2) if retry_counts else 0

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
            "tcp_port_closed_count": tcp_port_closed_count,
            "tcp_port_closed_percent": tcp_port_closed_percent,
            "total_retries": total_retries,
            "mean_retries": mean_retries,
            "test_mode": "Async" if hasattr(self, "aiohttp_session") else "Sync",
            **stats
        }

    
    def print_summary(self, stats: Dict[str, Any], file_path: str):
        """Print test summary to console"""
        print("\nTest completed.")
        print(f"File saved to: {file_path}")
        print(f"Start time: {stats['start_time']}")
        print(f"End time: {stats['end_time']}")
        print(f"Protocol: {'HTTP' if self.use_http else 'TCP'} to {self.router_address}:{self.port}")
        print(f"Test Mode: {stats['test_mode']}")
        print(f"Dynamic TCP Check: {'Yes' if self.use_dynamic_http_check else 'No'}")
        print(f"Successful responses: {stats['success_count']}")
        print(f"Lost packets: {stats['loss_count']} ({stats['loss_percent']:.2f}%)")
        print(f"Total retries: {stats['total_retries']} | Mean retries per attempt: {stats['mean_retries']}")

        if self.use_dynamic_http_check:
            print(f"TCP Port Closed: {stats['tcp_port_closed_count']} ({stats['tcp_port_closed_percent']:.2f}%)")

        print(f"Mean: {stats['mean_time']} ms | Median: {stats['median_time']} ms | "
            f"Min: {stats['min_time']} ms | Max: {stats['max_time']} ms")

        
    def close(self):
        """Close any persistent resources like HTTP session"""
        if self.session:
            self.session.close()
