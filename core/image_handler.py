"""
Image handling functionality for ImCull
"""

import os
import logging
from typing import List, Dict, Tuple, Optional, Set, Any
import cv2
import numpy as np
import rawpy
from PIL import Image
import exifread
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('imcull.image_handler')

# Supported file extensions
RAW_EXTENSIONS = {'.arw', '.cr2', '.cr3', '.nef', '.orf', '.raf', '.rw2', '.dng'}
JPEG_EXTENSIONS = {'.jpg', '.jpeg', '.jpe', '.jif', '.jfif'}
SUPPORTED_EXTENSIONS = RAW_EXTENSIONS.union(JPEG_EXTENSIONS)

@dataclass
class ImageInfo:
    """Class for storing image information"""
    path: str
    filename: str
    base_filename: str  # Filename without extension
    extension: str
    rating: int = 0
    rejected: bool = False
    is_blurry: bool = False
    blur_score: float = 0.0
    paired_file: Optional[str] = None
    metadata: Dict = None
    thumbnail: np.ndarray = None

    @property
    def is_raw(self) -> bool:
        """Check if the file is a RAW file"""
        return self.extension.lower() in RAW_EXTENSIONS

    @property
    def is_jpeg(self) -> bool:
        """Check if the file is a JPEG file"""
        return self.extension.lower() in JPEG_EXTENSIONS


