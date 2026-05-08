#!/usr/bin/env python3
"""Generate default category fallback images for frameworks without Substack images."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).parent.parent
DEFAULTS_DIR = BASE_DIR / "images" / "defaults"
DEFAULTS_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = {
    "public-policy": ("Public Policy", "#1a4480"),
    "political-thinking": ("Political Thinking", "#8B2942"),
    "public-finance": ("Public Finance", "#2E5A38"),
    "foreign-policy-defence-geopolitics": ("Foreign Policy, Defence & Geopolitics", "#5B3A7B"),
    "society": ("Society", "#A0522D"),
    "universe": ("Universe", "#4A6572"),
}

WIDTH, HEIGHT = 800, 450


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def darken(rgb: tuple, factor: float = 0.7) -> tuple:
    return tuple(int(c * factor) for c in rgb)


def generate_image(slug: str, label: str, color_hex: str):
    base_rgb = hex_to_rgb(color_hex)
    dark_rgb = darken(base_rgb, 0.6)

    img = Image.new("RGB", (WIDTH, HEIGHT), base_rgb)
    draw = ImageDraw.Draw(img)

    # Draw a subtle diagonal band
    band_points = [
        (0, HEIGHT * 0.35),
        (WIDTH, HEIGHT * 0.15),
        (WIDTH, HEIGHT * 0.55),
        (0, HEIGHT * 0.75),
    ]
    draw.polygon(band_points, fill=dark_rgb)

    # Try to load a system font; fall back to default
    font_size = 52
    font = None
    for font_name in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_name, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Center text
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) // 2
    y = (HEIGHT - text_h) // 2

    # Draw text with slight shadow for depth
    shadow_offset = 2
    draw.text((x + shadow_offset, y + shadow_offset), label, font=font, fill=(30, 30, 30))
    draw.text((x, y), label, font=font, fill=(245, 245, 245))

    # Small subtitle
    sub_font = None
    if font:
        try:
            sub_font = ImageFont.truetype(font.font, 20)
        except Exception:
            sub_font = ImageFont.load_default()
    if sub_font is None:
        sub_font = ImageFont.load_default()

    subtitle = "Frameworks for Public Policy"
    bbox2 = draw.textbbox((0, 0), subtitle, font=sub_font)
    sub_w = bbox2[2] - bbox2[0]
    draw.text(
        ((WIDTH - sub_w) // 2, y + text_h + 20),
        subtitle,
        font=sub_font,
        fill=(200, 200, 200),
    )

    out_path = DEFAULTS_DIR / f"{slug}.png"
    img.save(out_path, "PNG")
    print(f"Generated: {out_path}")


def main():
    for slug, (label, color) in CATEGORIES.items():
        generate_image(slug, label, color)
    print("\nAll default images generated.")


if __name__ == "__main__":
    main()
