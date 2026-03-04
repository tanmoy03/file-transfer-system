import os
import uuid
from functools import wraps
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)

# Allow UI (any origin in local-dev) and allow Authorization header
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization"])

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "api_storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory stores (fine for local dev / assignment)
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
    # For now: return everything (we’ll filter by owner in the next feature)
    public = []
    for meta in FILES.values():
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

    saved_path = STORAGE_DIR / f"{file_id}_{filename}"
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
    # Allow token via Authorization header OR ?token= for browser downloads
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

    path = Path(meta["saved_path"])
    if not path.exists():
        return jsonify({"error": "File missing on disk"}), 404

    return send_file(path, as_attachment=True, download_name=meta["filename"])

@app.delete("/files/<file_id>")
@require_auth
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

    return jsonify({"ok": True, "deleted": file_id}), 200

if __name__ == "__main__":
    # 0.0.0.0 allows other laptops on the same WiFi to access the API
    app.run(host="0.0.0.0", port=8000, debug=True)