from pathlib import Path
import os


temp_savefile = Path("tempsave.txt")
temp_savefile_to_delete = Path("todelete.txt")
temp_index = Path("temporary_index.txt")
temp_index_to_delete = Path("index_to_delete.txt")


class SimpleLocalFile:
    def __init__(self, string, ver, timestamp):
        self.string = string
        self.ver = ver
        self.timestamp = timestamp
        """
        EVERYTHING IS A STRING
        """


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


class IndexFileHandler:
    def __init__(self, home_index):
        self.home_index = home_index
        self.files = []

    def read_home_index(self):
        with open(self.home_index, "r") as f:
            while True:
                line = f.readline().rstrip("\n")
                if line == "":
                    break
                splitline = line.split("///")
                self.files.append(SimpleLocalFile(splitline[0], splitline[1], splitline[2]))

    def write_home_index(self):
        with open(temp_index, "w+") as f:
            for n in self.files:
                f.write(f"{n.string}///{n.ver}///{n.timestamp}\n")
        if temp_index_to_delete.exists():
            os.remove(temp_index_to_delete)
        os.rename(self.home_index, temp_index_to_delete)

        os.rename(temp_index, self.home_index)

        if temp_index_to_delete.exists():
            os.remove(temp_index_to_delete)