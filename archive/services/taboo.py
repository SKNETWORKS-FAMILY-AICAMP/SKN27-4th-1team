from typing import Any

from django.utils import timezone

from archive.models import Superstition


TABOO_RESULT_LIMIT = 500


def serialize_taboo(taboo: Superstition) -> dict[str, Any]:
    """금기 모델 객체를 API 응답에 맞는 딕셔너리로 변환한다."""
    return {
        "id": taboo.id,
        "index": taboo.source_ref_id or str(taboo.id),
        "content": taboo.content,
        "category": taboo.category or "미분류",
        "region": taboo.region or "지역 미상",
        "source": taboo.source,
        "source_ref_id": taboo.source_ref_id,
    }


def list_taboos(limit: int = TABOO_RESULT_LIMIT):
    """금기 목록을 ID 순서로 제한 개수만큼 조회한다."""
    return Superstition.objects.order_by("id")[:limit]


def search_taboos(keyword: str, limit: int = TABOO_RESULT_LIMIT):
    """금기 내용, 분류, 지역, 출처 필드에서 키워드를 명시적으로 검색한다."""
    keyword = str(keyword or "").strip()
    if not keyword:
        return list_taboos(limit)

    taboos = (
        Superstition.objects.filter(content__icontains=keyword)
        | Superstition.objects.filter(category__icontains=keyword)
        | Superstition.objects.filter(region__icontains=keyword)
        | Superstition.objects.filter(source__icontains=keyword)
        | Superstition.objects.filter(source_ref_id__icontains=keyword)
    )
    if keyword.isdecimal():
        taboos = taboos | Superstition.objects.filter(id=int(keyword))

    return taboos.order_by("id").distinct()[:limit]


def get_today_taboo() -> Superstition | None:
    """오늘 날짜를 기준으로 고정된 일일 금기 하나를 선택한다."""
    count = Superstition.objects.count()
    if count == 0:
        return None

    today = timezone.localdate().isoformat()
    offset = sum(ord(char) for char in today) % count
    return Superstition.objects.order_by("id")[offset]


def get_taboo(taboo_id: int) -> Superstition:
    """ID로 금기 상세 기록을 조회한다."""
    return Superstition.objects.get(id=taboo_id)
