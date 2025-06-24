# ImCull - Photography Workflow Assistant

A fast, keyboard-driven photography culling and management tool designed for photographers using Linux.

## Features

- **Fast Culling**: Quickly browse and select photos with keyboard shortcuts
- **Smart Detection**: AI-powered blurry photo detection
- **Paired File Handling**: Treats RAW+JPEG pairs as a single photo
- **Rating System**: Simple 3-star rating system with keyboard shortcuts
- **Darktable Integration**: Automatically add selected photos to Darktable
- **Backup Options**: Back up selected photos to multiple locations
- **Enhanced RAW Support**: Robust metadata extraction from RAW files with multiple fallback methods
- **High-Resolution Previews**: Better focus determination with higher quality image previews
- **Intuitive UI**: Thumbnail strip at the bottom with image viewer and metadata panel side-by-side
- **Zoom Controls**: Easily inspect image details with zoom buttons and level indicator

## Requirements

- Linux with Wayland (tested on Hyprland compositor)
- Python 3.8+
- Darktable installed for photo processing integration

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/jasonzondor/imcull.git
   cd imcull
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```
python imcull.py
```

### Keyboard Shortcuts

- **Space**: Next image
- **Backspace**: Previous image
- **1-3**: Rate current image (1-3 stars)
- **0**: Remove rating
- **X**: Mark for rejection
- **Enter**: Confirm selection and proceed
- **Ctrl+D**: Send selected photos to Darktable
- **Ctrl+B**: Backup selected photos

## Configuration

The configuration file is located at `~/.config/imcull/config.yaml`. You can customize:
- Default import directories
- Backup locations
- Darktable integration settings
- Blur detection threshold
- Keyboard shortcuts

## Development

### Project Structure

```
imcull/
├── core/           # Core functionality and business logic
├── ui/             # User interface components
├── imcull.py       # Main application entry point
└── requirements.txt # Python dependencies
```

### Core Components

- **Image Handler**: Manages image loading, metadata extraction, and thumbnail generation
- **Metadata Panel**: Displays comprehensive image information including RAW metadata
- **Thumbnail Strip**: Horizontal strip at the bottom for quick navigation between images
- **Image Viewer**: Displays images with zoom controls and overlay information

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT-
