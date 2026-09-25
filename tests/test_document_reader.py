import io
import json
import unittest
from unittest.mock import patch

from document_reader import extract_fields, render_pdf


def sample_pdf():
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length 40 >>\nstream\nBT /F1 18 Tf 20 200 Td (Sample) Tj ET\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, value in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


class DocumentReadingTests(unittest.TestCase):
    def test_ocr_text_returns_editable_fields(self):
        def fake_urlopen(request, timeout):
            payload = json.loads(request.data)
            self.assertEqual(payload["model"], "openai/gpt-oss-20b")
            self.assertIn("Mistaken name", payload["messages"][0]["content"])
            output = {"choices": [{"message": {"content": json.dumps({
                "extracted_fields": [{"label": "Buyer", "value": "Mistaken name", "confidence": "low"}],
            })}}]}
            return io.BytesIO(json.dumps(output).encode())

        with patch("document_reader.urlopen", side_effect=fake_urlopen):
            result = extract_fields("Buyer: Mistaken name", "test-key")
        self.assertEqual(result["fields"][0]["value"], "Mistaken name")
        self.assertTrue(any(field["label"] == "Seller" and field["value"] == "" for field in result["fields"]))
        self.assertEqual(result["documentText"], "Buyer: Mistaken name")

    def test_rejects_invalid_and_oversized_files(self):
        with self.assertRaises(ValueError):
            render_pdf(b"not a pdf")
        with self.assertRaises(ValueError):
            render_pdf(b"%PDF-" + b"x" * (8 * 1024 * 1024))
        with self.assertRaises(ValueError):
            extract_fields("", "test-key")

    def test_pdf_renders_first_page(self):
        result = render_pdf(sample_pdf())
        self.assertEqual(result["pageCount"], 1)
        self.assertTrue(result["imageData"].startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()