from django.shortcuts import render
from django.http import JsonResponse

from .models import HorrorStory, MythEntity, Superstition


SEARCH_RESULT_LIMIT = 10
BODY_PREVIEW_LIMIT = 1200


def index(request):
    return render(request, 'archive/index.html')


def sillokgwan(request):
    return render(request, 'archive/sillokgwan.html')


def sillokgwan_view(request):
    return sillokgwan(request)


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


def geumgirok(request):
    return render(request, 'archive/geumgirok.html')


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
