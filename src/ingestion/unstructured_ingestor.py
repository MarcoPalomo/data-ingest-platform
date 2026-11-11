from pathlib import Path


def ingest_unstructured(path: str):
    p = Path(path)
    if p.suffix.lower() in ['.txt', '.md']:
        return p.read_text(encoding='utf-8')
    # Placeholder: integrate OCR / Form Recognizer for PDFs/images
    return None
