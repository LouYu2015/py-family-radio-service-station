import tkinter as tk
import config


class GUI:
    def __init__(self, destroy_callback):
        self.destroy_callback = destroy_callback

        self.window = tk.Tk()
        self.window.bind("<Destroy>", self.on_destroy)
        for i in range(len(config.CHANNELS)):
            tk.Label(self.window, text=f"{i + 1}").grid(row=0, column=i)
            tk.Button(self.window, text="M").grid(row=1, column=i)

    def on_destroy(self, event):
        self.destroy_callback()

    def mainloop(self):
        self.window.mainloop()


if __name__ == "__main__":
    GUI().mainloop()
