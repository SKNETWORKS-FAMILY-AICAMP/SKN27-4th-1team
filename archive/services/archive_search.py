import os
import random
import socket
from functools import lru_cache
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, connection

from archive.models import DcinsidePost, HorrorStory, MythEntity, Superstition
from archive.services.keyword_extractor import extract_fallback_keywords
from archive.services.search_policy import SINGLE_KEYWORD_WEAK_MATCH_COUNTS
from archive.services.search_relevance import (
    is_generic_record_name,
    is_relevant_record,
    score_record_text,
)


def search_archive_records_for_question(
    question: str,
    keywords: list[str],
    semantic_query: str = "",
    limit: int = 5,
    body_limit: int = 1800,
) -> list[dict[str, Any]]:
    """의미 기반 검색과 정제 키워드 검색으로 관련 기록을 찾는다."""
    semantic_results = search_archive_records_by_semantic_query(
        semantic_query,
        limit=limit,
        body_limit=body_limit,
    )
    neo4j_driver = get_neo4j_driver()
    try:
        related_keywords = []
        if neo4j_driver is not None:
            related_keywords = get_neo4j_related_keywords(
                keywords,
                limit=limit,
                driver=neo4j_driver,
            )

        search_keywords = merge_keywords(keywords, related_keywords)
        search_results = search_archive_records_by_keywords(
            search_keywords,
            limit=limit,
            body_limit=body_limit,
        )
        if search_results:
            return merge_archive_search_results(
                semantic_results,
                search_results,
                limit=limit,
            )

        fallback_keywords = extract_fallback_keywords(question, keywords)
        if not fallback_keywords:
            return semantic_results[:limit]

        related_fallback_keywords = []
        if neo4j_driver is not None:
            related_fallback_keywords = get_neo4j_related_keywords(
                fallback_keywords,
                limit=limit,
                driver=neo4j_driver,
            )

        fallback_search_keywords = merge_keywords(
            fallback_keywords,
            related_fallback_keywords,
        )
        fallback_results = search_archive_records_by_keywords(
            fallback_search_keywords,
            limit=limit,
            body_limit=body_limit,
        )
        return merge_archive_search_results(
            semantic_results,
            fallback_results,
            limit=limit,
        )
    finally:
        if neo4j_driver is not None:
            neo4j_driver.close()


def search_archive_records_by_semantic_query(
    semantic_query: str,
    limit: int = 5,
    body_limit: int = 1800,
) -> list[dict[str, Any]]:
    """pgvector record_embeddings에서 content 의미 유사도가 높은 기록을 찾는다."""
    cleaned_query = semantic_query.strip()
    if not cleaned_query:
        return []

    query_vector = embed_semantic_query(cleaned_query)
    if not query_vector:
        return []

    rows = fetch_semantic_search_rows(
        query_vector,
        limit=limit,
        preview_length=body_limit,
        min_similarity=get_semantic_min_similarity(),
    )
    records = []
    for row in rows:
        record = build_record_from_embedding_row(row, body_limit=body_limit)
        if not record:
            continue

        records.append(record)

    return records


