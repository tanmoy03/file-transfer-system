import socket
import os
import threading
from common.wire import send_json, recv_json, send_bytes, recv_bytes

PORT = 5001
DOWNLOADS_DIR = "downloads"


def receiver_loop(sock: socket.socket, stop_event: threading.Event):
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    while not stop_event.is_set():
        try:
            msg = recv_json(sock)
        except (ConnectionError, OSError):
            # Socket closed / program shutting down
            break
        except Exception:
            # Ignore unexpected decode/parse errors
            continue

        mtype = msg.get("type")

        if mtype == "INCOMING_FILE":
            sender = msg.get("from")
            filename = os.path.basename(msg.get("filename") or "file.bin")
            size = int(msg.get("file_size") or 0)

            try:
                data = recv_bytes(sock, size)
            except (ConnectionError, OSError):
                break

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

    stop_event = threading.Event()
    recv_thread = threading.Thread(target=receiver_loop, args=(sock, stop_event))
    recv_thread.start()

    try:
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

                send_json(sock, {
                    "type": "SEND_FILE",
                    "to": to_user,
                    "filename": filename,
                    "file_size": file_size
                })

                print("Uploading file...")
                with open(path, "rb") as f:
                    send_bytes(sock, f.read())

            elif cmd == "quit":
                try:
                    send_json(sock, {"type": "QUIT"})
                except Exception:
                    pass
                break

            else:
                print("Commands: list, send, quit")

    finally:
        # Clean shutdown
        stop_event.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

        recv_thread.join(timeout=2)


if __name__ == "__main__":
    main()