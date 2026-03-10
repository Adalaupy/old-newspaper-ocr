"""
Setup script to install dependencies and prepare the application
"""
import subprocess
import sys
import os


def install_dependencies():
    """Install required packages"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\n✓ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error installing dependencies: {e}")
        return False


def create_output_folder():
    """Create output folder if it doesn't exist"""
    if not os.path.exists("output"):
        os.makedirs("output")
        print("✓ Created output folder")


def main():
    """Main setup function"""
    print("=" * 50)
    print("OCR Application Setup")
    print("=" * 50)
    print()
    
    # Install dependencies
    if not install_dependencies():
        print("\nSetup failed. Please install dependencies manually:")
        print("  pip install -r requirements.txt")
        return 1
    
    # Create necessary folders
    create_output_folder()
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("=" * 50)
    print("\nTo run the application:")
    print("  python main.py")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
