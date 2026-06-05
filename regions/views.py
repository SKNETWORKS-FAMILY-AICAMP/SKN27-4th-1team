from django.shortcuts import render
from django.http import JsonResponse
from .services import query_region_relations

def jidogam_view(request):
    """Renders the regions map template."""
    return render(request, 'regions/jidogam.html')

def region_query_api(request):
    """API endpoint to query region details (places & horror stories) from Neo4j."""
    region_name = request.GET.get('region', '').strip()
    if not region_name:
        return JsonResponse({'status': 'empty', 'results': []})
    
    results = query_region_relations(region_name)
    return JsonResponse({
        'status': 'success',
        'region': region_name,
        'results': results
    })