def embed_semantic_query(query: str) -> list[float]:
    """검색 문장을 저장된 record_embeddings와 같은 모델의 query 벡터로 바꾼다."""
    model_name = get_embedding_model_name()
    if not model_name:
        return []

    try:
        model = get_embedding_model(model_name)
        vector = model.encode(
            f"query: {query}",
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        values = [float(value) for value in vector.tolist()]
    except Exception:
        return []

    expected_dimension = get_embedding_output_dimension()
    if len(values) != expected_dimension:
        return []

    return values


def get_embedding_model_name() -> str:
    """archive 의미 검색에 사용할 임베딩 모델명을 읽는다."""
    return os.getenv(
        "ARCHIVE_EMBEDDING_MODEL_NAME",
        "intfloat/multilingual-e5-base",
    ).strip()


def get_embedding_output_dimension() -> int:
    """archive 의미 검색 임베딩 차원을 읽는다."""
    return int(os.getenv("ARCHIVE_EMBEDDING_OUTPUT_DIMENSION", "768"))


def get_semantic_min_similarity() -> float:
    """archive 의미 검색 결과로 인정할 최소 유사도를 읽는다."""
    return float(os.getenv("ARCHIVE_SEMANTIC_MIN_SIMILARITY", "0.5"))


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str) -> Any:
    """동일 프로세스에서 임베딩 모델을 재사용한다."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def fetch_semantic_search_rows(
    query_vector: list[float],
    limit: int,
    preview_length: int,
    min_similarity: float,
) -> list[tuple[Any, ...]]:
    """record_embeddings.content 청크의 embedding과 query vector를 비교한다."""
    vector_literal = vector_to_sql_literal(query_vector)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    source_table,
                    source_id,
                    chunk_index,
                    title,
                    LEFT(content, %s) AS content_preview,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM record_embeddings
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [
                    preview_length,
                    vector_literal,
                    vector_literal,
                    min_similarity,
                    vector_literal,
                    limit,
                ],
            )
            return cursor.fetchall()
    except Exception:
        return []


def build_record_from_embedding_row(
    row: tuple[Any, ...],
    body_limit: int,
) -> dict[str, Any]:
    """record_embeddings row를 기존 archive 검색 결과 dict로 변환한다."""
    source_table = str(row[0])
    source_id = int(row[1])
    record_type = get_record_type_for_source_table(source_table)
    if not record_type:
        return {}

    try:
        record = get_archive_record(record_type, source_id, body_limit=body_limit)
    except ObjectDoesNotExist:
        return {}

    similarity = float(row[5])
    record["score"] = similarity
    record["semantic_similarity"] = similarity
    record["semantic_chunk_index"] = int(row[2])
    record["semantic_preview"] = str(row[4] or "").strip()
    return record


def get_record_type_for_source_table(source_table: str) -> str:
    """임베딩 원본 테이블명을 archive record type으로 바꾼다."""
    if source_table == HorrorStory._meta.db_table:
        return "horror_story"

    elif source_table == DcinsidePost._meta.db_table:
        return "dcinside_post"

    return ""


def merge_archive_search_results(
    *result_groups: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """semantic 결과를 우선하고 키워드 결과를 뒤에 보강해 중복 없이 합친다."""
    merged_results = []
    seen_keys = set()
    for result_group in result_groups:
        for record in result_group:
            record_key = (record.get("type"), record.get("id"))
            if record_key in seen_keys:
                continue

            merged_results.append(record)
            seen_keys.add(record_key)
            if len(merged_results) >= limit:
                return merged_results

    return merged_results


def vector_to_sql_literal(vector: list[float]) -> str:
    """Python float 리스트를 pgvector literal 문자열로 변환한다."""
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def get_random_archive_suggestions(limit: int = 3, body_limit: int = 40) -> list[str]:
    """일반 대화에서 제안할 archive 주제를 DB에서 무작위로 가져온다."""
    query_builders = [
        lambda: HorrorStory.objects.order_by("?").values_list("title", flat=True)[:limit],
        lambda: DcinsidePost.objects.order_by("?").values_list("content", flat=True)[:limit],
    ]
    random.shuffle(query_builders)

    suggestions = []
    try:
        for build_query in query_builders:
            for value in build_query():
                suggestion = make_preview(value, limit=body_limit)
                if not suggestion:
                    continue

                if suggestion in suggestions:
                    continue

                suggestions.append(suggestion)
                if len(suggestions) >= limit:
                    return suggestions
    except DatabaseError:
        return []

    return suggestions


def get_random_archive_records(
    limit: int = 5,
    body_limit: int = 1800,
) -> list[dict[str, Any]]:
    """구체 검색어가 없을 때 여러 archive 원천에서 후보 기록을 가져온다."""
    query_builders = [
        ("horror_story", lambda: HorrorStory.objects.order_by("?").values_list("id", flat=True)[:limit]),
        ("dcinside_post", lambda: DcinsidePost.objects.order_by("?").values_list("id", flat=True)[:limit]),
    ]
    random.shuffle(query_builders)

    records = []
    per_source_limit = max(1, (limit // len(query_builders)) + 1)
    try:
        for record_type, build_query in query_builders:
            for record_id in build_query()[:per_source_limit]:
                records.append(
                    get_archive_record(
                        record_type,
                        int(record_id),
                        body_limit=body_limit,
                    )
                )
    except DatabaseError:
        return []

    random.shuffle(records)
    return records[:limit]


def get_neo4j_related_keywords(
    keywords: list[str],
    limit: int = 5,
    min_length: int = 2,
    max_length: int = 60,
    driver: Any = None,
) -> list[str]:
    """Neo4j 관계 그래프에서 검색어와 인접한 노드 이름을 연관 키워드로 가져온다."""
    normalized_keywords = [
        keyword.lower().strip()
        for keyword in keywords
        if keyword and keyword.strip()
    ]
    if not normalized_keywords:
        return []

    active_driver = driver or get_neo4j_driver()
    if active_driver is None:
        return []

    try:
        with active_driver.session() as session:
            records = session.run(
                """
                MATCH (n)
                WHERE (
                    n:Story OR n:Legend OR n:Yokai OR n:SCP OR
                    n:Region OR n:Place OR n:Origin OR n:Location
                )
                AND any(keyword IN $keywords WHERE
                    toLower(coalesce(n.name, "")) CONTAINS keyword OR
                    toLower(coalesce(n.body, "")) CONTAINS keyword OR
                    toLower(coalesce(n.text, "")) CONTAINS keyword
                )
                OPTIONAL MATCH (n)-[]-(related)
                WITH [candidate IN [n.name, related.name] WHERE candidate IS NOT NULL] AS names
                UNWIND names AS name
                WITH trim(toString(name)) AS name, count(*) AS mention_count
                WHERE name <> "" AND NOT toLower(name) IN $keywords
                RETURN name
                ORDER BY mention_count DESC, size(name) ASC
                LIMIT $limit
                """,
                keywords=normalized_keywords,
                limit=limit,
            )
            return filter_related_keywords(
                [record["name"] for record in records],
                keywords,
                min_length=min_length,
                max_length=max_length,
            )
    except Exception:
        return []
    finally:
        if driver is None:
            active_driver.close()


def get_neo4j_driver() -> Any:
    """archive 검색에서 사용할 Neo4j 드라이버를 만든다. 연결 실패 시 None을 반환한다."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return None

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not user or not password:
        return None

    try:
        host_part = uri.split("//")[1].split(":")[0]
        socket.gethostbyname(host_part)
    except Exception:
        return None

    try:
        return GraphDatabase.driver(
            uri,
            auth=(user, password),
        )
    except Exception:
        return None


