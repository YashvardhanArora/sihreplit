---
name: Groq vision availability
description: A model-availability constraint behind the project's OCR approach
---

As of 2026-09-25, this project's Groq account exposed text and audio models but no vision-capable model. A request to a previously documented Llama vision model returned `model_not_found`.

**Why:** A model name from older public examples can produce a broken upload path even when the API key works for text analysis.

**How to apply:** Check the account's live model list before designing Groq image features. Keep image transcription separate from text-only evidence analysis unless an accessible vision model is confirmed.