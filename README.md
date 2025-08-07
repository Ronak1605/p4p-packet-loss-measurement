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