def filter_related_keywords(
    candidates: list[str],
    original_keywords: list[str],
    min_length: int,
    max_length: int,
) -> list[str]:
    """원본 키워드와 중복되거나 검색에 부적합한 연관 키워드를 제거한다."""
    normalized_originals = {
        keyword.lower().strip()
        for keyword in original_keywords
        if keyword and keyword.strip()
    }
    filtered_keywords = []
    seen_keywords = set()
    for candidate in candidates:
        keyword = str(candidate).strip()
        normalized_keyword = keyword.lower()
        if not keyword:
            continue

        if normalized_keyword in normalized_originals:
            continue

        if normalized_keyword in seen_keywords:
            continue

        if len(keyword) < min_length:
            continue

        if len(keyword) > max_length:
            continue

        filtered_keywords.append(keyword)
        seen_keywords.add(normalized_keyword)

    return filtered_keywords


def merge_keywords(*keyword_groups: list[str]) -> list[str]:
    """여러 키워드 목록을 순서 유지 중복 제거 방식으로 합친다."""
    merged_keywords = []
    seen_keywords = set()
    for keyword_group in keyword_groups:
        for keyword in keyword_group:
            normalized_keyword = str(keyword).lower().strip()
            if not normalized_keyword:
                continue

            if normalized_keyword in seen_keywords:
                continue

            merged_keywords.append(str(keyword).strip())
            seen_keywords.add(normalized_keyword)

    return merged_keywords


