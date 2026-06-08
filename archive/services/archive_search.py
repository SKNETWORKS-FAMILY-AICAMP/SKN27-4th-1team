import os
import random
import socket
from typing import Any

from django.db import DatabaseError

from archive.models import HorrorStory, MythEntity, Superstition
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
    limit: int = 5,
    body_limit: int = 1800,
) -> list[dict[str, Any]]:
    """정제 키워드 검색 후 결과가 없으면 원문 토큰으로 한 번 더 검색한다."""
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
            return search_results

        fallback_keywords = extract_fallback_keywords(question, keywords)
        if not fallback_keywords:
            return []

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
        return search_archive_records_by_keywords(
            fallback_search_keywords,
            limit=limit,
            body_limit=body_limit,
        )
    finally:
        if neo4j_driver is not None:
            neo4j_driver.close()


def get_random_archive_suggestions(limit: int = 3, body_limit: int = 40) -> list[str]:
    """일반 대화에서 제안할 archive 주제를 DB에서 무작위로 가져온다."""
    query_builders = [
        lambda: HorrorStory.objects.order_by("?").values_list("title", flat=True)[:limit],
        lambda: MythEntity.objects.order_by("?").values_list("name", flat=True)[:limit],
        lambda: Superstition.objects.order_by("?").values_list("content", flat=True)[:limit],
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
    """키워드별 명시적 필터를 합쳐 괴담, 존재, 금기 기록을 검색한다."""
    records = []
    story_queryset = HorrorStory.objects.none()
    entity_queryset = MythEntity.objects.none()
    superstition_queryset = Superstition.objects.none()

    for keyword in keywords:
        story_queryset = (
            story_queryset
            | HorrorStory.objects.filter(title__icontains=keyword)
            | HorrorStory.objects.filter(content__icontains=keyword)
            | HorrorStory.objects.filter(preview__icontains=keyword)
            | HorrorStory.objects.filter(region__icontains=keyword)
            | HorrorStory.objects.filter(category__icontains=keyword)
        )
        entity_queryset = (
            entity_queryset
            | MythEntity.objects.filter(name__icontains=keyword)
            | MythEntity.objects.filter(origin__icontains=keyword)
            | MythEntity.objects.filter(description__icontains=keyword)
            | MythEntity.objects.filter(behavior__icontains=keyword)
            | MythEntity.objects.filter(weakness__icontains=keyword)
            | MythEntity.objects.filter(history__icontains=keyword)
            | MythEntity.objects.filter(signs__icontains=keyword)
        )
        superstition_queryset = (
            superstition_queryset
            | Superstition.objects.filter(content__icontains=keyword)
            | Superstition.objects.filter(category__icontains=keyword)
            | Superstition.objects.filter(region__icontains=keyword)
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

    for entity in entity_queryset.distinct()[: limit * 3]:
        body = make_preview(
            entity.description,
            entity.behavior,
            entity.weakness,
            entity.history,
            entity.signs,
            "\n".join(entity.survival_rules or []),
            limit=body_limit,
        )
        if not is_relevant_record(
            keywords,
            strong_values=[entity.name, entity.origin, entity.signs],
            weak_values=[
                entity.description,
                entity.behavior,
                entity.weakness,
                entity.history,
                "\n".join(entity.survival_rules or []),
            ],
            single_keyword_weak_match_count=SINGLE_KEYWORD_WEAK_MATCH_COUNTS["myth_entity"],
        ):
            continue

        records.append({
            "id": entity.id,
            "name": entity.name,
            "body": body,
            "regions": clean_regions(entity.origin),
            "type": "myth_entity",
            "score": score_record_text(
                keywords,
                entity.name,
                entity.origin,
                entity.signs,
                entity.description,
                entity.behavior,
                entity.weakness,
                entity.history,
                "\n".join(entity.survival_rules or []),
            ),
        })

    for superstition in superstition_queryset.distinct()[: limit * 3]:
        body = make_preview(superstition.content, limit=body_limit)
        if not is_relevant_record(
            keywords,
            strong_values=[superstition.region, superstition.category],
            weak_values=[superstition.content],
            single_keyword_weak_match_count=SINGLE_KEYWORD_WEAK_MATCH_COUNTS["superstition"],
        ):
            continue

        records.append({
            "id": superstition.id,
            "name": superstition.content[:50],
            "body": body,
            "regions": clean_regions(superstition.region, superstition.category),
            "type": "superstition",
            "score": score_record_text(
                keywords,
                superstition.content,
                superstition.region,
                superstition.category,
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

    raise ValueError("지원하지 않는 archive 기록 타입입니다.")


def make_preview(*parts: Any, limit: int) -> str:
    """여러 본문 조각을 합친 뒤 프롬프트에 넣을 길이로 줄인다."""
    body = "\n".join(str(part).strip() for part in parts if part)
    if len(body) <= limit:
        return body

    return f"{body[:limit].rstrip()}..."


def clean_regions(*values: Any) -> list[str]:
    """빈 지역값을 제거하고 화면 표시용 지역 목록을 만든다."""
    return [str(value).strip() for value in values if str(value).strip()]
