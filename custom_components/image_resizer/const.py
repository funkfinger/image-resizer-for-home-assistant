"""Constants for the Image Resizer integration."""

DOMAIN = "image_resizer"

# Service names
SERVICE_RESIZE_IMAGE = "resize_image"

# Service parameters
ATTR_SOURCE = "source"
ATTR_DESTINATION = "destination"
ATTR_WIDTH = "width"
ATTR_HEIGHT = "height"
ATTR_QUALITY = "quality"
ATTR_FORMAT = "format"
ATTR_KEEP_ASPECT_RATIO = "keep_aspect_ratio"
ATTR_METHOD = "method"

# Default values
DEFAULT_QUALITY = 85
DEFAULT_KEEP_ASPECT_RATIO = True
DEFAULT_METHOD = "lanczos"  # High-quality downsampling filter

# Resize methods
RESIZE_METHODS = ["nearest", "box", "bilinear", "hamming", "bicubic", "lanczos"]

# Supported formats
SUPPORTED_FORMATS = ["JPEG", "PNG", "WEBP", "BMP", "GIF"]
