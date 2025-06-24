"""
Image viewer component for ImCull
"""

import logging
from typing import Optional
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsItem, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRectF, QPointF, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush, QTransform, QIcon

from core.image_handler import ImageInfo

logger = logging.getLogger('imcull.ui.image_viewer')


class ImageViewer(QWidget):
    """Widget for displaying and interacting with images"""

    # Signals
    rating_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.current_image: Optional[ImageInfo] = None
        self.zoom_factor = 1.0
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create graphics view for image display
        self.scene = QGraphicsScene()
        self.view = ImageGraphicsView(self.scene)
        
        # Configure view properties
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        
        # Set transformation anchor to ensure proper zooming behavior
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        # Create pixmap item for the image (will be populated in display_image)
        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.scene.addItem(self.pixmap_item)

        # Create initial overlay items
        self._create_overlay_items()

        # Create zoom controls
        self._create_zoom_controls()

        # Add view to layout
        layout.addWidget(self.view)
        
        # Add zoom controls to layout
        layout.addWidget(self.zoom_control_frame)

        # Connect signals
        self.view.zoom_changed.connect(self.on_zoom_changed)

    def set_image(self, image_info: ImageInfo):
        """Set the current image to display"""
        self.current_image = image_info

        if image_info.thumbnail is not None:
            # Use the pre-loaded thumbnail
            self.display_image(image_info.thumbnail)
        else:
            # Load the image
            from core.image_handler import ImageHandler
            handler = ImageHandler()
            img = handler.load_thumbnail(image_info)
            if img is not None:
                self.display_image(img)

        # Update rating display
        self.update_rating(image_info.rating)

        # Update rejected status
        self.update_rejected(image_info.rejected)

        # Update blur warning
        self.update_blur_warning(image_info.is_blurry)

    def display_image(self, image: np.ndarray):
        """Display an image from a numpy array"""
        if image is None:
            logger.error("Cannot display None image")
            return

        try:
            # Convert numpy array to QImage
            height, width, channels = image.shape
            bytes_per_line = channels * width
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

            # Convert QImage to QPixmap
            pixmap = QPixmap.fromImage(q_image)
            
            # Clear the scene first to avoid any artifacts
            self.scene.clear()
            
            # Re-add the pixmap item and overlay items
            self.pixmap_item = QGraphicsPixmapItem()
            self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self.pixmap_item.setPixmap(pixmap)
            self.scene.addItem(self.pixmap_item)
            
            # Recreate overlay items
            self._create_overlay_items()
            
            # Set the scene rect to exactly match the pixmap size
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            
            # Reset view transformation
            self.view.resetTransform()
            
            # Apply fit to view with aspect ratio preservation
            QTimer.singleShot(0, self._apply_fit_to_view)
            
            logger.debug(f"Displayed image with dimensions {width}x{height}")
        except Exception as e:
            logger.error(f"Error displaying image: {e}")
            
    def _create_overlay_items(self):
        """Create overlay items for rating, rejection status, and blur warning"""
        # Create rating overlay
        self.rating_item = self.scene.addText("")
        self.rating_item.setDefaultTextColor(QColor(255, 215, 0))  # Gold color for stars
        font = QFont()
        font.setPointSize(24)
        self.rating_item.setFont(font)
        self.rating_item.setZValue(10)  # Ensure it's on top

        # Create rejected overlay
        self.rejected_item = self.scene.addText("REJECTED")
        self.rejected_item.setDefaultTextColor(QColor(255, 0, 0))  # Red color
        font = QFont()
        font.setPointSize(36)
        font.setBold(True)
        self.rejected_item.setFont(font)
        self.rejected_item.setZValue(10)  # Ensure it's on top
        self.rejected_item.setVisible(False)

        # Create blur warning overlay
        self.blur_item = self.scene.addText("POTENTIALLY BLURRY")
        self.blur_item.setDefaultTextColor(QColor(255, 165, 0))  # Orange color
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.blur_item.setFont(font)
        self.blur_item.setZValue(10)  # Ensure it's on top
        self.blur_item.setVisible(False)
        
        # Update rating, rejected status, and blur warning if we have a current image
        if self.current_image:
            self.update_rating(self.current_image.rating)
            self.update_rejected(self.current_image.rejected)
            self.update_blur_warning(self.current_image.is_blurry)
            
    def _apply_fit_to_view(self):
        """Apply fit to view with proper aspect ratio preservation"""
        if not self.pixmap_item or not self.pixmap_item.pixmap() or self.pixmap_item.pixmap().isNull():
            return
            
        try:
            # Ensure the view has the correct scene rect
            self.view.setSceneRect(self.scene.sceneRect())
            
            # Apply fit in view with aspect ratio preservation
            self.view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            
            # Update zoom factor
            self.view.zoom_factor = self.view.transform().m11()
            
            # Position overlays after fitting
            self._position_overlays()
            
            logger.debug(f"Applied fit to view with zoom factor: {self.view.zoom_factor}")
        except Exception as e:
            logger.error(f"Error applying fit to view: {e}")



    def update_rating(self, rating: int):
        """Update the rating display"""
        if rating == 0:
            self.rating_item.setPlainText("")
        else:
            stars = "★" * rating
            self.rating_item.setPlainText(stars)

        self._position_overlays()

    def update_rejected(self, rejected: bool):
        """Update the rejected status display"""
        self.rejected_item.setVisible(rejected)
        self._position_overlays()

    def update_blur_warning(self, is_blurry):
        """Update the blur warning display"""
        is_blurry_bool = bool(is_blurry)
        self.blur_item.setVisible(is_blurry_bool)
        self._position_overlays()

    def _position_overlays(self):
        """Position the overlay items"""
        if not self.pixmap_item.pixmap() or self.pixmap_item.pixmap().isNull():
            return

        # Get the current view rect
        view_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(view_rect).boundingRect()

        # Position rating in top-left corner
        self.rating_item.setPos(
            scene_rect.left() + 10,
            scene_rect.top() + 10
        )

        # Position rejected text in the center
        rejected_rect = self.rejected_item.boundingRect()
        self.rejected_item.setPos(
            scene_rect.center().x() - rejected_rect.width() / 2,
            scene_rect.center().y() - rejected_rect.height() / 2
        )

        # Position blur warning in bottom-left corner
        blur_rect = self.blur_item.boundingRect()
        self.blur_item.setPos(
            scene_rect.left() + 10,
            scene_rect.bottom() - blur_rect.height() - 10
        )

    def on_zoom_changed(self, zoom_factor: float):
        """Handle zoom factor changes"""
        self.zoom_factor = zoom_factor
        self._position_overlays()
        
        # Update zoom level indicator if it exists
        if hasattr(self, 'zoom_level_label'):
            zoom_percent = int(zoom_factor * 100)
            self.zoom_level_label.setText(f"{zoom_percent}%")

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # Use a timer to delay the fit operation until after the resize is complete
        # This prevents multiple rapid resize operations from causing flickering
        if self.pixmap_item and self.pixmap_item.pixmap() and not self.pixmap_item.pixmap().isNull():
            # Use a longer delay to ensure resize is complete
            QTimer.singleShot(50, self._handle_resize_complete)
    
    def _handle_resize_complete(self):
        """Called after resize is complete to handle view adjustments"""
        # Check if user has manually zoomed
        current_zoom = self.view.zoom_factor
        default_zoom = 1.0
        
        # If user hasn't manually zoomed (or zoom is close to default), refit the view
        if abs(current_zoom - default_zoom) < 0.1:
            self._apply_fit_to_view()
        else:
            # Just update overlay positions if user has manually zoomed
            self._position_overlays()
            
        # Update zoom level indicator if it exists
        if hasattr(self, 'zoom_level_label'):
            zoom_percent = int(self.view.zoom_factor * 100)
            self.zoom_level_label.setText(f"{zoom_percent}%")
        
    def _fit_to_view_with_aspect_ratio(self):
        """Legacy method - redirects to _apply_fit_to_view"""
        self._apply_fit_to_view()
        
    def _create_zoom_controls(self):
        """Create zoom control buttons and indicators"""
        # Create a frame to hold zoom controls
        self.zoom_control_frame = QFrame()
        self.zoom_control_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.zoom_control_frame.setMaximumHeight(40)
        
        # Create layout for zoom controls
        zoom_layout = QHBoxLayout(self.zoom_control_frame)
        zoom_layout.setContentsMargins(5, 0, 5, 0)
        
        # Create zoom out button
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setToolTip("Zoom Out")
        self.zoom_out_button.setMaximumWidth(40)
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        
        # Create zoom level indicator
        self.zoom_level_label = QLabel("100%")
        self.zoom_level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_level_label.setMinimumWidth(60)
        
        # Create zoom in button
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setToolTip("Zoom In")
        self.zoom_in_button.setMaximumWidth(40)
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        
        # Create fit to view button
        self.fit_button = QPushButton("Fit")
        self.fit_button.setToolTip("Fit to View")
        self.fit_button.setMaximumWidth(50)
        self.fit_button.clicked.connect(self._on_fit_to_view)
        
        # Create 100% (actual size) button
        self.actual_size_button = QPushButton("100%")
        self.actual_size_button.setToolTip("Actual Size")
        self.actual_size_button.setMaximumWidth(50)
        self.actual_size_button.clicked.connect(self._on_actual_size)
        
        # Add widgets to layout
        zoom_layout.addStretch()
        zoom_layout.addWidget(self.zoom_out_button)
        zoom_layout.addWidget(self.zoom_level_label)
        zoom_layout.addWidget(self.zoom_in_button)
        zoom_layout.addWidget(self.fit_button)
        zoom_layout.addWidget(self.actual_size_button)
        zoom_layout.addStretch()
    
    def _on_zoom_in(self):
        """Handle zoom in button click"""
        self.view.zoom_factor = min(self.view.zoom_factor + self.view.zoom_step, self.view.max_zoom)
        self.view.setTransform(QTransform().scale(self.view.zoom_factor, self.view.zoom_factor))
        self.view.zoom_changed.emit(self.view.zoom_factor)
    
    def _on_zoom_out(self):
        """Handle zoom out button click"""
        self.view.zoom_factor = max(self.view.zoom_factor - self.view.zoom_step, self.view.min_zoom)
        self.view.setTransform(QTransform().scale(self.view.zoom_factor, self.view.zoom_factor))
        self.view.zoom_changed.emit(self.view.zoom_factor)
    
    def _on_fit_to_view(self):
        """Handle fit to view button click"""
        self.view.fitToView()
    
    def _on_actual_size(self):
        """Handle actual size (100%) button click"""
        self.view.resetZoom()


