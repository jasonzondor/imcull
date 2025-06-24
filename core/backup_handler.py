"""
Backup functionality for ImCull
"""

import os
import logging
import shutil
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from core.image_handler import ImageInfo

logger = logging.getLogger('imcull.backup')


class BackupHandler:
    """Handles backing up selected photos to multiple locations"""

    def __init__(self, backup_locations: List[str] = None):
        self.backup_locations = backup_locations or []
        self._validate_backup_locations()

    def _validate_backup_locations(self) -> None:
        """Validate that backup locations exist and are writable"""
        valid_locations = []
        for location in self.backup_locations:
            path = Path(os.path.expanduser(location))
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created backup location: {path}")
                    valid_locations.append(str(path))
                except Exception as e:
                    logger.error(f"Failed to create backup location {path}: {e}")
            elif not os.access(path, os.W_OK):
                logger.error(f"Backup location not writable: {path}")
            else:
                valid_locations.append(str(path))

        self.backup_locations = valid_locations

    def add_backup_location(self, location: str) -> bool:
        """Add a new backup location"""
        path = Path(os.path.expanduser(location))
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created backup location: {path}")
            except Exception as e:
                logger.error(f"Failed to create backup location {path}: {e}")
                return False

        if not os.access(path, os.W_OK):
            logger.error(f"Backup location not writable: {path}")
            return False

        if str(path) not in self.backup_locations:
            self.backup_locations.append(str(path))
            return True

        return False

    def remove_backup_location(self, location: str) -> bool:
        """Remove a backup location"""
        if location in self.backup_locations:
            self.backup_locations.remove(location)
            return True
        return False

    def backup_images(self, images: List[ImageInfo], create_date_subfolder: bool = True) -> Dict[str, List[str]]:
        """
        Backup images to all configured backup locations
        Returns a dictionary of {backup_location: [successful_backups]}
        """
        if not images:
            logger.warning("No images to backup")
            return {}

        if not self.backup_locations:
            logger.warning("No backup locations configured")
            return {}

        results = {}

        for location in self.backup_locations:
            successful_backups = []

            # Create date subfolder if requested
            target_dir = location
            if create_date_subfolder:
                today = datetime.now().strftime('%Y-%m-%d')
                target_dir = os.path.join(location, today)
                os.makedirs(target_dir, exist_ok=True)

            # Copy each image
            for img in images:
                try:
                    # Copy the main file
                    dest_path = os.path.join(target_dir, img.filename)
                    shutil.copy2(img.path, dest_path)
                    successful_backups.append(dest_path)

                    # Copy paired file if it exists
                    if img.paired_file:
                        paired_filename = os.path.basename(img.paired_file)
                        paired_dest_path = os.path.join(target_dir, paired_filename)
                        shutil.copy2(img.paired_file, paired_dest_path)
                        successful_backups.append(paired_dest_path)
                except Exception as e:
                    logger.error(f"Error backing up {img.path} to {target_dir}: {e}")

            results[location] = successful_backups
            logger.info(f"Backed up {len(successful_backups)} files to {target_dir}")

        return results
