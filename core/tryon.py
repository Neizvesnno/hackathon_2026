"""Примірка картини на фото кімнати. Власник: R4 (Максим)."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter


def overlay(
    room: Image.Image,
    painting: Image.Image,
    cx: float = 0.5,
    cy: float = 0.4,
    width: float = 0.35,
) -> Image.Image:
    """Накладає картину (з рамкою і легкою тінню) на фото кімнати.

    cx, cy — центр картини, width — ширина картини; усе частками 0…1 від розміру фото.
    """
    room = room.convert("RGBA")
    painting = painting.convert("RGBA")

    rw, rh = room.size
    target_w = max(8, int(rw * width))
    # зберігаємо пропорції картини
    pw, ph = painting.size
    target_h = max(8, int(target_w * ph / pw))

    # трохи більша рамка
    frame_w = max(2, target_w // 40)
    outer_w = target_w + 2 * frame_w
    outer_h = target_h + 2 * frame_w

    # тінь
    shadow = Image.new("RGBA", (outer_w + 8, outer_h + 8), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rectangle(
        [4, 4, outer_w + 3, outer_h + 3],
        fill=(0, 0, 0, 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))

    # полотно з рамкою
    framed = Image.new("RGBA", (outer_w, outer_h), (40, 30, 20, 255))
    # внутрішня світла облямівка
    inner = Image.new("RGBA", (target_w + 2, target_h + 2), (245, 240, 230, 255))
    framed.paste(inner, (frame_w - 1, frame_w - 1))

    # сама картина
    painting_resized = painting.resize((target_w, target_h), Image.Resampling.LANCZOS)
    framed.paste(painting_resized, (frame_w, frame_w), painting_resized)

    # позиція центру
    left = int(cx * rw - outer_w / 2)
    top = int(cy * rh - outer_h / 2)

    result = room.copy()
    # тінь трохи зміщена
    result.paste(shadow, (left + 3, top + 5), shadow)
    result.paste(framed, (left, top), framed)

    return result.convert("RGB")
