import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import threading
import socket as pysocket

connections_lock = threading.Lock()
connections = {}  # username -> socket.socket

from common.wire import send_json, recv_json, send_bytes, recv_bytes

# If you already implemented UDP server discovery:
try:
    from common.discovery import find_server
except Exception:
    find_server = None

APP_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = APP_ROOT / "uploads"
DOWNLOADS_DIR = APP_ROOT / "downloads_web"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SERVER_PORT = 5001

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"  # for flash messages

def get_or_create_connection(username: str):
    with connections_lock:
        existing = connections.get(username)
        if existing:
            return existing

    server_ip = get_server_ip()
    if not server_ip:
        raise RuntimeError("Server not found. Set FILE_SERVER_IP or enable discovery.")

    s = pysocket.socket(pysocket.AF_INET, pysocket.SOCK_STREAM)
    s.connect((server_ip, DEFAULT_SERVER_PORT))

    send_json(s, {"type": "LOGIN", "username": username})
    resp = recv_json(s)
    if resp.get("type") != "LOGIN_OK":
        s.close()
        raise RuntimeError(f"Login failed: {resp}")

    with connections_lock:
        connections[username] = s

    return s


def close_connection(username: str):
    with connections_lock:
        s = connections.pop(username, None)
    if s:
        try:
            send_json(s, {"type": "QUIT"})
        except Exception:
            pass
        try:
            s.shutdown(pysocket.SHUT_RDWR)
        except Exception:
            pass
        try:
            s.close()
        except Exception:
            pass

def get_server_ip() -> str | None:
    # Prefer env var if provided (useful for demos)
    env_ip = os.environ.get("FILE_SERVER_IP")
    if env_ip:
        return env_ip.strip()

    # Otherwise try discovery if available
    if find_server is not None:
        return find_server()

    return None


def connect_and_login(username: str):
    import socket

    server_ip = get_server_ip()
    if not server_ip:
        raise RuntimeError("Server not found. Set FILE_SERVER_IP env var or enable UDP discovery.")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, DEFAULT_SERVER_PORT))

    send_json(sock, {"type": "LOGIN", "username": username})
    resp = recv_json(sock)
    if resp.get("type") != "LOGIN_OK":
        sock = get_or_create_connection(username)
        raise RuntimeError(f"Login failed: {resp}")

    return sock, server_ip


def list_users(sock):
    send_json(sock, {"type": "LIST_USERS"})
    return recv_json(sock)  # expects USER_LIST


def send_file_to_user(sock, to_user: str, file_path: Path):
    filename = file_path.name
    file_size = file_path.stat().st_size

    send_json(sock, {
        "type": "SEND_FILE",
        "to": to_user,
        "filename": filename,
        "file_size": file_size
    })

    ready = recv_json(sock)
    if ready.get("type") != "READY":
        raise RuntimeError(f"Server not ready: {ready}")

    # Stream bytes
    sent = 0
    chunk_size = 4096
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            send_bytes(sock, chunk)
            sent += len(chunk)

    # The server should respond with FORWARDED/QUEUED (your server sends one of these)
    final = recv_json(sock)
    return final


def inbox_list(sock):
    send_json(sock, {"type": "INBOX"})
    return recv_json(sock)  # expects INBOX_LIST


def download_inbox_file(sock, filename: str, out_path: Path):
    send_json(sock, {"type": "GET_FILE", "filename": filename})

    hdr = recv_json(sock)
    if hdr.get("type") == "ERROR":
        raise RuntimeError(hdr.get("message", "Unknown error"))
    if hdr.get("type") != "FILE_DOWNLOAD":
        raise RuntimeError(f"Unexpected response: {hdr}")

    size = int(hdr.get("file_size") or 0)
    if size <= 0:
        raise RuntimeError("Invalid file size from server")

    # Receive exact bytes
    data = recv_bytes(sock, size)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    # If you implemented delete-after-download confirmation:
    # server might send FILE_CONSUMED afterwards; ignore if not present.
    try:
        sock.settimeout(0.2)
        maybe = recv_json(sock)
        # ignore
        _ = maybe
    except Exception:
        pass
    finally:
        try:
            sock.settimeout(None)
        except Exception:
            pass

    return out_path


@app.route("/", methods=["GET"])
def index():
    server_ip = get_server_ip()
    return render_template("index.html", server_ip=server_ip)


@app.route("/users", methods=["POST"])
def users():
    username = request.form.get("username", "").strip()
    if not username:
        flash("Please enter a username.", "error")
        return redirect(url_for("index"))

    try:
        sock, server_ip = connect_and_login(username)
        resp = list_users(sock)
        sock = get_or_create_connection(username)
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("index"))

    users = resp.get("users", []) if resp.get("type") == "USER_LIST" else []
    return render_template("index.html", server_ip=server_ip, username=username, users=users)


@app.route("/send", methods=["POST"])
def send():
    username = request.form.get("username", "").strip()
    to_user = request.form.get("to_user", "").strip()
    up = request.files.get("file")

    if not username or not to_user or not up:
        flash("Username, recipient, and file are required.", "error")
        return redirect(url_for("index"))

    # Save upload temporarily
    safe_name = os.path.basename(up.filename)
    temp_name = f"{uuid.uuid4().hex}_{safe_name}"
    temp_path = UPLOAD_DIR / temp_name
    up.save(temp_path)

    try:
        sock, server_ip = connect_and_login(username)
        result = send_file_to_user(sock, to_user, temp_path)
        sock = get_or_create_connection(username)
    except Exception as e:
        flash(str(e), "error")
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return redirect(url_for("index"))

    try:
        temp_path.unlink(missing_ok=True)
    except Exception:
        pass

    flash(f"Sent '{safe_name}' to {to_user}. Server says: {result}", "ok")
    return redirect(url_for("index"))

@app.route("/inbox", methods=["POST"])
def inbox():
    username = request.form.get("username", "").strip()
    if not username:
        flash("Enter the username whose inbox you want to view.", "error")
        return redirect(url_for("index"))

    try:
        sock, server_ip = connect_and_login(username)
        resp = inbox_list(sock)
        sock = get_or_create_connection(username)
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("index"))

    files = resp.get("files", []) if resp.get("type") == "INBOX_LIST" else []
    return render_template("index.html", server_ip=server_ip, username=username, inbox_files=files)


@app.route("/get", methods=["POST"])
def get_file():
    username = request.form.get("username", "").strip()
    filename = request.form.get("filename", "").strip()

    if not username or not filename:
        flash("Username and filename are required.", "error")
        return redirect(url_for("index"))

    out_path = DOWNLOADS_DIR / username / os.path.basename(filename)

    try:
        sock, server_ip = connect_and_login(username)
        downloaded = download_inbox_file(sock, filename, out_path)
        sock = get_or_create_connection(username)
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("index"))

    return send_file(downloaded, as_attachment=True, download_name=downloaded.name)

@app.route("/logout", methods=["POST"])
def logout():
    username = request.form.get("username", "").strip()
    if username:
        close_connection(username)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)