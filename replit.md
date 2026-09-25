# BhoomiLens

BhoomiLens is an interactive prototype built from `BhoomiLens.dc.html` and
its generated browser runtime, `support.js`. `server.py` serves the app and
provides text analysis via Groq and first-page PDF rendering. OCR of printed
English and Hindi text runs in the browser using local assets under
`vendor/tesseract/`. Set `GROQ_API_KEY` for field extraction and evidence
analysis; the site still loads without it.

## Run

Start the **Start application** workflow. It runs:

```sh
python3 server.py
```

The server listens on `0.0.0.0:5000` for Replit's web preview (or the `PORT`
environment variable) and serves BhoomiLens at the root URL. Render installs
PyMuPDF from `requirements.txt` for PDF rendering; local development can use
the available `pdftoppm` utility.

## Notes

- `support.js` is generated runtime code and should not be edited directly.
- The prototype uses fictional demonstration data.