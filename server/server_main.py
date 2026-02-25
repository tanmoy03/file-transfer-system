import os
import time
import socket
import threading
from typing import Dict, Tuple, Optional
from common.discovery import run_discovery_server

from common.wire import send_json, recv_json, recv_bytes, send_bytes

HOST = "0.0.0.0"
PORT = 5001

STORAGE_DIR = "storage"
LOG_PATH = "server_transfers.log"

# username -> (socket, address)
clients: Dict[str, Tuple[socket.socket, Tuple[str, int]]] = {}
clients_lock = threading.Lock()

last_seen = {}
LAST_SEEN_WINDOW = 15

def broadcast(message: dict, exclude=None):
    with clients_lock:
        for user, (sock, _) in clients.items(): # sends JSON message to all connected clients
            if sock == exclude:
                continue
            try:
                send_json(sock, message)
            except Exception:
                pass 

def log_line(text: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {text}\n")

def safe_filename(name: str) -> str:
    return os.path.basename(name)  # prevents ../ path traversal

def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    username: Optional[str] = None

    try:
        # --- LOGIN first ---
        msg = recv_json(conn)
        if msg.get("type") != "LOGIN" or not msg.get("username"):
            send_json(conn, {"type": "ERROR", "message": "LOGIN required"})
            return

        username = msg["username"].strip()
        if not username:
            send_json(conn, {"type": "ERROR", "message": "Invalid username"})
            return

        with clients_lock:
            if username in clients:
                send_json(conn, {"type": "ERROR", "message": "Username already in use"})
                return
            clients[username] = (conn, addr)

        broadcast({
            "type": "USER_JOINED",
            "username": username
        }, exclude=conn)
            

        send_json(conn, {"type": "LOGIN_OK", "username": username})
        last_seen[username] = time.time()
        print(f"[+] {username} connected from {addr}")

        # --- Main loop ---
        while True:
            msg = recv_json(conn)
            mtype = msg.get("type")

            if mtype == "LIST_USERS":
                now = time.time()
                with clients_lock:
                    # sockets-connected users
                    online = set(clients.keys())

                # recently active users (web heartbeats)
                recent = {u for u, ts in last_seen.items() if now - ts <= LAST_SEEN_WINDOW}

                users = sorted(online | recent)
                send_json(conn, {"type": "USER_LIST", "users": users})

            elif mtype == "INBOX":
                user_dir = os.path.join(STORAGE_DIR, username)
                os.makedirs(user_dir, exist_ok=True)

                files = sorted(os.listdir(user_dir))

                send_json(conn, {
                    "type": "INBOX_LIST",
                    "files": files
                })

            elif mtype == "GET_FILE":
                filename = safe_filename(msg.get("filename") or "")

                user_dir = os.path.join(STORAGE_DIR, username)
                file_path = os.path.join(user_dir, filename)

                if not os.path.exists(file_path):
                    send_json(conn, {"type": "ERROR", "message": "File not found"})
                    continue

                file_size = os.path.getsize(file_path)

                send_json(conn, {
                    "type": "FILE_DOWNLOAD",
                    "filename": filename,
                    "file_size": file_size
                })

                # Send file
                with open(file_path, "rb") as f:
                    data = f.read()
                    send_bytes(conn, data)

                # Delete file after successful delivery
                try:
                    os.remove(file_path)
                    log_line(f"DELIVERED and DELETED file={filename} user={username}")
                except Exception as e:
                    log_line(f"DELETE FAILED file={filename} error={e}")
        
                # Inform client of successful consumption
                send_json(conn, {
                    "type": "FILE_CONSUMED",
                    "filename": filename
                })

            elif mtype == "SEND_FILE":
                to_user = (msg.get("to") or "").strip()
                filename = safe_filename(msg.get("filename") or "")
                file_size = int(msg.get("file_size") or 0)

                if not to_user or not filename or file_size <= 0:
                    send_json(conn, {"type": "ERROR", "message": "Invalid SEND_FILE request"})
                    continue

                # Store under recipient folder
                recipient_dir = os.path.join(STORAGE_DIR, to_user)
                os.makedirs(recipient_dir, exist_ok=True)
                out_path = os.path.join(recipient_dir, filename)

                # Tell sender we're ready for bytes
                send_json(conn, {"type": "READY"})

                # Receive raw bytes
                file_data = recv_bytes(conn, file_size)
                with open(out_path, "wb") as f:
                    f.write(file_data)

                log_line(f"RECEIVED from={username} to={to_user} file={filename} size={file_size} path={out_path}")

                # If recipient online, forward immediately
                with clients_lock:
                    target = clients.get(to_user)

                if target:
                    target_conn, _ = target
                    send_json(target_conn, {
                        "type": "INCOMING_FILE",
                        "from": username,
                        "filename": filename,
                        "file_size": file_size
                    })
                    send_bytes(target_conn, file_data)
                    log_line(f"FORWARDED from={username} to={to_user} file={filename} size={file_size}")
                    send_json(conn, {"type": "FORWARDED", "to": to_user})
                else:
                    send_json(conn, {"type": "QUEUED", "to": to_user, "note": "Recipient offline; stored on server."})

            elif mtype == "HEARTBEAT":
                last_seen[username] = time.time()
                send_json(conn, {"type": "OK"})

            elif mtype == "QUIT":
                send_json(conn, {"type": "BYE"})
                return

            else:
                send_json(conn, {"type": "ERROR", "message": f"Unknown command: {mtype}"})

    except Exception:
        # disconnected or parse error
        pass

    finally:
        if username:
            with clients_lock:
                cur = clients.get(username)
                if cur and cur[0] is conn:
                    clients.pop(username, None)
            print(f"[-] {username} disconnected")
        
            broadcast({
                "type": "USER_LEFT", # informs other clients that this user has left before socket close
                "username": username
            })

        try:
            conn.close()
        except Exception:
            pass


def main() -> None:
    threading.Thread(target=run_discovery_server, daemon=True).start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()

    print(f"Server running on {HOST}:{PORT}")
    os.makedirs(STORAGE_DIR, exist_ok=True)

    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()