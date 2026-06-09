"""Import source JSON files into PostgreSQL through Django ORM.

Run from the project root:
    python database/PostgreSQL/import_json_data.py
"""

from __future__ import annotations

import json
import os
import sys
import hashlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from archive.models import DcinsidePost, HorrorStory, MythEntity, Superstition  # noqa: E402


DATA_DIR = PROJECT_ROOT / "database" / "data"
PROCESSED_DIR = PROJECT_ROOT / "database" / "processed"


def load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_processed_json(filename: str) -> list[dict]:
    path = PROCESSED_DIR / filename
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def make_preview(content: str, limit: int = 180) -> str:
    normalized = " ".join((content or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def make_source_ref_id(*parts: object, length: int = 24) -> str:
    """원본 id가 없는 JSON row를 반복 적재할 수 있도록 안정적인 해시 id를 만든다."""

    raw = "||".join(str(part or "").strip() for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def import_horror_stories() -> int:
    rows = load_json("verified_korean_horror_master.json")
    count = 0

    for row in rows:
        source = row.get("source") or "verified_korean_horror_master"
        content = row.get("content") or ""
        source_ref_id = str(
            row.get("id")
            or make_source_ref_id(source, row.get("title"), row.get("region"), content)
        )

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
            source_ref_id=str(
                row.get("id")
                or make_source_ref_id(source, row.get("name"), row.get("origin"))
            ),
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


def category_from_dcinside_title(title: str) -> str | None:
    """DCInside title 태그를 열린 게시판 분류값으로 변환한다."""

    normalized = (title or "").strip()
    if normalized == "[창작]":
        return "CREATION"
    if normalized in {"[경험]", "[괴담]", "[공포]", "[사건/사고]"}:
        return "WITNESS"
    return None


def import_dcinside_posts() -> int:
    rows = load_processed_json("dcinside_horror_processed.json")
    count = 0

    for row in rows:
        metadata = row.get("metadata") or {}
        raw_title = metadata.get("raw_title") or ""
        content = row.get("cleaned_text") or row.get("description") or ""
        keywords = row.get("keywords") or []
        source = row.get("source") or "dcinside_gongpow"
        category = metadata.get("category") or category_from_dcinside_title(raw_title)

        # 분류가 확실하지 않거나 본문이 비어 있는 row는 게시판 seed 품질을 위해 제외한다.
        if not category or not content.strip():
            continue

        source_ref_id = str(
            row.get("source_id")
            or make_source_ref_id(source, raw_title, metadata.get("region"), content)
        )
        DcinsidePost.objects.update_or_create(
            source=source,
            source_ref_id=source_ref_id,
            defaults={
                "category": category,
                "region": metadata.get("region") or "한국",
                "content": content,
                "keywords": keywords,
                "metadata": metadata,
                "is_active": True,
            },
        )
        count += 1

    return count


def main() -> None:
    imported = {
        "horror_stories": import_horror_stories(),
        "myth_entities": import_myth_entities(),
        "superstitions": import_superstitions(),
        "dcinside_posts": import_dcinside_posts(),
    }

    for table_name, count in imported.items():
        print(f"{table_name}: imported_or_updated={count}")


if __name__ == "__main__":
    main()

