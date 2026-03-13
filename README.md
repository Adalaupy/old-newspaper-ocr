# Traditional Chinese Newspaper OCR

![App Cover](App%20Screenshot.jpg)

A desktop OCR tool for old newspaper workflows: import images/PDF pages, crop target regions, run OCR in batches, review text, and export annotated outputs.

## Highlights

- Batch import for images and PDFs
- Clipboard image paste with Ctrl+V
- Region-based OCR with drag-to-crop
- Crop reordering and live preview
- Pause, resume, and stop controls for queue processing
- OCR engine switch in UI settings (PaddleOCR, EasyOCR, Mistral OCR)
- Traditional Chinese final conversion via OpenCC

## OCR Engines

- PaddleOCR: local OCR, sorted by detection position, exported as paragraph-style text
- EasyOCR: local OCR, direct text extraction
- Mistral OCR: API OCR via `MISTRAL_API_KEY`, using original crop images and strict transcription-oriented extraction

The active engine can be changed from:
- UI: `Settings -> OCR Engine`
- Config: `OCR_ENGINE` in `config.py`

When you switch engines from the UI, the app reloads the engine immediately and marks existing items as pending so the next run uses the selected engine.

## Installation

### Option 1 (Windows helper script)

```bash
setup.bat
```

### Option 2 (manual)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If you use Mistral OCR, create `.env` in project root:

```bash
MISTRAL_API_KEY=your_api_key_here
```

## Run

```bash
python main.py
```

or on Windows:

```bash
run.bat
```

## Typical Workflow

1. Import images or PDF pages.
2. Draw crop rectangles for OCR targets.
3. Set language, reading direction, and OCR engine in the left settings panel.
4. Click `Submit for OCR`.
5. Review results in the preview panel.
6. Click `Save Results` to export annotated images and text.

## Configuration

Main settings are in `config.py`.

### Engine selection

```python
OCR_ENGINE_OPTIONS = {
    "PaddleOCR": "ocr_engine_paddle",
    "EasyOCR": "ocr_engine_easyocr",
    "Mistral OCR": "ocr_engine_mistral",
}

OCR_ENGINE = "ocr_engine_mistral"
ORC_ENGINE = OCR_ENGINE
```

### Other useful settings

- `OCR_LANG`: language code used by OCR engines
- `OCR_USE_GPU`: enable/disable GPU when supported
- `OCR_ENFORCE_TRADITIONAL_CHINESE`: final OpenCC conversion toggle
- `OCR_TRADITIONAL_CONVERSION`: OpenCC conversion profile
- Mistral-specific settings: `OCR_MISTRAL_MODEL`, `OCR_MISTRAL_LANGUAGE_HINT_ENABLED`, `OCR_MISTRAL_LANGUAGE_HINT`
- Mistral accuracy settings: `OCR_MISTRAL_REQUEST_DOCUMENT_ANNOTATION`, `OCR_MISTRAL_STRICT_TRANSCRIPTION`, `OCR_MISTRAL_CLEAN_MARKDOWN_FALLBACK`, `OCR_MISTRAL_APPLY_PYCORRECTOR`

### Mistral accuracy defaults

```python
OCR_MISTRAL_REQUEST_DOCUMENT_ANNOTATION = True
OCR_MISTRAL_STRICT_TRANSCRIPTION = True
OCR_MISTRAL_CLEAN_MARKDOWN_FALLBACK = True
OCR_MISTRAL_APPLY_PYCORRECTOR = False
```

These defaults are intended to reduce common failure modes in old newspaper scans:

- Prefer structured `document_annotation.text` before markdown-style page output
- Keep Mistral from reformatting paragraphs into bullets or headings
- Avoid pycorrector changing already-correct OCR text from the Mistral model

## Project Structure

```text
OCR/
├── main.py
├── config.py
├── requirements.txt
├── run.bat
├── setup.bat
├── models/
├── services/
│   ├── __init__.py
│   ├── image_processor.py
│   ├── pdf_handler.py
│   ├── file_manager.py
│   ├── text_corrector.py
│   └── ocr/
│       ├── ocr_base.py
│       ├── ocr_shared.py
│       ├── ocr_engine_paddle.py
│       ├── ocr_engine_easyocr.py
│       └── ocr_engine_mistral.py
├── ui/
│   ├── main_window.py
│   ├── image_canvas.py
│   └── crop_list_panel.py
└── output/
```

## Troubleshooting

### Engine init errors

- PaddleOCR/EasyOCR model download may run on first startup; wait for completion.
- Switching to PaddleOCR is slow the first time because model initialization is heavy; later switches should be faster because the app reuses cached engine instances.
- For Mistral OCR, verify `.env` exists and `MISTRAL_API_KEY` is set.
- If switching engines fails from UI, stop active OCR processing first.

### OCR result quality

- Adjust crop size to include full characters and margins.
- Try switching OCR engine from UI settings.
- Tune language (`OCR_LANG`) and Mistral hint settings in `config.py`.
- For Mistral OCR, prefer larger crops with full paragraph context instead of very tight character cuts.
- If Mistral starts drifting on later crops, set `OCR_MISTRAL_LANGUAGE_HINT` explicitly, for example `Traditional Chinese`.
- If Mistral output is too aggressively normalized, keep `OCR_MISTRAL_APPLY_PYCORRECTOR = False`.

## License

For educational and personal use.
