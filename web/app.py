import os
import uuid
from functools import wraps
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization"])

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "api_storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory stores
FILES = {}     # id -> {id, filename, size, saved_path, uploaded_at, owner, download_url}
SESSIONS = {}  # token -> username
USERS = set()  # registered usernames (simple demo store)

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
    return "File API running. Use /login and /files", 200

@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"error": "Username required"}), 400

    USERS.add(username)
    token = uuid.uuid4().hex
    SESSIONS[token] = username
    return jsonify({"token": token, "username": username}), 200

@app.post("/logout")
@require_auth
def logout():
    # remove current token
    SESSIONS.pop(request.token, None)
    return jsonify({"ok": True}), 200

@app.get("/files")
@require_auth
def list_files():
    public = []
    for meta in FILES.values():
        if meta.get("owner") != request.username:
            continue
        public.append({
            "id": meta["id"],
            "filename": meta["filename"],
            "size": meta["size"],
            "uploaded_at": meta["uploaded_at"],
            "download_url": meta["download_url"],
            "owner": meta.get("owner"),
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

    meta = {
        "id": file_id,
        "filename": filename,
        "size": saved_path.stat().st_size,
        "uploaded_at": iso_now(),
        "download_url": f"/files/{file_id}/download",
        "owner": request.username,
        "saved_path": str(saved_path),  # internal only
    }
    FILES[file_id] = meta

    # Return JSON without internal path
    return jsonify({
        "id": file_id,
        "filename": filename,
        "size": meta["size"],
        "uploaded_at": meta["uploaded_at"],
        "download_url": meta["download_url"],
        "owner": meta["owner"],
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

    meta = FILES.get(file_id)
    if not meta:
        return jsonify({"error": "Not found"}), 404
    
    if meta.get("owner") != username:
        return jsonify({"error": "Forbidden"}), 403

    path = Path(meta["saved_path"])
    if not path.exists():
        return jsonify({"error": "File missing on disk"}), 404

    return send_file(path, as_attachment=True, download_name=meta["filename"])

@app.delete("/files/<file_id>")
@require_auth
def delete_file(file_id: str):
    meta = FILES.get(file_id)
    if not meta:
        return jsonify({"error": "Not found"}), 404

    if meta.get("owner") != request.username:
        return jsonify({"error": "Forbidden"}), 403

    FILES.pop(file_id, None)

    path = Path(meta["saved_path"])
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {e}"}), 500

    return jsonify({"ok": True, "deleted": file_id}), 200

@app.post("/files/<file_id>/send")
@require_auth
def send_file_to_user(file_id: str):
    data = request.get_json(silent=True) or {}
    recipient = (data.get("to") or "").strip()

    if not recipient:
        return jsonify({"error": "Recipient username required"}), 400

    if recipient not in USERS:
        return jsonify({"error": "User does not exist"}), 404

    meta = FILES.get(file_id)
    if not meta:
        return jsonify({"error": "File not found"}), 404

    # Only owner can send
    if meta.get("owner") != request.username:
        return jsonify({"error": "Forbidden"}), 403

    src_path = Path(meta["saved_path"])
    if not src_path.exists():
        return jsonify({"error": "File missing"}), 404

    # Create recipient directory
    dest_dir = STORAGE_DIR / recipient
    dest_dir.mkdir(parents=True, exist_ok=True)

    new_id = uuid.uuid4().hex
    dest_filename = meta["filename"]
    dest_path = dest_dir / f"{new_id}_{dest_filename}"

    # Copy file
    import shutil
    shutil.copy2(src_path, dest_path)

    new_meta = {
        "id": new_id,
        "filename": dest_filename,
        "size": dest_path.stat().st_size,
        "uploaded_at": iso_now(),
        "download_url": f"/files/{new_id}/download",
        "owner": recipient,
        "saved_path": str(dest_path),
    }

    FILES[new_id] = new_meta

    return jsonify({
        "message": f"File sent to {recipient}",
        "file_id": new_id
    }), 200

@app.get("/users/online")
@require_auth
def users_online():
    # Users with active session tokens
    online = sorted(set(SESSIONS.values()))
    return jsonify({"users": online}), 200

if __name__ == "__main__":
    # 0.0.0.0 allows other laptops on the same WiFi to access the API
    app.run(host="0.0.0.0", port=8000, debug=True)