from django.db.models import Q
from django.utils import timezone

from archive.models import Superstition


TABOO_RESULT_LIMIT = 500


def serialize_taboo(taboo):
    return {
        "id": taboo.id,
        "index": taboo.source_ref_id or str(taboo.id),
        "content": taboo.content,
        "category": taboo.category or "미분류",
        "region": taboo.region or "지역 미상",
        "source": taboo.source,
        "source_ref_id": taboo.source_ref_id,
    }


def list_taboos(limit=TABOO_RESULT_LIMIT):
    return Superstition.objects.order_by("id")[:limit]


def search_taboos(keyword, limit=TABOO_RESULT_LIMIT):
    keyword = str(keyword or "").strip()
    if not keyword:
        return list_taboos(limit)

    filters = (
        Q(content__icontains=keyword)
        | Q(category__icontains=keyword)
        | Q(region__icontains=keyword)
        | Q(source__icontains=keyword)
        | Q(source_ref_id__icontains=keyword)
    )
    if keyword.isdecimal():
        filters |= Q(id=int(keyword))

    return (
        Superstition.objects.filter(filters)
        .order_by("id")
        .distinct()[:limit]
    )


def get_today_taboo():
    count = Superstition.objects.count()
    if count == 0:
        return None

    today = timezone.localdate().isoformat()
    offset = sum(ord(char) for char in today) % count
    return Superstition.objects.order_by("id")[offset]


def get_taboo(taboo_id):
    return Superstition.objects.get(id=taboo_id)
