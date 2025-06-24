"""
Settings dialog component for ImCull
"""

import logging
import os
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QPushButton, QFileDialog, QTabWidget, QWidget,
    QFormLayout, QGroupBox, QComboBox, QDialogButtonBox,
    QMessageBox
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal

from core.config import Config

logger = logging.getLogger('imcull.ui.settings_dialog')

class SettingsDialog(QDialog):
    """Dialog for configuring application settings"""
    
    # Signal emitted when settings are saved
    settings_saved = pyqtSignal(dict)
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        
        self.config = config
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("ImCull Settings")
        self.resize(600, 500)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.general_tab = self.create_general_tab()
        self.culling_tab = self.create_culling_tab()
        self.darktable_tab = self.create_darktable_tab()
        self.backup_tab = self.create_backup_tab()
        self.shortcuts_tab = self.create_shortcuts_tab()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.culling_tab, "Culling")
        self.tab_widget.addTab(self.darktable_tab, "Darktable")
        self.tab_widget.addTab(self.backup_tab, "Backup")
        self.tab_widget.addTab(self.shortcuts_tab, "Shortcuts")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Add button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Apply | 
            QDialogButtonBox.StandardButton.Reset
        )
        
        # Connect button signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_settings)
        self.button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset_settings)
        
        # Add button box to main layout
        main_layout.addWidget(self.button_box)
    
    def create_general_tab(self) -> QWidget:
        """Create the general settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Directories group
        directories_group = QGroupBox("Directories")
        directories_layout = QFormLayout(directories_group)
        
        # Default import directory
        self.import_dir_edit = QLineEdit()
        self.import_dir_button = QPushButton("Browse...")
        self.import_dir_button.clicked.connect(lambda: self.browse_directory(self.import_dir_edit, "Select Import Directory"))
        
        import_dir_layout = QHBoxLayout()
        import_dir_layout.addWidget(self.import_dir_edit)
        import_dir_layout.addWidget(self.import_dir_button)
        directories_layout.addRow("Default Import Directory:", import_dir_layout)
        
        # UI group
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout(ui_group)
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        ui_layout.addRow("Theme:", self.theme_combo)
        
        # Thumbnail size
        self.thumbnail_size_spin = QSpinBox()
        self.thumbnail_size_spin.setRange(50, 300)
        self.thumbnail_size_spin.setSingleStep(10)
        self.thumbnail_size_spin.setSuffix(" px")
        ui_layout.addRow("Thumbnail Size:", self.thumbnail_size_spin)
        
        # Add groups to layout
        layout.addWidget(directories_group)
        layout.addWidget(ui_group)
        layout.addStretch()
        
        return tab
    
    def create_culling_tab(self) -> QWidget:
        """Create the culling settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Blur detection group
        blur_group = QGroupBox("Blur Detection")
        blur_layout = QFormLayout(blur_group)
        
        # Blur threshold
        self.blur_threshold_spin = QDoubleSpinBox()
        self.blur_threshold_spin.setRange(0.1, 1000.0)
        self.blur_threshold_spin.setSingleStep(1.0)
        self.blur_threshold_spin.setDecimals(1)
        blur_layout.addRow("Blur Threshold:", self.blur_threshold_spin)
        
        # Enable blur detection
        self.enable_blur_check = QCheckBox("Enable automatic blur detection")
        blur_layout.addRow("", self.enable_blur_check)
        
        # Rating group
        rating_group = QGroupBox("Rating")
        rating_layout = QFormLayout(rating_group)
        
        # Default rating
        self.default_rating_spin = QSpinBox()
        self.default_rating_spin.setRange(0, 3)
        rating_layout.addRow("Default Rating:", self.default_rating_spin)
        
        # Add groups to layout
        layout.addWidget(blur_group)
        layout.addWidget(rating_group)
        layout.addStretch()
        
        return tab
    
    def create_darktable_tab(self) -> QWidget:
        """Create the Darktable settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Darktable group
        darktable_group = QGroupBox("Darktable Integration")
        darktable_layout = QFormLayout(darktable_group)
        
        # Darktable executable
        self.darktable_exec_edit = QLineEdit()
        self.darktable_exec_button = QPushButton("Browse...")
        self.darktable_exec_button.clicked.connect(lambda: self.browse_file(self.darktable_exec_edit, "Select Darktable Executable"))
        
        darktable_exec_layout = QHBoxLayout()
        darktable_exec_layout.addWidget(self.darktable_exec_edit)
        darktable_exec_layout.addWidget(self.darktable_exec_button)
        darktable_layout.addRow("Darktable Executable:", darktable_exec_layout)
        
        # Auto-import to Darktable
        self.auto_import_check = QCheckBox("Automatically import selected images to Darktable")
        darktable_layout.addRow("", self.auto_import_check)
        
        # Add groups to layout
        layout.addWidget(darktable_group)
        layout.addStretch()
        
        return tab
    
    def create_backup_tab(self) -> QWidget:
        """Create the backup settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Primary backup group
        primary_group = QGroupBox("Primary Backup Location")
        primary_layout = QFormLayout(primary_group)
        
        # Primary backup directory
        self.primary_backup_edit = QLineEdit()
        self.primary_backup_button = QPushButton("Browse...")
        self.primary_backup_button.clicked.connect(lambda: self.browse_directory(self.primary_backup_edit, "Select Primary Backup Directory"))
        
        primary_backup_layout = QHBoxLayout()
        primary_backup_layout.addWidget(self.primary_backup_edit)
        primary_backup_layout.addWidget(self.primary_backup_button)
        primary_layout.addRow("Directory:", primary_backup_layout)
        
        # Use date subfolders
        self.primary_date_check = QCheckBox("Use date-based subfolders (YYYY/MM/DD)")
        primary_layout.addRow("", self.primary_date_check)
        
        # Secondary backup group
        secondary_group = QGroupBox("Secondary Backup Location")
        secondary_layout = QFormLayout(secondary_group)
        
        # Secondary backup directory
        self.secondary_backup_edit = QLineEdit()
        self.secondary_backup_button = QPushButton("Browse...")
        self.secondary_backup_button.clicked.connect(lambda: self.browse_directory(self.secondary_backup_edit, "Select Secondary Backup Directory"))
        
        secondary_backup_layout = QHBoxLayout()
        secondary_backup_layout.addWidget(self.secondary_backup_edit)
        secondary_backup_layout.addWidget(self.secondary_backup_button)
        secondary_layout.addRow("Directory:", secondary_backup_layout)
        
        # Use date subfolders
        self.secondary_date_check = QCheckBox("Use date-based subfolders (YYYY/MM/DD)")
        secondary_layout.addRow("", self.secondary_date_check)
        
        # Add groups to layout
        layout.addWidget(primary_group)
        layout.addWidget(secondary_group)
        layout.addStretch()
        
        return tab
    
    def create_shortcuts_tab(self) -> QWidget:
        """Create the keyboard shortcuts tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Shortcuts info label
        info_label = QLabel(
            "Keyboard shortcuts can be configured in the config file located at:\n"
            "~/.imcull/config.yaml\n\n"
            "Default shortcuts:\n"
            "- Next Image: Right Arrow, Space\n"
            "- Previous Image: Left Arrow\n"
            "- Rate 0 Stars: 0\n"
            "- Rate 1 Star: 1\n"
            "- Rate 2 Stars: 2\n"
            "- Rate 3 Stars: 3\n"
            "- Toggle Reject: X\n"
            "- Send to Darktable: D\n"
            "- Backup Selected: B\n"
            "- Open Settings: S"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        return tab
    
    def load_settings(self):
        """Load settings from config into UI"""
        # General tab
        self.import_dir_edit.setText(self.config.get('import.default_source_dir', ''))
        self.theme_combo.setCurrentText(self.config.get('ui.theme', 'Dark'))
        self.thumbnail_size_spin.setValue(self.config.get('ui.thumbnail_size', 100))
        
        # Culling tab
        self.blur_threshold_spin.setValue(self.config.get('culling.blur_detection_threshold', 100.0))
        self.enable_blur_check.setChecked(self.config.get('culling.show_metadata', True))
        self.default_rating_spin.setValue(self.config.get('rating.default_rating', 0))
        
        # Darktable tab
        self.darktable_exec_edit.setText(self.config.get('darktable.executable', 'darktable'))
        self.auto_import_check.setChecked(self.config.get('darktable.auto_import', False))
        
        # Backup tab
        self.primary_backup_edit.setText(self.config.get('import.backup_locations.0', ''))
        self.primary_date_check.setChecked(True)  # Default to true
        self.secondary_backup_edit.setText(self.config.get('import.backup_locations.1', ''))
        self.secondary_date_check.setChecked(True)  # Default to true
    
    def save_settings(self) -> Dict[str, Any]:
        """Save settings from UI to config"""
        modified_config = {}
        
        # General tab
        modified_config['import'] = {
            'default_source_dir': self.import_dir_edit.text(),
            'backup_locations': []
        }
        
        # Add backup locations if they exist
        if self.primary_backup_edit.text():
            modified_config['import']['backup_locations'].append(self.primary_backup_edit.text())
        if self.secondary_backup_edit.text():
            modified_config['import']['backup_locations'].append(self.secondary_backup_edit.text())
            
        modified_config['ui'] = {
            'theme': self.theme_combo.currentText(),
            'thumbnail_size': self.thumbnail_size_spin.value()
        }
        
        # Culling tab
        modified_config['culling'] = {
            'blur_detection_threshold': self.blur_threshold_spin.value(),
            'show_metadata': self.enable_blur_check.isChecked(),
            'auto_advance': True,
            'show_histograms': True
        }
        
        modified_config['rating'] = {
            'default_rating': self.default_rating_spin.value()
        }
        
        # Darktable tab
        modified_config['darktable'] = {
            'executable': self.darktable_exec_edit.text(),
            'auto_import': self.auto_import_check.isChecked(),
            'enabled': True
        }
        
        # Keep keyboard shortcuts from original config
        modified_config['keyboard'] = self.config.get_all().get('keyboard', {})
        
        return modified_config
    
    def apply_settings(self):
        """Apply settings without closing the dialog"""
        settings = self.save_settings()
        self.config.update(settings)
        self.config.save()
        self.settings_saved.emit(settings)
    
    def reset_settings(self):
        """Reset settings to defaults"""
        self.config.reset_to_defaults()
        self.modified_config = self.config.get_all().copy()
        self.load_settings()
    
    def accept(self):
        """Handle dialog acceptance (OK button)"""
        self.apply_settings()
        super().accept()
    
    def browse_directory(self, line_edit: QLineEdit, title: str):
        """Open directory browser dialog"""
        current_dir = line_edit.text()
        if not current_dir or not os.path.isdir(current_dir):
            current_dir = os.path.expanduser("~")
        
        directory = QFileDialog.getExistingDirectory(
            self, title, current_dir, 
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if directory:
            line_edit.setText(directory)
    
    def browse_file(self, line_edit: QLineEdit, title: str):
        """Open file browser dialog"""
        current_file = line_edit.text()
        current_dir = os.path.dirname(current_file) if current_file else os.path.expanduser("~")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, current_dir
        )
        
        if file_path:
            line_edit.setText(file_path)