def search_archive_records_by_keywords(
    keywords: list[str],
    limit: int = 5,
    body_limit: int = 1800,
) -> list[dict[str, Any]]:
    """키워드별 명시적 필터를 합쳐 괴담과 DCInside 기록을 검색한다."""
    records = []
    story_queryset = HorrorStory.objects.none()
    dcinside_queryset = DcinsidePost.objects.none()

    for keyword in keywords:
        story_queryset = (
            story_queryset
            | HorrorStory.objects.filter(title__icontains=keyword)
            | HorrorStory.objects.filter(content__icontains=keyword)
            | HorrorStory.objects.filter(preview__icontains=keyword)
            | HorrorStory.objects.filter(region__icontains=keyword)
            | HorrorStory.objects.filter(category__icontains=keyword)
        )
        dcinside_queryset = (
            dcinside_queryset
            | DcinsidePost.objects.filter(content__icontains=keyword)
            | DcinsidePost.objects.filter(category__icontains=keyword)
            | DcinsidePost.objects.filter(region__icontains=keyword)
            | DcinsidePost.objects.filter(keywords__contains=[keyword])
        )

    for story in story_queryset.distinct()[: limit * 3]:
        body = make_preview(story.preview, story.content, limit=body_limit)
        if is_generic_record_name(story.title, keywords):
            continue

        if not is_relevant_record(
            keywords,
            strong_values=[story.title, story.region, story.category],
            weak_values=[story.content],
            single_keyword_weak_match_count=SINGLE_KEYWORD_WEAK_MATCH_COUNTS["horror_story"],
        ):
            continue

        records.append({
            "id": story.id,
            "name": story.title,
            "body": body,
            "regions": clean_regions(story.region),
            "type": "horror_story",
            "score": score_record_text(
                keywords,
                story.title,
                story.region,
                story.category,
                story.content,
            ),
        })

    for post in dcinside_queryset.distinct()[: limit * 3]:
        category_name = post.get_category_display()
        body = make_preview(post.content, limit=body_limit)
        if not is_relevant_record(
            keywords,
            strong_values=[post.region, category_name],
            weak_values=[post.content, " ".join(post.keywords or [])],
            single_keyword_weak_match_count=SINGLE_KEYWORD_WEAK_MATCH_COUNTS["dcinside_post"],
        ):
            continue

        records.append({
            "id": post.id,
            "name": make_dcinside_display_name(post.content),
            "body": body,
            "regions": clean_regions(post.region, category_name),
            "type": "dcinside_post",
            "score": score_record_text(
                keywords,
                post.region,
                category_name,
                post.content,
                " ".join(post.keywords or []),
            ),
        })

    records.sort(key=lambda record: record["score"], reverse=True)
    return records[:limit]


def get_archive_record(record_type: str, record_id: int, body_limit: int = 1800) -> dict[str, Any]:
    """타입과 ID로 단일 archive 원본 기록을 조회해 생성 파이프라인 입력 형태로 변환한다."""
    if record_type == "horror_story":
        story = HorrorStory.objects.get(id=record_id)
        body = make_preview(story.preview, story.content, limit=body_limit)
        return {
            "id": story.id,
            "name": story.title,
            "body": body,
            "regions": clean_regions(story.region),
            "type": "horror_story",
            "score": 1,
        }

    elif record_type == "myth_entity":
        entity = MythEntity.objects.get(id=record_id)
        body = make_preview(
            entity.description,
            entity.behavior,
            entity.weakness,
            entity.history,
            entity.signs,
            "\n".join(entity.survival_rules or []),
            limit=body_limit,
        )
        return {
            "id": entity.id,
            "name": entity.name,
            "body": body,
            "regions": clean_regions(entity.origin),
            "type": "myth_entity",
            "score": 1,
        }

    elif record_type == "superstition":
        superstition = Superstition.objects.get(id=record_id)
        return {
            "id": superstition.id,
            "name": superstition.content[:50],
            "body": make_preview(superstition.content, limit=body_limit),
            "regions": clean_regions(superstition.region, superstition.category),
            "type": "superstition",
            "score": 1,
        }

    elif record_type == "dcinside_post":
        post = DcinsidePost.objects.get(id=record_id)
        category_name = post.get_category_display()
        return {
            "id": post.id,
            "name": make_dcinside_display_name(post.content),
            "body": make_preview(post.content, limit=body_limit),
            "regions": clean_regions(post.region, category_name),
            "type": "dcinside_post",
            "score": 1,
        }

    raise ValueError("지원하지 않는 archive 기록 타입입니다.")


def make_preview(*parts: Any, limit: int) -> str:
    """여러 본문 조각을 합친 뒤 프롬프트에 넣을 길이로 줄인다."""
    body = "\n".join(str(part).strip() for part in parts if part)
    if len(body) <= limit:
        return body

    return f"{body[:limit].rstrip()}..."


def make_dcinside_display_name(
    content: str,
    title_limit: int = 40,
) -> str:
    """DCInside 수집 글은 별도 title 없이 본문 앞부분으로 표시명을 만든다."""
    content_preview = make_preview(content, limit=title_limit)
    if content_preview:
        return content_preview

    return "DCInside 공포 기록"


def clean_regions(*values: Any) -> list[str]:
    """빈 지역값을 제거하고 화면 표시용 지역 목록을 만든다."""
    return [str(value).strip() for value in values if str(value).strip()]
