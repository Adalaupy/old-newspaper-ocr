"""
PDF handling service
"""
import fitz  # PyMuPDF
from PIL import Image
from typing import List, Tuple
import io


class PDFHandler:
    """Handles PDF file operations"""
    
    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        """
        Get the number of pages in a PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Number of pages
        """
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return 0
    
    @staticmethod
    def extract_page(pdf_path: str, page_number: int, dpi: int = 300) -> Image.Image:
        """
        Extract a single page from PDF as image
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (0-indexed)
            dpi: Resolution for conversion
            
        Returns:
            PIL Image of the page
        """
        try:
            doc = fitz.open(pdf_path)
            
            if page_number >= len(doc):
                raise ValueError(f"Page {page_number} does not exist")
            
            page = doc[page_number]
            
            # Calculate zoom factor for desired DPI
            zoom = dpi / 72  # 72 is default DPI
            mat = fitz.Matrix(zoom, zoom)
            
            # Render page to image
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            doc.close()
            return image
            
        except Exception as e:
            print(f"Error extracting page {page_number}: {e}")
            raise
    
    @staticmethod
    def extract_pages(pdf_path: str, page_numbers: List[int], dpi: int = 300) -> List[Tuple[int, Image.Image]]:
        """
        Extract multiple pages from PDF
        
        Args:
            pdf_path: Path to PDF file
            page_numbers: List of page numbers (0-indexed)
            dpi: Resolution for conversion
            
        Returns:
            List of tuples (page_number, PIL Image)
        """
        results = []
        
        try:
            doc = fitz.open(pdf_path)
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num in page_numbers:
                if page_num >= len(doc):
                    print(f"Warning: Page {page_num} does not exist, skipping")
                    continue
                
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                results.append((page_num, image))
            
            doc.close()
            return results
            
        except Exception as e:
            print(f"Error extracting pages: {e}")
            raise
    
    @staticmethod
    def extract_all_pages(pdf_path: str, dpi: int = 300) -> List[Tuple[int, Image.Image]]:
        """
        Extract all pages from PDF
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion
            
        Returns:
            List of tuples (page_number, PIL Image)
        """
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            
            page_numbers = list(range(page_count))
            return PDFHandler.extract_pages(pdf_path, page_numbers, dpi)
            
        except Exception as e:
            print(f"Error extracting all pages: {e}")
            raise
