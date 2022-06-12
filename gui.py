import tkinter as tk
import config


class GUI:
    def __init__(self, destroy_callback):
        # destroy_callback will be called when the window is closed
        self.destroy_callback = destroy_callback

        self.window = tk.Tk()
        self.window.bind("<Destroy>", self.on_destroy)
        self.channel_labels = []
        self.channel_muted = [False] * len(config.CHANNELS)
        self.default_fg = None
        self.default_bg = None
        for i in range(len(config.CHANNELS)):
            label = tk.Label(self.window, text=f"{i + 1}")
            label.grid(row=0, column=i)
            self.default_fg = label.cget('fg')
            self.default_bg = label.cget('bg')

            button = tk.Button(self.window, text="M", command=self.mute_handler(i))
            button.grid(row=1, column=i)

            self.channel_labels.append(label)

    def set_channel_activity(self, channel, status):
        if status == 'active':
            self.channel_labels[channel].configure(bg="orange", fg="white")
        elif status == 'waiting':
            self.channel_labels[channel].configure(bg="green", fg="white")
        elif status == 'nothing':
            self.channel_labels[channel].configure(bg=self.default_bg, fg=self.default_fg)
        else:  # Muted
            self.channel_labels[channel].configure(bg=self.default_bg, fg="red")

    def mute_handler(self, channel):
        def handler():
            self.channel_muted[channel] = not self.channel_muted[channel]
        return handler

    def on_destroy(self, event):
        self.destroy_callback()

    def mainloop(self):
        self.window.mainloop()


if __name__ == "__main__":
    # Test UI
    GUI(destroy_callback=lambda: None).mainloop()