class ImageGraphicsView(QGraphicsView):
    """Custom QGraphicsView with zoom functionality"""

    # Signals
    zoom_changed = pyqtSignal(float)

    def __init__(self, scene):
        super().__init__(scene)

        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 0.1

        # Enable mouse tracking for smoother interaction
        self.setMouseTracking(True)

        # Set rendering hints for better quality
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )

        # Set viewport update mode
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming"""
        # Get the position before scaling
        old_pos = self.mapToScene(event.position().toPoint())

        # Calculate zoom factor
        zoom_in = event.angleDelta().y() > 0

        if zoom_in:
            self.zoom_factor = min(self.zoom_factor + self.zoom_step, self.max_zoom)
        else:
            self.zoom_factor = max(self.zoom_factor - self.zoom_step, self.min_zoom)

        # Apply the transformation
        self.setTransform(QTransform().scale(self.zoom_factor, self.zoom_factor))

        # Get the position after scaling
        new_pos = self.mapToScene(event.position().toPoint())

        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

        # Emit signal
        self.zoom_changed.emit(self.zoom_factor)

    def keyPressEvent(self, event):
        """Handle key press events"""
        # Pass key events to parent
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press events"""
        # Enable panning with left mouse button
        if event.button() == Qt.MouseButton.LeftButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        # Reset drag mode
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        super().mouseReleaseEvent(event)

    def resetZoom(self):
        """Reset zoom to original size"""
        self.zoom_factor = 1.0
        self.resetTransform()
        self.zoom_changed.emit(self.zoom_factor)

    def fitToView(self):
        """Fit image to view"""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # Update zoom factor based on the current transform
        self.zoom_factor = self.transform().m11()  # Get horizontal scale factor
        self.zoom_changed.emit(self.zoom_factor)
