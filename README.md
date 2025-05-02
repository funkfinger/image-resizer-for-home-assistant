# Image Resizer for Home Assistant

This custom component for Home Assistant provides a service to resize images. It's useful for automations that need to process images, such as creating thumbnails, optimizing images for display, or preparing images for other services.

> **Note:** This project was entirely created by AI (Augment Code powered by Claude 3.7 Sonnet) with a human merely guiding the AI model through the development process.
>
> **Warning:** This is very much an early release and since it is only used for the creator's single use-case, it likely won't work for other's needs. The project is a test case for "vibe coding" and shouldn't be considered stable.

## Features

- Resize images to specific dimensions
- Maintain aspect ratio (optional)
- Support for multiple image formats (JPEG, PNG, WEBP, BMP, GIF)
- Support for animated GIFs
- Quality control for JPEG and WEBP formats
- Multiple resizing methods
- Support for HTTP/HTTPS URLs as source images
- Support for Home Assistant media URLs
- Template support for dynamic source paths/URLs

## Installation

### Manual Installation

1. Copy the `custom_components/image_resizer` folder to your Home Assistant's `custom_components` directory.
2. Restart Home Assistant.

### HACS Installation

1. Open HACS in your Home Assistant instance.
2. Click on "Integrations".
3. Click the three dots in the top right corner and select "Custom repositories".
4. Add the URL of this repository and select "Integration" as the category.
5. Click "Add".
6. Search for "Image Resizer" and install it.
7. Restart Home Assistant.

## Usage

The component provides the `image_resizer.resize_image` service that you can call from your automations, scripts, or the Developer Tools.

### Basic Example

```yaml
service: image_resizer.resize_image
data:
  source: /config/www/original.jpg
  destination: /config/www/resized.jpg
  width: 800
  height: 600
```

### HTTP Source Example

```yaml
service: image_resizer.resize_image
data:
  source: http://homeassistant.local:8123/api/media_player_proxy/media_player.living_room?token=xyz
  destination: /config/www/album_art.jpg
  width: 300
  height: 300
  quality: 90
```

### Template Example

```yaml
service: image_resizer.resize_image
data:
  source: "{{ 'http://homeassistant.local:8123' + states.media_player.living_room.attributes.entity_picture }}"
  destination: /config/www/current_album_art.jpg
  width: 400
  quality: 90
```

For more examples and detailed documentation, see the [component README](custom_components/image_resizer/README.md).

## License

This component is licensed under the MIT License.
