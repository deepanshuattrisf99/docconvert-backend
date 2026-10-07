import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, request, send_file, jsonify, after_this_request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pdf2docx import Converter
from werkzeug.utils import secure_filename

app = Flask(__name__)

MAX_MB = 20
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

# Set this in Render after your final Vercel/custom-domain URL is known.
# Multiple origins can be comma-separated.
allowed_origins = [
    x.strip() for x in os.environ.get("ALLOWED_ORIGINS", "").split(",") if x.strip()
]
if allowed_origins:
    CORS(app, resources={
        r"/pdf-to-word": {"origins": allowed_origins},
        r"/word-to-pdf": {"origins": allowed_origins},
    })
else:
    # Safe default for setup/testing: no cross-origin browser access.
    CORS(app, resources={})

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["60 per hour"],
    storage_uri="memory://",
)

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"

def safe_stem(filename: str) -> str:
    name = secure_filename(filename or "document")
    stem = Path(name).stem[:80]
    return stem or "document"

def valid_magic(path: Path, expected: bytes) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(len(expected)) == expected
    except OSError:
        return False

def cleanup_after_response(directory: Path):
    @after_this_request
    def cleanup(response):
        try:
            shutil.rmtree(directory, ignore_errors=True)
        except Exception:
            pass
        return response

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "DocConvert API",
        "converters": ["pdf-to-word", "word-to-pdf"]
    })

@app.post("/pdf-to-word")
@limiter.limit("10 per minute")
def pdf_to_word():
    f = request.files.get("file")
    if not f or not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a PDF file."}), 400

    work = Path(tempfile.mkdtemp(prefix="docconvert-"))
    cleanup_after_response(work)
    src = work / "input.pdf"
    out = work / f"{safe_stem(f.filename)}.docx"

    try:
        f.save(src)
        if not valid_magic(src, PDF_MAGIC):
            return jsonify({"error": "The uploaded file is not a valid PDF."}), 400

        cv = Converter(str(src))
        try:
            cv.convert(str(out))
        finally:
            cv.close()

        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("No output file was produced.")

        return send_file(
            out, as_attachment=True, download_name=out.name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception:
        app.logger.exception("PDF-to-Word conversion failed")
        return jsonify({"error": "Conversion failed. Please try another PDF."}), 500

@app.post("/word-to-pdf")
@limiter.limit("10 per minute")
def word_to_pdf():
    f = request.files.get("file")
    if not f or not f.filename or not f.filename.lower().endswith(".docx"):
        return jsonify({"error": "Please upload a DOCX file."}), 400

    work = Path(tempfile.mkdtemp(prefix="docconvert-"))
    cleanup_after_response(work)
    src = work / "input.docx"

    try:
        f.save(src)
        # DOCX is a ZIP-based format.
        if not valid_magic(src, ZIP_MAGIC):
            return jsonify({"error": "The uploaded file is not a valid DOCX."}), 400

        cmd = [
            "libreoffice", "--headless", "--nologo", "--nodefault",
            "--nolockcheck", "--nofirststartwizard",
            "--convert-to", "pdf", "--outdir", str(work), str(src)
        ]
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=90,
            env={**os.environ, "HOME": str(work)}
        )
        out = work / "input.pdf"

        if p.returncode != 0 or not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("LibreOffice conversion failed.")

        return send_file(
            out, as_attachment=True,
            download_name=f"{safe_stem(f.filename)}.pdf",
            mimetype="application/pdf"
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Conversion timed out. Try a smaller document."}), 504
    except Exception:
        app.logger.exception("Word-to-PDF conversion failed")
        return jsonify({"error": "Conversion failed. Please try another DOCX file."}), 500

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": f"File is too large. Maximum size is {MAX_MB} MB."}), 413

@app.errorhandler(429)
def rate_limited(_):
    return jsonify({"error": "Too many conversions. Please wait and try again."}), 429

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
