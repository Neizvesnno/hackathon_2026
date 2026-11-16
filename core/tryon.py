"""Примірка картини на фото кімнати. Власник: R4 (Максим)."""
from __future__ import annotations

from PIL import Image


def overlay(room: Image.Image, painting: Image.Image,
            cx: float = 0.5, cy: float = 0.4, width: float = 0.35) -> Image.Image:
    """Накладає картину (з рамкою і легкою тінню) на фото кімнати.

    cx, cy — центр картини, width — ширина картини; усе частками 0…1 від розміру фото.
    """
    raise NotImplementedError("R4: overlay")
