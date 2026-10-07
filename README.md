# DocConvert Backend — hardened version

Security changes:
- 20 MB request limit
- per-IP rate limits
- PDF/DOCX file signature validation
- sanitized download filenames
- generic client-facing errors
- temporary-file cleanup after each response
- LibreOffice timeout
- non-root Docker user
- restrictive browser security headers
- configurable CORS allowlist

## Required Render environment variable

Set:

`ALLOWED_ORIGINS=https://YOUR-VERCEL-DOMAIN.vercel.app`

Later, if you add a custom domain:

`ALLOWED_ORIGINS=https://YOUR-VERCEL-DOMAIN.vercel.app,https://yourdomain.com,https://www.yourdomain.com`

Do not use `*` for the production CORS allowlist.

Render will automatically redeploy when these files are committed to the connected GitHub repository.
