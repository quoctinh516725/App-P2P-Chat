import tkinter as tk

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Chat")
        tk.Label(root, text="GUI Chat Example").pack(padx=10, pady=10)
