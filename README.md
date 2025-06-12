# P4P #140 Packet Loss Repository
This repository holds the files for packet loss experiments for P4P #140.

## Running Files
Currently the only executable file is `mculog_debugger.serial_reader` which validates the output logs from the C2000 launchpad XL Microcontroller. Below are the steps to run it:

1. Naviagte to the root of the repository
2. Run ```pip install -r requirements.txt``` to install dependencies
3. Run ```python -m mculog_debugger.serial_reader``` or ```python3 -m mculog_debugger.serial_reader``` to start the reader


