
"""
******************************************************************************
* @file         : ppk.py
* @brief        : Log the average value of current coming from the Power Profiler Kit 2.
*
* Copyright    : Vision Metering, LLC
* Date         : December 5, 2023
* Author       : J.P.
* Version      : 0.0.1
******************************************************************************
"""

import csv
import time
import os
from ppk2_api.ppk2_api import PPK2_MP as PPK2_API

def get_formatted_time():
    return time.strftime("%Y-%m-%d %H:%M:%S")

ppk2s_connected = PPK2_API.list_devices()
if len(ppk2s_connected) == 1:
    ppk2_port = ppk2s_connected[0]
    print(f'Found PPK2 at {ppk2_port}')
else:
    print(f'Too many connected PPK2\'s: {ppk2s_connected}')
    exit()

ppk2_test = PPK2_API(ppk2_port, buffer_max_size_seconds=1, buffer_chunk_seconds=0.01, timeout=1, write_timeout=1,
                     exclusive=True)
ppk2_test.get_modifiers()
ppk2_test.set_source_voltage(3300)

# Dynamically generate a filename based on the current time and store it in the /data_ppk folder.
data_folder = "data_ppk"
os.makedirs(data_folder, exist_ok=True)
current_time_str = time.strftime("%Y%m%d_%H%M%S")
file_prefix = 'log_ppk'
csv_filename = os.path.join(data_folder, f"{file_prefix}_{current_time_str}.csv")

sampling_interval_seconds = 1
total_seconds = 28800       # 8hrs of Runtime.
new_file_interval = 60      # Create files every X seconds.
samples_per_second = 1000

try:
    # Open the CSV file for writing in the /data_ppk folder
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write headers to the CSV file
        csv_writer.writerow(["Time (s)", "Real Time", "Average Current (uA)"])

        # Get start time
        start_time = time.time()
        elapsed_time = 0

        # Source mode example
        ppk2_test.use_source_meter()
        ppk2_test.toggle_DUT_power("ON")
        ppk2_test.start_measuring()

        # Main loop
        while elapsed_time < total_seconds:
            read_data = ppk2_test.get_data()
            if read_data != b'':
                samples, raw_digital = ppk2_test.get_samples(read_data)
                average_current = sum(samples) / len(samples) if samples else 0

                elapsed_time = time.time() - start_time
                real_time = get_formatted_time()

                # Write data to CSV file
                csv_writer.writerow([elapsed_time, real_time, average_current])

                print(f"Elapsed time: {elapsed_time:.0f}s, Timestamp: {real_time}, Average Current: {average_current:.3f}uA")

                # Check if it's time to create a new file
                if int(elapsed_time) % new_file_interval == 0 and int(elapsed_time) != total_seconds:
                    print(f"New file created: {csv_filename}")
                    csvfile.close()

                    current_time_str = time.strftime("%Y%m%d_%H%M%S")
                    csv_filename = os.path.join(data_folder, f"{file_prefix}_{current_time_str}.csv")

                    # Open a new CSV file for writing
                    csvfile = open(csv_filename, 'w', newline='')
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(["Elapsed Time (s)", "Timestamp", "Average Current (uA)"])

            sleep_duration = max(0, sampling_interval_seconds - elapsed_time % sampling_interval_seconds)
            time.sleep(sleep_duration)

        ppk2_test.toggle_DUT_power("OFF")
        ppk2_test.stop_measuring()

except KeyboardInterrupt:
    print("ppk.py = Program terminated by user.")
    ppk2_test.toggle_DUT_power("OFF")
    ppk2_test.stop_measuring()
    csvfile.close()
except Exception as e:
    print(f"ppk.py = An error occurred: {e}")
    ppk2_test.toggle_DUT_power("OFF")
    ppk2_test.stop_measuring()
    csvfile.close()

# Ensure that the last file is closed
if 'csvfile' in locals() and not csvfile.closed:
    csvfile.close()
