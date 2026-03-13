"""
Crop list panel component
"""
import customtkinter as ctk
from typing import Optional, Callable, List
from models.crop_region import CropRegion


class CropListPanel(ctk.CTkFrame):
    """Panel for managing crop regions"""
    
    def __init__(self, parent, on_selection_changed: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None,
                 on_reorder: Optional[Callable] = None):
        """
        Initialize crop list panel
        
        Args:
            parent: Parent widget
            on_selection_changed: Callback when selection changes
            on_delete: Callback when delete is clicked
            on_reorder: Callback when order changes
        """
        super().__init__(parent)
        
        self.on_selection_changed = on_selection_changed
        self.on_delete = on_delete
        self.on_reorder = on_reorder
        
        self.crop_regions: List[CropRegion] = []
        self.selected_index: Optional[int] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components"""
        # Title
        title = ctk.CTkLabel(self, text="Crop Regions", font=("Arial", 14, "bold"))
        title.pack(pady=(5, 10))
        
        # Scrollable frame for crop list
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=300)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        # Delete button
        self.delete_btn = ctk.CTkButton(
            btn_frame,
            text="Delete Selected",
            command=self._on_delete_clicked,
            state="disabled"
        )
        self.delete_btn.pack(side="left", padx=2)
        
        # Move up button
        self.move_up_btn = ctk.CTkButton(
            btn_frame,
            text="↑",
            width=40,
            command=self._on_move_up,
            state="disabled"
        )
        self.move_up_btn.pack(side="right", padx=2)
        
        # Move down button
        self.move_down_btn = ctk.CTkButton(
            btn_frame,
            text="↓",
            width=40,
            command=self._on_move_down,
            state="disabled"
        )
        self.move_down_btn.pack(side="right", padx=2)
    
    def update_crops(self, crop_regions: List[CropRegion]):
        """
        Update the displayed crop regions
        
        Args:
            crop_regions: List of CropRegion objects
        """
        self.crop_regions = crop_regions
        self.selected_index = None
        self._refresh_list()
    
    def _refresh_list(self):
        """Refresh the crop list display"""
        # Clear existing items
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        # Add crop items
        for i, crop in enumerate(self.crop_regions):
            self._create_crop_item(i, crop)
        
        # Update button states
        self._update_button_states()
    
    def _create_crop_item(self, index: int, crop: CropRegion):
        """Create a crop item widget"""
        # Frame for this crop
        frame = ctk.CTkFrame(self.scroll_frame)
        frame.pack(fill="x", pady=2)
        
        # Crop info
        text = f"#{crop.order + 1}: ({crop.x}, {crop.y}) - {crop.width}x{crop.height}"
        
        btn = ctk.CTkButton(
            frame,
            text=text,
            command=lambda idx=index: self._on_crop_selected(idx),
            anchor="w"
        )
        btn.pack(fill="x", padx=2, pady=2)
        
        # Highlight if selected
        if index == self.selected_index:
            btn.configure(fg_color="green")
    
    def _on_crop_selected(self, index: int):
        """Handle crop selection"""
        self.selected_index = index
        self._refresh_list()
        
        if self.on_selection_changed:
            self.on_selection_changed(index)
    
    def _on_delete_clicked(self):
        """Handle delete button click"""
        if self.selected_index is not None and self.on_delete:
            self.on_delete(self.selected_index)
    
    def _on_move_up(self):
        """Move selected crop up in order"""
        if self.selected_index is not None and self.selected_index > 0:
            # Swap with previous
            new_order = list(range(len(self.crop_regions)))
            new_order[self.selected_index], new_order[self.selected_index - 1] = \
                new_order[self.selected_index - 1], new_order[self.selected_index]
            new_index = self.selected_index - 1
            if self.on_reorder:
                self.on_reorder(new_order)
            self.selected_index = new_index
            self._refresh_list()
    
    def _on_move_down(self):
        """Move selected crop down in order"""
        if (self.selected_index is not None and 
            self.selected_index < len(self.crop_regions) - 1):
            # Swap with next
            new_order = list(range(len(self.crop_regions)))
            new_order[self.selected_index], new_order[self.selected_index + 1] = \
                new_order[self.selected_index + 1], new_order[self.selected_index]
            new_index = self.selected_index + 1
            if self.on_reorder:
                self.on_reorder(new_order)
            self.selected_index = new_index
            self._refresh_list()
    
    def _update_button_states(self):
        """Update button enabled/disabled states"""
        has_selection = self.selected_index is not None
        has_multiple = len(self.crop_regions) > 1
        
        # Delete button
        if has_selection:
            self.delete_btn.configure(state="normal")
        else:
            self.delete_btn.configure(state="disabled")
        
        # Move up button
        if has_selection and self.selected_index > 0:
            self.move_up_btn.configure(state="normal")
        else:
            self.move_up_btn.configure(state="disabled")
        
        # Move down button
        if has_selection and self.selected_index < len(self.crop_regions) - 1:
            self.move_down_btn.configure(state="normal")
        else:
            self.move_down_btn.configure(state="disabled")
