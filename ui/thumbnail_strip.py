"""
Thumbnail strip component for ImCull
"""

import logging
from typing import List, Optional
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QMargins, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush

from core.image_handler import ImageInfo

logger = logging.getLogger('imcull.ui.thumbnail_strip')


class ThumbnailWidget(QLabel):
    """Widget for displaying a single thumbnail"""

    clicked = pyqtSignal(int)  # Signal emitted when thumbnail is clicked, with index

    def __init__(self, index: int, size: int = 100):
        super().__init__()

        self.index = index
        self.thumbnail_size = size
        self.is_selected = False
        self.rating = 0
        self.is_rejected = False
        self.is_blurry = False

        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.setStyleSheet("background-color: #2a2a2a; color: white;")

        # Set minimum size
        self.setMinimumSize(size, size)

    def set_image(self, image: np.ndarray):
        """Set the thumbnail image"""
        if image is None:
            self.clear()
            return

        # Convert numpy array to QImage
        height, width, channels = image.shape
        bytes_per_line = channels * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

        # Scale the image to fit the thumbnail size
        q_image = q_image.scaled(
            self.thumbnail_size,
            self.thumbnail_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Convert QImage to QPixmap and display it
        pixmap = QPixmap.fromImage(q_image)
        self.setPixmap(pixmap)

    def set_selected(self, selected: bool):
        """Set whether this thumbnail is selected"""
        self.is_selected = selected
        self.update_style()

    def set_rating(self, rating: int):
        """Set the rating for this thumbnail"""
        self.rating = rating
        self.update()

    def set_rejected(self, rejected: bool):
        """Set whether this thumbnail is rejected"""
        self.is_rejected = rejected
        self.update()

    def set_blurry(self, blurry: bool):
        """Set whether this thumbnail is potentially blurry"""
        self.is_blurry = blurry
        self.update()

    def update_style(self):
        """Update the widget style based on selection state"""
        if self.is_selected:
            self.setLineWidth(3)
            self.setStyleSheet("background-color: #2a2a2a; border: 3px solid #3daee9;")
        else:
            self.setLineWidth(1)
            self.setStyleSheet("background-color: #2a2a2a; border: 1px solid #555555;")

    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)

        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Custom paint event to overlay rating and rejection status"""
        # Call the parent class's paintEvent to draw the thumbnail
        super().paintEvent(event)

        # Get the painter
        painter = QPainter(self)

        # Draw rating stars
        if self.rating > 0:
            painter.setPen(QPen(QColor(255, 215, 0)))  # Gold color
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)

            stars = "★" * self.rating
            painter.drawText(QRect(5, 5, self.width() - 10, 20), Qt.AlignmentFlag.AlignLeft, stars)

        # Draw rejection X
        if self.is_rejected:
            painter.setPen(QPen(QColor(255, 0, 0), 2))  # Red color
            painter.drawLine(5, 5, self.width() - 5, self.height() - 5)
            painter.drawLine(5, self.height() - 5, self.width() - 5, 5)

        # Draw blur indicator
        if self.is_blurry:
            painter.setPen(QPen(QColor(255, 165, 0)))  # Orange color
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(
                QRect(5, self.height() - 20, self.width() - 10, 15),
                Qt.AlignmentFlag.AlignLeft,
                "Blurry"
            )

        painter.end()


class ThumbnailStrip(QWidget):
    """Widget for displaying a strip of thumbnails"""

    image_selected = pyqtSignal(int)  # Signal emitted when a thumbnail is selected

    def __init__(self, thumbnail_size: int = 150):
        super().__init__()

        self.thumbnail_size = thumbnail_size
        self.thumbnails: List[ThumbnailWidget] = []
        self.images: List[ImageInfo] = []
        self.selected_index = -1

        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add a title label
        title_label = QLabel("Thumbnails")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; color: white; background-color: #333333; padding: 2px;")
        main_layout.addWidget(title_label)

        # Create scroll area for thumbnails
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Set fixed height for the scroll area to make the thumbnail strip compact
        self.scroll_area.setMinimumHeight(self.thumbnail_size + 30)  # Thumbnail size + margins
        self.scroll_area.setMaximumHeight(self.thumbnail_size + 30)

        # Create widget to hold thumbnails
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QHBoxLayout(self.thumbnail_container)
        self.thumbnail_layout.setContentsMargins(5, 5, 5, 5)
        self.thumbnail_layout.setSpacing(5)
        self.thumbnail_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Set the container as the scroll area widget
        self.scroll_area.setWidget(self.thumbnail_container)

        # Add scroll area to main layout
        main_layout.addWidget(self.scroll_area)

    def set_images(self, images: List[ImageInfo]):
        """Set the images to display in the thumbnail strip"""
        # Clear existing thumbnails
        self.clear_thumbnails()

        # Store the images
        self.images = images

        # Create thumbnails for each image
        for i, image in enumerate(images):
            thumbnail = ThumbnailWidget(i, self.thumbnail_size)
            thumbnail.clicked.connect(self.on_thumbnail_clicked)

            # Set thumbnail image if available
            if image.thumbnail is not None:
                thumbnail.set_image(image.thumbnail)

            # Set rating and rejection status
            thumbnail.set_rating(image.rating)
            thumbnail.set_rejected(image.rejected)
            thumbnail.set_blurry(image.is_blurry)

            # Add to layout
            self.thumbnail_layout.addWidget(thumbnail)
            self.thumbnails.append(thumbnail)
            
        # Update the container's minimum width to accommodate all thumbnails
        min_width = (self.thumbnail_size + 10) * len(images) + 20  # thumbnail size + spacing + margins
        self.thumbnail_container.setMinimumWidth(min_width)

    def clear_thumbnails(self):
        """Clear all thumbnails"""
        # Remove all thumbnails from layout
        for thumbnail in self.thumbnails:
            self.thumbnail_layout.removeWidget(thumbnail)
            thumbnail.deleteLater()

        self.thumbnails = []
        self.selected_index = -1

    def update_thumbnail(self, index: int):
        """Update a specific thumbnail"""
        if 0 <= index < len(self.thumbnails) and index < len(self.images):
            image = self.images[index]
            thumbnail = self.thumbnails[index]

            # Update thumbnail image
            if image.thumbnail is not None:
                thumbnail.set_image(image.thumbnail)

            # Update rating and rejection status
            thumbnail.set_rating(image.rating)
            thumbnail.set_rejected(image.rejected)
            thumbnail.set_blurry(image.is_blurry)

    def select_image(self, index: int):
        """Select a specific thumbnail"""
        # Deselect previous selection
        if 0 <= self.selected_index < len(self.thumbnails):
            self.thumbnails[self.selected_index].set_selected(False)

        # Select new thumbnail
        if 0 <= index < len(self.thumbnails):
            self.thumbnails[index].set_selected(True)
            self.selected_index = index

            # Ensure the selected thumbnail is visible
            self.ensure_visible(index)

    def ensure_visible(self, index: int):
        """Ensure the thumbnail at the given index is visible"""
        if 0 <= index < len(self.thumbnails):
            thumbnail = self.thumbnails[index]
            self.scroll_area.ensureWidgetVisible(thumbnail)

    def on_thumbnail_clicked(self, index: int):
        """Handle thumbnail click events"""
        self.select_image(index)
        self.image_selected.emit(index)
