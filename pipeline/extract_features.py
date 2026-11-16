"""Будує app_data/features.parquet з data/. Власник: R1 (Олександр).

Запуск з кореня репозиторію:
    python -m pipeline.extract_features            # усі 10 000
    python -m pipeline.extract_features --limit 300  # чорновий файл
Схема колонок — CONTRACT.md, розділ features.parquet.
"""
from __future__ import annotations

import argparse

from core import config


def main(limit: int | None = None) -> None:
    raise NotImplementedError("R1: extract_features")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="обробити лише перші N картин")
    main(p.parse_args().limit)
