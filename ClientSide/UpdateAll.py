#!/bin/python3
from syncClient import do_single_file, do_dir
from pathlib import Path
from plyer import notification
import Logistics
import sys


notifications = True
print(sys.argv)
if "--no_notifications" in sys.argv:
    print("NOTIFICATIONS: OFF")
    notifications = False


def notify_upload(x):
    if notifications:
        notification.notify("Uploading...", str(x))


def notify_download(x):
    if notifications:
        notification.notify("Downloading...", str(x))


file_handler = Logistics.FileHandler()
file_handler.read_savefile()
print(file_handler.saved)

for n in file_handler.saved:
    if Path(n).is_dir():
        do_dir(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download)
    elif Path(n).is_file() or Path(n).suffix != "":
        do_single_file(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download)



