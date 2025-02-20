
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

def detect_ppk2_port():
    """
    Attempts to open each device returned by PPK2_API.list_devices().
    If we can successfully call a PPK2-specific function (e.g., get_modifiers())
    without error, we assume it's the correct port.

    Returns:
        A string with the device path (e.g. '/dev/ttyACM1') if found;
        otherwise None if no valid PPK2 device is detected.
    """
    candidate_ports = PPK2_API.list_devices()
    print("Candidate PPK2 ports:", candidate_ports)

    if not candidate_ports:
        print("No PPK2 devices found.")
        return None

    for dev in candidate_ports:
        print(f"Testing potential PPK2 device at: {dev}")
        try:
            # Try opening the device in a short-lived instance
            temp_ppk2 = PPK2_API(
                dev,
                buffer_max_size_seconds=1,
                buffer_chunk_seconds=0.01,
                timeout=1,
                write_timeout=1,
                exclusive=True
            )
            # This call will fail if 'dev' is not actually a PPK2
            temp_ppk2.get_modifiers()

            # If we got here without an exception, 'dev' is valid.
            print(f"Detected PPK2 at {dev}")
            return dev

        except Exception as e:
            # If something went wrong, assume it's not the correct port
            print(f"Port {dev} failed to open as PPK2. Error: {e}")
            # Just move on to the next candidate
            continue

    # If we tried everything and did not succeed, return None
    return None

def get_formatted_time():
    """Returns the current local time as a string in 'YYYY-MM-DD HH:MM:SS' format."""
    return time.strftime("%Y-%m-%d %H:%M:%S")

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
    # Dynamically detect the correct PPK2 port
    ppk2_port = detect_ppk2_port()
    if ppk2_port is None:
        print("Could not detect a valid PPK2 port. Exiting.")
        return

    print(f"Using PPK2 at {ppk2_port}")

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

    # Folder and file settings
    data_folder = "data_ppk"
    os.makedirs(data_folder, exist_ok=True)
    file_prefix = 'log_ppk'

    sampling_interval_seconds = 1
    total_seconds = 28800  # 8 hours
    new_file_interval = 60  # rotate files every 60 seconds

    # Open the first CSV file
    csvfile, csv_writer = create_new_csv_file(data_folder, file_prefix)

    # Setup measurement
    ppk2_test.use_source_meter()
    ppk2_test.toggle_DUT_power("ON")
    ppk2_test.start_measuring()

    start_time = time.time()
    next_rotation = start_time + new_file_interval

    try:
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time >= total_seconds:
                # Stop after the total runtime
                break

            # File rotation check
            now = time.time()
            if now >= next_rotation:
                csvfile.close()
                csvfile, csv_writer = create_new_csv_file(data_folder, file_prefix)
                next_rotation += new_file_interval

            # Grab data from PPK2
            read_data = ppk2_test.get_data()
            if read_data:
                samples, raw_digital = ppk2_test.get_samples(read_data)
                average_current = sum(samples) / len(samples) if samples else 0.0

                real_time_str = get_formatted_time()
                csv_writer.writerow([f"{elapsed_time:.2f}", real_time_str, f"{average_current:.3f}"])
                print(f"Elapsed: {elapsed_time:.0f}s | Time: {real_time_str} | Avg Current: {average_current:.3f} uA")

            # Sleep to approximate 1-second sampling intervals
            sleep_duration = max(0, sampling_interval_seconds - (time.time() - start_time) % sampling_interval_seconds)
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        print("KeyboardInterrupt detected. Exiting gracefully...")

    finally:
        # Always make sure we turn off DUT power and stop measuring
        ppk2_test.toggle_DUT_power("OFF")
        ppk2_test.stop_measuring()
        # Close CSV file if open
        if csvfile and not csvfile.closed:
            csvfile.close()

if __name__ == "__main__":
    main()
