"""
Custom component for resizing images in Home Assistant.

For more details about this component, please refer to the documentation at
https://github.com/home-assistant/example-custom-config/tree/master/custom_components/image_resizer
"""
import logging
import os
import io
import tempfile
import voluptuous as vol
from typing import Any, Dict, Optional, Tuple, Union
import aiohttp
import asyncio
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, template
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.components import http
import aiohttp

from .const import (
    DOMAIN,
    SERVICE_RESIZE_IMAGE,
    ATTR_SOURCE,
    ATTR_DESTINATION,
    ATTR_WIDTH,
    ATTR_HEIGHT,
    ATTR_QUALITY,
    ATTR_FORMAT,
    ATTR_KEEP_ASPECT_RATIO,
    ATTR_METHOD,
    ATTR_BMP_16BIT,
    DEFAULT_QUALITY,
    DEFAULT_KEEP_ASPECT_RATIO,
    DEFAULT_METHOD,
    RESIZE_METHODS,
    SUPPORTED_FORMATS,
)

_LOGGER = logging.getLogger(__name__)

RESIZE_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SOURCE): cv.template,  # Allow templates for source
        vol.Required(ATTR_DESTINATION): cv.string,
        vol.Optional(ATTR_WIDTH): cv.positive_int,
        vol.Optional(ATTR_HEIGHT): cv.positive_int,
        vol.Optional(ATTR_QUALITY, default=DEFAULT_QUALITY): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
        vol.Optional(ATTR_FORMAT): vol.In(SUPPORTED_FORMATS),
        vol.Optional(ATTR_KEEP_ASPECT_RATIO, default=DEFAULT_KEEP_ASPECT_RATIO): cv.boolean,
        vol.Optional(ATTR_METHOD, default=DEFAULT_METHOD): vol.In(RESIZE_METHODS),
        vol.Optional(ATTR_BMP_16BIT, default=False): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Image Resizer component."""

    async def handle_resize_image(call: ServiceCall) -> None:
        """Handle the resize_image service call."""
        # Get source and render template if needed
        source_template = call.data[ATTR_SOURCE]
        try:
            source = template.render_complex(source_template, {"hass": hass})
            if not isinstance(source, str):
                _LOGGER.error("Template did not render to a string: %s", source)
                return
        except template.TemplateError as ex:
            _LOGGER.error("Error rendering source template: %s", ex)
            return

        destination = call.data[ATTR_DESTINATION]
        width = call.data.get(ATTR_WIDTH)
        height = call.data.get(ATTR_HEIGHT)
        quality = call.data.get(ATTR_QUALITY, DEFAULT_QUALITY)
        output_format = call.data.get(ATTR_FORMAT)
        keep_aspect_ratio = call.data.get(ATTR_KEEP_ASPECT_RATIO, DEFAULT_KEEP_ASPECT_RATIO)
        method = call.data.get(ATTR_METHOD, DEFAULT_METHOD)
        bmp_16bit = call.data.get(ATTR_BMP_16BIT, False)

        # Validate that at least one of width or height is provided
        if width is None and height is None:
            _LOGGER.error("At least one of width or height must be specified")
            return

        # Ensure destination path is absolute
        if not os.path.isabs(destination):
            destination = hass.config.path(destination)

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination), exist_ok=True)

        try:
            # Check if source is a URL
            if source.startswith(("http://", "https://")):
                _LOGGER.debug("Source is a URL: %s", source)
                # Download the image from the URL
                image_data = await download_image(hass, source)
                if image_data is None:
                    _LOGGER.error("Failed to download image from URL: %s", source)
                    return

                # Process the image from memory
                await hass.async_add_executor_job(
                    resize_image_from_bytes,
                    image_data,
                    destination,
                    width,
                    height,
                    quality,
                    output_format,
                    keep_aspect_ratio,
                    method,
                    bmp_16bit,
                )
            else:
                # Ensure source path is absolute for local files
                if not os.path.isabs(source):
                    source = hass.config.path(source)

                # Process the image from file
                await hass.async_add_executor_job(
                    resize_image,
                    source,
                    destination,
                    width,
                    height,
                    quality,
                    output_format,
                    keep_aspect_ratio,
                    method,
                    bmp_16bit,
                )

            _LOGGER.info(
                "Image resized successfully from %s to %s", source, destination
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error resizing image: %s", err)

    hass.services.async_register(
        DOMAIN, SERVICE_RESIZE_IMAGE, handle_resize_image, schema=RESIZE_IMAGE_SCHEMA
    )

    return True


async def download_image(hass: HomeAssistant, url: str) -> Optional[bytes]:
    """Download an image from a URL."""
    try:
        # Create a new aiohttp session instead of using the helper
        timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Failed to download image, status code: %s", response.status
                    )
                    return None

                return await response.read()

    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.error("Error downloading image: %s", err)
        return None


def resize_image_from_bytes(
    image_data: bytes,
    destination: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    quality: int = DEFAULT_QUALITY,
    output_format: Optional[str] = None,
    keep_aspect_ratio: bool = DEFAULT_KEEP_ASPECT_RATIO,
    method: str = DEFAULT_METHOD,
    bmp_16bit: bool = False,
) -> None:
    """Resize an image from bytes data using Pillow."""
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            # Get original dimensions
            orig_width, orig_height = img.size

            # Calculate new dimensions
            new_width, new_height = calculate_dimensions(
                orig_width, orig_height, width, height, keep_aspect_ratio
            )

            # Determine output format
            if output_format is None:
                # Try to determine format from destination file extension
                ext = os.path.splitext(destination)[1].lower()
                if ext == ".jpg" or ext == ".jpeg":
                    output_format = "JPEG"
                elif ext == ".png":
                    output_format = "PNG"
                elif ext == ".webp":
                    output_format = "WEBP"
                elif ext == ".bmp":
                    output_format = "BMP"
                elif ext == ".gif":
                    output_format = "GIF"
                else:
                    # Default to JPEG if format can't be determined
                    output_format = "JPEG"

            # Resize image
            resized_img = img.resize((new_width, new_height), getattr(Image, method.upper()))

            # Save resized image
            save_kwargs = {}
            if output_format in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality

            # Handle 16-bit BMP
            if output_format == "BMP" and bmp_16bit:
                # Convert to RGB mode if not already
                if resized_img.mode != "RGB":
                    resized_img = resized_img.convert("RGB")
                # Save as 16-bit BMP (R5G6B5 format)
                save_kwargs["bits"] = 16

            # Preserve animation for GIFs if possible
            if output_format == "GIF" and getattr(img, "is_animated", False):
                frames = []
                for frame_idx in range(getattr(img, "n_frames", 1)):
                    img.seek(frame_idx)
                    frame = img.copy()
                    frame = frame.resize((new_width, new_height), getattr(Image, method.upper()))
                    frames.append(frame)

                frames[0].save(
                    destination,
                    format=output_format,
                    save_all=True,
                    append_images=frames[1:],
                    loop=getattr(img, "info", {}).get("loop", 0),
                    duration=getattr(img, "info", {}).get("duration", 100),
                    **save_kwargs
                )
            else:
                resized_img.save(destination, format=output_format, **save_kwargs)

    except UnidentifiedImageError:
        raise ValueError("Cannot identify image data")
    except PermissionError:
        raise PermissionError(f"Permission denied when accessing destination: {destination}")
    except Exception as err:
        raise Exception(f"Error processing image: {err}")


def resize_image(
    source: str,
    destination: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    quality: int = DEFAULT_QUALITY,
    output_format: Optional[str] = None,
    keep_aspect_ratio: bool = DEFAULT_KEEP_ASPECT_RATIO,
    method: str = DEFAULT_METHOD,
    bmp_16bit: bool = False,
) -> None:
    """Resize an image using Pillow."""
    try:
        with Image.open(source) as img:
            # Get original dimensions
            orig_width, orig_height = img.size

            # Calculate new dimensions
            new_width, new_height = calculate_dimensions(
                orig_width, orig_height, width, height, keep_aspect_ratio
            )

            # Determine output format
            if output_format is None:
                # Try to determine format from destination file extension
                ext = os.path.splitext(destination)[1].lower()
                if ext == ".jpg" or ext == ".jpeg":
                    output_format = "JPEG"
                elif ext == ".png":
                    output_format = "PNG"
                elif ext == ".webp":
                    output_format = "WEBP"
                elif ext == ".bmp":
                    output_format = "BMP"
                elif ext == ".gif":
                    output_format = "GIF"
                else:
                    # Default to JPEG if format can't be determined
                    output_format = "JPEG"

            # Resize image
            resized_img = img.resize((new_width, new_height), getattr(Image, method.upper()))

            # Save resized image
            save_kwargs = {}
            if output_format in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality

            # Handle 16-bit BMP
            if output_format == "BMP" and bmp_16bit:
                # Convert to RGB mode if not already
                if resized_img.mode != "RGB":
                    resized_img = resized_img.convert("RGB")
                # Save as 16-bit BMP (R5G6B5 format)
                save_kwargs["bits"] = 16

            # Preserve animation for GIFs if possible
            if output_format == "GIF" and getattr(img, "is_animated", False):
                frames = []
                for frame_idx in range(getattr(img, "n_frames", 1)):
                    img.seek(frame_idx)
                    frame = img.copy()
                    frame = frame.resize((new_width, new_height), getattr(Image, method.upper()))
                    frames.append(frame)

                frames[0].save(
                    destination,
                    format=output_format,
                    save_all=True,
                    append_images=frames[1:],
                    loop=getattr(img, "info", {}).get("loop", 0),
                    duration=getattr(img, "info", {}).get("duration", 100),
                    **save_kwargs
                )
            else:
                resized_img.save(destination, format=output_format, **save_kwargs)

    except FileNotFoundError:
        raise FileNotFoundError(f"Source file not found: {source}")
    except UnidentifiedImageError:
        raise ValueError(f"Cannot identify image file: {source}")
    except PermissionError:
        raise PermissionError(f"Permission denied when accessing {source} or {destination}")
    except Exception as err:
        raise Exception(f"Error processing image: {err}")


def calculate_dimensions(
    orig_width: int,
    orig_height: int,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    keep_aspect_ratio: bool = True,
) -> Tuple[int, int]:
    """Calculate new dimensions based on inputs and constraints."""
    if target_width is None and target_height is None:
        return orig_width, orig_height

    if not keep_aspect_ratio:
        return target_width or orig_width, target_height or orig_height

    # Calculate aspect ratio
    aspect_ratio = orig_width / orig_height

    if target_width is None:
        # Calculate width based on target height
        return int(target_height * aspect_ratio), target_height

    if target_height is None:
        # Calculate height based on target width
        return target_width, int(target_width / aspect_ratio)

    # Both width and height specified, maintain aspect ratio by using the smaller scale
    width_scale = target_width / orig_width
    height_scale = target_height / orig_height

    if width_scale < height_scale:
        return target_width, int(target_width / aspect_ratio)
    else:
        return int(target_height * aspect_ratio), target_height
