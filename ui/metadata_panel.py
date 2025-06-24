"""
Metadata panel component for ImCull
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont

from core.image_handler import ImageInfo

logger = logging.getLogger('imcull.ui.metadata_panel')


class MetadataPanel(QWidget):
    """Widget for displaying image metadata"""

    def __init__(self):
        super().__init__()

        self.current_image: Optional[ImageInfo] = None
        self.metadata_labels: Dict[str, QLabel] = {}

        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        # Create main layout
        main_layout = QVBoxLayout(self)

        # Create scroll area for metadata
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create container widget for metadata
        self.metadata_container = QWidget()
        self.metadata_layout = QGridLayout(self.metadata_container)
        self.metadata_layout.setContentsMargins(10, 10, 10, 10)
        self.metadata_layout.setSpacing(5)

        # Set the container as the scroll area widget
        self.scroll_area.setWidget(self.metadata_container)

        # Add scroll area to main layout
        main_layout.addWidget(self.scroll_area)

        # Add title
        title_label = QLabel("Image Metadata")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.insertWidget(0, title_label)

        # Initialize metadata fields
        self._init_metadata_fields()

    def _init_metadata_fields(self):
        """Initialize metadata fields with empty values"""
        # Define metadata fields to display
        metadata_fields = [
            # Basic file info
            ("filename", "Filename"),
            ("filepath", "Path"),
            ("filesize", "File Size"),
            ("filetype", "File Type"),

            # Image properties
            ("dimensions", "Dimensions"),
            ("resolution", "Resolution"),
            ("colorspace", "Color Space"),

            # Camera settings
            ("camera", "Camera"),
            ("lens", "Lens"),
            ("focal_length", "Focal Length"),
            ("aperture", "Aperture"),
            ("shutter_speed", "Shutter Speed"),
            ("iso", "ISO"),

            # Other metadata
            ("datetime", "Date/Time"),
            ("gps", "GPS Coordinates"),
            ("raw_info", "RAW File Info"),

            # ImCull specific
            ("rating", "Rating"),
            ("rejected", "Rejected"),
            ("blur_score", "Blur Score"),
            ("is_blurry", "Potentially Blurry"),
            ("has_raw", "Has RAW"),
            ("raw_path", "RAW Path"),
        ]

        # Create labels for each field
        row = 0
        for field_id, field_name in metadata_fields:
            # Create name label
            name_label = QLabel(f"{field_name}:")
            name_font = QFont()
            name_font.setBold(True)
            name_label.setFont(name_font)
            name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Create value label
            value_label = QLabel("-")
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            value_label.setWordWrap(True)

            # Add to layout
            self.metadata_layout.addWidget(name_label, row, 0)
            self.metadata_layout.addWidget(value_label, row, 1)

            # Store value label for later updates
            self.metadata_labels[field_id] = value_label

            row += 1

        # Add stretch to bottom
        self.metadata_layout.setRowStretch(row, 1)

        # Make the first column fixed width
        self.metadata_layout.setColumnStretch(0, 0)
        self.metadata_layout.setColumnStretch(1, 1)

    def set_image(self, image_info: ImageInfo):
        """Set the current image and update metadata display"""
        if image_info is None:
            self.clear()
            return
        
        try:
            logger.debug(f"Setting metadata for image: {image_info.filename}")
            self.current_image = image_info

            # Update basic file info
            self._update_label("filename", image_info.filename)
            self._update_label("filepath", image_info.path)

            # Format file size - handle missing attributes
            filesize = "-"
            if hasattr(image_info, 'filesize') and image_info.filesize is not None:
                filesize = self._format_file_size(image_info.filesize)
            self._update_label("filesize", filesize)
            
            # Blur score
            blur_score = "-"
            if hasattr(image_info, 'blur_score') and image_info.blur_score is not None:
                blur_score = f"{image_info.blur_score:.2f}"
            self._update_label("blur_score", blur_score)
            
            # Ensure the blur score is visible in the UI
            # This is needed because the label might be overwritten elsewhere
            QTimer.singleShot(10, lambda: self._update_label("blur_score", blur_score))
            
            # File type
            filetype = "-"
            if hasattr(image_info, 'filetype') and image_info.filetype:
                filetype = image_info.filetype.upper()
            elif hasattr(image_info, 'extension') and image_info.extension:
                # Use extension as filetype if filetype is not available
                filetype = image_info.extension.upper().lstrip('.')
            self._update_label("filetype", filetype)

            # Dimensions - try multiple sources
            dimensions = "-"
            if hasattr(image_info, 'width') and hasattr(image_info, 'height') and image_info.width and image_info.height:
                dimensions = f"{image_info.width} × {image_info.height}"
            elif image_info.metadata and 'ExifImageWidth' in image_info.metadata and 'ExifImageHeight' in image_info.metadata:
                dimensions = f"{image_info.metadata['ExifImageWidth']} × {image_info.metadata['ExifImageHeight']}"
            elif hasattr(image_info, 'thumbnail') and image_info.thumbnail is not None:
                # Extract dimensions from thumbnail as last resort
                height, width = image_info.thumbnail.shape[:2]
                dimensions = f"{width} × {height} (from thumbnail)"
            self._update_label("dimensions", dimensions)

            # Check if metadata is available
            if not hasattr(image_info, 'metadata') or not image_info.metadata:
                logger.warning(f"No metadata available for {image_info.filename}")
                # Clear remaining fields
                for field in ["resolution", "colorspace", "camera", "lens", "focal_length", 
                             "aperture", "shutter_speed", "iso", "datetime", "gps", "raw_info"]:
                    self._update_label(field, "-")
                
                # Try to get some basic info from the thumbnail
                if hasattr(image_info, 'thumbnail') and image_info.thumbnail is not None:
                    # Extract dimensions from thumbnail
                    height, width = image_info.thumbnail.shape[:2]
                    self._update_label("dimensions", f"{width} × {height} (from thumbnail)")
                    
                    # Add file info
                    try:
                        file_stat = os.stat(image_info.path)
                        self._update_label("filesize", self._format_file_size(file_stat.st_size))
                        self._update_label("datetime", datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'))
                    except Exception as e:
                        logger.warning(f"Failed to get file stats: {e}")
                return

            # Resolution
            resolution = "-"
            if 'XResolution' in image_info.metadata and 'YResolution' in image_info.metadata:
                try:
                    x_res = image_info.metadata['XResolution']
                    y_res = image_info.metadata['YResolution']
                    if isinstance(x_res, tuple) and isinstance(y_res, tuple):
                        x_res = x_res[0] / x_res[1] if x_res[1] != 0 else 0
                        y_res = y_res[0] / y_res[1] if y_res[1] != 0 else 0
                        resolution = f"{x_res:.0f} × {y_res:.0f} dpi"
                except (ZeroDivisionError, TypeError) as e:
                    logger.warning(f"Error calculating resolution: {e}")
            self._update_label("resolution", resolution)

            # Color space
            colorspace = image_info.metadata.get('ColorSpace', '-')
            if isinstance(colorspace, int):
                # Convert numeric color space to string
                if colorspace == 1:
                    colorspace = "sRGB"
                elif colorspace == 2:
                    colorspace = "Adobe RGB"
                elif colorspace == 65535:
                    colorspace = "Uncalibrated"
            self._update_label("colorspace", colorspace)

            # Camera info
            camera = "-"
            make = image_info.metadata.get('Make', '')
            model = image_info.metadata.get('Model', '')
            if make and model:
                # Remove redundant make name from model if present
                if model.startswith(make):
                    camera = model
                else:
                    camera = f"{make} {model}"
            elif model:
                camera = model
            elif make:
                camera = make
                
            # For RAW files, add raw type if available
            if image_info.is_raw and 'RawType' in image_info.metadata:
                camera = f"{camera} ({image_info.metadata['RawType']})"
                
            self._update_label("camera", camera)

            # Lens info
            lens = image_info.metadata.get('LensModel', image_info.metadata.get('Lens', '-'))
            self._update_label("lens", lens)

            # Focal length
            focal_length = "-"
            if 'FocalLength' in image_info.metadata:
                try:
                    fl = image_info.metadata['FocalLength']
                    if isinstance(fl, tuple) and len(fl) == 2 and fl[1] != 0:
                        focal_length = f"{fl[0] / fl[1]:.1f} mm"
                    elif isinstance(fl, (int, float)):
                        focal_length = f"{fl:.1f} mm"
                    else:
                        focal_length = f"{fl} mm"
                except (ZeroDivisionError, TypeError) as e:
                    logger.warning(f"Error calculating focal length: {e}")
            self._update_label("focal_length", focal_length)

            # Aperture
            aperture = "-"
            if 'FNumber' in image_info.metadata:
                try:
                    f_number = image_info.metadata['FNumber']
                    if isinstance(f_number, tuple) and len(f_number) == 2 and f_number[1] != 0:
                        aperture = f"f/{f_number[0] / f_number[1]:.1f}"
                    elif isinstance(f_number, (int, float)):
                        aperture = f"f/{f_number:.1f}"
                    else:
                        aperture = f"f/{f_number}"
                except (ZeroDivisionError, TypeError) as e:
                    logger.warning(f"Error calculating aperture: {e}")
            self._update_label("aperture", aperture)

            # Shutter speed
            shutter_speed = "-"
            if 'ExposureTime' in image_info.metadata:
                try:
                    exp_time = image_info.metadata['ExposureTime']
                    if isinstance(exp_time, tuple) and len(exp_time) == 2:
                        if exp_time[1] == 0:
                            shutter_speed = "-"
                        elif exp_time[1] == 1:
                            shutter_speed = f"{exp_time[0]} sec"
                        else:
                            # Format as fraction for faster shutter speeds
                            if exp_time[0] < exp_time[1]:
                                shutter_speed = f"1/{exp_time[1]/exp_time[0]:.0f} sec"
                            else:
                                shutter_speed = f"{exp_time[0]/exp_time[1]:.1f} sec"
                    elif isinstance(exp_time, (int, float)):
                        if exp_time < 1:
                            shutter_speed = f"1/{1/exp_time:.0f} sec"
                        else:
                            shutter_speed = f"{exp_time:.1f} sec"
                    else:
                        shutter_speed = f"{exp_time} sec"
                except (ZeroDivisionError, TypeError) as e:
                    logger.warning(f"Error calculating shutter speed: {e}")
            self._update_label("shutter_speed", shutter_speed)

            # ISO
            iso = image_info.metadata.get("ISOSpeedRatings", "-")
            if isinstance(iso, (list, tuple)) and len(iso) > 0:
                iso = iso[0]
            self._update_label("iso", str(iso))

            # Date and time
            date_time = image_info.metadata.get("DateTimeOriginal") or image_info.metadata.get("DateTime") or image_info.metadata.get("FileModTime", "-")
            self._update_label("datetime", date_time)

            # GPS coordinates
            gps_info = "-"
            if all(k in image_info.metadata for k in ['GPSLatitude', 'GPSLatitudeRef', 'GPSLongitude', 'GPSLongitudeRef']):
                try:
                    lat = self._convert_gps_coords(image_info.metadata['GPSLatitude'])
                    lat_ref = image_info.metadata['GPSLatitudeRef']
                    lon = self._convert_gps_coords(image_info.metadata['GPSLongitude'])
                    lon_ref = image_info.metadata['GPSLongitudeRef']
                    
                    if lat is not None and lon is not None and lat_ref and lon_ref:
                        lat_decimal = lat * (-1 if lat_ref == 'S' else 1)
                        lon_decimal = lon * (-1 if lon_ref == 'W' else 1)
                        gps_info = f"{lat_decimal:.6f}, {lon_decimal:.6f}"
                except Exception as e:
                    logger.warning(f"Error processing GPS coordinates: {e}")
            self._update_label("gps", gps_info)

            # RAW file info
            raw_info = "-"
            if image_info.is_raw:
                # For RAW files, show detailed raw information
                raw_details = []
                if 'RawDimensions' in image_info.metadata:
                    raw_details.append(f"Dimensions: {image_info.metadata['RawDimensions']}")
                if 'RawType' in image_info.metadata:
                    raw_details.append(f"Type: {image_info.metadata['RawType']}")
                
                if raw_details:
                    raw_info = "; ".join(raw_details)
            elif hasattr(image_info, 'paired_file') and image_info.paired_file:
                raw_info = f"Paired with: {image_info.paired_file}"
            elif hasattr(image_info, 'raw_path') and image_info.raw_path:
                raw_info = f"RAW file: {image_info.raw_path}"
            self._update_label("raw_info", raw_info)
            
            logger.debug(f"Successfully updated metadata for {image_info.filename}")
            
        except Exception as e:
            logger.error(f"Error setting image metadata: {e}")
            self.clear()

        # Update rejection status
        self._update_label("rejected", "Yes" if image_info.rejected else "No")
        
        # Update blur score - this is the single place where blur score should be set
        blur_score = "-"
        if hasattr(image_info, 'blur_score') and image_info.blur_score is not None:
            blur_score = f"{image_info.blur_score:.2f}"
        self._update_label("blur_score", blur_score)

        # Update blurry status
        self._update_label("is_blurry", "Yes" if image_info.is_blurry else "No")
        
        # Handle paired RAW file information
        has_raw = False
        raw_path = "-"
        
        if hasattr(image_info, 'paired_file') and image_info.paired_file:
            has_raw = True
            raw_path = image_info.paired_file
        elif hasattr(image_info, 'raw_path') and image_info.raw_path:
            has_raw = True
            raw_path = image_info.raw_path
            
        self._update_label("has_raw", "Yes" if has_raw else "No")
        self._update_label("raw_path", raw_path)

    def clear(self):
        """Clear all metadata fields"""
        for label in self.metadata_labels.values():
            label.setText("-")

    def _update_label(self, field_id: str, value: Any):
        """Update a metadata field label with a value"""
        if field_id in self.metadata_labels:
            try:
                self.metadata_labels[field_id].setText(str(value))
            except Exception as e:
                logger.error(f"Error updating label {field_id}: {e}")
                self.metadata_labels[field_id].setText("-")
        else:
            logger.warning(f"Field ID '{field_id}' not found in metadata_labels")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in bytes to human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _convert_gps_coords(self, coords):
        """Convert GPS coordinates from degrees, minutes, seconds to decimal degrees"""
        if isinstance(coords, tuple) and len(coords) == 3:
            degrees = coords[0]
            minutes = coords[1]
            seconds = coords[2]

            # Handle different formats
            if isinstance(degrees, tuple) and len(degrees) == 2:
                degrees = degrees[0] / degrees[1]

            if isinstance(minutes, tuple) and len(minutes) == 2:
                minutes = minutes[0] / minutes[1]

            if isinstance(seconds, tuple) and len(seconds) == 2:
                seconds = seconds[0] / seconds[1]

            return degrees + (minutes / 60.0) + (seconds / 3600.0)

        return coords
