import os
import shutil
import time
import getpass
import threading
import pyperclip
import hashlib
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, Menu
from tkinter.scrolledtext import ScrolledText
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from wallet import Wallet
from nft import NFT
from merkle_tree import calculate_merkle_root
from blockchain import store_nft_on_blockchain, get_stored_hash

WATCHED_FOLDER = "watched_folder"
BACKUP_FOLDER = "backups"
COOLDOWN_PERIOD = 2  # seconds
restored_files = {}  # file_path -> restore timestamp

os.makedirs(WATCHED_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)

class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_modified(self, event):
        if event.is_directory or self.app.pause_monitor:
            return

        file_path = event.src_path
        filename = os.path.basename(file_path)
        current_time = time.time()

        # 🔐 Skip if editing is authorized
        if self.app.authorized_editing.get(file_path):
            return

        if file_path in restored_files:
            if current_time - restored_files[file_path] < COOLDOWN_PERIOD:
                return
            else:
                del restored_files[file_path]

        current_hash = calculate_merkle_root(file_path)
        stored_hash = get_stored_hash(file_path)

        if current_hash != stored_hash:
            username = getpass.getuser()
            self.app.log_action(f"⚠️ Unauthorized modification on {filename}")
            self.restore_file(file_path)
            self.app.log_action(f"🔁 Restored {filename} from backup.")
            restored_files[file_path] = current_time
        else:
            self.app.log_action(f"✏️ Authorized modification on {filename}")

    def restore_file(self, file_path):
        filename = os.path.basename(file_path)
        backup_path = os.path.join(BACKUP_FOLDER, filename)
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)

class FileMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure File System")
        self.root.geometry("550x600")
        self.root.resizable(False, False)
        self.active_menu = None
        self.active_button = None
        self.logs = []
        self.pause_monitor = False  # new flag
        self.authorized_editing = {}  # Tracks authorized editing sessions


        tb.Label(root, text="Watched Files:", font=("Segoe UI", 14, "bold")).pack(anchor='w', padx=20, pady=(20, 10))

        self.file_frame = tb.Frame(root, bootstyle="dark")
        self.file_frame.pack(padx=20, pady=5, fill="both", expand=True)

        btn_row = tb.Frame(root)
        btn_row.pack(pady=15)

        tb.Button(btn_row, text="Upload File", bootstyle="info-outline", command=self.upload_file).pack(side="left", padx=10)
        tb.Button(btn_row, text="View Logs", bootstyle="info-outline", command=self.open_logs_window).pack(side="left", padx=10)
        self.log_window = None

        self.refresh_file_list()
        self.start_monitoring()

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        filename = os.path.basename(file_path)
        dest_path = os.path.join(WATCHED_FOLDER, filename)
        backup_path = os.path.join(BACKUP_FOLDER, filename)

        # Pause monitor logic
        self.pause_monitor = True

        shutil.copy2(file_path, dest_path)
        shutil.copy2(file_path, backup_path)

        try:
            nft_token = self.generate_nft_token(dest_path)
            if nft_token:
                self.show_uploaded_popup(nft_token)
                self.log_action(f"✅ {filename} uploaded successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log_action(f"❌ Failed to upload {filename}: {e}")

        self.refresh_file_list()
        time.sleep(1)  # Give time for blockchain write to settle

        self.pause_monitor = False  # Resume monitor

    def generate_nft_token(self, file_path):
        username = getpass.getuser()
        wallet = Wallet(username)
        wallet_address = wallet.get_wallet_address()
        merkle_root = calculate_merkle_root(file_path)
        if not merkle_root:
            raise Exception("Empty or unreadable file.")

        metadata = store_nft_on_blockchain(file_path, merkle_root, username)
        return metadata['nft_token'] if metadata else None

    def show_uploaded_popup(self, nft_token):
        popup = tb.Toplevel(self.root)
        popup.title("Upload Successful")
        popup.geometry("320x130")
        popup.resizable(False, False)

        tb.Label(popup, text="File uploaded successfully.", font=("Segoe UI", 11)).pack(pady=(20, 10))

        def copy_token():
            pyperclip.copy(nft_token)
            messagebox.showinfo("Copied", "NFT Token copied to clipboard.")

        tb.Button(popup, text="Copy NFT Token", bootstyle="success-outline", command=copy_token).pack(pady=(0, 20))

    def refresh_file_list(self):
        for widget in self.file_frame.winfo_children():
            widget.destroy()

        files = os.listdir(WATCHED_FOLDER)
        for f in files:
            row = tb.Frame(self.file_frame, bootstyle="dark")
            row.pack(fill='x', pady=6)

            label = tb.Label(row, text=f, anchor="w", font=("Segoe UI", 10))
            label.pack(side='left', padx=(10, 10), fill='x', expand=True)

            btn = tb.Button(row, text="⋮", bootstyle="secondary", width=3)
            btn.pack(side='right', padx=5)
            btn.configure(command=lambda f=f, b=btn: self.show_context_menu(f, b))

    def show_context_menu(self, filename, button_widget):
        if self.active_button == button_widget and self.active_menu:
            self.active_menu.unpost()
            self.active_menu = None
            self.active_button = None
            return

        if self.active_menu:
            self.active_menu.unpost()

        menu = Menu(self.root, tearoff=0, bg="#3c4043", fg="white", font=('Segoe UI', 10))
        menu.add_command(label="Modify File", command=lambda: self.modify_file(filename))
        menu.tk_popup(button_widget.winfo_rootx(), button_widget.winfo_rooty() + 30)
        self.active_menu = menu
        self.active_button = button_widget

    def modify_file(self, filename):
        file_path = os.path.join(WATCHED_FOLDER, filename)

        # NFT verification window
        auth_win = tb.Toplevel(self.root)
        auth_win.title(f"Authorize Modification: {filename}")
        auth_win.geometry("400x200")
        auth_win.resizable(False, False)

        tb.Label(auth_win, text="Enter NFT Token:", font=("Segoe UI", 11)).pack(pady=(20, 10))
        token_var = tb.StringVar()
        token_entry = tb.Entry(auth_win, textvariable=token_var, width=40)
        token_entry.pack()

        def attempt_modification():
            entered_token = token_var.get().strip()

            from blockchain import blockchain
            metadata = None
            for block in blockchain.chain:
                data = block.data
                if isinstance(data, dict) and data.get("file_path") == file_path:
                    metadata = data
                    break

            if not metadata:
                messagebox.showerror("Error", "File not registered on blockchain.")
                self.log_action(f"❌ Attempted modification (unregistered): {filename}")
                auth_win.destroy()
                return

            expected_token = metadata["nft_token"]
            expected_wallet = metadata["wallet_address"]

            username = getpass.getuser()
            wallet = Wallet(username)
            user_wallet = wallet.get_wallet_address()

            if entered_token != expected_token:
                messagebox.showerror("Access Denied", "Invalid NFT token.")
                self.log_action(f"❌ Invalid NFT token for {filename}")
                auth_win.destroy()
                return

            if user_wallet != expected_wallet:
                messagebox.showerror("Access Denied", "You are not the file owner.")
                self.log_action(f"❌ Unauthorized user tried to modify {filename}")
                auth_win.destroy()
                return

            # ✅ Authorized
            self.log_action(f"✅ Authorized modification of {filename}")
            self.authorized_editing[file_path] = True
            auth_win.destroy()
            self.open_editor_with_done_button(file_path)

        tb.Button(auth_win, text="Verify and Edit", bootstyle="success", command=attempt_modification).pack(pady=20)

    def log_action(self, message):
        timestamp = time.strftime("[%H:%M:%S]")
        entry = f"{timestamp} {message}"
        self.logs.append(entry)
        print(entry)

    def open_logs_window(self):
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.lift()
            return

        self.log_window = tb.Toplevel(self.root)
        self.log_window.title("System Logs")
        self.log_window.geometry("600x500")

        log_text = ScrolledText(self.log_window, font=("Segoe UI", 10))
        log_text.pack(fill="both", expand=True, padx=10, pady=10)
        log_text.insert("end", "\n".join(self.logs))
        log_text.config(state='disabled')

        def on_close():
            self.log_window.destroy()
            self.log_window = None

        self.log_window.protocol("WM_DELETE_WINDOW", on_close)

        tb.Button(self.log_window, text="Back", bootstyle="secondary-outline", command=on_close).pack(pady=10)



    def start_monitoring(self):
        event_handler = FileMonitorHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, WATCHED_FOLDER, recursive=False)
        observer_thread = threading.Thread(target=self.observer.start, daemon=True)
        observer_thread.start()
    
    def open_editor_with_done_button(self, file_path):
        editor_win = tb.Toplevel(self.root)
        editor_win.title("Editing File (Authorized)")
        editor_win.geometry("400x150")

        tb.Label(editor_win, text="You are authorized to edit this file.", font=("Segoe UI", 11)).pack(pady=10)
        tb.Label(editor_win, text="Edit in your editor, then click below when you're done.", font=("Segoe UI", 9)).pack()

        def done_editing():
            new_hash = calculate_merkle_root(file_path)
            shutil.copy2(file_path, os.path.join(BACKUP_FOLDER, os.path.basename(file_path)))

            # Add updated block to blockchain
            from blockchain import blockchain, get_latest_metadata
            metadata = get_latest_metadata(file_path)

            if metadata:
                updated_metadata = {
                    "merkle_root": new_hash,
                    "wallet_address": metadata["wallet_address"],
                    "nft_token": metadata["nft_token"],
                    "timestamp": time.time(),
                    "file_path": file_path
                }
                blockchain.add_block(updated_metadata)
                self.log_action(f"🧱 Blockchain updated after authorized edit: {os.path.basename(file_path)}")
            else:
                self.log_action(f"❌ Could not update blockchain for {os.path.basename(file_path)}")

            self.log_action(f"✅ Backup updated after authorized edit: {os.path.basename(file_path)}")
            self.authorized_editing[file_path] = False
            editor_win.destroy()


        tb.Button(editor_win, text="Done", bootstyle="success", command=done_editing).pack(pady=20)

        # Open the file in system's default text editor
        os.system(f"subl '{file_path}'")


if __name__ == "__main__":
    app = tb.Window(themename="darkly")
    FileMonitorApp(app)
    app.mainloop()
