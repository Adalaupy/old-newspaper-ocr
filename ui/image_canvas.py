"""
Image canvas component for displaying and cropping images
"""
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
from typing import Optional, Callable
import config


class ImageCanvas(ctk.CTkFrame):
    """Canvas for displaying images and selecting crop regions"""
    
    def __init__(self, parent, on_crop_added: Optional[Callable] = None):
        """
        Initialize image canvas
        
        Args:
            parent: Parent widget
            on_crop_added: Callback when crop region is added
        """
        super().__init__(parent)
        
        self.on_crop_added = on_crop_added
        
        # Current image data
        self.original_image: Optional[Image.Image] = None
        self.display_image: Optional[Image.Image] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        
        # Display state
        self.zoom_level = 1.0
        self.display_size = (0, 0)
        
        # Crop selection state
        self.crop_start = None
        self.crop_current = None
        self.is_cropping = False
        
        # Existing crops to display
        self.crop_regions = []
        self.selected_crop_index = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components"""
        # Canvas for image display
        self.canvas = ctk.CTkCanvas(
            self,
            bg=config.CANVAS_BG_COLOR,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bind mouse events for crop selection
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
    
    def load_image(self, image: Image.Image, crop_regions: list = None):
        """
        Load an image for display
        
        Args:
            image: PIL Image to display
            crop_regions: List of CropRegion objects
        """
        self.original_image = image
        self.crop_regions = crop_regions or []
        self.zoom_level = 1.0
        self.selected_crop_index = None
        self._update_display()
    
    def _update_display(self):
        """Update the canvas display"""
        if self.original_image is None:
            return
        
        # Calculate display size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not yet sized, use defaults
            canvas_width = config.MAX_DISPLAY_WIDTH
            canvas_height = config.MAX_DISPLAY_HEIGHT
        
        # Calculate zoom to fit
        img_width, img_height = self.original_image.size
        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height
        fit_ratio = min(width_ratio, height_ratio) * 0.95  # 95% to leave margin
        
        # Apply zoom
        display_ratio = fit_ratio * self.zoom_level
        new_width = int(img_width * display_ratio)
        new_height = int(img_height * display_ratio)
        
        self.display_size = (new_width, new_height)
        
        # Resize image for display
        self.display_image = self.original_image.copy()
        
        # Draw existing crop regions on image
        if self.crop_regions:
            self.display_image = self._draw_crops_on_image(self.display_image)
        
        # Resize for display
        self.display_image = self.display_image.resize(
            (new_width, new_height), 
            Image.Resampling.LANCZOS
        )
        
        # Convert to PhotoImage
        self.photo_image = ImageTk.PhotoImage(self.display_image)
        
        # Update canvas
        self.canvas.delete("all")
        
        # Center image on canvas
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        
        self.canvas.create_image(x, y, anchor="nw", image=self.photo_image)
        self.image_offset = (x, y)
    
    def _draw_crops_on_image(self, image: Image.Image) -> Image.Image:
        """
        Draw crop regions on image
        
        Args:
            image: PIL Image to draw on
            
        Returns:
            Image with crops drawn
        """
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        for i, crop in enumerate(self.crop_regions):
            color = config.SELECTED_CROP_COLOR if i == self.selected_crop_index else config.CROP_RECT_COLOR
            draw.rectangle(crop.get_bbox(), outline=color, width=config.CROP_RECT_WIDTH)
            
            # Draw order number
            text = str(crop.order + 1)
            text_pos = (crop.x + 5, crop.y + 5)
            draw.text(text_pos, text, fill=color)
        
        return img_copy
    
    def _on_mouse_down(self, event):
        """Handle mouse button press"""
        if self.original_image is None:
            return
        
        # Convert canvas coordinates to image coordinates
        img_x, img_y = self._canvas_to_image_coords(event.x, event.y)
        
        if img_x is not None:
            self.crop_start = (img_x, img_y)
            self.is_cropping = True
    
    def _on_mouse_drag(self, event):
        """Handle mouse drag"""
        if not self.is_cropping or self.crop_start is None:
            return
        
        # Convert canvas coordinates to image coordinates
        img_x, img_y = self._canvas_to_image_coords(event.x, event.y)
        
        if img_x is not None:
            self.crop_current = (img_x, img_y)
            self._draw_crop_preview()
    
    def _on_mouse_up(self, event):
        """Handle mouse button release"""
        if not self.is_cropping or self.crop_start is None:
            return
        
        # Convert canvas coordinates to image coordinates
        img_x, img_y = self._canvas_to_image_coords(event.x, event.y)
        
        if img_x is not None:
            # Calculate crop region
            x1, y1 = self.crop_start
            x2, y2 = img_x, img_y
            
            # Ensure x1 < x2 and y1 < y2
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            # Only add crop if it has meaningful size
            if width > 10 and height > 10:
                if self.on_crop_added:
                    self.on_crop_added(x, y, width, height)
        
        # Reset crop state
        self.is_cropping = False
        self.crop_start = None
        self.crop_current = None
        self._update_display()
    
    def _draw_crop_preview(self):
        """Draw preview of current crop selection"""
        if self.crop_start is None or self.crop_current is None:
            return
        
        # Redraw image
        self._update_display()
        
        # Draw crop preview rectangle
        x1, y1 = self._image_to_canvas_coords(*self.crop_start)
        x2, y2 = self._image_to_canvas_coords(*self.crop_current)
        
        if x1 is not None and x2 is not None:
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="green",
                width=2,
                dash=(5, 5)
            )
    
    def _canvas_to_image_coords(self, canvas_x, canvas_y):
        """Convert canvas coordinates to original image coordinates"""
        if self.original_image is None or not hasattr(self, 'image_offset'):
            return None, None
        
        offset_x, offset_y = self.image_offset
        display_width, display_height = self.display_size
        
        # Check if click is within image bounds
        if (canvas_x < offset_x or canvas_x > offset_x + display_width or
            canvas_y < offset_y or canvas_y > offset_y + display_height):
            return None, None
        
        # Convert to image coordinates
        img_width, img_height = self.original_image.size
        img_x = int((canvas_x - offset_x) * img_width / display_width)
        img_y = int((canvas_y - offset_y) * img_height / display_height)
        
        # Clamp to image bounds
        img_x = max(0, min(img_x, img_width))
        img_y = max(0, min(img_y, img_height))
        
        return img_x, img_y
    
    def _image_to_canvas_coords(self, img_x, img_y):
        """Convert original image coordinates to canvas coordinates"""
        if self.original_image is None or not hasattr(self, 'image_offset'):
            return None, None
        
        offset_x, offset_y = self.image_offset
        display_width, display_height = self.display_size
        img_width, img_height = self.original_image.size
        
        canvas_x = int(img_x * display_width / img_width) + offset_x
        canvas_y = int(img_y * display_height / img_height) + offset_y
        
        return canvas_x, canvas_y
    
    def zoom_in(self):
        """Zoom in the image"""
        self.zoom_level *= config.ZOOM_FACTOR
        self._update_display()
    
    def zoom_out(self):
        """Zoom out the image"""
        self.zoom_level /= config.ZOOM_FACTOR
        self._update_display()
    
    def zoom_reset(self):
        """Reset zoom to fit"""
        self.zoom_level = 1.0
        self._update_display()
    
    def set_selected_crop(self, index: Optional[int]):
        """Highlight a specific crop region"""
        self.selected_crop_index = index
        self._update_display()
