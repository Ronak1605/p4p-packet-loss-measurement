# P4P #140 Packet Loss Repository
This repository holds the files for packet loss experiments for P4P #140.

## Running Files
### Microcontroller Communication:
The relevant file is `mculog_debugger.serial_reader` which validates the output logs from the C2000 launchpad XL Microcontroller. Below are the steps to run it:

1. Ensure that the C2000 launchpad XL Microcontroller is connected to your PC/Laptop, you can verify the connection on Mac by:
   1. Naviagting to your root user directory
   2. Running the command ```ls /dev/cu.*``` in a terminal
   3. You should see a listed device similar to ```/dev/cu.usbserial-TI4MYIGN1```
2. Naviagte to the root of this repository on your device
3. Run ```pip install -r requirements.txt``` in a terminal to install dependencies
4. Run ```python -m mculog_debugger.serial_reader``` or ```python3 -m mculog_debugger.serial_reader``` in the same terminal as above to start the reader

### Oscilloscope Communication:
The relevant file is `oscilloscope_logger.oscilloscope_logger` which logs the information from the oscilloscope and creates logs of the readings and any communication errors or packet loss events. Below are the steps to run it:

1. Ensure that the InfiniiVision DSOX3024T Oscilloscope is connected to your PC/Laptop
2. Naviagte to the root of this repository on your device
3. Run ```pip install -r requirements.txt``` in a terminal to install dependencies
4. Run ```python -m oscilloscope_logger.oscilloscope_logger``` or ```python3 -m oscilloscope_logger.oscilloscope_logger``` in the same terminal as above to start the reader


### Visualisation for Shielded vs Unshielded Cables
python3 -m oscilloscope_logger.visualise_results --compare oscilloscope_logger/results/lan/cable/shielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0021.csv oscilloscope_logger/results/lan/cable/shielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0022.csv oscilloscope_logger/results/lan/cable/shielded/high_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0023.csv oscilloscope_logger/results/lan/cable/unshielded/High_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0018.csv oscilloscope_logger/results/lan/cable/unshielded/High_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0019.csv oscilloscope_logger/results/lan/cable/unshielded/High_power_120deg/lan_test_results_lan_test_ac_output_60V_120_deg_test_0020.csv

### Router Packet Loss Testing:
#### TCP
Communicate to the router via a wired LAN connection. 

1. Navigate to `pc_to_router_logger` in your code space
2. Find the IP of the router on your PC
3. Run ```python router_test.py <router ip>``` or ```python router_test.py <router ip>``` e.g. ```python3 router_test.py 192.168.0.1```, this will start the packet loss detection.

### Oscilloscope Communication via Raspberry Pi (WiFi TCP Mode)

You can run oscilloscope tests by connecting the oscilloscope to a Raspberry Pi via USB, and then retrieving results from your PC over the **same WiFi network**.

#### **Setup Steps**

1. **Connect the Oscilloscope to the Raspberry Pi via USB.**

2. **Power on the Pi and connect it to your WiFi network.**

3. **Find the Pi’s IP address:**
    - If you have a monitor/keyboard attached, run:
      ```sh
      hostname -I
      ```
      or
      ```sh
      ip addr show wlan0
      ```
    - If you do not have a monitor, you can check your router’s admin page for a device named `raspberrypi` or similar.
    - If your Pi is set to a static IP, use that.  
      **For the TP-Link in the lab, the static IP is `192.168.0.50`.**

4. **(Optional) Set a static IP:**  
   You can configure a static IP for your Pi by using the network manager on the Pi

5. **SSH into the Pi from your PC (replace `<pi-ip>` with your Pi’s IP address):**
    ```sh
    ssh <your-username>@<pi-ip>
    ```
    Example for the lab Pi:
    ```sh
    ssh p4p-140@192.168.0.50
    ```

6. **Install dependencies on the Pi (using a Python virtual environment is recommended):**
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

7. **Run the TCP server on the Pi (using `sudo` and the full venv Python path):**
    ```sh
    cd oscilloscope_logger
    sudo /home/p4p-140/Downloads/p4p-repos/p4p-packet-loss-measurement/venv/bin/python3 oscilloscope_tcp_server.py
    ```
    - The server will wait for a connection from your PC and send each test result as it is collected.
    - `sudo` is required to access the USB oscilloscope device.
    - **Note:** You must use the full path to the Python executable inside your virtual environment when running with `sudo`, or the server will not see your installed dependencies.

8. **On your PC (connected to the same WiFi network), update the Pi IP in the client script and run the TCP client:**
    - Open `oscilloscope_logger/oscilloscope_tcp_client.py` and set the `PI_IP` variable to your Pi’s IP address (e.g., `192.168.0.50` for the lab Pi):
      ```python
      PI_IP = '192.168.0.50'  # Replace with your Pi's IP address
      ```
    - Then run:
      ```sh
      cd oscilloscope_logger
      python3 oscilloscope_tcp_client.py
      ```
    - The client will connect to the Pi and save results as a CSV file.

9. **Results will be saved as a CSV file in the appropriate results folder, with the same format as the USB logger.**

#### **Notes**
- The Pi and PC must be on the same WiFi network.
- You can run the Pi headless (no monitor/keyboard) and control it via SSH.
- To auto-start the server on boot, add a script to your crontab or create a systemd service.
- All test configuration (number of tests, cable type, etc.) is set in `oscilloscope_logger/test_config.py`.

#### **Troubleshooting**
- Ensure the oscilloscope is powered on and visible to the Pi (`lsusb` or `pyvisa` resource list).
- If you have connection issues, check your firewall and network settings.
- For SSH access, use your Pi’s username (e.g., `ssh p4p-140@192.168.0.50`).
- Sometimes in the GUI the Pi will start at the command line, in such a scenario enter the command 'startx' and it should be normal
- Somtimes the Pi will not detect the device in that case: repower the scope while it is insstalled in the PI




---

