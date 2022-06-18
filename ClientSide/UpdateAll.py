from syncClient import do_single_file, do_dir
from pathlib import Path
from plyer import notification
import Logistics


def notify_upload(x):
    notification.notify("Uploading...", str(x))


def notify_download(x):
    notification.notify("Downloading...", str(x))


file_handler = Logistics.FileHandler()
file_handler.read_savefile()
print(file_handler.saved)

for n in file_handler.saved:
    print("H")
    if Path(n).is_dir():
        do_dir(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download)
    elif Path(n).is_file():
        do_single_file(Path(n), when_upload_callback=notify_upload, when_download_callback=notify_download)
    print(Path(n).suffix)



