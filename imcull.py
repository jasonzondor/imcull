#!/usr/bin/env python3
"""
ImCull - Photography Workflow Culling Tool
"""

import sys
import os
import logging
import xdg.BaseDirectory
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from core.config import Config
from ui.main_window import MainWindow

# Set up logging
def setup_logging():
    app_dir = xdg.BaseDirectory.save_data_path('imcull')
    log_file = os.path.join(app_dir, 'imcull.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )
    logger = logging.getLogger('imcull')

def ensure_app_dirs():
    """Ensure application directories exist"""
    app_dir = xdg.BaseDirectory.save_data_path('imcull')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def main():
    """Main application entry point"""
    # Set up logging
    setup_logging()

    # Ensure app directories exist
    app_dir = ensure_app_dirs()

    # Load configuration
    config = Config()

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName('ImCull')
    app.setApplicationVersion('0.1.0')
    app.setOrganizationName('ImCull')
    app.setOrganizationDomain("imcull.local")

    # Initialize settings
    settings = QSettings()

    # Create main window
    main_window = MainWindow(config, settings)
    main_window.show()

    # Run application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
