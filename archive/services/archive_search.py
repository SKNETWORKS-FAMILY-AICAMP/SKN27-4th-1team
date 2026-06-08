from typing import Any

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
    search_results = search_archive_records_by_keywords(
        keywords,
        limit=limit,
        body_limit=body_limit,
    )
    if search_results:
        return search_results

    fallback_keywords = extract_fallback_keywords(question, keywords)
    if not fallback_keywords:
        return []

    return search_archive_records_by_keywords(
        fallback_keywords,
        limit=limit,
        body_limit=body_limit,
    )


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
