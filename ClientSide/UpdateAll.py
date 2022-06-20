#!/bin/python3
from syncClient import do_single_file, do_dir
from pathlib import Path
from plyer import notification
import Logistics
import sys


notifications = True
if "--no_notifications" in sys.argv:
    print("NOTIFICATIONS: OFF")
    notifications = False


downloaded = []
uploaded = []


def notify_upload(x):
    uploaded.append(x)


def notify_download(x):
    downloaded.append(x)


def generate_notification_message():
    string = ""
    for n in uploaded:
        string += f"Uploaded {str(n)}\n"
    for n in downloaded:
        string += f"Downloaded {str(n)}\n"
    return string.rstrip("\n")


if __name__ == "__main__":
    file_handler = Logistics.FileHandler()
    file_handler.read_savefile()

    for n in file_handler.saved:
        if Path(n).is_dir():
            do_dir(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download)
        elif Path(n).is_file() or Path(n).suffix != "":
            do_single_file(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download)

    if notifications:
        notification.notify(title=f"{'Uploaded' if uploaded else ''}{' & ' if uploaded and downloaded else ''}{'Downloaded' if downloaded else ''}{'Certified' if not uploaded and not downloaded else ''}",
                            message=generate_notification_message(),
                            app_name="selfSync")



