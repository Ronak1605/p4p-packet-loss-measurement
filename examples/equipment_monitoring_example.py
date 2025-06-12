import pyvisa
import time
from datetime import datetime
import csv
import threading

# ---------------------------
# Shared Configuration
# ---------------------------
UART_CONFIG = {
    'baud_rate': 9600,
    'data_bits': 8,
    'parity': pyvisa.constants.Parity.none,
    'stop_bits': pyvisa.constants.StopBits.one,
    'timeout': 5000  # 5 seconds
}

# ---------------------------
# Oscilloscope Handler
# ---------------------------
class OscilloscopeMonitor:
    def __init__(self, port):
        self.rm = pyvisa.ResourceManager()
        self.scope = self._connect_scope(port)
        self.log_file = 'scope_errors.csv'
        self.running = False

    def _connect_scope(self, port):
        """Initialize UART connection to oscilloscope"""
        try:
            scope = self.rm.open_resource(port)
            scope.baud_rate = UART_CONFIG['baud_rate']
            scope.data_bits = UART_CONFIG['data_bits']
            scope.parity = UART_CONFIG['parity']
            scope.stop_bits = UART_CONFIG['stop_bits']
            scope.timeout = UART_CONFIG['timeout']
            
            # Verify connection
            scope.write('*IDN?')
            response = scope.read().strip()
            print(f"Connected to oscilloscope: {response}")
            
            # Configure error reporting
            scope.write('*CLS')
            scope.write(':SYSTEM:ERROR:ENABLE 1')
            return scope
            
        except pyvisa.VisaIOError as e:
            print(f"Oscilloscope connection failed: {str(e)}")
            return None

    def _log_error(self, error):
        """Log errors with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, error])

    def monitor_loop(self):
        """Main monitoring loop"""
        self.running = True
        while self.running:
            try:
                # Check for errors
                error = self.scope.query(':SYSTEM:ERROR?')
                if '0,"No error"' not in error:
                    self._log_error(error.strip())
                
                # Add additional parameter monitoring here
                time.sleep(0.5)
                
            except pyvisa.VisaIOError as e:
                error_msg = f"COM Error: {str(e)}"
                self._log_error(error_msg)
                time.sleep(2)  # Wait after communication error

# ---------------------------
# Power Supply Handler
# ---------------------------
class PowerSupplyMonitor:
    def __init__(self, port):
        self.rm = pyvisa.ResourceManager()
        self.ps = self._connect_ps(port)
        self.log_file = 'ps_errors.csv'
        self.running = False

    def _connect_ps(self, port):
        """Initialize UART connection to power supply"""
        try:
            ps = self.rm.open_resource(port)
            ps.baud_rate = UART_CONFIG['baud_rate']
            ps.data_bits = UART_CONFIG['data_bits']
            ps.parity = UART_CONFIG['parity']
            ps.stop_bits = UART_CONFIG['stop_bits']
            ps.timeout = UART_CONFIG['timeout']
            
            # Verify connection
            ps.write('*IDN?')
            response = ps.read().strip()
            print(f"Connected to power supply: {response}")
            
            # Initialize supply
            ps.write('*RST')
            ps.write('OUTP OFF')
            return ps
            
        except pyvisa.VisaIOError as e:
            print(f"Power supply connection failed: {str(e)}")
            return None

    def _log_error(self, error):
        """Log errors with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, error])

    def monitor_loop(self):
        """Main monitoring loop"""
        self.running = True
        while self.running:
            try:
                # Check for errors
                error = self.ps.query('SYST:ERR?')
                if '+0,"No error"' not in error:
                    self._log_error(error.strip())
                
                # Add additional parameter monitoring here
                time.sleep(0.5)
                
            except pyvisa.VisaIOError as e:
                error_msg = f"COM Error: {str(e)}"
                self._log_error(error_msg)
                time.sleep(2)  # Wait after communication error

# ---------------------------
# Main Execution
# ---------------------------
if __name__ == "__main__":
    # Initialize devices (modify ports as needed)
    scope_monitor = OscilloscopeMonitor('COM3')
    ps_monitor = PowerSupplyMonitor('COM4')

    # Start monitoring threads
    scope_thread = threading.Thread(target=scope_monitor.monitor_loop)
    ps_thread = threading.Thread(target=ps_monitor.monitor_loop)

    try:
        scope_thread.start()
        ps_thread.start()
        print("Monitoring started. Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        scope_monitor.running = False
        ps_monitor.running = False
        scope_thread.join()
        ps_thread.join()
        print("Monitoring stopped.")