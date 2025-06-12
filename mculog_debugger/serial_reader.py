import serial

def read_serial_log(port="/dev/cu.usbserial-TI4MYIGN1", baudrate=115200):
    """
    Establishes a serial connection with a microcontroller and reads log output.

    This function attempts to connect to a specified serial port and baud rate.
    If the connection is successful, it continuously reads and prints incoming
    serial data line by line. Errors during connection or runtime are logged
    to the console.

    Args:
        port (str): The serial port to connect to (e.g., '/dev/cu.usbserial-XXXX').
        baudrate (int): The baud rate for the serial connection (e.g., 115200).

    Raises:
        serial.SerialException: If the serial port cannot be opened.
        Exception: For any other unexpected errors during execution.
    """
    print(f"Connecting to {port} at {baudrate} baud...")

    try:
        with serial.Serial(port, baudrate, timeout=2) as ser:
            print("Serial connection established successfully.")
            # Future log processing would go here
            while True:
                line = ser.readline().decode(errors='ignore').strip()
                if line:
                    print("Received:", line)
    except serial.SerialException as e:
        print("Failed to connect to serial port.")
        print("Error:", e)
    except Exception as e:
        print("An unexpected error occurred.")
        print("Error:", e)

if __name__ == "__main__":
    read_serial_log()