from django.shortcuts import render
from django.http import JsonResponse
from .services import (
    query_region_relations, get_region_list,
    get_cities_by_region, city_nodes_exist, build_city_nodes, get_story_body
)


def jidogam(request):
    return render(request, 'regions/regioninfo.html')


def region_list_api(request):
    regions = get_region_list()
    return JsonResponse({'status': 'success', 'regions': regions})


def region_query_api(request):
    region_name = request.GET.get('region', '').strip()
    if not region_name:
        return JsonResponse({'status': 'empty', 'results': []})

    results = query_region_relations(region_name)
    return JsonResponse({
        'status': 'success',
        'region': region_name,
        'results': results
    })


def city_list_api(request):
    """Region 클릭 시 도시 폴더 트리를 반환한다.
    City 노드가 있으면 폴더 트리, 없으면 스토리 목록을 직접 반환한다."""
    region_name = request.GET.get('region', '').strip()
    if not region_name:
        return JsonResponse({'status': 'empty', 'cities': [], 'stories': []})

    if not city_nodes_exist():
        build_city_nodes()

    cities = get_cities_by_region(region_name)

    # City 노드가 없는 지역은 스토리를 직접 반환
    if not cities:
        results = query_region_relations(region_name)
        stories = []
        for place in results:
            stories.extend(place.get('stories', []))
        return JsonResponse({'status': 'success', 'region': region_name, 'cities': [], 'stories': stories})

    return JsonResponse({'status': 'success', 'region': region_name, 'cities': cities, 'stories': []})


def story_detail_api(request):
    """스토리 전체 본문을 반환한다."""
    story_id = request.GET.get('id', '').strip()
    if not story_id:
        return JsonResponse({'status': 'empty'}, status=400)

    data = get_story_body(story_id)
    if not data:
        return JsonResponse({'status': 'not_found'}, status=404)

    return JsonResponse({'status': 'success', **data})
