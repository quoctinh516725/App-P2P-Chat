#gui.py
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
from network import PeerNode
import threading, os, base64

class LoginGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Login to P2P Chat")
        tk.Label(root, text="Username:").pack(padx=16, pady=4)
        self.username_var = tk.StringVar()
        tk.Entry(root, textvariable=self.username_var).pack(padx=8, pady=4)
        tk.Label(root, text="Password:").pack(padx=16, pady=4)
        self.password_var = tk.StringVar()
        tk.Entry(root, textvariable=self.password_var, show="*").pack(padx=8, pady=4)
        tk.Button(root, text="Login", command=self.attempt_login).pack(padx=8, pady=8)

        self.users_db = {"user":"123","user1":"123"}  # dummy users

    def attempt_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if self.users_db.get(username) == password:
            messagebox.showinfo("Login", f"Welcome {username}")
            self.root.destroy()
            ChatGUI(tk.Tk(), username)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

class ChatGUI:
    def __init__(self, root, username):
        self.root = root
        self.root.title(f"P2P Chat - {username}")
        self.nick = username
        self.node = PeerNode(self._on_message_from_network, self._on_status_from_network)
        self.node.set_login_info(username, "dummy")

        top = tk.Frame(root); top.pack(padx=8, pady=8, fill='x')
        tk.Label(top, text="Peer IP:").pack(side='left')
        self.ip_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(top, textvariable=self.ip_var, width=15).pack(side='left', padx=4)
        tk.Label(top, text="Port:").pack(side='left')
        self.port_var = tk.IntVar(value=5555)
        tk.Entry(top, textvariable=self.port_var, width=6).pack(side='left', padx=4)
        tk.Button(top, text="Start Listening", command=self.start_listen).pack(side='left', padx=6)
        tk.Button(top, text="Connect", command=self.connect_peer).pack(side='left', padx=6)

        body = tk.Frame(root); body.pack(fill='both', expand=True, padx=8, pady=8)
        left = tk.Frame(body); left.pack(side='left', fill='both', expand=True)
        right = tk.Frame(body, width=200); right.pack(side='right', fill='y')

        self.chat = scrolledtext.ScrolledText(left, state='disabled', wrap='word', height=20)
        self.chat.pack(fill='both', expand=True)

        bottom = tk.Frame(root); bottom.pack(padx=8, pady=8, fill='x')
        self.entry = tk.Entry(bottom)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind("<Return>", self.send_msg)
        tk.Button(bottom, text="Send", command=self.send_msg).pack(side='left', padx=6)
        tk.Button(bottom, text="Broadcast File", command=self.send_file_broadcast).pack(side='left', padx=6)

        tk.Label(right, text="Peers:").pack(anchor='nw')
        self.peer_list = tk.Listbox(right, height=15)
        self.peer_list.pack(fill='y', expand=True)
        tk.Button(right, text="Send File to Selected", command=self.send_file_to_selected).pack(fill='x', pady=4)
        tk.Button(right, text="Refresh Peers", command=self.refresh_peers).pack(fill='x')

        self._incoming_files = {}
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def start_listen(self):
        try:
            self.node.start_listening(host=self.ip_var.get(), port=self.port_var.get())
            self.append_chat("[Status] Listening...")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def connect_peer(self):
        try:
            self.node.connect_to(self.ip_var.get(), self.port_var.get())
            self.append_chat(f"[Status] Connecting to {self.ip_var.get()}:{self.port_var.get()}...")
            self.root.after(500, self.refresh_peers)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def send_msg(self, event=None):
        text = self.entry.get().strip()
        if not text: return
        sel = self.peer_list.curselection()
        try:
            if sel:
                addr = eval(self.peer_list.get(sel[0]))
                self.node.send_text_to(addr, text, nick=self.nick)
                self.append_chat(f"{self.nick} (to {addr}): {text}")
            else:
                self.node.broadcast_text(text, nick=self.nick)
                self.append_chat(f"{self.nick} (broadcast): {text}")
            self.entry.delete(0, 'end')
        except Exception as e:
            messagebox.showwarning("Warning", str(e))

    def send_file_broadcast(self):
        filepath = filedialog.askopenfilename()
        if not filepath: return
        threading.Thread(target=self.node.broadcast_file, args=(filepath,), daemon=True).start()
        self.append_chat(f"[Status] Sending {os.path.basename(filepath)} to all peers...")

    def send_file_to_selected(self):
        sel = self.peer_list.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a peer first")
            return
        addr = eval(self.peer_list.get(sel[0]))
        filepath = filedialog.askopenfilename()
        if not filepath: return
        threading.Thread(target=self.node.send_file_to, args=(addr, filepath), daemon=True).start()
        self.append_chat(f"[Status] Sending {os.path.basename(filepath)} to {addr}...")

    def refresh_peers(self):
        self.peer_list.delete(0, 'end')
        for p in self.node.list_peers():
            self.peer_list.insert('end', repr(p))

    # incoming file
    def _start_incoming_file(self, peer, filename, size):
        self._incoming_files[peer] = {"filename":filename,"size":size,"chunks":[]}

    def _append_incoming_file_chunk(self, peer, b64):
        rec = self._incoming_files.get(peer)
        if not rec: return
        rec["chunks"].append(b64)

    def _finish_incoming_file(self, peer, filename):
        rec = self._incoming_files.pop(peer,None)
        if not rec: return None
        fname = filename
        save_path = filedialog.asksaveasfilename(initialfile=fname)
        if not save_path: return None
        all_bytes = b''.join([base64.b64decode(c.encode('ascii')) for c in rec["chunks"]])
        with open(save_path,'wb') as f: f.write(all_bytes)
        return save_path

    def _on_message_from_network(self,msg):
        self.root.after(0, lambda:self.on_message(msg))

    def _on_status_from_network(self,text):
        self.root.after(0, lambda:self.on_status(text))

    def on_message(self,msg):
        typ = msg.get('type')
        peer_nick = msg.get('from') or repr(msg.get('peer'))
        if typ == 'msg':
            self.append_chat(f"{peer_nick}: {msg.get('text')}")
        elif typ == 'file_start':
            fname = msg.get('filename'); size=msg.get('size')
            self.append_chat(f"[File] Incoming {fname} ({size} bytes) from {peer_nick}")
            self._start_incoming_file(msg.get('peer'), fname, size)
        elif typ == 'file_chunk':
            self._append_incoming_file_chunk(msg.get('peer'), msg.get('data'))
        elif typ == 'file_end':
            out = self._finish_incoming_file(msg.get('peer'), msg.get('filename'))
            if out: self.append_chat(f"[File] Received {msg.get('filename')} saved to {out}")
        else:
            self.append_chat(f"[{peer_nick}] {msg}")

    def on_status(self,text):
        self.append_chat(f"[Status] {text}")
        self.refresh_peers()

    def append_chat(self,text):
        self.chat.configure(state='normal')
        self.chat.insert('end', text+'\n')
        self.chat.configure(state='disabled')
        self.chat.see('end')

    def on_close(self):
        self.node.close()
        self.root.destroy()

if __name__=="__main__":
    LoginGUI(tk.Tk())
