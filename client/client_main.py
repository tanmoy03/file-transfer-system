import socket
import os
import threading
from common.wire import send_json, recv_json, send_bytes, recv_bytes

PORT = 5001

DOWNLOADS_DIR = "downloads"

def receiver_loop(sock: socket.socket):
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    while True:
        msg = recv_json(sock)
        mtype = msg.get("type")

        if mtype == "INCOMING_FILE":
            sender = msg.get("from")
            filename = os.path.basename(msg.get("filename") or "file.bin")
            size = int(msg.get("file_size") or 0)

            data = recv_bytes(sock, size)
            out_path = os.path.join(DOWNLOADS_DIR, filename)
            with open(out_path, "wb") as f:
                f.write(data)

            print(f"\n Received '{filename}' from {sender}. Saved to {out_path}")
            print("> ", end="", flush=True)

        elif mtype == "READY":
            print("\nServer ready — sending file...")
            print("> ", end="", flush=True)

        else:
            print(f"\n[SERVER] {msg}")
            print("> ", end="", flush=True)

def main() -> None:
    server_ip = input("Server IP: ").strip()
    username = input("Username: ").strip()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, PORT))

    # Login
    send_json(sock, {"type": "LOGIN", "username": username})
    resp = recv_json(sock)

    if resp.get("type") != "LOGIN_OK":
        print("Login failed:", resp)
        sock.close()
        return

    print(f"Logged in as {resp.get('username')}. Commands: list, send, quit")
    threading.Thread(target=receiver_loop, args=(sock,), daemon=True).start()

    while True:
        cmd = input("> ").strip().lower()

        if cmd == "list":
            send_json(sock, {"type": "LIST_USERS"})

        elif cmd == "send":
            to_user = input("Send to (username): ").strip()
            path = input("File path: ").strip()

            if not os.path.isfile(path):
                print("File not found.")
                continue

            filename = os.path.basename(path)
            file_size = os.path.getsize(path)

            send_json(sock, {"type": "SEND_FILE", "to": to_user, "filename": filename, "file_size": file_size})

            print("Uploading file...")

            with open(path, "rb") as f:
                send_bytes(sock, f.read())

            # The final FORWARDED/QUEUED response will arrive and be printed by receiver thread

        elif cmd == "quit":
            send_json(sock, {"type": "QUIT"})
            # BYE might be printed by receiver thread; safe to close
            sock.close()
            return

        else:
            print("Commands: list, send, quit")


if __name__ == "__main__":
    main()