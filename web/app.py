# import os
# import uuid
# import socket
# import threading
# from pathlib import Path

# from flask import Flask, render_template, request, redirect, url_for, flash, send_file

# from common.wire import send_json, recv_json, send_bytes, recv_bytes

# # If you implemented UDP discovery:
# try:
#     from common.discovery import find_server
# except Exception:
#     find_server = None


# DEFAULT_SERVER_PORT = 5001

# APP_ROOT = Path(__file__).resolve().parent
# UPLOAD_DIR = APP_ROOT / "uploads"
# DOWNLOADS_DIR = APP_ROOT / "downloads_web"
# UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# app = Flask(__name__)
# app.secret_key = "dev-secret-change-me"


# # -----------------------------
# # Connection manager (persistent per username)
# # -----------------------------
# connections_lock = threading.Lock()
# connections: dict[str, socket.socket] = {}

# user_locks_lock = threading.Lock()
# user_locks: dict[str, threading.Lock] = {}


# def _get_user_lock(username: str) -> threading.Lock:
#     with user_locks_lock:
#         if username not in user_locks:
#             user_locks[username] = threading.Lock()
#         return user_locks[username]


# def get_server_ip() -> str | None:
#     # Prefer explicit config (best for demos)
#     env_ip = os.environ.get("FILE_SERVER_IP")
#     if env_ip:
#         return env_ip.strip()

#     # Otherwise try discovery if available
#     if find_server is not None:
#         return find_server()

#     return None


# def _login_new_socket(username: str) -> socket.socket:
#     server_ip = get_server_ip()
#     if not server_ip:
#         raise RuntimeError("Server not found. Set FILE_SERVER_IP or enable UDP discovery.")

#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.connect((server_ip, DEFAULT_SERVER_PORT))

#     send_json(s, {"type": "LOGIN", "username": username})
#     resp = recv_json(s)
#     if resp.get("type") != "LOGIN_OK":
#         s.close()
#         raise RuntimeError(f"Login failed: {resp}")

#     return s


# def get_or_create_connection(username: str) -> socket.socket:
#     """
#     Returns a persistent socket for this username.
#     If existing socket is broken, it reconnects.
#     """
#     username = username.strip()
#     if not username:
#         raise RuntimeError("Username required.")

#     with connections_lock:
#         s = connections.get(username)

#     if s:
#         # Socket exists: check if it is still alive by sending a lightweight request.
#         try:
#             # Use LIST_USERS as a safe 'ping' (server already supports it)
#             send_json(s, {"type": "LIST_USERS"})
#             _ = recv_json(s)
#             return s
#         except Exception:
#             # Dead socket -> close and recreate
#             close_connection(username)

#     # Create new socket + login
#     s = _login_new_socket(username)
#     with connections_lock:
#         connections[username] = s
#     return s


# def close_connection(username: str) -> None:
#     with connections_lock:
#         s = connections.pop(username, None)

#     if s:
#         try:
#             send_json(s, {"type": "QUIT"})
#         except Exception:
#             pass
#         try:
#             s.shutdown(socket.SHUT_RDWR)
#         except Exception:
#             pass
#         try:
#             s.close()
#         except Exception:
#             pass


# # -----------------------------
# # Protocol operations (must hold user lock)
# # -----------------------------
# def op_list_users(sock: socket.socket) -> list[str]:
#     send_json(sock, {"type": "LIST_USERS"})
#     resp = recv_json(sock)
#     if resp.get("type") != "USER_LIST":
#         raise RuntimeError(f"Unexpected response: {resp}")
#     return resp.get("users", [])


# def op_send_file(sock: socket.socket, to_user: str, file_path: Path) -> dict:
#     to_user = to_user.strip()
#     if not to_user:
#         raise RuntimeError("Recipient required.")

#     filename = file_path.name
#     file_size = file_path.stat().st_size

#     send_json(sock, {
#         "type": "SEND_FILE",
#         "to": to_user,
#         "filename": filename,
#         "file_size": file_size
#     })

#     ready = recv_json(sock)
#     if ready.get("type") != "READY":
#         raise RuntimeError(f"Server not ready: {ready}")

#     # Stream bytes in chunks
#     chunk_size = 4096
#     with open(file_path, "rb") as f:
#         while True:
#             chunk = f.read(chunk_size)
#             if not chunk:
#                 break
#             send_bytes(sock, chunk)

#     # Expect server final response (FORWARDED or QUEUED)
#     final = recv_json(sock)
#     return final


# def op_inbox_list(sock: socket.socket) -> list[str]:
#     send_json(sock, {"type": "INBOX"})
#     resp = recv_json(sock)
#     if resp.get("type") != "INBOX_LIST":
#         raise RuntimeError(f"Unexpected response: {resp}")
#     return resp.get("files", [])


# def op_get_file(sock: socket.socket, filename: str, out_path: Path) -> Path:
#     filename = os.path.basename(filename.strip())
#     if not filename:
#         raise RuntimeError("Filename required.")

#     send_json(sock, {"type": "GET_FILE", "filename": filename})

#     hdr = recv_json(sock)
#     if hdr.get("type") == "ERROR":
#         raise RuntimeError(hdr.get("message", "Unknown error"))
#     if hdr.get("type") != "FILE_DOWNLOAD":
#         raise RuntimeError(f"Unexpected response: {hdr}")

#     size = int(hdr.get("file_size") or 0)
#     if size <= 0:
#         raise RuntimeError("Invalid file size from server.")

#     data = recv_bytes(sock, size)

#     out_path.parent.mkdir(parents=True, exist_ok=True)
#     with open(out_path, "wb") as f:
#         f.write(data)

