import socket
import os
import threading

from common.wire import send_json, recv_json, send_bytes
from common.discovery import find_server

PORT = 5001
DOWNLOADS_DIR = "downloads"

# ================= RECEIVER THREAD =================
def receiver_loop(sock: socket.socket, stop_event: threading.Event):
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    while not stop_event.is_set():
        try:
            msg = recv_json(sock)
        except (ConnectionError, OSError):
            break
        except Exception:
            continue

        mtype = msg.get("type")

        # ---------- Incoming live file ----------
        if mtype == "INCOMING_FILE":
            sender = msg.get("from")
            filename = os.path.basename(msg.get("filename") or "file.bin")
            size = int(msg.get("file_size") or 0)

            out_path = os.path.join(DOWNLOADS_DIR, filename)

            received = 0
            chunk_size = 4096

            last_percent = -1

            with open(out_path, "wb") as f:
                while received < size:
                    chunk = sock.recv(min(chunk_size, size - received))
                    if not chunk:
                        break

                    f.write(chunk)
                    received += len(chunk)

                    percent = int((received / size) * 100)

                    if last_percent != percent:
                        print(f"\rDownloading: {percent}%", end="", flush=True)
                        last_percent = percent

            print(f"\n Received '{filename}' from {sender}. Saved to {out_path}")
            print("> ", end="", flush=True)

        # ---------- Inbox download ----------
        elif mtype == "FILE_DOWNLOAD":
            filename = os.path.basename(msg.get("filename"))
            size = int(msg.get("file_size"))

            out_path = os.path.join(DOWNLOADS_DIR, filename)

            received = 0
            chunk_size = 4096

            last_percent = -1

            with open(out_path, "wb") as f:
                while received < size:
                    chunk = sock.recv(min(chunk_size, size - received))
                    if not chunk:
                        break

                    f.write(chunk)
                    received += len(chunk)

                    percent = int((received / size) * 100)

                    if percent != last_percent:
                        print(f"\rDownloading: {percent}%", end="", flush=True)
                        last_percent = percent

            print(f"\n Downloaded '{filename}' to {out_path}")
            print("> ", end="", flush=True)

        elif mtype == "FILE_CONSUMED":
            print(f"\n[INFO] '{msg.get('filename')}' removed from server inbox")
            print("> ", end="", flush=True)

        elif mtype == "INBOX_LIST":
            files = msg.get("files", [])

            print("\n Inbox files:")
            if not files:
                print("  (empty)")
            else:
                for f in files:
                    print(" -", f)

            print("> ", end="", flush=True)

        elif mtype == "USER_JOINED":
            print(f"\n[INFO] {msg.get('username')} joined the server")
            print("> ", end="", flush=True)

        elif mtype == "USER_LEFT":
            print(f"\n[INFO] {msg.get('username')} left the server")
            print("> ", end="", flush=True)

        elif mtype == "READY":
            print("\nServer ready — sending file...")
            print("> ", end="", flush=True)

        else:
            print(f"\n[SERVER] {msg}")
            print("> ", end="", flush=True)


# ================= MAIN CLIENT =================
def main():

    print("Searching for server...")
    server_ip = find_server()

    if server_ip is None:
        server_ip = input("Server not found. Enter IP manually: ")
    else:
        print("Server found at:", server_ip)

    username = input("Username: ").strip()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, PORT))

    # ---------- LOGIN ----------
    send_json(sock, {"type": "LOGIN", "username": username})
    resp = recv_json(sock)

    if resp.get("type") != "LOGIN_OK":
        print("Login failed:", resp)
        sock.close()
        return

    print(f"Logged in as {username}. Commands: list, send, inbox, get, quit")

    stop_event = threading.Event()
    recv_thread = threading.Thread(
        target=receiver_loop,
        args=(sock, stop_event)
    )
    recv_thread.start()

    # ---------- COMMAND LOOP ----------
    try:
        while True:
            cmd = input("> ").strip().lower()

            if cmd == "list":
                send_json(sock, {"type": "LIST_USERS"})

            elif cmd == "inbox":
                send_json(sock, {"type": "INBOX"})

            elif cmd == "get":
                filename = input("Filename to download: ").strip()
                send_json(sock, {"type": "GET_FILE", "filename": filename})

            elif cmd == "send":
                to_user = input("Send to (username): ").strip()
                path = input("File path: ").strip()

                if not os.path.isfile(path):
                    print("File not found.")
                    continue

                filename = os.path.basename(path)
                file_size = os.path.getsize(path)

                send_json(sock, {
                    "type": "SEND_FILE",
                    "to": to_user,
                    "filename": filename,
                    "file_size": file_size
                })

                print("Uploading file...")

                sent = 0
                chunk_size = 4096

                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break

                        send_bytes(sock, chunk)
                        sent += len(chunk)

                        percent = int((sent / file_size) * 100)
                        print(f"\rUploading: {percent}%", end="", flush=True)

                print("\nUpload complete.")

            elif cmd == "quit":
                try:
                    send_json(sock, {"type": "QUIT"})
                except Exception:
                    pass
                break

            else:
                print("Commands: list, send, inbox, get, quit")

    finally:
        stop_event.set()

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass

        sock.close()
        recv_thread.join(timeout=2)


if __name__ == "__main__":
    main()