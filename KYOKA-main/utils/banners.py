from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw, ImageFont


DEFAULT_BACKGROUND = (15, 15, 20)
DEFAULT_ACCENT = (120, 80, 255)


async def download_image(url: str) -> Image.Image:
    """Download an image and return it as a PIL Image."""

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError("Failed to download image.")

            data = await response.read()

    image = Image.open(BytesIO(data)).convert("RGBA")
    return image


def crop_to_square(image: Image.Image, size: int = 512):
    """Crop an image to a centered square."""

    width, height = image.size
    side = min(width, height)

    left = (width - side) // 2
    top = (height - side) // 2

    image = image.crop(
        (left, top, left + side, top + side)
    )

    return image.resize(
        (size, size),
        Image.Resampling.LANCZOS
    )


def create_gradient_background(
    size=(1200, 400),
    color1=(15, 15, 20),
    color2=(60, 30, 100)
):
    """Create a simple horizontal gradient."""

    width, height = size

    image = Image.new(
        "RGB",
        size,
        color1
    )

    pixels = image.load()

    for x in range(width):
        ratio = x / max(width - 1, 1)

        r = int(
            color1[0] * (1 - ratio)
            + color2[0] * ratio
        )

        g = int(
            color1[1] * (1 - ratio)
            + color2[1] * ratio
        )

        b = int(
            color1[2] * (1 - ratio)
            + color2[2] * ratio
        )

        for y in range(height):
            pixels[x, y] = (r, g, b)

    return image


def load_font(size: int, bold: bool = False):
    """Load a commonly available font."""

    font_paths = []

    if bold:
        font_paths.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ])
    else:
        font_paths.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ])

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue

    return ImageFont.load_default()


def rounded_avatar(
    avatar: Image.Image,
    size: int = 180
):
    """Create a circular avatar."""

    avatar = crop_to_square(
        avatar,
        size
    )

    mask = Image.new(
        "L",
        (size, size),
        0
    )

    draw = ImageDraw.Draw(mask)

    draw.ellipse(
        (0, 0, size, size),
        fill=255
    )

    result = Image.new(
        "RGBA",
        (size, size),
        (0, 0, 0, 0)
    )

    result.paste(
        avatar,
        (0, 0),
        mask
    )

    return result


def create_welcome_banner(
    username: str,
    display_name: str,
    server_name: str,
    member_count: int,
    avatar: Image.Image = None,
    background: Image.Image = None
):
    """
    Generate a KYŌKA welcome banner.

    Returns a PIL Image.
    """

    width = 1200
    height = 500

    if background:
        background = background.convert("RGB")
        background = background.resize(
            (width, height),
            Image.Resampling.LANCZOS
        )

        image = background.convert("RGBA")

    else:
        image = create_gradient_background(
            (width, height),
            DEFAULT_BACKGROUND,
            (55, 25, 95)
        ).convert("RGBA")

    # Dark overlay for readability
    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 80)
    )

    image = Image.alpha_composite(
        image,
        overlay
    )

    draw = ImageDraw.Draw(image)

    # Fonts
    title_font = load_font(
        58,
        bold=True
    )

    name_font = load_font(
        38,
        bold=True
    )

    normal_font = load_font(
        26
    )

    small_font = load_font(
        22
    )

    # Avatar
    if avatar:
        avatar = rounded_avatar(
            avatar,
            180
        )

        image.alpha_composite(
            avatar,
            (70, 160)
        )

    # Welcome text
    draw.text(
        (290, 85),
        "WELCOME",
        font=title_font,
        fill=(255, 255, 255)
    )

    draw.text(
        (290, 165),
        display_name or username,
        font=name_font,
        fill=(190, 160, 255)
    )

    draw.text(
        (290, 225),
        f"Welcome to {server_name}",
        font=normal_font,
        fill=(235, 235, 235)
    )

    draw.text(
        (290, 275),
        f"Member #{member_count}",
        font=small_font,
        fill=(190, 190, 200)
    )

    # Bottom branding
    draw.text(
        (70, 435),
        "KYŌKA",
        font=small_font,
        fill=(180, 160, 255)
    )

    return image


def image_to_bytes(
    image: Image.Image,
    format: str = "PNG"
):
    """Convert a PIL image into bytes."""

    buffer = BytesIO()

    image.save(
        buffer,
        format=format
    )

    buffer.seek(0)

    return buffer
