# Traditional Chinese Newspaper OCR

![App Cover](App%20Screenshot.jpg)

A Python application for OCR processing of traditional Chinese old newspapers with a user-friendly interface.

## Features

- **Multi-file Import**: Import multiple images or PDF files in a single batch
- **Clipboard Paste**: Paste images directly into the batch with Ctrl+V
- **PDF Support**: Extract and process specific pages from PDF documents
- **Flexible Crop Selection**: Use rectangle selection tool to choose specific areas
- **Reading Direction Support**: 
  - Vertical Right-to-Left (Traditional Chinese default)
  - Vertical Left-to-Right
  - Horizontal Left-to-Right
  - Horizontal Right-to-Left
- **Image Operations**: Rotate, zoom, and enhance images
- **Manual Crop Ordering**: Drag to reorder crop regions for proper text flow
- **Real-time Preview**: View OCR results before saving
- **Batch Processing**: Process multiple images with background queue
- **Comprehensive Output**: Saves annotated image and OCR text

## Installation

### Prerequisites

- Python 3.8 or higher
- Windows/Linux/MacOS

### Steps

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. For PDF support, you may need to install Poppler:
   - Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/
   - Linux: `sudo apt-get install poppler-utils`
   - MacOS: `brew install poppler`

## Usage

1. Run the application:
```bash
python main.py
```

2. Import files:
   - Click "Import Files" button
   - Select one or multiple image files or PDFs
   - For PDFs, choose whether to import all pages
   - Or press Ctrl+V to paste images from the clipboard

3. Process images:
   - Draw rectangles on the image to select crop regions
   - Adjust filename, language, and reading direction as needed
   - Use zoom and rotate buttons if necessary
   - Manage crop order using the crop list panel
   - Click "Submit for OCR" to process

4. Save results:
   - Review OCR results in the preview panel
   - Click "Save Results" to export everything to a folder
   - Output includes:
     - Annotated image with crop rectangles
     - Text file with OCR results

## Project Structure

```
OCR/
├── App Screenshot.jpg     # UI cover image
├── instruction.md         # Original requirements
├── main.py                # Application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── run.bat                # Run script (Windows)
├── setup.bat              # Setup script (Windows)
├── setup.py               # Packaging/setup metadata
├── models/                # Data models
│   ├── image_data.py       # Image data model
│   └── crop_region.py      # Crop region model
├── services/              # Business logic
│   ├── image_processor.py  # Image preprocessing
│   ├── ocr_base.py         # Shared OCR engine pipeline
│   ├── ocr_shared.py       # Shared OCR post-processing utilities
│   ├── ocr_engine_paddle.py # PaddleOCR engine implementation
│   ├── ocr_engine_easyocr.py # EasyOCR engine implementation
│   ├── text_corrector.py   # Shared pycorrector post-correction
│   ├── pdf_handler.py      # PDF processing
│   └── file_manager.py     # File I/O operations
├── ui/                    # User interface
│   ├── main_window.py      # Main application window
│   ├── image_canvas.py     # Image display and cropping
│   └── crop_list_panel.py  # Crop management panel
└── output/                # Output folder (created automatically)
```

## Configuration

Edit `config.py` to customize:
- Default language and reading direction
- UI colors and sizes
- OCR settings (GPU usage, language models)
- Output formats

## Supported Formats

- **Images**: PNG, JPG, JPEG, TIFF, BMP
- **Documents**: PDF

## Requirements

See `requirements.txt` for detailed dependencies:
- PaddleOCR (OCR engine)
- CustomTkinter (Modern UI)
- OpenCV (Image processing)
- PyMuPDF (PDF handling)
- Pillow (Image manipulation)

## Troubleshooting

### OCR Engine Initialization Failed
- Ensure PaddlePaddle and PaddleOCR are properly installed
- Check if the language model is downloaded (happens automatically on first run)
- For GPU support, install paddlepaddle-gpu instead

### PDF Import Issues
- Verify Poppler is installed and accessible
- Check PDF file is not corrupted or password-protected

### Performance Issues
- Reduce image resolution before processing
- Enable GPU acceleration if available (edit config.py)
- Process fewer images per batch

## License

This project is for educational and personal use.

## Acknowledgments

- PaddleOCR for the excellent OCR engine
- CustomTkinter for the modern UI framework