#     # If your server sends FILE_CONSUMED afterwards, we can optionally read it
#     # but we don't require it.
#     return out_path


# # -----------------------------
# # Routes
# # -----------------------------
# @app.route("/", methods=["GET"])
# def index():
#     server_ip = get_server_ip()
#     return render_template("index.html", server_ip=server_ip)


# @app.route("/users", methods=["POST"])
# def users():
#     username = request.form.get("username", "").strip()
#     if not username:
#         flash("Please enter a username.", "error")
#         return redirect(url_for("index"))

#     try:
#         sock = get_or_create_connection(username)
#         lock = _get_user_lock(username)
#         with lock:
#             users_list = op_list_users(sock)
#     except Exception as e:
#         flash(str(e), "error")
#         return redirect(url_for("index"))

#     return render_template("index.html", server_ip=get_server_ip(), username=username, users=users_list)


# @app.route("/send", methods=["POST"])
# def send():
#     username = request.form.get("username", "").strip()
#     to_user = request.form.get("to_user", "").strip()
#     up = request.files.get("file")

#     if not username or not to_user or not up:
#         flash("Username, recipient, and file are required.", "error")
#         return redirect(url_for("index"))

#     safe_name = os.path.basename(up.filename)
#     temp_name = f"{uuid.uuid4().hex}_{safe_name}"
#     temp_path = UPLOAD_DIR / temp_name
#     up.save(temp_path)

#     try:
#         sock = get_or_create_connection(username)
#         lock = _get_user_lock(username)
#         with lock:
#             result = op_send_file(sock, to_user, temp_path)
#     except Exception as e:
#         flash(str(e), "error")
#         try:
#             temp_path.unlink(missing_ok=True)
#         except Exception:
#             pass
#         return redirect(url_for("index"))

#     try:
#         temp_path.unlink(missing_ok=True)
#     except Exception:
#         pass

#     flash(f"Sent '{safe_name}' to {to_user}. Server: {result}", "ok")
#     return redirect(url_for("index"))


# @app.route("/inbox", methods=["POST"])
# def inbox():
#     username = request.form.get("username", "").strip()
#     if not username:
#         flash("Enter a username to view inbox.", "error")
#         return redirect(url_for("index"))

#     try:
#         sock = get_or_create_connection(username)
#         lock = _get_user_lock(username)
#         with lock:
#             files = op_inbox_list(sock)
#     except Exception as e:
#         flash(str(e), "error")
#         return redirect(url_for("index"))

#     return render_template("index.html", server_ip=get_server_ip(), username=username, inbox_files=files)


# @app.route("/get", methods=["POST"])
# def get_file():
#     username = request.form.get("username", "").strip()
#     filename = request.form.get("filename", "").strip()

#     if not username or not filename:
#         flash("Username and filename are required.", "error")
#         return redirect(url_for("index"))

#     out_path = DOWNLOADS_DIR / username / os.path.basename(filename)

#     try:
#         sock = get_or_create_connection(username)
#         lock = _get_user_lock(username)
#         with lock:
#             downloaded = op_get_file(sock, filename, out_path)
#     except Exception as e:
#         flash(str(e), "error")
#         return redirect(url_for("index"))

#     return send_file(downloaded, as_attachment=True, download_name=downloaded.name)


# @app.route("/logout", methods=["POST"])
# def logout():
#     username = request.form.get("username", "").strip()
#     if username:
#         close_connection(username)
#         flash(f"Logged out: {username}", "ok")
#     return redirect(url_for("index"))


# if __name__ == "__main__":
#     # Run single-process for demo; multi-process servers would need a different connection strategy
#     app.run(host="127.0.0.1", port=8000, debug=True, threaded=True)
import os
import uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow UI on :5173 to call API on :8000

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "api_storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# in-memory metadata (fine for local dev/assignment)
FILES = {}  # id -> {id, filename, size, saved_path, uploaded_at_iso}


def iso_now():
    return datetime.utcnow().isoformat() + "Z"


def safe_name(name: str) -> str:
    return os.path.basename(name or "file.bin")


@app.get("/files")
def list_files():
    # Return array of file objects
    return jsonify(list(FILES.values()))


@app.post("/files")
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Missing file field 'file'"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No filename provided"}), 400

    file_id = uuid.uuid4().hex
    filename = safe_name(f.filename)

    # store with id prefix to avoid collisions
    saved_path = STORAGE_DIR / f"{file_id}_{filename}"
    f.save(saved_path)

    meta = {
        "id": file_id,
        "filename": filename,
        "size": saved_path.stat().st_size,
        "uploaded_at": iso_now(),
        "download_url": f"/files/{file_id}/download",
    }
    FILES[file_id] = {**meta, "saved_path": str(saved_path)}

    # Return JSON without internal path
    return jsonify(meta), 201


@app.get("/files/<file_id>/download")
def download_file(file_id: str):
    meta = FILES.get(file_id)
    if not meta:
        return jsonify({"error": "Not found"}), 404

    path = Path(meta["saved_path"])
    if not path.exists():
        return jsonify({"error": "File missing on disk"}), 404

    return send_file(path, as_attachment=True, download_name=meta["filename"])


@app.delete("/files/<file_id>")
def delete_file(file_id: str):
    meta = FILES.pop(file_id, None)
    if not meta:
        return jsonify({"error": "Not found"}), 404

    path = Path(meta["saved_path"])
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {e}"}), 500

    return jsonify({"ok": True, "deleted": file_id})


@app.get("/")
def home():
    return "File API running. Use /files", 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)