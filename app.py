import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter

app = Flask(__name__)
CORS(app)

MAX_MB = 20
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "DocConvert API",
        "converters": ["pdf-to-word", "word-to-pdf"]
    })

@app.post("/pdf-to-word")
def pdf_to_word():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a PDF file."}), 400

    work = Path(tempfile.mkdtemp(prefix="docconvert-"))
    src = work / "input.pdf"
    out = work / (Path(f.filename).stem + ".docx")
    try:
        f.save(src)
        cv = Converter(str(src))
        cv.convert(str(out))
        cv.close()
        return send_file(out, as_attachment=True, download_name=out.name,
                         mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        return jsonify({"error": "PDF conversion failed.", "detail": str(e)}), 500
    finally:
        # send_file reads the file after the handler returns, so Flask may still need it.
        # Cleanup is handled by the platform's temporary filesystem lifecycle.
        pass

@app.post("/word-to-pdf")
def word_to_pdf():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".docx"):
        return jsonify({"error": "Please upload a DOCX file."}), 400

    work = Path(tempfile.mkdtemp(prefix="docconvert-"))
    src = work / "input.docx"
    try:
        f.save(src)
        cmd = [
            "libreoffice", "--headless", "--nologo", "--nodefault",
            "--nolockcheck", "--nofirststartwizard",
            "--convert-to", "pdf", "--outdir", str(work), str(src)
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = work / "input.pdf"
        if p.returncode != 0 or not out.exists():
            return jsonify({"error": "Word conversion failed.", "detail": p.stderr or p.stdout}), 500
        download_name = Path(f.filename).stem + ".pdf"
        return send_file(out, as_attachment=True, download_name=download_name,
                         mimetype="application/pdf")
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Conversion timed out."}), 504
    except Exception as e:
        return jsonify({"error": "Word conversion failed.", "detail": str(e)}), 500

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": f"File is too large. Maximum size is {MAX_MB} MB."}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
