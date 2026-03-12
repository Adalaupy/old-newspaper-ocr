"""
Main entry point for the OCR application
"""
import customtkinter as ctk
import sys
import os

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import MainWindow


def main():
    """Main application entry point"""
    try:
        # Create and run application
        app = MainWindow()
        app.mainloop()
    except KeyboardInterrupt:
        # Allow clean shutdown when stopping from terminal (Ctrl+C)
        print("Application interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
