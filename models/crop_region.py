"""
Data model for crop regions
"""

class CropRegion:
    """Represents a cropped region of an image"""
    
    def __init__(self, x, y, width, height, order=0):
        """
        Initialize a crop region
        
        Args:
            x: X coordinate of top-left corner
            y: Y coordinate of top-left corner
            width: Width of the region
            height: Height of the region
            order: Order number for processing sequence
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.order = order
        self.ocr_result = ""
        
    def get_bbox(self):
        """Get bounding box as (x, y, x+width, y+height)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def get_rect(self):
        """Get rectangle as (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)
    
    def contains_point(self, px, py):
        """Check if a point is inside this region"""
        return (self.x <= px <= self.x + self.width and 
                self.y <= py <= self.y + self.height)
    
    def __repr__(self):
        return f"CropRegion(x={self.x}, y={self.y}, w={self.width}, h={self.height}, order={self.order})"
