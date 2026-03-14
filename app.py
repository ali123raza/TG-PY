"""
TG-PY Unified Application
Combined Backend + Frontend with Direct Service Access
No FastAPI needed - direct calls for realtime data sharing
"""
import sys
import os
import asyncio
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment variable for base directory
os.environ['TG_BASE_DIR'] = str(Path(__file__).parent.parent)

def main():
    """Main entry point for unified application"""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    
    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("TG-PY")
    app.setApplicationVersion("1.0.0")
    
    # Set application font
    font = QFont("Inter", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # Enable high DPI scaling
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # Import and initialize data service (replaces API client)
    from data_service import get_data_service
    
    logger.info("Initializing data service...")
    data_service = get_data_service()
    data_service.connect()
    
    logger.info("Data service connected successfully")
    
    # Import main window from main module
    from main import MainWindow
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info("TG-PY Unified Application started")
    
    # Run application
    try:
        exit_code = app.exec()
    finally:
        # Cleanup
        data_service.disconnect()
        logger.info("TG-PY Application closed")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
