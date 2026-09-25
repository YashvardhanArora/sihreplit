# Deploy BhoomiLens on Render

This project is configured as a Render Web Service. The build installs
PyMuPDF to render the first page of uploaded PDFs. The included Tesseract
browser assets read printed English and Hindi text locally, and Groq
structures the transcription into fields for manual correction.

## Option 1: Deploy with the included Blueprint

1. Push this folder to a GitHub repository.
2. In Render, choose **New → Blueprint**.
3. Select the GitHub repository.
4. Render will read `render.yaml`.
5. Enter the value for `GROQ_API_KEY` when Render asks for it.
6. Create the service.

## Option 2: Create a Web Service manually

Use these settings:

```text
Runtime: Python 3
Build command: pip install -r requirements.txt
Start command: python3 server.py
Health check path: /
```

Add this environment variable in Render:

```text
GROQ_API_KEY=<your Groq API key>
```

Do not commit the API key to GitHub. Render supplies `PORT` automatically, and
`server.py` uses it in production while continuing to use port 5000 locally.

## Files required for the app

Keep these files and folders together in the repository:

- `server.py`
- `document_reader.py`
- `BhoomiLens.dc.html`
- `support.js`
- `vendor/tesseract/`
- `attached_assets/`
- `requirements.txt`
- `render.yaml`

The public homepage is served at `/`. `/api/render-pdf` renders the first
page of a PDF; `/api/extract-fields` and `/api/analyze-document` require
`GROQ_API_KEY`. OCR and review are demonstrations, not official filing.