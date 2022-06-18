from pathlib import Path
import os


temp_savefile = Path("tempsave.txt")
temp_savefile_to_delete = Path("todelete.txt")


class FileHandler:
    def __init__(self, savefile=Path("savefile.txt")):
        self.savefile = savefile
        self.savefile.touch()
        self.saved = []

    def read_savefile(self):
        with open(self.savefile, "r") as f:
            while True:
                r = f.readline().rstrip("\n")
                if r == "":
                    break
                self.saved.append(Path(r))

    def write_savefile(self):
        with open(temp_savefile, "w+") as f:
            for n in self.saved:
                f.write(f"{n}\n")
        if temp_savefile_to_delete.exists():
            os.remove(temp_savefile_to_delete)
        if self.savefile.exists():
            os.rename(self.savefile, temp_savefile_to_delete)

        os.rename(temp_savefile, self.savefile)
        if temp_savefile_to_delete.exists():
            os.remove(temp_savefile_to_delete)

    def remove(self, o):
        self.saved.remove(o)
        self.write_savefile()

    def append(self, o):
        self.saved.append(o)
        self.write_savefile()

    def __repr__(self):
        return self.saved