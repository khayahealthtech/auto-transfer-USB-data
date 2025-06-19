
# This is a new file


import os
import shutil
import logging
import psutil
import pyudev
import time

# Configure logging
#LOGFILE = "/var/log/usb_autocopy.log"
#logging.basicConfig(filename=LOGFILE, level=logging.INFO, format="%(asctime)s - %(message)s")

DEST_FOLDER = "/home/pi/USB_Backups"

def get_mounted_usb():
	for partition in psutil.disk_partitions(all=True):
		if "/media/pi/KHAYA" in partition.mountpoint: # Adjust for different OS paths if needed
			return partition.mountpoint
	return None

def copy_files(src, dst):

	if not os.path.exists(dst):
		os.makedirs(dst)
		print("making a new folder")

	for root, _, files in os.walk(src):
		for file in files:
			src_path = os.path.join(root, file)
			dst_path = os.path.join(dst, os.path.relpath(src_path, src))
			os.makedirs(os.path.dirname(dst_path), exist_ok=True)

			try:
				shutil.copy2(src_path, dst_path)
               # logging.info(f"Copied: {src_path} -> {dst_path}")
				print("copying...")
			except Exception as e:
				print("failed")
               # logging.error(f"Failed to copy {src_path}: {e}")

def monitor_usb():
   #Continuously listens for USB insertions and copies data."""
	context = pyudev.Context()
	monitor = pyudev.Monitor.from_netlink(context)
	monitor.filter_by(subsystem="block")

  #  logging.info("Monitoring for USB insertions...")

	for device in iter(monitor.poll, None):
		if device.action == "add":
			time.sleep(2)  # Give system time to mount USB

			usb_path = get_mounted_usb()
			if usb_path:
				backup_folder = os.path.join(DEST_FOLDER, os.path.basename(usb_path))
              		 # logging.info(f"USB detected at {usb_path}, copying to {backup_folder}...")
				copy_files(usb_path, backup_folder)
              		 # logging.info("File copy completed.")

if __name__ == "__main__":
    monitor_usb()
