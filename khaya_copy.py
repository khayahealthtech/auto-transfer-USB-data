# Script for Khayahealthtech to auto-copy files from SD-card to gcloud storage
# Written by: Qhamani Maqungu
# Date Modified: 26 June 2025


import os
import shutil
import logging
import psutil
import pyudev
import time
from datetime import date

import venv
import zipfile

# to run gcloud 
from google.cloud import storage
import RPi.GPIO as GPIO



venv_dir = "/home/khayahealthtech/khaya_ws/venv"
DEST_FOLDER = "./khaya_ws/Patient_Data"
patient_data = "./khaya_ws/Patient_Data.zip" 

ip_address = "8.8.8.8"  # Google's DNS

bucket_name = "khaya-app-1.firebasestorage.app"
device_name = "device-001"
today = date.today().strftime('%Y%m%d')

#find the mount point for USB insertion
mount_point = "/media/khayahealthtech/KHAYA"


#start mode is standby, and will be updated
mode =  "stand-by"


#init GPIOs  using BOARD numbering
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



# Creating a zip-folder for the patient data
def createZipFolder(source, zip_folder):

	try:
		with zipfile.ZipFile(zip_folder, 'w', zipfile.ZIP_DEFLATED) as zipf:
			for root, _, files in os.walk(source):
				for file in files:
					full_path = os.path.join(root, file)
					relative_path = os.path.relpath(full_path, source)
					zipf.write(full_path, relative_path)
	except Exception as e:
		print("failed to compress file")]

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


# Locate the KHAYA device once mounted
def get_mounted_usb():
	for partition in psutil.disk_partitions(all=True):
		if "/media/khayahealthtech/KHAYA" in partition.mountpoint: 
			mountpoint = partition.mountpoint
			return partition.mountpoint
	return None



# Performs Local copy of files by
# using the mountpoint and the destination folder "Patient_Data"
def copy_files(src, dst):
	if not os.path.exists(dst):
		os.makedirs(dst) # creating new folder if one doesn't exist
	for root, _, files in os.walk(src):
		for file in files:
			src_path = os.path.join(root, file)
			dst_path = os.path.join(dst, os.path.relpath(src_path, src))
			os.makedirs(os.path.dirname(dst_path), exist_ok=True)

			try:
				shutil.copy2(src_path, dst_path)
				statusIndicator("local") # Progress Indicator via LED
			except Exception as e:
				print("failed")
				# Will need to show error on display



# Entry point in the script
def monitor_usb():

	# checking if KHAYA USB is already connected on mountpoint at start of the script
	# uses psutil to check through disk partitions 
	if get_mounted_usb() == mount_point: 
		backup_folder = os.path.join(DEST_FOLDER, os.path.basename(mount_point))
		copy_files(mount_point, backup_folder)

		print("done copying locally")
		GPIO.output(localCopy_LED, GPIO.LOW)

		upload_to_cloud(bucket_name, patient_data, patient_name);

   	# Then listens for USB insertions and copies data locally.
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

					# Zip the locally copied folder before uploading to gcloud storage
					createZipFolder(DEST_FOLDER,patient_data)

					# Making sure the file is compressed before attempting to uplad
					time.sleep(2)
					print("Stage 1 upload complete!")

				except Exception as e :
					print("failed to copy locally: ", e)


				# Init uploading to gcloud, check internet connection using  google's DSN server
				if(isDeviceOnline):
					statusIndicator("online")
					patient_id = device_name + today
					upload_to_cloud(bucket_name, patient_data, patient_id);

					statusIndicator("stand-by")

				else:
					print("please make sure device is connected to the internet")
def isDeviceOnline():

# check internet connection before coppying files to the internet
	try:
		subprocess.run(["ping", "-c", "1", "-w", "2", ip_address], timeout=2, check=True)
		return True
	except subprocess.CalledProcessError:
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

	generation_match_precondition = 1

	blob.upload_from_filename(source)
	# blob.upload_from_filename(source, if_generation_match=generation_match_precondition)

	print(f"File {source} uploaded to {destination_blob_name}.")

	statusIndicator("stand-by")
	exit()
	GPIO.cleanup()


if __name__ == "__main__":
	main()
