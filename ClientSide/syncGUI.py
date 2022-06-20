#!/bin/python3
import PySimpleGUI as sg
from tkinter import filedialog
from Logistics import FileHandler


sg.theme("DarkBrown4")


delimiter = "\\"
fontsize = 15
fonttype = "Helvetica"
txtcolor = sg.theme_text_color()
initialwinsize = (400, 200)
initialwinpos = (50, 50)


file_handler = FileHandler()
file_handler.read_savefile()


shouldrestart = True


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
        self.shouldbreak = False
        self.topcol = [[sg.Button("ADD DIR"), sg.Button("ADD FILE")]]

        self.delcol = [
        ]

        self.filescol = [
        ]

        self.maincol = []

        for n in file_handler.saved:
            self.filescol.append(sg.T(n))
            self.delcol.append(deletebutton(n))

        for ind, n in enumerate(self.delcol):
            self.maincol.append([self.delcol[ind], self.filescol[ind]])

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
        shouldrestart = True
        self.close()


while shouldrestart:
    shouldrestart = False
    OpenWin()
