# Image Resizer for Home Assistant

This custom component for Home Assistant provides a service to resize images. It's useful for automations that need to process images, such as creating thumbnails, optimizing images for display, or preparing images for other services.

## Installation

### Manual Installation

1. Copy the `image_resizer` folder to your Home Assistant's `custom_components` directory.
2. Restart Home Assistant.

### HACS Installation

1. Open HACS in your Home Assistant instance.
2. Click on "Integrations".
3. Click the three dots in the top right corner and select "Custom repositories".
4. Add the URL of this repository and select "Integration" as the category.
5. Click "Add".
6. Search for "Image Resizer" and install it.
7. Restart Home Assistant.

## Configuration

No configuration is needed. The component registers a service that you can call from your automations, scripts, or the Developer Tools.

## Usage

The component provides the following service:

### `image_resizer.resize_image`

Resizes an image to the specified dimensions.

#### Parameters

| Parameter           | Type    | Required | Default   | Description                                                                                                                               |
| ------------------- | ------- | -------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `source`            | string  | Yes      | -         | Path to the source image or HTTP/HTTPS URL. Can be a local file path or a URL (including Home Assistant media URLs). Supports templates.  |
| `destination`       | string  | Yes      | -         | Path to save the resized image.                                                                                                           |
| `width`             | integer | No       | -         | Target width in pixels. If not specified, it will be calculated based on the height and aspect ratio.                                     |
| `height`            | integer | No       | -         | Target height in pixels. If not specified, it will be calculated based on the width and aspect ratio.                                     |
| `quality`           | integer | No       | 85        | JPEG quality (1-100). Only applies to JPEG and WEBP formats.                                                                              |
| `format`            | string  | No       | -         | Output format. If not specified, it will be determined from the destination file extension. Options: "JPEG", "PNG", "WEBP", "BMP", "GIF". |
| `keep_aspect_ratio` | boolean | No       | true      | Whether to maintain the original aspect ratio.                                                                                            |
| `method`            | string  | No       | "lanczos" | Resizing method to use. Options: "nearest", "box", "bilinear", "hamming", "bicubic", "lanczos".                                           |

**Note:** At least one of `width` or `height` must be specified.

## Examples

### Basic Usage

```yaml
service: image_resizer.resize_image
data:
  source: /config/www/original.jpg
  destination: /config/www/resized.jpg
  width: 800
  height: 600
```

### Resize to a Specific Width (Maintaining Aspect Ratio)

```yaml
service: image_resizer.resize_image
data:
  source: /config/www/original.jpg
  destination: /config/www/resized.jpg
  width: 800
```

### Resize to a Specific Height (Maintaining Aspect Ratio)

```yaml
service: image_resizer.resize_image
data:
  source: /config/www/original.jpg
  destination: /config/www/resized.jpg
  height: 600
```

### Convert Image Format

```yaml
service: image_resizer.resize_image
data:
  source: /config/www/original.jpg
  destination: /config/www/converted.webp
  width: 800
  format: WEBP
  quality: 90
```

### Resize Without Maintaining Aspect Ratio

```yaml
service: image_resizer.resize_image
data:
  source: /config/www/original.jpg
  destination: /config/www/resized.jpg
  width: 800
  height: 600
  keep_aspect_ratio: false
```

### Resize an Image from a URL

```yaml
service: image_resizer.resize_image
data:
  source: http://homeassistant.local:8123/api/media_player_proxy/media_player.work_room_2?token=393cbd70c62598d80d322d92857bc2ce047a3fac3f832e4f6258cfa6b6e83a3c
  destination: /config/www/album_art_thumbnail.jpg
  width: 300
  height: 300
  quality: 90
```

### Use in an Automation

```yaml
automation:
  trigger:
    platform: state
    entity_id: binary_sensor.motion
    to: "on"
  action:
    - service: image_resizer.resize_image
      data:
        source: /config/www/camera_snapshot.jpg
        destination: /config/www/thumbnail.jpg
        width: 320
        quality: 75
```

### Use with Media Player Album Art (Using Templates)

```yaml
automation:
  trigger:
    platform: state
    entity_id: media_player.living_room
    attribute: entity_picture
  action:
    - service: image_resizer.resize_image
      data:
        source: "{{ 'http://homeassistant.local:8123' + trigger.to_state.attributes.entity_picture }}"
        destination: /config/www/current_album_art.jpg
        width: 400
        quality: 90
```

### Using Templates for Dynamic Sources

```yaml
# Resize the entity picture of the currently playing media player
service: image_resizer.resize_image
data:
  source: >
    {% set player = states.media_player | selectattr('attributes.entity_picture', 'defined') | selectattr('state', 'eq', 'playing') | list | first %}
    {% if player %}
      {{ 'http://homeassistant.local:8123' + player.attributes.entity_picture }}
    {% else %}
      /config/www/default_image.jpg
    {% endif %}
  destination: /config/www/now_playing.jpg
  width: 300
  height: 300
```

## Troubleshooting

- Make sure the source image exists and is readable.
- Make sure the destination directory exists and is writable.
- Check the Home Assistant logs for error messages.

## License

This component is licensed under the MIT License.
