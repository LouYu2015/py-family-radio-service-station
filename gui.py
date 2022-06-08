import tkinter as tk
import config


class GUI:
    def __init__(self):
        self.window = tk.Tk()
        for i in range(len(config.CHANNELS)):
            tk.Label(self.window, text=f"{i + 1}").grid(row=0, column=i)
            tk.Button(self.window, text="M").grid(row=1, column=i)

    def mainloop(self):
        self.window.mainloop()


if __name__ == "__main__":
    GUI().mainloop()
