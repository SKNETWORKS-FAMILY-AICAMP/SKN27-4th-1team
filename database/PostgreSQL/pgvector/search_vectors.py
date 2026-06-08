"""pgvector에 저장된 record_embeddings에서 의미 기반 검색을 실행한다.

실행 위치는 프로젝트 루트 기준이다.

    python database/PostgreSQL/pgvector/search_vectors.py "폐교 음악실 소리"

검색어를 embed_records.py와 같은 KURE-v1 임베딩 모델로 임베딩한 뒤,
record_embeddings.embedding 컬럼과 cosine distance를 비교해 가까운 청크를 출력한다.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
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

from django.db import connection  # noqa: E402

from embed_records import (  # noqa: E402
    DEFAULT_MODEL_NAME,
    SOURCE_CHOICES,
    get_hf_token,
    vector_to_sql_literal,
)


DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class SearchResult:
    """검색 결과 1건을 출력하기 쉬운 형태로 묶는다."""

    rank: int
    source_table: str
    source_id: int
    chunk_index: int
    title: str
    content_preview: str
    similarity: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="record_embeddings 테이블에서 pgvector 유사도 검색을 실행한다.",
    )
    parser.add_argument("query", help="검색할 문장 또는 키워드.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"출력할 검색 결과 개수. 기본값은 {DEFAULT_TOP_K}.",
    )
    parser.add_argument(
        "--source",
        choices=SOURCE_CHOICES,
        default="all",
        help="검색할 원본 테이블 범위. 기본값은 all.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help=f"검색어 임베딩에 사용할 모델. 기본값은 {DEFAULT_MODEL_NAME}.",
    )
    parser.add_argument(
        "--preview-length",
        type=int,
        default=180,
        help="결과 본문 미리보기 길이. 기본값은 180.",
    )
    return parser.parse_args()


def embed_query(query: str, model_name: str) -> list[float]:
    """검색어를 pgvector 검색에 사용할 1024차원 벡터로 변환한다."""

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, token=get_hf_token())

    # 저장된 본문 임베딩과 같은 KURE-v1 모델과 정규화 옵션으로 검색어도 벡터화한다.
    vector = model.encode(
        query,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [float(value) for value in vector.tolist()]


def search_embeddings(
    *,
    query_vector: list[float],
    source: str,
    top_k: int,
    preview_length: int,
) -> list[SearchResult]:
    """record_embeddings에서 검색 벡터와 가까운 청크를 조회한다."""

    vector_literal = vector_to_sql_literal(query_vector)
    source_filter = ""
    params: list[Any] = [preview_length, vector_literal]

    if source != "all":
        source_filter = "WHERE source_table = %s"
        params.append(source)

    params.extend([vector_literal, top_k])

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                source_table,
                source_id,
                chunk_index,
                title,
                LEFT(content, %s) AS content_preview,
                1 - (embedding <=> %s::vector) AS similarity
            FROM record_embeddings
            {source_filter}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            params,
        )

        rows = cursor.fetchall()

    return [
        SearchResult(
            rank=index + 1,
            source_table=row[0],
            source_id=row[1],
            chunk_index=row[2],
            title=row[3],
            content_preview=" ".join(str(row[4] or "").split()),
            similarity=float(row[5]),
        )
        for index, row in enumerate(rows)
    ]


def print_results(query: str, results: list[SearchResult]) -> None:
    print(f"검색어: {query}")
    print(f"검색 결과: {len(results)}건")
    print()

    if not results:
        print("검색 결과가 없습니다. record_embeddings에 임베딩 데이터가 있는지 확인하세요.")
        return

    for result in results:
        print(
            f"{result.rank}. {result.source_table} #{result.source_id} "
            f"chunk={result.chunk_index} similarity={result.similarity:.4f}"
        )
        print(f"   제목: {result.title}")
        print(f"   내용: {result.content_preview}")
        print()


def main() -> None:
    args = parse_args()

    if args.top_k <= 0:
        raise ValueError("top-k는 1 이상이어야 한다.")
    if args.preview_length <= 0:
        raise ValueError("preview-length는 1 이상이어야 한다.")

    query_vector = embed_query(args.query, args.model)
    results = search_embeddings(
        query_vector=query_vector,
        source=args.source,
        top_k=args.top_k,
        preview_length=args.preview_length,
    )
    print_results(args.query, results)


if __name__ == "__main__":
    main()
