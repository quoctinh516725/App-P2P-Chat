#app.py
import tkinter as tk
from gui import LoginGUI

def main():
    root = tk.Tk()
    LoginGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
