"""PostgreSQL 원본 데이터를 pgvector 임베딩 테이블에 저장한다.

실행 위치는 프로젝트 루트 기준이다.

    python database/PostgreSQL/pgvector/embed_records.py

기본 대상 테이블은 horror_stories, myth_entities 이다.
각 레코드는 semantic_chunker.py로 청크 분리한 뒤 KURE-v1 임베딩 모델로
1024차원 벡터를 만들고 record_embeddings 테이블에 upsert 한다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import connection, transaction  # noqa: E402

from archive.models import HorrorStory, MythEntity  # noqa: E402
from semantic_chunker import chunk_record  # noqa: E402


DEFAULT_MODEL_NAME = "nlpai-lab/KURE-v1"
DEFAULT_BATCH_SIZE = 32
SOURCE_ALL = "all"
SOURCE_HORROR = "horror_stories"
SOURCE_MYTH = "myth_entities"
SOURCE_CHOICES = (SOURCE_ALL, SOURCE_HORROR, SOURCE_MYTH)
HF_TOKEN_ENV_NAMES = ("HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "HUGGINGFACE_HUB_TOKEN")


@dataclass(frozen=True)
class SourceRecord:
    """임베딩할 원본 레코드를 공통 형태로 표현한다."""

    source_table: str
    source_id: int
    title: str
    parts: list[str]
    metadata: dict


@dataclass(frozen=True)
class EmbeddingRow:
    """record_embeddings에 저장할 청크 1개와 벡터를 묶은 값이다."""

    source_table: str
    source_id: int
    chunk_index: int
    title: str
    content: str
    embedding: list[float]
    metadata: dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PostgreSQL 원본 테이블을 읽어 record_embeddings에 pgvector 임베딩을 저장한다.",
    )
    parser.add_argument(
        "--source",
        choices=SOURCE_CHOICES,
        default=SOURCE_ALL,
        help="임베딩할 원본 테이블. 기본값은 all.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help=f"사용할 sentence-transformers 임베딩 모델. 기본값은 {DEFAULT_MODEL_NAME}.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"한 번에 임베딩할 청크 수. 기본값은 {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="테스트용 처리 개수 제한. 지정하지 않으면 전체 처리.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="선택한 source의 기존 임베딩을 삭제한 뒤 다시 생성.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB 저장 없이 청크 생성 개수만 확인.",
    )
    return parser.parse_args()


def iter_records(source: str, limit: int | None = None) -> Iterable[SourceRecord]:
    """선택한 원본 테이블의 레코드를 SourceRecord 형태로 순회한다."""

    selected_sources = (SOURCE_HORROR, SOURCE_MYTH) if source == SOURCE_ALL else (source,)

    remaining = limit
    for selected in selected_sources:
        queryset = _queryset_for_source(selected)
        if remaining is not None:
            queryset = queryset[:remaining]

        count = 0
        for obj in queryset.iterator(chunk_size=500):
            yield _record_from_model(selected, obj)
            count += 1

        if remaining is not None:
            remaining -= count
            if remaining <= 0:
                return


def _queryset_for_source(source: str):
    if source == SOURCE_HORROR:
        return HorrorStory.objects.order_by("id")
    if source == SOURCE_MYTH:
        return MythEntity.objects.order_by("id")
    raise ValueError(f"지원하지 않는 source: {source}")


def _record_from_model(source: str, obj) -> SourceRecord:
    if source == SOURCE_HORROR:
        return SourceRecord(
            source_table=SOURCE_HORROR,
            source_id=obj.id,
            title=obj.title or "",
            parts=[obj.preview or "", obj.content or ""],
            metadata={
                "source": obj.source,
                "source_ref_id": obj.source_ref_id,
                "language": obj.language,
                "region": obj.region,
                "category": obj.category,
                "url": obj.url,
            },
        )

    if source == SOURCE_MYTH:
        survival_rules = obj.survival_rules or []
        rules_text = "\n".join(str(rule) for rule in survival_rules)
        return SourceRecord(
            source_table=SOURCE_MYTH,
            source_id=obj.id,
            title=obj.name or "",
            parts=[
                obj.description or "",
                obj.behavior or "",
                obj.weakness or "",
                obj.history or "",
                obj.signs or "",
                rules_text,
            ],
            metadata={
                "source": obj.source,
                "source_ref_id": obj.source_ref_id,
                "origin": obj.origin,
                "source_site": obj.source_site,
                "source_url": obj.source_url,
                **(obj.metadata or {}),
            },
        )

    raise ValueError(f"지원하지 않는 source: {source}")


def reset_embeddings(source: str) -> None:
    """선택한 source의 기존 임베딩을 삭제한다."""

    sources = (SOURCE_HORROR, SOURCE_MYTH) if source == SOURCE_ALL else (source,)
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM record_embeddings WHERE source_table = ANY(%s)",
            [list(sources)],
        )


def build_embedding_rows(
    records: Iterable[SourceRecord],
    model: Any,
    batch_size: int,
    dry_run: bool = False,
) -> tuple[int, int]:
    """원본 레코드를 청크화하고 임베딩을 만들어 저장한다."""

    processed_records = 0
    processed_chunks = 0
    pending: list[tuple[SourceRecord, dict[str, str | int]]] = []

    for record in records:
        chunks = chunk_record(title=record.title, parts=record.parts)
        processed_records += 1

        if dry_run:
            processed_chunks += len(chunks)
            print(
                f"[DRY-RUN] {record.source_table}:{record.source_id} "
                f"chunks={len(chunks)} title={record.title[:40]}"
            )
            continue

        # 기존 레코드가 수정되어 청크 수가 줄어든 경우, 남는 예전 청크를 삭제한다.
        delete_stale_chunks(record, keep_chunk_count=len(chunks))

        for chunk in chunks:
            pending.append((record, chunk))
            if len(pending) >= batch_size:
                processed_chunks += flush_batch(pending, model, batch_size)
                pending.clear()

    if pending and not dry_run:
        processed_chunks += flush_batch(pending, model, batch_size)
        pending.clear()

    return processed_records, processed_chunks


def delete_stale_chunks(record: SourceRecord, keep_chunk_count: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM record_embeddings
            WHERE source_table = %s
              AND source_id = %s
              AND chunk_index >= %s
            """,
            [record.source_table, record.source_id, keep_chunk_count],
        )


