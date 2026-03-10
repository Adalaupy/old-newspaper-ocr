"""
Data model for imported images
"""
from datetime import datetime
from typing import List, Optional
from PIL import Image
from models.crop_region import CropRegion
import config


class ImageData:
    """Represents an imported image or PDF page"""
    
    def __init__(self, file_path: str, content: Image.Image, page_number: Optional[int] = None, image_index: Optional[int] = None):
        """
        Initialize image data
        
        Args:
            file_path: Original file path
            content: PIL Image object
            page_number: Page number if from PDF
        """
        self.file_path = file_path
        self.content = content
        self.page_number = page_number
        self.image_index = image_index
        
        # Image dimensions
        self.width, self.height = content.size
        
        # Settings
        self.read_direction = config.DEFAULT_READ_DIRECTION
        self.language = config.DEFAULT_LANGUAGE
        self.filename = self._generate_default_filename()
        
        # Crop regions
        self.crop_regions: List[CropRegion] = []
        self._add_default_crop()
        
        # Processing state
        self.is_processed = False
        self.rotation_angle = 0  # Track total rotation
        
    def _generate_default_filename(self) -> str:
        """Generate default filename based on date and import order"""
        if self.image_index is not None:
            template = datetime.now().strftime(config.DEFAULT_FILENAME_FORMAT)
            return template.format(id=self.image_index + 1)
        date_str = datetime.now().strftime("%Y%m%d")
        page_suffix = f"_p{self.page_number}" if self.page_number else ""
        return f"{date_str}{page_suffix}"
    
    def _add_default_crop(self):
        """Add default crop region (full image)"""
        self.crop_regions.append(
            CropRegion(0, 0, self.width, self.height, order=0)
        )
    
    def add_crop_region(self, x: int, y: int, width: int, height: int) -> CropRegion:
        """
        Add a new crop region
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Width of region
            height: Height of region
            
        Returns:
            The created CropRegion
        """
        # If only default crop exists, remove it
        if len(self.crop_regions) == 1:
            default_crop = self.crop_regions[0]
            if (default_crop.x == 0 and default_crop.y == 0 and 
                default_crop.width == self.width and default_crop.height == self.height):
                self.crop_regions.clear()
        
        order = len(self.crop_regions)
        crop = CropRegion(x, y, width, height, order)
        self.crop_regions.append(crop)
        return crop
    
    def remove_crop_region(self, crop: CropRegion):
        """Remove a specific crop region"""
        if crop in self.crop_regions:
            self.crop_regions.remove(crop)
            # Reorder remaining crops
            for i, c in enumerate(self.crop_regions):
                c.order = i
    
    def clear_crop_regions(self):
        """Remove all crop regions and reset to default (full image)"""
        self.crop_regions.clear()
        self._add_default_crop()
    
    def reorder_crops(self, new_order: List[int]):
        """
        Reorder crop regions based on new order list
        
        Args:
            new_order: List of indices representing new order
        """
        reordered = [self.crop_regions[i] for i in new_order]
        for i, crop in enumerate(reordered):
            crop.order = i
        self.crop_regions = reordered
    
    def rotate_image(self, angle: int):
        """
        Rotate image and update dimensions
        
        Args:
            angle: Rotation angle (90, 180, 270, or -90)
        """
        self.content = self.content.rotate(-angle, expand=True)
        self.width, self.height = self.content.size
        self.rotation_angle = (self.rotation_angle + angle) % 360
        
        # Clear crops after rotation as coordinates are invalid
        self.clear_crop_regions()
    
    def get_cropped_image(self, crop: CropRegion) -> Image.Image:
        """
        Get the cropped portion of the image
        
        Args:
            crop: CropRegion to extract
            
        Returns:
            Cropped PIL Image
        """
        return self.content.crop(crop.get_bbox())
    
    def __repr__(self):
        return f"ImageData(file={self.file_path}, size={self.width}x{self.height}, crops={len(self.crop_regions)})"
