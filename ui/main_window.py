"""
Main application window
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageGrab
import threading
import queue
import os
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

import config
from models import ImageData, CropRegion
from services import ImageProcessor, OCREngine, PDFHandler, FileManager

from ui.image_canvas import ImageCanvas
from ui.crop_list_panel import CropListPanel

if TYPE_CHECKING:
    from services.ocr.ocr_base import BaseOCREngine


class MainWindow(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title(config.WINDOW_TITLE)
        self.geometry(config.WINDOW_SIZE)
        self._maximize_on_startup()
        
        # Application state
        self.image_batch: List[ImageData] = []
        self.current_image_index = 0
        self.ocr_engine: Optional["BaseOCREngine"] = None
        self.processing_queue = queue.Queue()
        self.processing_paused = threading.Event()
        self.processing_paused.set()
        self.stop_requested = threading.Event()
        self.is_processing = False
        self.batch_id: Optional[str] = None
        
        # Initialize services
        self._init_services()
        
        # Setup UI
        self._setup_ui()
        self._setup_menu()
        self.bind_all("<Control-v>", self._paste_image)
        
        # Start background processor
        self._start_background_processor()

    def _maximize_on_startup(self):
        """Maximize the main window when the app starts."""
        try:
            self.state("zoomed")
        except Exception:
            # Fallback for environments that use the -zoomed window attribute.
            self.after(0, lambda: self.attributes("-zoomed", True))
    
    def _init_services(self):
        """Initialize service objects"""
        try:
            self.ocr_engine = OCREngine()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize OCR engine: {e}")
    
    def _setup_ui(self):
        """Setup main UI layout"""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Left panel - Controls
        self.left_panel = self._create_left_panel()
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Center panel - Image canvas
        self.canvas_panel = ImageCanvas(self, on_crop_added=self._on_crop_added)
        self.canvas_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Right panel - Crop list and preview
        self.right_panel = self._create_right_panel()
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
    
    def _create_left_panel(self):
        """Create left control panel"""
        panel = ctk.CTkFrame(self, width=250)
        panel.grid_propagate(False)
        
        # Title
        title = ctk.CTkLabel(panel, text="Controls", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # File operations
        file_frame = ctk.CTkFrame(panel)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(file_frame, text="File Operations", font=("Arial", 12, "bold")).pack(pady=5)
        
        ctk.CTkButton(file_frame, text="Import Files", command=self._import_files).pack(fill="x", pady=2)
        ctk.CTkLabel(
            file_frame,
            text="Paste (Ctrl+V) to add images",
            font=("Arial", 9),
            text_color="gray70"
        ).pack(pady=(2, 0))
        ctk.CTkButton(file_frame, text="Clear All", command=self._clear_all_images).pack(fill="x", pady=2)
        
        # Navigation
        nav_frame = ctk.CTkFrame(file_frame)
        nav_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(nav_frame, text="◄ Prev", width=70, command=self._prev_image).pack(side="left", padx=2)
        self.image_counter = ctk.CTkLabel(nav_frame, text="0/0", width=90)
        self.image_counter.pack(side="left", padx=5)
        ctk.CTkButton(nav_frame, text="Next ►", width=70, command=self._next_image).pack(side="right", padx=2)
        
        # Image settings
        settings_frame = ctk.CTkFrame(panel)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Settings", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Filename
        ctk.CTkLabel(settings_frame, text="Filename:").pack(anchor="w", padx=5)
        self.filename_entry = ctk.CTkEntry(settings_frame)
        self.filename_entry.pack(fill="x", padx=5, pady=2)
        self.filename_entry.bind("<KeyRelease>", self._on_filename_changed)
        
        # Language
        ctk.CTkLabel(settings_frame, text="Language:").pack(anchor="w", padx=5, pady=(5,0))
        self.language_var = ctk.StringVar(value=config.DEFAULT_LANGUAGE)
        self.language_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=list(config.SUPPORTED_LANGUAGES.keys()),
            variable=self.language_var,
            command=self._on_language_changed
        )
        self.language_menu.pack(fill="x", padx=5, pady=2)
        
        # Reading direction
        ctk.CTkLabel(settings_frame, text="Reading Direction:").pack(anchor="w", padx=5, pady=(5,0))
        self.read_dir_var = ctk.StringVar(value=list(config.READ_DIRECTIONS.keys())[0])
        self.read_dir_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=list(config.READ_DIRECTIONS.keys()),
            variable=self.read_dir_var,
            command=self._on_read_dir_changed
        )
        self.read_dir_menu.pack(fill="x", padx=5, pady=2)
        
        # Image operations
        ops_frame = ctk.CTkFrame(panel)
        ops_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(ops_frame, text="Image Operations", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Zoom buttons
        zoom_frame = ctk.CTkFrame(ops_frame)
        zoom_frame.pack(fill="x", pady=2)
        
        ctk.CTkButton(zoom_frame, text="Zoom In", width=80, command=self._zoom_in).pack(side="left", padx=2)
        ctk.CTkButton(zoom_frame, text="Zoom Out", width=80, command=self._zoom_out).pack(side="left", padx=2)
        ctk.CTkButton(zoom_frame, text="Reset", width=80, command=self._zoom_reset).pack(side="left", padx=2)
        
        # Hint for panning
        hint_label = ctk.CTkLabel(
            ops_frame, 
            text="💡 Right-click & drag to pan when zoomed",
            font=("Arial", 9),
            text_color="gray70"
        )
        hint_label.pack(pady=(2, 5))
        
        # Rotation
        ctk.CTkButton(ops_frame, text="Rotate 90°", command=self._rotate_image).pack(fill="x", pady=2)
        
        # Crop operations
        ctk.CTkButton(ops_frame, text="Clear All Crops", command=self._clear_crops).pack(fill="x", pady=2)
        
        # Processing
        process_frame = ctk.CTkFrame(panel)
        process_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(process_frame, text="Processing", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.submit_btn = ctk.CTkButton(
            process_frame,
            text="Submit for OCR",
            command=self._submit_for_ocr,
            fg_color="green"
        )
        self.submit_btn.pack(fill="x", pady=2)

        controls_frame = ctk.CTkFrame(process_frame)
        controls_frame.pack(fill="x", pady=2)

        self.pause_btn = ctk.CTkButton(
            controls_frame,
            text="Pause OCR",
            width=100,
            command=self._toggle_pause_processing,
            state="disabled"
        )
        self.pause_btn.pack(side="left", padx=2)

        self.stop_btn = ctk.CTkButton(
            controls_frame,
            text="Stop OCR",
            width=100,
            command=self._stop_processing,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=2)
        
        self.progress_label = ctk.CTkLabel(process_frame, text="Ready")
        self.progress_label.pack(pady=5)
        
        return panel
    
    def _create_right_panel(self):
        """Create right panel with crop list and preview"""
        panel = ctk.CTkFrame(self, width=300)
        panel.grid_propagate(False)
        
        # Crop list
        self.crop_list = CropListPanel(
            panel,
            on_selection_changed=self._on_crop_selected,
            on_delete=self._on_crop_deleted,
            on_reorder=self._on_crops_reordered
        )
        self.crop_list.pack(fill="both", expand=True, pady=(5, 5))
        
        # OCR Preview
        preview_frame = ctk.CTkFrame(panel)
        preview_frame.pack(fill="both", expand=True, pady=(5, 5))
        
        ctk.CTkLabel(preview_frame, text="OCR Preview", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.preview_text = ctk.CTkTextbox(preview_frame, wrap="word")
        self.preview_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Save button
        ctk.CTkButton(preview_frame, text="Save Results", command=self._save_results).pack(pady=5)
        
        return panel
    
    def _setup_menu(self):
        """Setup menu bar (if needed)"""
        # CustomTkinter doesn't have native menu, so we skip or use buttons
        pass
    
    def _import_files(self):
        """Import image or PDF files"""
        filepaths = filedialog.askopenfilenames(
            title="Select images or PDFs",
            filetypes=config.SUPPORTED_IMAGE_FORMATS
        )
        
        if not filepaths:
            return
        self.batch_id = datetime.now().strftime("%H%M")
        self.image_batch.clear()
        
        for filepath in filepaths:
            try:
                if filepath.lower().endswith('.pdf'):
                    self._import_pdf(filepath)
                else:
                    self._import_image(filepath)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import {filepath}: {e}")
        
        if self.image_batch:
            self.current_image_index = 0
            self._load_current_image()
            self._update_image_counter()

    def _paste_image(self, event=None):
        """Paste image(s) from clipboard and append to current batch."""
        clipboard_data = ImageGrab.grabclipboard()
        if clipboard_data is None:
            messagebox.showinfo("Paste", "Clipboard is empty or has no image.")
            return

        new_images = []
        if isinstance(clipboard_data, Image.Image):
            new_images.append(("clipboard", clipboard_data))
        elif isinstance(clipboard_data, list):
            supported_exts = (".png", ".jpg", ".jpeg", ".tiff", ".bmp")
            for path in clipboard_data:
                if isinstance(path, str) and path.lower().endswith(supported_exts):
                    try:
                        new_images.append((path, Image.open(path)))
                    except Exception:
                        continue

        if not new_images:
            messagebox.showinfo("Paste", "No image found in clipboard.")
            return

        if self.batch_id is None:
            self.batch_id = datetime.now().strftime("%H%M")

        was_empty = len(self.image_batch) == 0
        for path, img in new_images:
            image_index = len(self.image_batch)
            image_data = ImageData(path, img, image_index=image_index)
            self.image_batch.append(image_data)

        if was_empty and self.image_batch:
            self.current_image_index = 0
            self._load_current_image()

        self._update_image_counter()

    def _clear_all_images(self):
        """Clear all loaded images and reset UI state."""
        if self.is_processing:
            self.stop_requested.set()
            self.processing_paused.set()

        self._drain_processing_queue()
        self.image_batch.clear()
        self.current_image_index = 0
        self.batch_id = None

        self.canvas_panel.clear_image()
        self.crop_list.update_crops([])
        self.preview_text.delete("1.0", "end")
        self.filename_entry.delete(0, "end")
        self.language_var.set(config.DEFAULT_LANGUAGE)
        default_read_dir_key = next(
            (key for key, value in config.READ_DIRECTIONS.items()
             if value == config.DEFAULT_READ_DIRECTION),
            list(config.READ_DIRECTIONS.keys())[0]
        )
        self.read_dir_var.set(default_read_dir_key)
        self.image_counter.configure(text="0/0")
        self._set_processing_controls_idle()
        self._update_pending_status()
    
    def _import_image(self, filepath: str):
        """Import a single image file"""
        image = Image.open(filepath)
        image_index = len(self.image_batch)
        image_data = ImageData(filepath, image, image_index=image_index)
        self.image_batch.append(image_data)
    
    def _import_pdf(self, filepath: str):
        """Import PDF file with page selection"""
        page_count = PDFHandler.get_page_count(filepath)
        
        if page_count == 0:
            raise ValueError("PDF has no pages or is corrupted")
        
        # Simple dialog to select pages (for now, import all)
        response = messagebox.askyesno(
            "Import PDF",
            f"PDF has {page_count} pages. Import all pages?"
        )

        if response:
            pages = PDFHandler.extract_all_pages(filepath)
        else:
            page_spec = self._prompt_pdf_page_selection(page_count)

            if page_spec is None:
                return

            try:
                selected_pages = self._parse_pdf_page_selection(page_spec, page_count)
            except ValueError as e:
                messagebox.showerror("Invalid Page Selection", str(e))
                return

            pages = PDFHandler.extract_pages(filepath, selected_pages)

        for page_num, page_image in pages:
            image_index = len(self.image_batch)
            image_data = ImageData(filepath, page_image, page_number=page_num + 1, image_index=image_index)
            self.image_batch.append(image_data)

    def _parse_pdf_page_selection(self, page_spec: str, page_count: int) -> List[int]:
        """Parse page input like '1,3,5-7' into zero-based page indices."""
        if page_spec is None:
            raise ValueError("No page selection was provided.")

        selected_pages = []
        seen = set()

        for part in page_spec.split(','):
            token = part.strip()
            if not token:
                continue

            if '-' in token:
                bounds = [p.strip() for p in token.split('-', 1)]
                if len(bounds) != 2 or not bounds[0] or not bounds[1]:
                    raise ValueError(f"Invalid range: '{token}'")

                try:
                    start = int(bounds[0])
                    end = int(bounds[1])
                except ValueError as e:
                    raise ValueError(f"Invalid range: '{token}'") from e

                if start > end:
                    raise ValueError(f"Invalid range: '{token}' (start must be <= end)")

                for page in range(start, end + 1):
                    if page < 1 or page > page_count:
                        raise ValueError(f"Page {page} is out of range (1-{page_count}).")
                    zero_based = page - 1
                    if zero_based not in seen:
                        selected_pages.append(zero_based)
                        seen.add(zero_based)
            else:
                try:
                    page = int(token)
                except ValueError as e:
                    raise ValueError(f"Invalid page number: '{token}'") from e

                if page < 1 or page > page_count:
                    raise ValueError(f"Page {page} is out of range (1-{page_count}).")

                zero_based = page - 1
                if zero_based not in seen:
                    selected_pages.append(zero_based)
                    seen.add(zero_based)

        if not selected_pages:
            raise ValueError("No valid pages selected.")

        return selected_pages

    def _prompt_pdf_page_selection(self, page_count: int) -> Optional[str]:
        """Show a larger dialog for selecting PDF pages."""
        result = {"value": None}

        dialog = ctk.CTkToplevel(self)
        dialog.title("Import PDF Pages")
        dialog.geometry("560x260")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"Select pages to import (1-{page_count})",
            font=("Arial", 16, "bold")
        ).pack(pady=(16, 8))

        ctk.CTkLabel(
            dialog,
            text="Use commas and ranges, e.g. 1,3,5-7",
            font=("Arial", 12)
        ).pack(pady=(0, 8))

        page_var = ctk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=page_var, width=500, height=36)
        entry.pack(pady=(4, 12), padx=20)
        entry.focus_set()

        def on_ok():
            value = page_var.get().strip()
            result["value"] = value if value else None
            dialog.destroy()

        def on_cancel():
            result["value"] = None
            dialog.destroy()

        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=(4, 14))

        ctk.CTkButton(button_frame, text="Import", width=120, command=on_ok).pack(side="left", padx=8)
        ctk.CTkButton(button_frame, text="Cancel", width=120, command=on_cancel).pack(side="left", padx=8)

        dialog.bind("<Return>", lambda event: on_ok())
        dialog.bind("<Escape>", lambda event: on_cancel())
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        self.wait_window(dialog)
        return result["value"]
    
    def _load_current_image(self):
        """Load the current image to canvas"""
        if not self.image_batch or self.current_image_index >= len(self.image_batch):
            return
        
        image_data = self.image_batch[self.current_image_index]
        
        # Update UI elements
        self.filename_entry.delete(0, 'end')
        self.filename_entry.insert(0, image_data.filename)
        self.language_var.set(image_data.language)
        self.read_dir_var.set(image_data.read_direction)
        
        # Load image to canvas
        self.canvas_panel.load_image(image_data.content, image_data.crop_regions)
        
        # Update crop list
        self.crop_list.update_crops(image_data.crop_regions)
        
        # Update preview if processed
        self._update_preview()
    
    def _update_image_counter(self):
        """Update the image counter label"""
        if self.image_batch:
            self.image_counter.configure(
                text=f"{self.current_image_index + 1}/{len(self.image_batch)}"
            )
        else:
            self.image_counter.configure(text="0/0")
    
    def _prev_image(self):
        """Navigate to previous image"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self._load_current_image()
            self._update_image_counter()
    
    def _next_image(self):
        """Navigate to next image"""
        if self.current_image_index < len(self.image_batch) - 1:
            self.current_image_index += 1
            self._load_current_image()
            self._update_image_counter()
    
    def _on_filename_changed(self, event):
        """Handle filename change"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            image_data.filename = self.filename_entry.get()
    
    def _on_language_changed(self, choice):
        """Handle language change"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            image_data.language = choice
    
    def _on_read_dir_changed(self, choice):
        """Handle reading direction change"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            image_data.read_direction = config.READ_DIRECTIONS[choice]
    
    def _zoom_in(self):
        """Zoom in current image"""
        self.canvas_panel.zoom_in()
    
    def _zoom_out(self):
        """Zoom out current image"""
        self.canvas_panel.zoom_out()
    
    def _zoom_reset(self):
        """Reset zoom"""
        self.canvas_panel.zoom_reset()
    
    def _rotate_image(self):
        """Rotate current image"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            image_data.rotate_image(config.ROTATION_ANGLE)
            self._load_current_image()
    
    def _clear_crops(self):
        """Clear all crop regions"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            image_data.clear_crop_regions()
            self._load_current_image()
            self._mark_image_pending(image_data)
    
    def _on_crop_added(self, x, y, width, height):
        """Handle new crop region added"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            image_data.add_crop_region(x, y, width, height)
            self._load_current_image()
            self._mark_image_pending(image_data)
    
    def _on_crop_selected(self, index):
        """Handle crop selection in list"""
        self.canvas_panel.set_selected_crop(index)
    
    def _on_crop_deleted(self, index):
        """Handle crop deletion"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            if index < len(image_data.crop_regions):
                crop = image_data.crop_regions[index]
                image_data.remove_crop_region(crop)
                self._load_current_image()
                self._mark_image_pending(image_data)
    
    def _on_crops_reordered(self, new_order):
        """Handle crop reordering"""
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            image_data.reorder_crops(new_order)
            self._load_current_image()
            self._mark_image_pending(image_data)
    
    def _submit_for_ocr(self):
        """Submit current image for OCR processing"""
        if not self.image_batch:
            messagebox.showwarning("Warning", "No images loaded")
            return
        
        if self.ocr_engine is None:
            messagebox.showerror("Error", "OCR engine not initialized")
            return
        
        # Add to processing queue
        queued_count = 0
        for image_data in self.image_batch:
            if not image_data.is_processed:
                self.processing_queue.put(image_data)
                queued_count += 1

        if queued_count == 0:
            self.progress_label.configure(text="No pending OCR tasks")
            return

        self.stop_requested.clear()
        self.processing_paused.set()
        self._set_processing_controls_active()
        self.pause_btn.configure(text="Pause OCR")
        
        self.progress_label.configure(text="Processing...")

    def _toggle_pause_processing(self):
        """Pause or resume OCR processing"""
        if not self.is_processing:
            return

        if self.processing_paused.is_set():
            self.processing_paused.clear()
            self.pause_btn.configure(text="Resume OCR")
            self.progress_label.configure(text="Paused")
        else:
            self.processing_paused.set()
            self.pause_btn.configure(text="Pause OCR")
            self.progress_label.configure(text="Processing...")

    def _stop_processing(self):
        """Request OCR processing stop"""
        if not self.is_processing:
            return

        self.stop_requested.set()
        self.processing_paused.set()
        self.progress_label.configure(text="Stopping...")

    def _set_processing_controls_idle(self):
        """Set processing control buttons back to idle state"""
        self.is_processing = False
        self.pause_btn.configure(state="disabled", text="Pause OCR")
        self.stop_btn.configure(state="disabled")
        self.submit_btn.configure(state="normal")

    def _set_processing_controls_active(self):
        """Set processing control buttons to active state"""
        self.is_processing = True
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        self.submit_btn.configure(state="disabled")

    def _count_pending_images(self) -> int:
        """Count images that need OCR processing."""
        return sum(1 for image_data in self.image_batch if not image_data.is_processed)

    def _update_pending_status(self):
        """Update progress label with pending OCR count when idle."""
        if self.is_processing:
            return

        pending_count = self._count_pending_images()
        if pending_count > 0:
            self.progress_label.configure(text=f"Pending OCR tasks: {pending_count}")
        else:
            self.progress_label.configure(text="Ready")

    def _mark_image_pending(self, image_data: ImageData):
        """Mark an image as needing OCR and clear any stale results."""
        image_data.is_processed = False
        for crop in image_data.crop_regions:
            crop.ocr_result = ""

        self._update_preview()
        self._update_pending_status()

    def _drain_processing_queue(self):
        """Remove all pending OCR tasks from queue"""
        while True:
            try:
                self.processing_queue.get_nowait()
                self.processing_queue.task_done()
            except queue.Empty:
                break
    
    def _start_background_processor(self):
        """Start background OCR processor"""
        def processor():
            while True:
                try:
                    self.processing_paused.wait()

                    if self.stop_requested.is_set():
                        self._drain_processing_queue()
                        self.stop_requested.clear()
                        self.after(0, self._set_processing_controls_idle)
                        self.after(0, lambda: self.progress_label.configure(text="Stopped"))
                        continue

                    image_data = self.processing_queue.get(timeout=1)
                    self.after(0, self._set_processing_controls_active)
                    self.after(0, lambda: self.progress_label.configure(text="Processing..."))
                    self._process_image(image_data)

                    if not self.stop_requested.is_set():
                        image_data.is_processed = True
                    
                    # Update UI on main thread
                    self.after(0, self._update_preview)
                    self.processing_queue.task_done()

                    if self.processing_queue.empty() and not self.stop_requested.is_set():
                        self.after(0, self._set_processing_controls_idle)
                        self.after(0, lambda: self.progress_label.configure(text="Ready"))
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Error processing image: {e}")
                    error_message = f"Error: {e}"
                    self.after(0, self._set_processing_controls_idle)
                    self.after(0, lambda msg=error_message: self.progress_label.configure(text=msg))
        
        thread = threading.Thread(target=processor, daemon=True)
        thread.start()
    
    def _process_image(self, image_data: ImageData):
        """Process a single image with OCR"""
        for index, crop in enumerate(image_data.crop_regions):
            if self.stop_requested.is_set():
                return

            self.processing_paused.wait()

            try:
                # Get cropped image
                cropped_img = image_data.get_cropped_image(crop)

                # Keep OCR language aligned with each image's selected language.
                selected_language = image_data.language
                selected_lang_code = config.SUPPORTED_LANGUAGES.get(selected_language, config.OCR_LANG)
                config.OCR_LANG = selected_lang_code

                # if hasattr(self.ocr_engine, "set_runtime_language"):
                #     try:
                #         self.ocr_engine.set_runtime_language(selected_language, selected_lang_code)
                #     except Exception as language_error:
                #         print(f"Warning: failed to set runtime OCR language: {language_error}")
                
                # Preprocess
                processed_img = ImageProcessor.preprocess(cropped_img)
                
                # Perform OCR
                text = self.ocr_engine.recognize_text(processed_img, image_data.read_direction)
                
                # Store result
                crop.ocr_result = text
            except Exception as e:
                print(f"Error processing crop #{index + 1}: {e}")
                crop.ocr_result = ""
    
    def _update_preview(self):
        """Update OCR preview text"""
        self.preview_text.delete("1.0", "end")
        
        if self.image_batch and self.current_image_index < len(self.image_batch):
            image_data = self.image_batch[self.current_image_index]
            
            for i, crop in enumerate(image_data.crop_regions):
                if crop.ocr_result:
                    self.preview_text.insert("end", f"--- Region {i + 1} ---\n")
                    self.preview_text.insert("end", crop.ocr_result)
                    self.preview_text.insert("end", "\n\n")
    
    def _save_results(self):
        """Save OCR results to files"""
        if not self.image_batch:
            messagebox.showwarning("Warning", "No images to save")
            return

        processed_images = [image_data for image_data in self.image_batch if image_data.is_processed]
        if len(processed_images) == 0:
            messagebox.showwarning("Warning", "No processed files to save")
            return

        batch_date = datetime.now().strftime("%Y%m%d")
        batch_id = self.batch_id or datetime.now().strftime("%H%M")

        saved_count = 0
        saved_folders = []
        for index, image_data in enumerate(processed_images):
            try:
                folder_base_name = f"{batch_date}_{batch_id}_{index + 1}"
                result = FileManager.save_all_results(image_data, folder_base_name=folder_base_name)
                saved_folders.append(result['folder'])
                saved_count += 1
            except Exception as e:
                print(f"Error saving {image_data.filename}: {e}")

        if saved_count > 0:
            parent_folder = os.path.dirname(saved_folders[0])
            messagebox.showinfo("Success", f"Saved {saved_count} image(s) to separate folders in:\n{parent_folder}")
        else:
            messagebox.showwarning("Warning", "No results were saved")
