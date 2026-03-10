"""
File management service
"""
import os
import shutil
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from typing import List
import config
from models.image_data import ImageData


class FileManager:
    """Handles file operations for saving results"""
    
    @staticmethod
    def create_output_folder(base_name: str) -> str:
        """
        Create a unique output folder
        
        Args:
            base_name: Base name for the folder
            
        Returns:
            Path to created folder
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{base_name}_{timestamp}"
        folder_path = os.path.join(config.OUTPUT_FOLDER, folder_name)
        
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    @staticmethod
    def create_image_folder(parent_folder: str, base_name: str) -> str:
        """
        Create a unique folder for a single image inside a parent folder

        Args:
            parent_folder: Parent output folder
            base_name: Base name for the folder

        Returns:
            Path to created folder
        """
        os.makedirs(parent_folder, exist_ok=True)

        safe_base = (base_name or "image").strip()
        if not safe_base:
            safe_base = "image"
        safe_base = safe_base.replace(os.sep, "_")
        if os.altsep:
            safe_base = safe_base.replace(os.altsep, "_")

        folder_path = os.path.join(parent_folder, safe_base)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            return folder_path

        counter = 1
        while True:
            candidate = os.path.join(parent_folder, f"{safe_base}_{counter}")
            if not os.path.exists(candidate):
                os.makedirs(candidate, exist_ok=True)
                return candidate
            counter += 1
    
    @staticmethod
    def save_original_image(image_data: ImageData, output_folder: str) -> str:
        """
        Save the original image
        
        Args:
            image_data: ImageData object
            output_folder: Output folder path
            
        Returns:
            Path to saved file
        """
        filename = f"{image_data.filename}_original.png"
        filepath = os.path.join(output_folder, filename)
        image_data.content.save(filepath)
        return filepath
    
    @staticmethod
    def save_annotated_image(image_data: ImageData, output_folder: str) -> str:
        """
        Save image with crop rectangles annotated
        
        Args:
            image_data: ImageData object
            output_folder: Output folder path
            
        Returns:
            Path to saved file
        """
        # Create a copy of the image
        annotated = image_data.content.copy()
        draw = ImageDraw.Draw(annotated)
        
        # Draw rectangles for each crop region
        for i, crop in enumerate(image_data.crop_regions):
            bbox = crop.get_bbox()
            
            # Draw rectangle
            draw.rectangle(bbox, outline=config.CROP_RECT_COLOR, width=config.CROP_RECT_WIDTH)
            
            # Draw crop number
            text = str(i + 1)
            try:
                # Try to use a larger font
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
            
            # Position text at top-left of crop
            text_position = (crop.x + 5, crop.y + 5)
            draw.text(text_position, text, fill=config.CROP_RECT_COLOR, font=font)
        
        # Save annotated image
        filename = f"{image_data.filename}_annotated.png"
        filepath = os.path.join(output_folder, filename)
        annotated.save(filepath)
        return filepath
    
    @staticmethod
    def save_ocr_results(image_data: ImageData, output_folder: str) -> str:
        """
        Save OCR results to text file
        
        Args:
            image_data: ImageData object
            output_folder: Output folder path
            
        Returns:
            Path to saved file
        """
        filename = f"{image_data.filename}_ocr.txt"
        filepath = os.path.join(output_folder, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write metadata
            f.write(f"File: {image_data.file_path}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Language: {image_data.language}\n")
            f.write(f"Reading Direction: {image_data.read_direction}\n")
            f.write(f"Image Size: {image_data.width} x {image_data.height}\n")
            f.write(f"Number of Regions: {len(image_data.crop_regions)}\n")
            f.write("=" * 50 + "\n\n")
            
            # Write OCR results for each crop
            for i, crop in enumerate(image_data.crop_regions):
                f.write(f"--- Region {i + 1} ---\n")
                f.write(f"Position: ({crop.x}, {crop.y})\n")
                f.write(f"Size: {crop.width} x {crop.height}\n\n")
                f.write(crop.ocr_result)
                f.write("\n\n" + "=" * 50 + "\n\n")
        
        return filepath
    
    @staticmethod
    def save_all_results(image_data: ImageData, batch_folder: str = None, folder_base_name: str = None) -> dict:
        """
        Save all results (annotated image and OCR text)
        
        Args:
            image_data: ImageData object
            batch_folder: Optional existing batch folder, creates image folder inside if provided
            folder_base_name: Optional base name for the image folder when batch_folder is None
            
        Returns:
            Dictionary with paths to saved files
        """
        if batch_folder is None:
            base_name = folder_base_name or image_data.filename
            output_folder = FileManager.create_image_folder(config.OUTPUT_FOLDER, base_name)
        else:
            output_folder = FileManager.create_image_folder(batch_folder, image_data.filename)
        
        results = {
            'folder': output_folder,
            'annotated': FileManager.save_annotated_image(image_data, output_folder),
            'ocr_text': FileManager.save_ocr_results(image_data, output_folder)
        }
        
        return results
