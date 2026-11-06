"""Show an image as a full-screen window, standing in for a browser on the test display."""
import sys
import tkinter as tk

root = tk.Tk()
root.overrideredirect(True)
img = tk.PhotoImage(file=sys.argv[1])
root.geometry("%dx%d+0+0" % (img.width(), img.height()))
tk.Label(root, image=img, bd=0).pack()
root.mainloop()
