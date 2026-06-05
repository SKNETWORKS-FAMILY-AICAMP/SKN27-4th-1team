from django.shortcuts import render
from django.http import JsonResponse
from .services import query_region_relations, get_region_list


def jidogam(request):
    return render(request, 'regions/jidogam.html')


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
