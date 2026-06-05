from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError

from .models import HorrorStory, MythEntity, Superstition
from . import services


SEARCH_RESULT_LIMIT = 10
BODY_PREVIEW_LIMIT = 1200


def index(request):
    return render(request, 'archive/index.html')


def chatbot(request):
    return render(request, 'archive/chatbot.html')


def chatbot_view(request):
    return chatbot(request)


def sillok_search_api(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'status': 'empty', 'results': []})

    results = search_archive_records(query)
    llm_response = make_search_message(query, len(results))

    conversation_history = request.session.get('conversation_history', [])
    conversation_history.append({"role": "user", "content": query})
    conversation_history.append({"role": "assistant", "content": llm_response})
    request.session['conversation_history'] = conversation_history[-10:]
    request.session.modified = True

    request.session['last_search_results'] = [
        {
            'id': r['id'],
            'name': r['name'],
            'body': r['body'],
            'regions': r['regions'],
            'type': r['type'],
        }
        for r in results
    ]

    return JsonResponse({
        'status': 'success',
        'query': query,
        'results': results,
        'llm_response': llm_response
    })


def archive(request):
    return render(request, 'archive/archive.html')


def taboo_list_api(request):
    try:
        taboos = [services.serialize_taboo(taboo) for taboo in services.list_taboos()]
        total_count = Superstition.objects.count()
    except DatabaseError:
        return JsonResponse({
            'status': 'error',
            'message': '금기 테이블을 사용할 수 없습니다. migration과 DB 상태를 확인해 주세요.',
            'taboos': [],
        }, status=503)

    return JsonResponse({
        'status': 'success',
        'query': '',
        'count': len(taboos),
        'total_count': total_count,
        'taboos': taboos,
    })


def taboo_search_api(request):
    query = request.GET.get('q', '').strip()
    try:
        taboos = [services.serialize_taboo(taboo) for taboo in services.search_taboos(query)]
        total_count = Superstition.objects.count()
    except DatabaseError:
        return JsonResponse({
            'status': 'error',
            'message': '금기 테이블을 사용할 수 없습니다. migration과 DB 상태를 확인해 주세요.',
            'taboos': [],
        }, status=503)

    return JsonResponse({
        'status': 'success',
        'query': query,
        'count': len(taboos),
        'total_count': total_count,
        'taboos': taboos,
    })


def today_taboo_api(request):
    try:
        taboo = services.get_today_taboo()
    except DatabaseError:
        return JsonResponse({
            'status': 'error',
            'message': '금기 테이블을 사용할 수 없습니다. migration과 DB 상태를 확인해 주세요.',
        }, status=503)

    if taboo is None:
        return JsonResponse({
            'status': 'empty',
            'message': '등록된 금기가 없습니다.',
        })

    return JsonResponse({
        'status': 'success',
        'taboo': services.serialize_taboo(taboo),
    })


def taboo_detail_api(request, taboo_id):
    try:
        taboo = services.get_taboo(taboo_id)
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'not_found',
            'message': '해당 금기를 찾을 수 없습니다.',
        }, status=404)
    except DatabaseError:
        return JsonResponse({
            'status': 'error',
            'message': '금기 테이블을 사용할 수 없습니다. migration과 DB 상태를 확인해 주세요.',
        }, status=503)

    return JsonResponse({
        'status': 'success',
        'taboo': services.serialize_taboo(taboo),
    })


def search_archive_records(query):
    results = []

    stories = (
        HorrorStory.objects.filter(title__icontains=query)
        | HorrorStory.objects.filter(content__icontains=query)
        | HorrorStory.objects.filter(preview__icontains=query)
        | HorrorStory.objects.filter(region__icontains=query)
        | HorrorStory.objects.filter(category__icontains=query)
    ).distinct()[:SEARCH_RESULT_LIMIT]

    for story in stories:
        results.append({
            "id": story.id,
            "name": story.title,
            "body": make_preview(story.preview, story.content),
            "regions": clean_regions(story.region),
            "type": "horror_story",
        })

    entities = (
        MythEntity.objects.filter(name__icontains=query)
        | MythEntity.objects.filter(origin__icontains=query)
        | MythEntity.objects.filter(description__icontains=query)
        | MythEntity.objects.filter(behavior__icontains=query)
        | MythEntity.objects.filter(weakness__icontains=query)
        | MythEntity.objects.filter(history__icontains=query)
        | MythEntity.objects.filter(signs__icontains=query)
    ).distinct()[:SEARCH_RESULT_LIMIT]

    for entity in entities:
        results.append({
            "id": entity.id,
            "name": entity.name,
            "body": make_preview(
                entity.description,
                entity.behavior,
                entity.weakness,
                entity.history,
                entity.signs,
                "\n".join(entity.survival_rules or []),
            ),
            "regions": clean_regions(entity.origin),
            "type": "myth_entity",
        })

    superstitions = (
        Superstition.objects.filter(content__icontains=query)
        | Superstition.objects.filter(category__icontains=query)
        | Superstition.objects.filter(region__icontains=query)
    ).distinct()[:SEARCH_RESULT_LIMIT]

    for superstition in superstitions:
        results.append({
            "id": superstition.id,
            "name": superstition.content[:50],
            "body": superstition.content,
            "regions": clean_regions(superstition.region, superstition.category),
            "type": "superstition",
        })

    return results[:SEARCH_RESULT_LIMIT]


def make_search_message(query, result_count):
    if result_count:
        return (
            f"'{query}' search returned {result_count} record(s). "
            "Select a number to open a record."
        )
    return f"No archive records found for '{query}'."


def make_preview(*parts):
    body = "\n".join(str(part).strip() for part in parts if part)
    if len(body) <= BODY_PREVIEW_LIMIT:
        return body
    return f"{body[:BODY_PREVIEW_LIMIT].rstrip()}..."


def clean_regions(*values):
    return [str(value).strip() for value in values if str(value).strip()]
