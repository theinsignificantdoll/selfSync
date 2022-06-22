#!/bin/python3
from syncClient import do_single_file, do_dir, LocalFile
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
deleted = []


def notify_upload(x: LocalFile):
    uploaded.append(x)


def notify_download(x: LocalFile):
    downloaded.append(x)


def notify_delete(x: LocalFile):
    deleted.append(x)


def failed_to_connect():
    global connection_failed
    connection_failed = True


def generate_notification_message():
    string = ""
    for n in uploaded:
        string += f"Uploaded {str(n)}\n"
    for n in downloaded:
        string += f"Downloaded {str(n)}\n"
    for n in deleted:
        string += f"Deleted {str(n)}\n"
    if len(string) > 256:
        return string[:256]
    return string.rstrip("\n")


def generate_header():
    if connection_failed:
        return "Failed to connect"
    out = ""
    if uploaded:
        out += "Uploaded"
        if downloaded:
            if deleted:
                out += ", "
            else:
                out += " & "
    if downloaded:
        out += "Downloaded"
        if deleted:
            out += " & "
    if deleted:
        out += "Deleted"
    if out == "":
        return "Certified"
    return out


if __name__ == "__main__":
    file_handler = Logistics.FileHandler()
    file_handler.read_savefile()
    connection_failed = False

    for n in file_handler.saved:
        if Path(n).is_dir():
            do_dir(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download,
                   when_delete_callback=notify_delete)
        elif Path(n).is_file() or Path(n).suffix != "":
            do_single_file(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download,
                           when_delete_callback=notify_delete)
        if connection_failed:
            break

    if notifications:
        notification.notify(title=generate_header(),
                            message=generate_notification_message(),
                            app_name="selfSync")



