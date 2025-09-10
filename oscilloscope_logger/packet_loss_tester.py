import time
import csv
import numpy as np
from statistics import mean, median
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import test_config

class PacketLossTester:
    def __init__(self, scope, connection_type: str, num_tests: int = 100):
        self.scope = scope
        self.connection_type = connection_type
        self.num_tests = num_tests
        self.results = []
        self.response_times = []
        self.success_count = 0
        
    def run_test(self, delay_between_tests: float = 0) -> Dict[str, Any]:
        """Run the packet loss test and return results
        Args:
            delay_between_tests (float): Delay in seconds between each test attempt. If too small, it will do it as fast as possible.
        Returns:
            Dict[str, Any]: Summary statistics including success count, loss count, and response times.
        """
        print(f"Starting {self.connection_type} test with {self.num_tests} attempts")
        
        # Pause once before all tests
        self.scope.write(":STOP")
        
        start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        test_start = time.time()
        
        for n in range(self.num_tests):
            result = self._run_single_test(n + 1)
            self.results.append(result)
            
            if result[2] == "Success":  # Status field
                self.success_count += 1
                self.response_times.append(result[3])  # Response time field
                
            time.sleep(delay_between_tests)
        
        # Resume after all tests
        self.scope.write(":RUN")
        test_end = time.time()
        
        return self._calculate_summary_stats(start_time_str, test_start, test_end)
    
    def _run_single_test(self, attempt_num: int) -> List:
        """Run a single test attempt"""
        t0 = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        try:
            # Get waveform data instead of checking identification
            self.scope.write(":WAVeform:SOURce CHANnel2")
            self.scope.write(":WAVeform:FORMat BYTE")
            self.scope.write(":WAVeform:POINts 4000")
            waveform_data = self.scope.query_binary_values(":WAVeform:DATA?", datatype='B')
            
            elapsed = round((time.time() - t0) * 1000, 2)
            
            if waveform_data and len(waveform_data) > 0:
                # Get measurements
                v_rms = self.scope.query(":MEASure:VRMS? CHAN1").strip()
                acrms_ch2 = self.scope.query(":MEASure:ACRMS? CHAN2").strip()
                acrms_ch3 = self.scope.query(":MEASure:ACRMS? CHAN3").strip()
                
                # Calculate some basic stats about the waveform
                waveform_min = min(waveform_data)
                waveform_max = max(waveform_data)
                waveform_avg = round(sum(waveform_data) / len(waveform_data), 2)
                
                print(f"[{attempt_num}/{self.num_tests}] {elapsed} ms | VRMS CH1: {v_rms} V | CH2: {acrms_ch2} A | CH3: {acrms_ch3} A | Waveform points: {len(waveform_data)}")
                
                return [attempt_num, timestamp, "Success", elapsed, f"Data points: {len(waveform_data)}", v_rms, acrms_ch2, acrms_ch3, waveform_min, waveform_max, waveform_avg]
            else:
                print(f"[{attempt_num}/{self.num_tests}] No waveform data received")
                return [attempt_num, timestamp, "No Data", elapsed, "No waveform data", "", "", "", "", "", ""]
                
        except Exception as err:
            elapsed = round((time.time() - t0) * 1000, 2)
            print(f"[{attempt_num}/{self.num_tests}] Timeout/Error after {elapsed} ms: {err}")
            return [attempt_num, timestamp, "Timeout/Error", elapsed, str(err), "", "", "", "", "", ""]
    
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
            writer.writerow([f"{self.connection_type.upper()} Test with Measurement Logging"])
            writer.writerow(["Start Time", stats["start_time"]])
            writer.writerow(["End Time", stats["end_time"]])
            writer.writerow(["Cable Type", test_config.cable_type])
            writer.writerow(["Position", test_config.position])
            writer.writerow(["Power State", test_config.power_state])
            writer.writerow(["Conduction Angle", test_config.conduction_angle])
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
                "V RMS CH1 (V)", "AC RMS CH2 (A)", "AC RMS CH3 (A)", 
                "Waveform Min", "Waveform Max", "Waveform Avg"
            ])
            writer.writerows(self.results)
    
    def print_summary(self, stats: Dict[str, Any], file_path: str):
        """Print test summary to console"""
        print("\nTest completed.")
        print(f"File saved to: {file_path}")
        print(f"Start time: {stats['start_time']}")
        print(f"End time: {stats['end_time']}")
        print(f"Successful responses: {stats['success_count']}")
        print(f"Lost packets: {stats['loss_count']} ({stats['loss_percent']:.2f}%)")
        print(f"Mean: {stats['mean_time']} ms | Median: {stats['median_time']} ms | Min: {stats['min_time']} ms | Max: {stats['max_time']} ms")

def convert_vrms_to_current(vrms_str: str, gain_mV_per_A: float, channel: str) -> float:
    """Convert VRMS to current using probe gain"""
    try:
        vrms = float(vrms_str)
        sensitivity_V_per_A = gain_mV_per_A / 1000.0
        return round(vrms / sensitivity_V_per_A, 6)
    except ValueError:
        print(f"Invalid VRMS value from {channel}: '{vrms_str}'")
        return float("nan")