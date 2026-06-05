"""Import docs JSON files into PostgreSQL through Django ORM.

Run from the project root:
    python database/PostgreSQL/import_json_data.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from archive.models import HorrorStory, MythEntity, Superstition  # noqa: E402


DOCS_DIR = PROJECT_ROOT / "docs"


def load_json(filename: str) -> list[dict]:
    path = DOCS_DIR / filename
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def make_preview(content: str, limit: int = 180) -> str:
    normalized = " ".join((content or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def import_horror_stories() -> int:
    rows = load_json("verified_korean_horror_master.json")
    count = 0

    for row in rows:
        source = row.get("source") or "verified_korean_horror_master"
        source_ref_id = str(row["id"])
        content = row.get("content") or ""

        HorrorStory.objects.update_or_create(
            source=source,
            source_ref_id=source_ref_id,
            defaults={
                "title": row.get("title") or "",
                "language": "ko",
                "region": row.get("region") or "",
                "url": row.get("url") or "",
                "preview": make_preview(content),
                "content": content,
                "category": row.get("category") or "",
                "metadata": {},
            },
        )
        count += 1

    return count


def import_myth_entities() -> int:
    rows = load_json("ultimate_global_mythology_1000.json")
    count = 0
    source = "ultimate_global_mythology_1000"

    for row in rows:
        metadata = {}
        if "habitats" in row:
            metadata["habitats"] = row.get("habitats") or []

        MythEntity.objects.update_or_create(
            source=source,
            source_ref_id=str(row["id"]),
            defaults={
                "name": row.get("name") or "",
                "origin": row.get("origin") or "",
                "description": row.get("description") or "",
                "behavior": row.get("behavior") or "",
                "weakness": row.get("weakness") or "",
                "history": row.get("history") or "",
                "signs": row.get("signs") or "",
                "survival_rules": row.get("survival_rules") or [],
                "source_site": row.get("source_site") or "",
                "source_url": row.get("source_url") or "",
                "metadata": metadata,
            },
        )
        count += 1

    return count


def import_superstitions() -> int:
    rows = load_json("misin.json")
    count = 0
    source = "misin"

    for row in rows:
        Superstition.objects.update_or_create(
            source=source,
            source_ref_id=str(row["id"]),
            defaults={
                "content": row.get("content") or "",
                "category": "",
                "region": "",
                "metadata": {},
            },
        )
        count += 1

    return count


def main() -> None:
    imported = {
        "horror_stories": import_horror_stories(),
        "myth_entities": import_myth_entities(),
        "superstitions": import_superstitions(),
    }

    for table_name, count in imported.items():
        print(f"{table_name}: imported_or_updated={count}")


if __name__ == "__main__":
    main()
