
import subprocess # handles subprocesses like crating venv

import os
import shutil
import logging
import psutil
import pyudev
import time

import venv

# to run gcloud 
from google.cloud import storage
import RPi.GPIO as GPIO



venv_dir = "/home/khayahealthtech/khaya_ws/venv"
DEST_FOLDER = "/home/khayahealthtech/khaya_ws/Data"
source_name = "/home/khayahealthtech/khaya_ws/Data/KHAYA/khaya_usb_copy.py" 

ip_address = "8.8.8.8"  # Google's DNS

bucket_name = "khaya-app-1.firebasestorage.app"
patient_name = "Qhamani-Testing"

#find the mount poinyt for USB insertion
mount_point = "/media/khayahealthtech/KHAYA"


mode =  "stand-by"


#ini GPIOs  using BOARD numbering
GPIO.setmode(GPIO.BCM)

standby_LED = 15
localCopy_LED = 14
onlineCopy_LED = 17

GPIO.setup(standby_LED, GPIO.OUT)
GPIO.setup(localCopy_LED, GPIO.OUT)
GPIO.setup(onlineCopy_LED, GPIO.OUT)

GPIO.output(standby_LED, GPIO.LOW)
GPIO.output(localCopy_LED, GPIO.LOW)
GPIO.output(onlineCopy_LED, GPIO.LOW)

time.sleep(3)
# This will handle most of the UI operations

def main():
	monitor_usb()

def create_venv():
	builder = venv.EnvBuilder(with_pip=True)
	builder.create(venv_dir)
	print(f"Virtual environment created at {venv_dir}")

def statusIndicator(mode):

	match mode:
		case "stand-by":
			GPIO.output(localCopy_LED, GPIO.LOW)
			GPIO.output(onlineCopy_LED, GPIO.LOW)
			GPIO.output(standby_LED, GPIO.HIGH) 
		case "local":
			print("Local Copy in Progress..")
			GPIO.output(standby_LED, GPIO.LOW)
			GPIO.output(localCopy_LED, GPIO.HIGH)
		case "online":
			GPIO.output(localCopy_LED, GPIO.LOW)
			print("Online Copy in Progress..")
			GPIO.output(onlineCopy_LED, GPIO.HIGH)

def get_mounted_usb():
	for partition in psutil.disk_partitions(all=True):
		if "/media/khayahealthtech/KHAYA" in partition.mountpoint: # Adjust for different OS paths if needed
			mountpoint = partition.mountpoint
			return partition.mountpoint
	return None

#local copy of files
def copy_files(src, dst):
	if not os.path.exists(dst):
		os.makedirs(dst) #creating new folder if one doesn't exist
	for root, _, files in os.walk(src):
		for file in files:
			src_path = os.path.join(root, file)
			dst_path = os.path.join(dst, os.path.relpath(src_path, src))
			os.makedirs(os.path.dirname(dst_path), exist_ok=True)

			try:
				shutil.copy2(src_path, dst_path)
               # logging.info(f"Copied: {src_path} -> {dst_path}")
				statusIndicator("local")
			except Exception as e:
				print("failed")
               # logging.error(f"Failed to copy {src_path}: {e}")


# Entry point in the script
def monitor_usb():

	# checking if KHAYA USB is already connected on mountpoint at start of the script
	# uses psutil to check through disk partitions 
	if get_mounted_usb() == mount_point: 
		backup_folder = os.path.join(DEST_FOLDER, os.path.basename(mount_point))
		# logging.info(f"USB detected at {usb_path}, copying to {backup_folder}...")
		copy_files(mount_point, backup_folder)
		print("done copying locally")
		GPIO.output(localCopy_LED, GPIO.LOW)

		upload_to_cloud(bucket_name, source_name, patient_name);

   	#Then listens for USB insertions and copies data locally.
	context = pyudev.Context()
	monitor = pyudev.Monitor.from_netlink(context)
	monitor.filter_by(subsystem="block")

	print("======================================================")
	print("No KHAYA disc detected")
	print("======================================================")
	print("On standby mode!")
	statusIndicator("stand-by")

	for device in iter(monitor.poll, None):
		if device.action == "add":
			time.sleep(2)  # Give system time to mount USB

			usb_path = get_mounted_usb()
			if usb_path:
				backup_folder = os.path.join(DEST_FOLDER, os.path.basename(usb_path))

				try:
					copy_files(usb_path, backup_folder)
					print("Stage 1 upload complete!")
				except Exception as e :
					print("failed to copy locally: ", e)


				#Init uploading to gcloud
				if(isDeviceOnline):
					statusIndicator("online")
					upload_to_cloud(bucket_name, source_name, patient_name);

					statusIndicator("stand-by")
def isDeviceOnline():

#check internet connection before coppying files to the internet
	try:
		subprocess.run(["ping", "-c", "1", "-w", "2", ip_address], timeout=2, check=True)
		print("Connected to the internet")
		return True
	except subprocess.CalledProcessError:
		print("No internet connection")
		return False

def upload_to_cloud(bucket_name, source, destination_blob_name):
    #Uploads a file to the bucket
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

	storage_client = storage.Client()
	bucket = storage_client.bucket(bucket_name)
	blob = bucket.blob(destination_blob_name)

    # Optional: set a generation-match precondition to avoid potential race conditions
    # and data corruptions. The request to upload is aborted if the object's
    # generation number does not match your precondition. For a destination
    # object that does not yet exist, set the if_generation_match precondition to 0.
    # If the destination object already exists in your bucket, set instead a
    # generation-match precondition using its generation number.
	generation_match_precondition = 1

	blob.upload_from_filename(source)
	#blob.upload_from_filename(source, if_generation_match=generation_match_precondition)

	print(f"File {source} uploaded to {destination_blob_name}.")

	statusIndicator("stand-by")
	exit()


if __name__ == "__main__":
	main()
