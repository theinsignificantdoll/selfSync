#!/bin/python3
import PySimpleGUI as sg
from tkinter import filedialog
from Logistics import FileHandler, IndexFileHandler
from pathlib import Path
from functools import partial


index_extension = ".index"
sg.theme("DarkBrown4")


delimiter = "\\"
fontsize = 15
fonttype = "Helvetica"
txtcolor = sg.theme_text_color()
initialwinsize = (400, 200)
initialwinpos = (50, 50)


file_handler = FileHandler()
file_handler.read_savefile()


def add_file_or_dir(directory):
    if directory:
        f = filedialog.askdirectory()
    else:
        f = filedialog.askopenfilename()
    if f is None:
        return
    file_handler.append(f)


def deletebutton(file):
    return sg.Button("DEL", key=file)


class OpenWin:
    def __init__(self):
        global shouldrestart
        self.shouldbreak = False
        self.topcol = [[sg.Button("ADD DIR"), sg.Button("ADD FILE")]]

        self.delcol = [
        ]

        self.deactivate_files = [

        ]

        self.filescol = [
        ]

        self.maincol = []

        for n in file_handler.saved:
            self.filescol.append(sg.T(n))
            self.deactivate_files.append(sg.Button("ADMIN", key=f"DEACTIVATE:{n}", disabled=n.is_file()))
            self.delcol.append(deletebutton(n))

        for ind, n in enumerate(self.delcol):
            self.maincol.append([self.delcol[ind], self.deactivate_files[ind], self.filescol[ind]])

        self.layout = [
            [sg.Col(self.topcol)],
            [sg.Col(self.maincol, vertical_scroll_only=True, scrollable=True, expand_y=True, expand_x=True)]
        ]

        self.win = sg.Window(title="syncGUI", layout=self.layout, size=(600, 300), resizable=True)

        while not self.shouldbreak:
            event, values = self.win.read(timeout=200)

            if event == "__TIMEOUT__":
                continue
            elif event == "ADD DIR":
                add_file_or_dir(True)
                self.restart()
            elif event == "ADD FILE":
                add_file_or_dir(False)
                self.restart()
            elif event[:11] == "DEACTIVATE:":
                shouldrestart = partial(DeactivateFileWin, (Path(event[11:]).parts[-1]))
                self.close()
            elif event == sg.WIN_CLOSED:
                self.close()
                break

            for n in file_handler.saved:
                if event == n:
                    if sg.popup_yes_no("Are you sure that you wish to delete this thing?"):
                        file_handler.remove(n)
                        self.restart()

    def close(self):
        self.shouldbreak = True
        self.win.close()

    def restart(self):
        global shouldrestart
        shouldrestart = OpenWin
        self.close()


class DeactivateFileWin:
    def __init__(self, home):
        global shouldrestart
        self.home = Path(home).parts[-1]
        self.home_index = Path(f"{self.home}{index_extension}")

        self.index_file_manager = IndexFileHandler(self.home_index)
        self.index_file_manager.read_home_index()

        self.deactivate_col = []
        self.file_names = []

        self.main_col = []

        for n in self.index_file_manager.files:
            self.deactivate_col.append(sg.Button("DE-ACT", key=n))
            self.file_names.append(sg.T(n.string))

        for ind, n in enumerate(self.file_names):
            self.main_col.append([self.deactivate_col[ind], self.file_names[ind]])

        self.layout = [
            [sg.Col(self.main_col, vertical_scroll_only=True, scrollable=True, expand_x=True,
                    expand_y=True)]
        ]

        self.win = sg.Window(str(home), self.layout, resizable=True)

        while True:
            event, values = self.win.read()

            if event == sg.WIN_CLOSED:
                self.win.close()
                shouldrestart = OpenWin
                break
            else:
                for n in self.index_file_manager.files:
                    if event == n:
                        self.index_file_manager.register_deactivation(event)


shouldrestart = OpenWin
while shouldrestart is not False:
    shouldrestart()
