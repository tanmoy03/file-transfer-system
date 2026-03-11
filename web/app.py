import os
import uuid
import sqlite3
from functools import wraps
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization"])

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "api_storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "users.db"

SESSIONS = {}  # token -> username

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            size INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL,
            owner TEXT NOT NULL,
            saved_path TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def insert_file_record(file_id, filename, size, uploaded_at, owner, saved_path):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO files (id, filename, size, uploaded_at, owner, saved_path)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (file_id, filename, size, uploaded_at, owner, saved_path)
    )
    conn.commit()
    conn.close()


def get_files_for_user(owner):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT id, filename, size, uploaded_at, owner, saved_path
        FROM files
        WHERE owner = ?
        ORDER BY uploaded_at DESC
        """,
        (owner,)
    ).fetchall()
    conn.close()
    return rows


def get_file_by_id(file_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT id, filename, size, uploaded_at, owner, saved_path
        FROM files
        WHERE id = ?
        """,
        (file_id,)
    ).fetchone()
    conn.close()
    return row


def delete_file_record(file_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing Authorization Bearer token"}), 401
        token = auth.split(" ", 1)[1].strip()
        username = SESSIONS.get(token)
        if not username:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.username = username
        request.token = token
        return fn(*args, **kwargs)
    return wrapper

def iso_now():
    return datetime.utcnow().isoformat() + "Z"

def safe_name(name: str) -> str:
    return os.path.basename(name or "file.bin")

@app.get("/")
def home():
    return jsonify({
        "message": "File Transfer API running",
        "endpoints": [
            "/register",
            "/login",
            "/logout",
            "/files",
            "/users/online"
        ]
    })

@app.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    password_hash = generate_password_hash(password)

    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409

    return jsonify({"message": "User registered successfully"}), 201

@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Invalid username or password"}), 401

    if not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    token = uuid.uuid4().hex

    # Remove any existing session for the same user
    for t, u in list(SESSIONS.items()):
        if u == username:
            SESSIONS.pop(t)

    SESSIONS[token] = username

    return jsonify({
        "token": token,
        "username": username
    }), 200

@app.post("/logout")
@require_auth
def logout():
    # remove current token
    SESSIONS.pop(request.token, None)
    return jsonify({"ok": True}), 200

@app.get("/files")
@require_auth
def list_files():
    rows = get_files_for_user(request.username)

    public = []
    for row in rows:
        public.append({
            "id": row["id"],
            "filename": row["filename"],
            "size": row["size"],
            "uploaded_at": row["uploaded_at"],
            "download_url": f"/files/{row['id']}/download",
            "owner": row["owner"],
        })

    return jsonify(public)

@app.post("/files")
@require_auth
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Missing file field 'file'"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No filename provided"}), 400

    file_id = uuid.uuid4().hex
    filename = safe_name(f.filename)

    user_dir = STORAGE_DIR / request.username
    user_dir.mkdir(parents=True, exist_ok=True)

    saved_path = user_dir / f"{file_id}_{filename}"
    f.save(saved_path)

    uploaded_at = iso_now()
    size = saved_path.stat().st_size

    insert_file_record(
        file_id=file_id,
        filename=filename,
        size=size,
        uploaded_at=uploaded_at,
        owner=request.username,
        saved_path=str(saved_path)
    )

    # Return JSON without internal path
    return jsonify({
        "id": file_id,
        "filename": filename,
        "size": size,
        "uploaded_at": uploaded_at,
        "download_url": f"/files/{file_id}/download",
        "owner": request.username,
    }), 201

@app.get("/files/<file_id>/download")
def download_file(file_id: str):
    auth = request.headers.get("Authorization", "")
    token = ""

    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
    else:
        token = (request.args.get("token") or "").strip()

    username = SESSIONS.get(token)
    if not username:
        return jsonify({"error": "Missing or invalid token"}), 401

    row = get_file_by_id(file_id)
    if row is None:
        return jsonify({"error": "Not found"}), 404

    if row["owner"] != username:
        return jsonify({"error": "Forbidden"}), 403

    path = Path(row["saved_path"])
    if not path.exists():
        return jsonify({"error": "File missing on disk"}), 404

    return send_file(path, as_attachment=True, download_name=row["filename"])

@app.delete("/files/<file_id>")
@require_auth
def delete_file(file_id: str):
    row = get_file_by_id(file_id)
    if row is None:
        return jsonify({"error": "Not found"}), 404

    if row["owner"] != request.username:
        return jsonify({"error": "Forbidden"}), 403

    path = Path(row["saved_path"])
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {e}"}), 500

    delete_file_record(file_id)
    return jsonify({"ok": True, "deleted": file_id}), 200

@app.post("/files/<file_id>/send")
@require_auth
def send_file_to_user(file_id: str):
    data = request.get_json(silent=True) or {}
    recipient = (data.get("to") or "").strip()

    if not recipient:
        return jsonify({"error": "Recipient username required"}), 400

    # Check recipient exists in DB
    conn = get_db_connection()
    user_row = conn.execute(
        "SELECT username FROM users WHERE username = ?",
        (recipient,)
    ).fetchone()
    conn.close()

    if user_row is None:
        return jsonify({"error": "User does not exist"}), 404

    # Look up file
    file_row = get_file_by_id(file_id)
    if file_row is None:
        return jsonify({"error": "File not found"}), 404

    # Only owner can send
    if file_row["owner"] != request.username:
        return jsonify({"error": "Forbidden"}), 403

    src_path = Path(file_row["saved_path"])
    if not src_path.exists():
        return jsonify({"error": "File missing"}), 404

    # Create recipient directory
    dest_dir = STORAGE_DIR / recipient
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate new file metadata
    new_id = uuid.uuid4().hex
    dest_filename = file_row["filename"]
    dest_path = dest_dir / f"{new_id}_{dest_filename}"

    # Copy file
    import shutil
    shutil.copy2(src_path, dest_path)

    uploaded_at = iso_now()
    size = dest_path.stat().st_size

    insert_file_record(
        file_id=new_id,
        filename=dest_filename,
        size=size,
        uploaded_at=uploaded_at,
        owner=recipient,
        saved_path=str(dest_path)
    )

    return jsonify({
        "message": f"File sent to {recipient}",
        "file_id": new_id
    }), 200

@app.get("/users/online")
def users_online():
    # Users with active session tokens
    online = sorted(list(set(SESSIONS.values())))
    return jsonify({"users": online}), 200

if __name__ == "__main__":
    init_db()
    # 0.0.0.0 allows other laptops on the same WiFi to access the API
    app.run(host="0.0.0.0", port=8000, debug=True)