class ImageHandler:
    """Handles image loading, analysis, and management"""

    def __init__(self, blur_threshold: int = 100):
        self.blur_threshold = blur_threshold
        self.images: List[ImageInfo] = []
        self.current_index = 0

    def scan_directory(self, directory: str) -> List[ImageInfo]:
        """
        Scan a directory for supported image files
        Returns a list of ImageInfo objects
        """
        logger.info(f"Scanning directory: {directory}")

        if not os.path.exists(directory):
            logger.error(f"Directory does not exist: {directory}")
            return []

        # Get all files in the directory
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, filename))

        logger.info(f"Found {len(files)} supported image files")

        # Group files by base filename (for RAW+JPEG pairs)
        file_groups = {}
        for file_path in files:
            filename = os.path.basename(file_path)
            base_filename, ext = os.path.splitext(filename)

            # Some cameras add suffixes to JPEGs, try to match them with RAWs
            # For example: IMG_1234.CR2 and IMG_1234.JPG
            clean_base = base_filename.split('_')[0] if '_' in base_filename else base_filename

            if clean_base not in file_groups:
                file_groups[clean_base] = []
            file_groups[clean_base].append(file_path)

        # Create ImageInfo objects
        images = []
        for base_name, file_paths in file_groups.items():
            # If there's only one file, add it directly
            if len(file_paths) == 1:
                file_path = file_paths[0]
                filename = os.path.basename(file_path)
                base_filename, ext = os.path.splitext(filename)

                images.append(ImageInfo(
                    path=file_path,
                    filename=filename,
                    base_filename=base_filename,
                    extension=ext,
                    metadata=self._extract_metadata(file_path)
                ))
            else:
                # If there are multiple files with the same base name, pair them
                raw_file = None
                jpeg_file = None

                for file_path in file_paths:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in RAW_EXTENSIONS:
                        raw_file = file_path
                    elif ext in JPEG_EXTENSIONS:
                        jpeg_file = file_path

                # Add the RAW file as primary if it exists, otherwise add the JPEG
                if raw_file:
                    filename = os.path.basename(raw_file)
                    base_filename, ext = os.path.splitext(filename)

                    images.append(ImageInfo(
                        path=raw_file,
                        filename=filename,
                        base_filename=base_filename,
                        extension=ext,
                        paired_file=jpeg_file,
                        metadata=self._extract_metadata(raw_file)
                    ))
                elif jpeg_file:
                    filename = os.path.basename(jpeg_file)
                    base_filename, ext = os.path.splitext(filename)

                    images.append(ImageInfo(
                        path=jpeg_file,
                        filename=filename,
                        base_filename=base_filename,
                        extension=ext,
                        metadata=self._extract_metadata(jpeg_file)
                    ))

        self.images = images
        return images

    def load_image(self, image_info: ImageInfo) -> np.ndarray:
        """Load an image from disk"""
        try:
            if image_info.is_raw:
                # For RAW files, use rawpy
                with rawpy.imread(image_info.path) as raw:
                    # Convert to RGB
                    rgb = raw.postprocess(use_camera_wb=True, half_size=False, no_auto_bright=False)
                    return rgb
            else:
                # For JPEG files, use OpenCV
                img = cv2.imread(image_info.path)
                if img is None:
                    logger.error(f"Failed to load image: {image_info.path}")
                    return None
                # Convert from BGR to RGB
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.error(f"Error loading image {image_info.path}: {e}")
            return None

    def load_thumbnail(self, image_info: ImageInfo, max_size: Tuple[int, int] = (1600, 1200)) -> np.ndarray:
        """Load a thumbnail of an image while preserving aspect ratio"""
        try:
            if image_info.is_raw:
                # For RAW files, use rawpy to extract embedded thumbnail or process at higher quality
                with rawpy.imread(image_info.path) as raw:
                    try:
                        # Try to get embedded thumbnail
                        thumb = raw.extract_thumb()
                        if thumb.format == rawpy.ThumbFormat.JPEG:
                            # Load the JPEG data
                            thumb_img = cv2.imdecode(
                                np.frombuffer(thumb.data, dtype=np.uint8),
                                cv2.IMREAD_COLOR
                            )
                            # If the thumbnail is too small for focus determination, use full processing
                            if thumb_img.shape[0] < 1000 or thumb_img.shape[1] < 1000:
                                logger.debug(f"Thumbnail too small ({thumb_img.shape}), using full processing")
                                # Use higher quality processing for better focus determination
                                rgb = raw.postprocess(use_camera_wb=True, half_size=False, no_auto_bright=False, demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
                                # Resize while preserving aspect ratio
                                rgb = self._resize_preserve_aspect_ratio(rgb, max_size)
                                return rgb
                            else:
                                # Resize while preserving aspect ratio
                                thumb_img = self._resize_preserve_aspect_ratio(thumb_img, max_size)
                                return cv2.cvtColor(thumb_img, cv2.COLOR_BGR2RGB)
                    except Exception as e:
                        logger.warning(f"Failed to extract thumbnail from RAW, using postprocess: {e}")
                        # If thumbnail extraction fails, use higher quality processing
                        rgb = raw.postprocess(use_camera_wb=True, half_size=False, no_auto_bright=False, demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
                        # Resize while preserving aspect ratio
                        rgb = self._resize_preserve_aspect_ratio(rgb, max_size)
                        return rgb
            else:
                # For JPEG files, use OpenCV with higher resolution
                img = cv2.imread(image_info.path)
                if img is None:
                    logger.error(f"Failed to load thumbnail: {image_info.path}")
                    return None
                # Resize while preserving aspect ratio
                img = self._resize_preserve_aspect_ratio(img, max_size)
                # Convert from BGR to RGB
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.error(f"Error loading thumbnail {image_info.path}: {e}")
            return None
            
    def _resize_preserve_aspect_ratio(self, image: np.ndarray, max_size: Tuple[int, int]) -> np.ndarray:
        """Resize an image while preserving its aspect ratio"""
        if image is None:
            return None
            
        # Get original dimensions
        h, w = image.shape[:2]
        max_w, max_h = max_size
        
        # Calculate aspect ratios
        aspect_ratio = w / h
        target_aspect_ratio = max_w / max_h
        
        # Determine new dimensions while preserving aspect ratio
        if aspect_ratio > target_aspect_ratio:
            # Image is wider than target, constrain by width
            new_w = max_w
            new_h = int(new_w / aspect_ratio)
        else:
            # Image is taller than target, constrain by height
            new_h = max_h
            new_w = int(new_h * aspect_ratio)
        
        # Only resize if the image is larger than the target size
        if w > new_w or h > new_h:
            logger.debug(f"Resizing image from {w}x{h} to {new_w}x{new_h}")
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            # If image is already smaller than max_size, return as is
            return image

    def detect_blur(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if an image is blurry using the Laplacian variance method
        Returns a tuple of (is_blurry, blur_score)
        """
        if image is None:
            return True, 0.0

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Calculate the Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        score = laplacian.var()

        # Determine if the image is blurry based on the threshold
        is_blurry = score < self.blur_threshold

        return is_blurry, score

    def analyze_image(self, image_info: ImageInfo) -> ImageInfo:
        """Analyze an image for blur detection and other properties"""
        # Load a thumbnail for analysis
        thumbnail = self.load_thumbnail(image_info)
        if thumbnail is not None:
            # Detect blur
            is_blurry, blur_score = self.detect_blur(thumbnail)
            image_info.is_blurry = is_blurry
            image_info.blur_score = blur_score
            image_info.thumbnail = thumbnail

        return image_info

    def _extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from an image file with multiple fallback methods"""
        metadata = {}
        ext = os.path.splitext(file_path)[1].lower()
        
        # Try exifread first (works well for JPEGs)
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                
                # If we got some tags, extract them
                if tags:
                    # Extract basic metadata
                    if 'EXIF DateTimeOriginal' in tags:
                        metadata['DateTimeOriginal'] = str(tags['EXIF DateTimeOriginal'])
                    elif 'Image DateTime' in tags:
                        metadata['DateTime'] = str(tags['Image DateTime'])
                        
                    if 'EXIF ExposureTime' in tags:
                        metadata['ExposureTime'] = tags['EXIF ExposureTime'].values
                        
                    if 'EXIF FNumber' in tags:
                        metadata['FNumber'] = tags['EXIF FNumber'].values
                        
                    if 'EXIF ISOSpeedRatings' in tags:
                        metadata['ISOSpeedRatings'] = tags['EXIF ISOSpeedRatings'].values
                        
                    if 'EXIF FocalLength' in tags:
                        metadata['FocalLength'] = tags['EXIF FocalLength'].values
                        
                    if 'Image Model' in tags:
                        metadata['Model'] = str(tags['Image Model'])
                        
                    if 'Image Make' in tags:
                        metadata['Make'] = str(tags['Image Make'])
                        
                    # Extract GPS information
                    for key in tags:
                        if key.startswith('GPS'):
                            metadata[key] = tags[key].values if hasattr(tags[key], 'values') else str(tags[key])
                            
                    # Extract image dimensions
                    if 'EXIF ExifImageWidth' in tags and 'EXIF ExifImageHeight' in tags:
                        metadata['ExifImageWidth'] = int(str(tags['EXIF ExifImageWidth']))
                        metadata['ExifImageHeight'] = int(str(tags['EXIF ExifImageHeight']))
                    elif 'Image ImageWidth' in tags and 'Image ImageLength' in tags:
                        metadata['ExifImageWidth'] = int(str(tags['Image ImageWidth']))
                        metadata['ExifImageHeight'] = int(str(tags['Image ImageLength']))
                        
                    # Extract color space
                    if 'EXIF ColorSpace' in tags:
                        metadata['ColorSpace'] = tags['EXIF ColorSpace'].values
                        
                    # Extract lens information
                    if 'EXIF LensModel' in tags:
                        metadata['LensModel'] = str(tags['EXIF LensModel'])
                    elif 'EXIF LensInfo' in tags:
                        metadata['Lens'] = str(tags['EXIF LensInfo'])
        except Exception as e:
            logger.warning(f"Exifread failed for {file_path}: {e}")
            
        # If exifread didn't get much metadata and this is a RAW file, try rawpy
        if ext in RAW_EXTENSIONS:
            try:
                logger.debug(f"Trying rawpy for metadata extraction from {file_path}")
                with rawpy.imread(file_path) as raw:
                    # Get basic metadata from rawpy
                    if hasattr(raw, 'camera_model'):
                        metadata['Model'] = raw.camera_model
                    if hasattr(raw, 'camera_manufacturer'):
                        metadata['Make'] = raw.camera_manufacturer
                    
                    # Get image dimensions
                    if hasattr(raw, 'sizes'):
                        metadata['ExifImageWidth'] = raw.sizes.width
                        metadata['ExifImageHeight'] = raw.sizes.height
                    
                    # Get color description
                    if hasattr(raw, 'color_desc'):
                        metadata['ColorSpace'] = raw.color_desc.decode('utf-8', errors='ignore')
                    
                    # Get raw metadata
                    if hasattr(raw, 'raw_type'):
                        metadata['RawType'] = raw.raw_type
                    
                    # Get other available raw attributes
                    if hasattr(raw, 'raw_image_visible'):
                        h, w = raw.raw_image_visible.shape
                        metadata['RawDimensions'] = f"{w} × {h}"
                    
                    # Extract thumbnail and get its metadata
                    try:
                        thumb = raw.extract_thumb()
                        if thumb.format == rawpy.ThumbFormat.JPEG:
                            # Try to extract EXIF from the thumbnail
                            import io
                            thumb_img = Image.open(io.BytesIO(thumb.data))
                            
                            # Store thumbnail dimensions
                            if not metadata.get('ExifImageWidth') or not metadata.get('ExifImageHeight'):
                                metadata['ExifImageWidth'], metadata['ExifImageHeight'] = thumb_img.size
                                metadata['ThumbSource'] = 'Embedded JPEG'
                            
                            # Extract EXIF data from thumbnail
                            if hasattr(thumb_img, '_getexif') and thumb_img._getexif():
                                exif = thumb_img._getexif()
                                # Map standard EXIF tags
                                if exif:
                                    exif_tags = {
                                        0x010F: 'Make',
                                        0x0110: 'Model',
                                        0x8827: 'ISOSpeedRatings',
                                        0x829A: 'ExposureTime',
                                        0x829D: 'FNumber',
                                        0x920A: 'FocalLength',
                                        0x9003: 'DateTimeOriginal',
                                        0x8822: 'ExposureProgram',
                                        0x9204: 'ExposureBiasValue',
                                        0x9207: 'MeteringMode',
                                        0x9209: 'Flash',
                                        0xA002: 'ExifImageWidth',
                                        0xA003: 'ExifImageHeight',
                                        0xA301: 'SceneType',
                                        0xA402: 'ExposureMode',
                                        0xA403: 'WhiteBalance',
                                        0xA406: 'SceneCaptureType'
                                    }
                                    
                                    for tag, tag_name in exif_tags.items():
                                        if tag in exif and not metadata.get(tag_name):
                                            metadata[tag_name] = exif[tag]
                            
                            # If we still don't have basic metadata, try to get it from the thumbnail's info dict
                            if hasattr(thumb_img, 'info'):
                                for key, value in thumb_img.info.items():
                                    if key not in metadata and key != 'exif':
                                        metadata[key] = value
                    except Exception as e:
                        logger.debug(f"Thumbnail metadata extraction failed: {e}")
            except Exception as e:
                logger.warning(f"Rawpy metadata extraction failed for {file_path}: {e}")
                
        # If we still don't have dimensions, try to get them from PIL
        if not metadata.get('ExifImageWidth') or not metadata.get('ExifImageHeight'):
            try:
                # Only attempt to open non-RAW files with PIL directly
                if ext not in RAW_EXTENSIONS:
                    with Image.open(file_path) as img:
                        metadata['ExifImageWidth'], metadata['ExifImageHeight'] = img.size
            except Exception as e:
                logger.debug(f"PIL failed to get dimensions for {file_path}: {e}")
                
        # Add file information
        try:
            file_stat = os.stat(file_path)
            metadata['FileSize'] = file_stat.st_size
            metadata['FileModTime'] = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"Failed to get file stats for {file_path}: {e}")
            
        return metadata

    def get_current_image(self) -> Optional[ImageInfo]:
        """Get the current image"""
        if not self.images or self.current_index >= len(self.images):
            return None
        return self.images[self.current_index]

    def next_image(self) -> Optional[ImageInfo]:
        """Move to the next image and return it"""
        if not self.images:
            return None

        self.current_index = (self.current_index + 1) % len(self.images)
        return self.get_current_image()

    def prev_image(self) -> Optional[ImageInfo]:
        """Move to the previous image and return it"""
        if not self.images:
            return None

        self.current_index = (self.current_index - 1) % len(self.images)
        return self.get_current_image()

    def set_rating(self, rating: int) -> None:
        """Set the rating for the current image"""
        if not self.images:
            return

        self.images[self.current_index].rating = rating

    def toggle_reject(self) -> bool:
        """Toggle the reject status for the current image"""
        if not self.images:
            return False

        self.images[self.current_index].rejected = not self.images[self.current_index].rejected
        return self.images[self.current_index].rejected

    def get_selected_images(self, min_rating: int = 1) -> List[ImageInfo]:
        """Get all images with a rating >= min_rating and not rejected"""
        return [img for img in self.images if img.rating >= min_rating and not img.rejected]

    def get_rejected_images(self) -> List[ImageInfo]:
        """Get all rejected images"""
        return [img for img in self.images if img.rejected]
