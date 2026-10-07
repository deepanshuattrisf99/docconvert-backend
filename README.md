# DocConvert Backend

Free/self-hosted backend for:
- PDF -> DOCX using `pdf2docx`
- DOCX -> PDF using LibreOffice headless

## Render deployment
Create a Render Web Service from this GitHub repository. Render should detect the Dockerfile automatically.

Endpoints:
- `GET /` health check
- `POST /pdf-to-word` multipart form field: `file`
- `POST /word-to-pdf` multipart form field: `file`

Current upload limit: 20 MB.

Note: PDF-to-DOCX formatting quality depends on the source PDF. Scanned PDFs need OCR, which is not included in this first version.
