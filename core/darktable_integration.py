"""
Darktable integration for ImCull
"""

import os
import logging
import subprocess
from typing import List, Optional

from core.image_handler import ImageInfo

logger = logging.getLogger('imcull.darktable')


class DarktableIntegration:
    """Handles integration with Darktable"""

    def __init__(self, executable: str = 'darktable'):
        self.executable = executable
        self._check_darktable_available()

    def _check_darktable_available(self) -> bool:
        """Check if Darktable is available"""
        try:
            result = subprocess.run(
                [self.executable, '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode == 0:
                logger.info(f"Darktable found: {result.stdout.strip()}")
                return True
            else:
                logger.warning(f"Darktable not found or error: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error checking Darktable: {e}")
            return False

    def import_images(self, images: List[ImageInfo]) -> bool:
        """Import images to Darktable"""
        if not images:
            logger.warning("No images to import to Darktable")
            return False

        try:
            # Collect all image paths
            image_paths = []
            for img in images:
                image_paths.append(img.path)
                # If there's a paired file, add it too
                if img.paired_file:
                    image_paths.append(img.paired_file)

            # Launch Darktable with the images
            logger.info(f"Importing {len(image_paths)} images to Darktable")
            subprocess.Popen(
                [self.executable] + image_paths,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except Exception as e:
            logger.error(f"Error importing images to Darktable: {e}")
            return False

    def open_darktable(self) -> bool:
        """Open Darktable without importing any images"""
        try:
            subprocess.Popen(
                [self.executable],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except Exception as e:
            logger.error(f"Error opening Darktable: {e}")
            return False
