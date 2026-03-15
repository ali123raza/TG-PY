"""
TG-PY Unified Application
Combined Backend + Frontend with Direct Service Access
"""
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FIX: BASE_DIR = full_app folder (where data/, sessions/, media/ live)
# Old code was .parent.parent which pointed to TG-PY/ instead of TG-PY/full_app/
os.environ['TG_BASE_DIR'] = str(Path(__file__).parent)


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont

    app = QApplication(sys.argv)
    app.setApplicationName("TG-PY")
    app.setApplicationVersion("1.0.0")

    font = QFont("Inter", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    from data_service import get_data_service

    logger.info("Initializing data service...")
    data_service = get_data_service()
    data_service.connect()
    logger.info("Data service connected")

    from main import MainWindow

    window = MainWindow()
    window.show()

    logger.info("TG-PY started")

    try:
        exit_code = app.exec()
    finally:
        data_service.disconnect()
        logger.info("TG-PY closed")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()