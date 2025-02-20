
"""
******************************************************************************
* @file         : ppk.py
* @brief        : Log the average value of current coming from the Power Profiler Kit 2.
*
* Copyright    : Vision Metering, LLC
* Date         : December 5, 2023
* Author       : J.P.
* Version      : 1.0.0
******************************************************************************
"""

import csv
import time
import os

from ppk2_api.ppk2_api import PPK2_MP as PPK2_API

def get_formatted_time():
    """
    Returns the current local time as a string in "YYYY-MM-DD HH:MM:SS" format.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S")

def select_ppk2_port():
    """
    Lists available PPK2 devices and returns the first match for '/dev/ttyACM0'.
    Raises SystemExit if no suitable port is found.
    """
    ppk2s = PPK2_API.list_devices()
    print("Detected PPK2 devices:", ppk2s)

    if not ppk2s:
        raise SystemExit("No PPK2 found!")

    # Decide which device to pick, for example /dev/ttyACM0
    for dev in ppk2s:
        if "/dev/ttyACM0" in dev:
            print(f"Using PPK2 at {dev}")
            return dev

    raise SystemExit("Could not find a valid PPK2 port (e.g., '/dev/ttyACM0').")

def create_new_csv_file(data_folder, file_prefix):
    """
    Creates a new CSV file in data_folder with a dynamically generated filename.
    Returns (csvfile, csv_writer).
    """
    current_time_str = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(data_folder, f"{file_prefix}_{current_time_str}.csv")
    csvfile = open(filename, 'w', newline='')
    csv_writer = csv.writer(csvfile)
    # Write headers
    csv_writer.writerow(["Elapsed Time (s)", "Real Time", "Average Current (uA)"])
    print(f"New file created: {filename}")
    return csvfile, csv_writer

def main():
    ppk2_port = select_ppk2_port()
    
    # Initialize PPK2
    ppk2_test = PPK2_API(
        ppk2_port,
        buffer_max_size_seconds=1,
        buffer_chunk_seconds=0.01,
        timeout=1,
        write_timeout=1,
        exclusive=True
    )
    ppk2_test.get_modifiers()
    ppk2_test.set_source_voltage(3300)

    # Prepare folders and file naming
    data_folder = "data_ppk"
    os.makedirs(data_folder, exist_ok=True)
    file_prefix = 'log_ppk'

    sampling_interval_seconds = 1
    total_seconds = 28800  # 8 hours
    new_file_interval = 60  # rotate files every 60 seconds

    # Open the first CSV file
    csvfile, csv_writer = create_new_csv_file(data_folder, file_prefix)

    try:
        # Start measuring
        ppk2_test.use_source_meter()
        ppk2_test.toggle_DUT_power("ON")
        ppk2_test.start_measuring()

        start_time = time.time()
        next_rotation = start_time + new_file_interval

        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time >= total_seconds:
                break  # we've reached the total runtime

            # Check if it's time to rotate the file
            now = time.time()
            if now >= next_rotation:
                # Close the old file
                csvfile.close()
                # Open a new file
                csvfile, csv_writer = create_new_csv_file(data_folder, file_prefix)
                next_rotation += new_file_interval

            # Get data from PPK2
            read_data = ppk2_test.get_data()
            if read_data:
                samples, raw_digital = ppk2_test.get_samples(read_data)
                average_current = sum(samples) / len(samples) if samples else 0.0

                real_time_str = get_formatted_time()
                csv_writer.writerow([f"{elapsed_time:.2f}", real_time_str, f"{average_current:.3f}"])
                print(
                    f"Elapsed: {elapsed_time:.0f}s | "
                    f"Time: {real_time_str} | "
                    f"Avg Current: {average_current:.3f} uA"
                )

            # Sleep until the next second boundary to achieve ~1 sample/sec
            sleep_duration = max(0, sampling_interval_seconds - (time.time() - start_time) % sampling_interval_seconds)
            time.sleep(sleep_duration)

        # Stop measuring and power off
        ppk2_test.toggle_DUT_power("OFF")
        ppk2_test.stop_measuring()

    except KeyboardInterrupt:
        print("Program terminated by user (KeyboardInterrupt).")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Always clean up
        ppk2_test.toggle_DUT_power("OFF")
        ppk2_test.stop_measuring()
        if csvfile and not csvfile.closed:
            csvfile.close()

if __name__ == "__main__":
    main()
