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
    app.run(host="0.0.0.0", port=8000)