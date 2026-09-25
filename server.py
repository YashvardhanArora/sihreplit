import base64
import binascii
import json
import os
import threading
import time
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from document_reader import extract_fields, render_pdf

_api_slots = threading.BoundedSemaphore(2)
_api_usage = deque()
_api_usage_lock = threading.Lock()


class BhoomiLensHandler(SimpleHTTPRequestHandler):
    def _json_response(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/favicon.ico":
            self.path = "/favicon.svg"
        if self.path in ("", "/"):
            self.path = "/BhoomiLens.dc.html"
        super().do_GET()

    def do_HEAD(self):
        if self.path == "/favicon.ico":
            self.path = "/favicon.svg"
        if self.path in ("", "/"):
            self.path = "/BhoomiLens.dc.html"
        super().do_HEAD()

    def do_POST(self):
        if self.path not in ("/api/analyze-document", "/api/extract-fields", "/api/render-pdf"):
            self._json_response(404, {"error": "Not found"})
            return

        acquired = False
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 12 * 1024 * 1024:
                self._json_response(413, {"error": "Choose a file under 8 MB."})
                return
            request_data = json.loads(self.rfile.read(length) or b"{}")
            if not _api_slots.acquire(blocking=False):
                self._json_response(429, {"error": "Document review is busy. Try again shortly."})
                return
            acquired = True
            if self.path == "/api/render-pdf":
                encoded = request_data.get("fileData", "")
                if not isinstance(encoded, str) or len(encoded) > 11 * 1024 * 1024:
                    self._json_response(413, {"error": "Choose a PDF under 8 MB."})
                    return
                try:
                    raw = base64.b64decode(encoded, validate=True)
                    result = render_pdf(raw)
                except (binascii.Error, ValueError) as error:
                    self._json_response(400, {"error": str(error)})
                    return
                self._json_response(200, result)
                return
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                self._json_response(503, {"error": "GROQ_API_KEY is not configured."})
                return
            with _api_usage_lock:
                now = time.monotonic()
                while _api_usage and _api_usage[0] < now - 600:
                    _api_usage.popleft()
                if len(_api_usage) >= 12:
                    self._json_response(429, {"error": "Demo review limit reached. Try again in a few minutes."})
                    return
                _api_usage.append(now)
            if self.path == "/api/extract-fields":
                try:
                    result = extract_fields(request_data.get("documentText"), api_key)
                except ValueError as error:
                    self._json_response(400, {"error": str(error)})
                    return
                self._json_response(200, result)
                return
            document_text = str(request_data.get("documentText", "")).strip()
            corrected_fields = request_data.get("correctedFields") or []
            if not isinstance(corrected_fields, list):
                corrected_fields = []
            corrected_fields = [
                {"field": str(field.get("label") or "")[:80], "value": str(field.get("value") or "")[:500]}
                for field in corrected_fields[:20] if isinstance(field, dict)
            ]
            parcel_id = str(request_data.get("parcelId", "HR06MNS0012345")).strip()
            if not document_text and not any(f["value"] for f in corrected_fields):
                self._json_response(400, {"error": "Add document text or a corrected field before analyzing it."})
                return

            prompt = f"""You are an evidence-review assistant for a government land-records portal.
Analyze the document text below against parcel ID {parcel_id}.
User-corrected fields take precedence over contradictory OCR transcription.
Corrected fields: {json.dumps(corrected_fields, ensure_ascii=False)}
Do not decide legal ownership. Identify only evidence, inconsistencies, and items an authorized officer should verify.
Return valid JSON with exactly these keys:
document_type (string), extracted_fields (array of objects with field and value),
conflicts (array of strings), confidence (one of high, medium, low),
officer_action (string), summary (string).

Document text:
{document_text[:12000]}"""
            payload = {
                "model": "openai/gpt-oss-20b",
                "temperature": 0.1,
                "max_tokens": 900,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You return concise, auditable JSON for a land-record officer."},
                    {"role": "user", "content": prompt},
                ],
            }
            request = Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "BhoomiLens/1.0",
                },
                method="POST",
            )
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            analysis = json.loads(content)
            self._json_response(200, {"analysis": analysis, "provider": "Groq"})
        except HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8"))
            except Exception:
                detail = {}
            message = detail.get("error", {}).get("message", "Groq request failed.")
            self._json_response(502, {"error": message})
        except (URLError, TimeoutError):
            self._json_response(502, {"error": "The AI service could not be reached. Try again."})
        except (KeyError, json.JSONDecodeError):
            self._json_response(502, {"error": "The AI service returned an unexpected response."})
        except Exception as error:
            self._json_response(500, {"error": f"AI analysis failed: {error}"})
        finally:
            if acquired:
                _api_slots.release()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    ThreadingHTTPServer(("0.0.0.0", port), BhoomiLensHandler).serve_forever()