def flush_batch(
    pending: list[tuple[SourceRecord, dict[str, str | int]]],
    model: Any,
    batch_size: int,
) -> int:
    """청크 배치를 임베딩한 뒤 record_embeddings에 upsert 한다."""

    texts = [str(chunk["content"]) for _, chunk in pending]

    # KURE-v1은 sentence-transformers 모델이므로 문서 목록을 한 번에 encode한다.
    # 저장과 검색 모두 같은 모델과 정규화 옵션을 써야 cosine distance 비교가 의미 있다.
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    rows: list[EmbeddingRow] = []
    for (record, chunk), vector in zip(pending, vectors, strict=True):
        rows.append(
            EmbeddingRow(
                source_table=record.source_table,
                source_id=record.source_id,
                chunk_index=int(chunk["chunk_index"]),
                title=record.title,
                content=str(chunk["content"]),
                embedding=[float(value) for value in vector.tolist()],
                metadata=record.metadata,
            )
        )

    save_embedding_rows(rows)
    return len(rows)


def save_embedding_rows(rows: list[EmbeddingRow]) -> None:
    """EmbeddingRow 목록을 record_embeddings에 저장한다."""

    if not rows:
        return

    with transaction.atomic(), connection.cursor() as cursor:
        for row in rows:
            cursor.execute(
                """
                INSERT INTO record_embeddings (
                    source_table,
                    source_id,
                    chunk_index,
                    title,
                    content,
                    embedding,
                    metadata,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s::jsonb, NOW())
                ON CONFLICT (source_table, source_id, chunk_index)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                [
                    row.source_table,
                    row.source_id,
                    row.chunk_index,
                    row.title,
                    row.content,
                    vector_to_sql_literal(row.embedding),
                    json.dumps(row.metadata, ensure_ascii=False),
                ],
            )


def vector_to_sql_literal(vector: list[float]) -> str:
    """Python float 리스트를 pgvector가 읽을 수 있는 문자열로 바꾼다."""

    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def get_hf_token() -> str | None:
    """환경변수에 저장된 Hugging Face 토큰을 찾아 반환한다."""

    for env_name in HF_TOKEN_ENV_NAMES:
        token = os.environ.get(env_name)
        if token:
            return token
    return None


def main() -> None:
    args = parse_args()

    if args.batch_size <= 0:
        raise ValueError("batch-size는 1 이상이어야 한다.")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("limit은 1 이상이어야 한다.")

    if args.reset and not args.dry_run:
        reset_embeddings(args.source)
        print(f"기존 임베딩 삭제 완료: source={args.source}")

    if args.dry_run:
        model = None
    else:
        from sentence_transformers import SentenceTransformer

        token = get_hf_token()
        print(f"임베딩 모델 로딩 중: {args.model}")
        model = SentenceTransformer(args.model, token=token)

    records = iter_records(args.source, limit=args.limit)
    record_count, chunk_count = build_embedding_rows(
        records=records,
        model=model,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    mode = "dry_run" if args.dry_run else "saved"
    print(f"{mode}: records={record_count}, chunks={chunk_count}")


if __name__ == "__main__":
    main()
