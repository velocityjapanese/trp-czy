"""
Tropicozy YouTube Thumbnail Generator
- Generates high-CTR tropical music thumbnails (1280x720)
- Automatically detects and removes AI/Gemini watermarks via OpenCV inpainting
- Clean, aesthetic typography (Cinzel / Playfair)
- Rich tropical atmosphere, vibrant island colors, and 1-Hour badge
"""
import os
import sys
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TROPICAL_HOOKS = [
    {"main": "TROPICAL PARADISE", "sub": "1 HOUR RELAXING ISLAND MUSIC", "badge": "1 HOUR · 1080p HD"},
    {"main": "ISLAND DREAMS", "sub": "CALMING TROPICAL BEATS & RAINFOREST VIBES", "badge": "DEEP CHILL · 1 HOUR"},
    {"main": "CANOPY SUNSET", "sub": "SOOTHING TROPICAL CHILLOUT MELODIES", "badge": "1080p HD · 1 HOUR"},
    {"main": "RAINFOREST BLISS", "sub": "PEACEFUL TROPICAL NATURE & AMBIENT MUSIC", "badge": "TROPICOZY · 1 HOUR"},
    {"main": "EMERALD TIDES", "sub": "UNWIND TO CARIBBEAN OCEAN VIBES", "badge": "RELAX & STUDY · 1 HOUR"},
    {"main": "WARM HORIZON", "sub": "FEEL-GOOD TROPICAL SUNSHINE SOUNDS", "badge": "1 HOUR · 1080p HD"},
    {"main": "CARIBBEAN CHILL", "sub": "TRANQUIL TROPICAL SOUNDSCAPE FOR FOCUS", "badge": "TROPICAL VIBES · 1 HOUR"}
]


def remove_watermark(cv_img):
    """Removes corner AI watermarks seamlessly using OpenCV inpainting."""
    h, w = cv_img.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    # Watermark zone in bottom-right corner
    sx1 = int(w * 0.88)
    sy1 = int(h * 0.82)
    sx2 = int(w * 0.98)
    sy2 = int(h * 0.96)
    mask[sy1:sy2, sx1:sx2] = 255

    inpainted = cv2.inpaint(cv_img, mask, inpaintRadius=4, flags=cv2.INPAINT_TELEA)
    return inpainted


def get_font(font_name="Cinzel.ttf", size=56):
    """Load font with fallback hierarchy."""
    font_path = os.path.join(SCRIPT_DIR, "assets", "fonts", font_name)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    pf = os.path.join(SCRIPT_DIR, "assets", "fonts", "PlayfairDisplay.ttf")
    if os.path.exists(pf):
        try:
            return ImageFont.truetype(pf, size)
        except Exception:
            pass

    # System fonts fallback
    for f in [r"C:\Windows\Fonts\georgiab.ttf", r"C:\Windows\Fonts\georgia.ttf", r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass

    return ImageFont.load_default()


def apply_tropical_vignette(img, intensity=0.25):
    """Applies a rich cinematic vignette to frame tropical visuals."""
    W, H = img.size
    mask = Image.new("L", (W, H), 0)
    draw_m = ImageDraw.Draw(mask)
    draw_m.ellipse([-W * 0.15, -H * 0.15, W * 1.15, H * 1.15], fill=int(255 * (1.0 - intensity)))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=int(W * 0.07)))
    dark = Image.new("RGBA", (W, H), (10, 20, 15, 255))
    return Image.composite(img, dark, mask)


def create_tropical_thumbnail(bg_path, output_path, main_text=None, sub_text=None, badge_text=None):
    """
    Creates a clean, high-converting Tropical Music YouTube thumbnail (1280x720).
    """
    if not main_text:
        preset = random.choice(TROPICAL_HOOKS)
        main_text = preset["main"]
        sub_text = preset["sub"]
        badge_text = preset.get("badge", "1 HOUR · 1080p HD")
    elif not badge_text:
        badge_text = "1 HOUR · 1080p HD"

    # 1. Load image & Inpaint watermark
    cv_img = cv2.imread(bg_path)
    if cv_img is not None:
        clean_cv = remove_watermark(cv_img)
        rgb_img = cv2.cvtColor(clean_cv, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_img).convert("RGBA")
    else:
        img = Image.open(bg_path).convert("RGBA")

    target_w, target_h = 1280, 720
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        offset = (img.width - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, img.height))
    else:
        new_h = int(img.width / target_ratio)
        offset = (img.height - new_h) // 2
        img = img.crop((0, offset, img.width, offset + new_h))

    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Enhance tropical warmth & lushness
    img = ImageEnhance.Color(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.08)

    # 2. Add vignette
    img = apply_tropical_vignette(img, intensity=0.25)

    # 3. Create text overlay
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_main = get_font("Cinzel.ttf", size=62)
    font_sub = get_font("PlayfairDisplay.ttf", size=28)
    font_badge = get_font("Cinzel.ttf", size=24)

    # Bottom-left typography layout
    x_pos = 70
    y_base = target_h - 165

    # Subtitle
    if sub_text:
        for dx, dy in [(-2, 2), (2, 2), (0, 2), (2, 0), (-1, -1)]:
            draw.text((x_pos + dx, y_base - 40 + dy), sub_text.upper(), font=font_badge, fill=(0, 0, 0, 230))
        draw.text((x_pos, y_base - 40), sub_text.upper(), font=font_badge, fill=(255, 230, 130, 255))

    # Main Headline
    for dx, dy in [(-3, 3), (3, 3), (0, 4), (4, 4), (-2, -2), (2, -2)]:
        draw.text((x_pos + dx, y_base + dy), main_text.upper(), font=font_main, fill=(0, 0, 0, 240))
    draw.text((x_pos, y_base), main_text.upper(), font=font_main, fill=(255, 255, 255, 255))

    # Top-Right Badge
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bx = target_w - bw - 70
    by = 45
    padding_x = 18
    padding_y = 10

    draw.rounded_rectangle(
        [bx - padding_x, by - padding_y, bx + bw + padding_x, by + bh + padding_y],
        radius=10,
        fill=(10, 25, 20, 200),
        outline=(255, 200, 50, 200),
        width=2
    )
    draw.text((bx, by), badge_text, font=font_badge, fill=(255, 245, 210, 255))

    final = Image.alpha_composite(img, overlay).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final.save(output_path, quality=96)
    print(f"[+] Generated Tropical Thumbnail: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) > 2:
        create_tropical_thumbnail(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python thumbnail_generator.py <input_image> <output_thumbnail>")
