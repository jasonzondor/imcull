"""
Main window for ImCull
"""

import os
import logging
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QToolBar, QFileDialog, QMessageBox, QDialog,
    QStatusBar, QSplitter, QPushButton, QLineEdit, QFormLayout,
    QDialogButtonBox, QComboBox, QCheckBox
)
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QImage
from PyQt6.QtCore import Qt, QSettings, QSize, QTimer, pyqtSlot

from core.image_handler import ImageHandler, ImageInfo
from core.darktable_integration import DarktableIntegration
from core.backup_handler import BackupHandler
from ui.image_viewer import ImageViewer
from ui.thumbnail_strip import ThumbnailStrip
from ui.metadata_panel import MetadataPanel
from ui.settings_dialog import SettingsDialog

logger = logging.getLogger('imcull.ui.main_window')


class MainWindow(QMainWindow):
    """Main window for ImCull"""

    def __init__(self, config, settings: QSettings):
        super().__init__()

        self.config = config
        self.settings = settings

        # Initialize components
        self.image_handler = ImageHandler(
            blur_threshold=config.get('culling.blur_detection_threshold', 100)
        )
        self.darktable = DarktableIntegration(
            executable=config.get('darktable.executable', 'darktable')
        )
        self.backup_handler = BackupHandler(
            backup_locations=config.get('import.backup_locations', [])
        )

        # Set up UI
        self.setup_ui()
        self.setup_shortcuts()
        self.restore_settings()

        # Status variables
        self.current_directory = None
        self.is_culling_mode = False

        self.setWindowTitle("ImCull - Photography Workflow Assistant")
        self.show_welcome_message()

    def setup_ui(self):
        """Set up the user interface"""
        # Set window properties
        self.resize(1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Create toolbar
        self.create_toolbar()

        # Create main content area
        main_content = QWidget()
        content_layout = QVBoxLayout(main_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for image viewer and metadata panel
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Create image viewer
        self.image_viewer = ImageViewer()

        # Create metadata panel
        self.metadata_panel = MetadataPanel()

        # Add widgets to splitter
        self.main_splitter.addWidget(self.image_viewer)
        self.main_splitter.addWidget(self.metadata_panel)

        # Set splitter sizes
        self.main_splitter.setSizes([800, 400])
        
        # Add splitter to content layout
        content_layout.addWidget(self.main_splitter)
        
        # Create thumbnail strip at the bottom
        self.thumbnail_strip = ThumbnailStrip()
        
        # Add main content and thumbnail strip to main layout
        main_layout.addWidget(main_content, 1)  # Give main content area stretch factor
        main_layout.addWidget(self.thumbnail_strip, 0)  # No stretch for thumbnail strip

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Connect signals
        self.thumbnail_strip.image_selected.connect(self.on_thumbnail_selected)
        self.image_viewer.rating_changed.connect(self.on_rating_changed)

    def create_toolbar(self):
        """Create the main toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Open directory action
        self.action_open = QAction("Open Directory", self)
        self.action_open.triggered.connect(self.open_directory)
        self.toolbar.addAction(self.action_open)

        self.toolbar.addSeparator()

        # Rating actions
        self.action_rate_1 = QAction("★", self)
        self.action_rate_1.triggered.connect(lambda: self.set_rating(1))
        self.toolbar.addAction(self.action_rate_1)

        self.action_rate_2 = QAction("★★", self)
        self.action_rate_2.triggered.connect(lambda: self.set_rating(2))
        self.toolbar.addAction(self.action_rate_2)

        self.action_rate_3 = QAction("★★★", self)
        self.action_rate_3.triggered.connect(lambda: self.set_rating(3))
        self.toolbar.addAction(self.action_rate_3)

        self.action_rate_0 = QAction("No Rating", self)
        self.action_rate_0.triggered.connect(lambda: self.set_rating(0))
        self.toolbar.addAction(self.action_rate_0)

        self.action_reject = QAction("Reject", self)
        self.action_reject.triggered.connect(self.toggle_reject)
        self.toolbar.addAction(self.action_reject)

        self.toolbar.addSeparator()

        # Navigation actions
        self.action_prev = QAction("Previous", self)
        self.action_prev.triggered.connect(self.prev_image)
        self.toolbar.addAction(self.action_prev)

        self.action_next = QAction("Next", self)
        self.action_next.triggered.connect(self.next_image)
        self.toolbar.addAction(self.action_next)

        self.toolbar.addSeparator()

        # Darktable actions
        self.action_darktable = QAction("Send to Darktable", self)
        self.action_darktable.triggered.connect(self.send_to_darktable)
        self.toolbar.addAction(self.action_darktable)

        # Backup actions
        self.action_backup = QAction("Backup Selected", self)
        self.action_backup.triggered.connect(self.backup_selected)
        self.toolbar.addAction(self.action_backup)

        self.toolbar.addSeparator()

        # Settings action
        self.action_settings = QAction("Settings", self)
        self.action_settings.triggered.connect(self.show_settings)
        self.toolbar.addAction(self.action_settings)

    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Navigation shortcuts
        self.shortcut_next = QKeySequence(self.config.get('keyboard.next_image', 'Space'))
        self.action_next.setShortcut(self.shortcut_next)

        self.shortcut_prev = QKeySequence(self.config.get('keyboard.prev_image', 'Backspace'))
        self.action_prev.setShortcut(self.shortcut_prev)

        # Rating shortcuts
        self.shortcut_rate_1 = QKeySequence(self.config.get('keyboard.rate_1', '1'))
        self.action_rate_1.setShortcut(self.shortcut_rate_1)

        self.shortcut_rate_2 = QKeySequence(self.config.get('keyboard.rate_2', '2'))
        self.action_rate_2.setShortcut(self.shortcut_rate_2)

        self.shortcut_rate_3 = QKeySequence(self.config.get('keyboard.rate_3', '3'))
        self.action_rate_3.setShortcut(self.shortcut_rate_3)

        self.shortcut_rate_0 = QKeySequence(self.config.get('keyboard.remove_rating', '0'))
        self.action_rate_0.setShortcut(self.shortcut_rate_0)

        self.shortcut_reject = QKeySequence(self.config.get('keyboard.reject', 'X'))
        self.action_reject.setShortcut(self.shortcut_reject)

        # Action shortcuts
        self.shortcut_darktable = QKeySequence(self.config.get('keyboard.send_to_darktable', 'Ctrl+D'))
        self.action_darktable.setShortcut(self.shortcut_darktable)

        self.shortcut_backup = QKeySequence(self.config.get('keyboard.backup', 'Ctrl+B'))
        self.action_backup.setShortcut(self.shortcut_backup)

    def restore_settings(self):
        """Restore window settings from QSettings"""
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))

        if self.settings.contains("windowState"):
            self.restoreState(self.settings.value("windowState"))

        if self.settings.contains("splitterSizes"):
            # Convert string values to integers if needed
            splitter_sizes = self.settings.value("splitterSizes")
            if splitter_sizes and isinstance(splitter_sizes[0], str):
                splitter_sizes = [int(size) for size in splitter_sizes]
            self.main_splitter.setSizes(splitter_sizes)

    def save_settings(self):
        """Save window settings to QSettings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("splitterSizes", self.main_splitter.sizes())

    def closeEvent(self, event):
        """Handle window close event"""
        self.save_settings()
        super().closeEvent(event)

    def show_welcome_message(self):
        """Show welcome message in status bar"""
        self.status_bar.showMessage("Welcome to ImCull. Open a directory to begin culling.")

    def open_directory(self):
        """Open a directory dialog and load images"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory with Photos",
            self.config.get('import.default_source_dir', '') or os.path.expanduser("~")
        )

        if directory:
            self.load_directory(directory)

    def load_directory(self, directory: str):
        """Load images from the specified directory"""
        self.status_bar.showMessage(f"Loading images from {directory}...")

        # Scan directory for images
        images = self.image_handler.scan_directory(directory)

        if not images:
            QMessageBox.warning(
                self,
                "No Images Found",
                f"No supported image files found in {directory}"
            )
            self.status_bar.showMessage("No images found.")
            return

        # Update current directory
        self.current_directory = directory

        # Analyze images for blur detection
        self.status_bar.showMessage(f"Analyzing {len(images)} images...")

        # Process first image immediately
        if images:
            first_image = self.image_handler.analyze_image(images[0])
            self.display_image(first_image)

        # Process remaining images in background
        QTimer.singleShot(100, self.process_next_image)

        # Update thumbnail strip
        self.thumbnail_strip.set_images(images)

        self.status_bar.showMessage(f"Loaded {len(images)} images from {directory}")

    def process_next_image(self):
        """Process the next unanalyzed image"""
        for i, image in enumerate(self.image_handler.images):
            if image.thumbnail is None:
                self.image_handler.analyze_image(image)
                self.thumbnail_strip.update_thumbnail(i)

                # Schedule next image processing
                QTimer.singleShot(50, self.process_next_image)
                return

    def display_image(self, image_info: ImageInfo):
        """Display the current image"""
        if not image_info:
            return

        # Load and display the image
        self.image_viewer.set_image(image_info)

        # Update metadata panel
        self.metadata_panel.set_image(image_info)

        # Update thumbnail strip selection
        self.thumbnail_strip.select_image(self.image_handler.current_index)

        # Update status bar
        status = f"Image {self.image_handler.current_index + 1}/{len(self.image_handler.images)}"
        if image_info.is_blurry:
            status += " | Potentially blurry"
        self.status_bar.showMessage(status)

    @pyqtSlot(int)
    def on_thumbnail_selected(self, index: int):
        """Handle thumbnail selection"""
        if 0 <= index < len(self.image_handler.images):
            self.image_handler.current_index = index
            self.display_image(self.image_handler.get_current_image())

    @pyqtSlot(int)
    def on_rating_changed(self, rating: int):
        """Handle rating change from image viewer"""
        self.set_rating(rating)

    def next_image(self):
        """Display the next image"""
        image = self.image_handler.next_image()
        self.display_image(image)

    def prev_image(self):
        """Display the previous image"""
        image = self.image_handler.prev_image()
        self.display_image(image)

    def set_rating(self, rating: int):
        """Set the rating for the current image"""
        self.image_handler.set_rating(rating)
        self.image_viewer.update_rating(rating)
        self.thumbnail_strip.update_thumbnail(self.image_handler.current_index)

        # Auto advance to next image if configured
        if self.config.get('culling.auto_advance', True):
            self.next_image()

    def toggle_reject(self):
        """Toggle reject status for the current image"""
        rejected = self.image_handler.toggle_reject()
        self.image_viewer.update_rejected(rejected)
        self.thumbnail_strip.update_thumbnail(self.image_handler.current_index)

        # Auto advance to next image if configured
        if self.config.get('culling.auto_advance', True):
            self.next_image()

    def send_to_darktable(self):
        """Send selected images to Darktable"""
        selected_images = self.image_handler.get_selected_images()

        if not selected_images:
            QMessageBox.information(
                self,
                "No Images Selected",
                "No images are selected for sending to Darktable. "
                "Rate images with at least 1 star to select them."
            )
            return

        # Confirm with user
        result = QMessageBox.question(
            self,
            "Send to Darktable",
            f"Send {len(selected_images)} selected images to Darktable?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            success = self.darktable.import_images(selected_images)
            if success:
                self.status_bar.showMessage(f"Sent {len(selected_images)} images to Darktable")
            else:
                self.status_bar.showMessage("Failed to send images to Darktable")

    def backup_selected(self):
        """Backup selected images"""
        selected_images = self.image_handler.get_selected_images()

        if not selected_images:
            QMessageBox.information(
                self,
                "No Images Selected",
                "No images are selected for backup. "
                "Rate images with at least 1 star to select them."
            )
            return

        # Check if backup locations are configured
        if not self.backup_handler.backup_locations:
            result = QMessageBox.question(
                self,
                "No Backup Locations",
                "No backup locations are configured. Would you like to add one now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if result == QMessageBox.StandardButton.Yes:
                self.add_backup_location()
            else:
                return

        # Confirm with user
        result = QMessageBox.question(
            self,
            "Backup Images",
            f"Backup {len(selected_images)} selected images to {len(self.backup_handler.backup_locations)} location(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            results = self.backup_handler.backup_images(selected_images)

            total_files = sum(len(files) for files in results.values())
            if total_files > 0:
                self.status_bar.showMessage(f"Backed up {total_files} files to {len(results)} location(s)")
            else:
                self.status_bar.showMessage("Failed to backup images")

    def add_backup_location(self):
        """Add a new backup location"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Directory",
            os.path.expanduser("~")
        )

        if directory:
            success = self.backup_handler.add_backup_location(directory)
            if success:
                # Update config
                self.config.set('import.backup_locations', self.backup_handler.backup_locations)
                self.config.save()
                self.status_bar.showMessage(f"Added backup location: {directory}")
            else:
                self.status_bar.showMessage(f"Failed to add backup location: {directory}")

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update configuration
            updated_config = dialog.save_settings()
            self.config.update(updated_config)
            self.config.save()

            # Update components with new config
            self.image_handler.blur_threshold = self.config.get('culling.blur_detection_threshold', 100)
            self.darktable.executable = self.config.get('darktable.executable', 'darktable')
            self.backup_handler.backup_locations = self.config.get('import.backup_locations', [])

            # Update shortcuts
            self.setup_shortcuts()

            self.status_bar.showMessage("Settings updated")
