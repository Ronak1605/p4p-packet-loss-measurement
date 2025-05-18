import serial
import time
from collections import deque
import crc8

class UARTMonitor:
    def __init__(self, port, baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        self.sequence = 0
        self.last_received_seq = -1
        self.loss_history = deque(maxlen=1000)
        self.crc_generator = crc8.crc8()

    def send(self, data):
        """Send data with sequence number and CRC."""
        payload = f"{self.sequence}:{data}"
        self.crc_generator.update(payload.encode())
        crc = self.crc_generator.hexdigest()
        packet = f"${payload}*{crc}\n".encode()
        self.ser.write(packet)
        self.sequence += 1

    def receive(self):
        """Check for packet loss and corruption."""
        raw = self.ser.readline()
        if not raw:
            return None
        try:
            decoded = raw.decode().strip()
            if decoded[0] != '$' or '*' not in decoded:
                raise ValueError("Invalid packet format")
            
            payload, crc_received = decoded[1:].split('*')
            seq_str, data = payload.split(':', 1)
            seq = int(seq_str)
            
            # CRC Check
            self.crc_generator.reset()
            self.crc_generator.update(payload.encode())
            if self.crc_generator.hexdigest() != crc_received:
                raise ValueError("CRC mismatch")
            
            # Sequence Check
            if seq != self.last_received_seq + 1 and self.last_received_seq != -1:
                self.loss_history.append((time.time(), seq))
            self.last_received_seq = seq
            return data
        except Exception as e:
            print(f"Error processing packet: {e}")
            return None

    def get_loss_rate(self, window_sec=10):
        now = time.time()
        recent_losses = [ts for ts, _ in self.loss_history if now - ts <= window_sec]
        return len(recent_losses) / window_sec  # Losses per second