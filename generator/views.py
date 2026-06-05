from django.shortcuts import render
from django.http import JsonResponse
import json
from .services import generate_ghost_story_pipeline

def goeijejoso(request):
    return render(request, 'generator/storymaker.html')

def generate_story_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pipeline_data = {
                'region': data.get('region', '미상'),
                'location': data.get('place', '미상'),
                'anomaly_type': data.get('entityType', '미상'),
                'taboo': data.get('taboo', '미상'),
                'time': data.get('time', '미상'),
                'condition': data.get('condition', '미상'),
                'outcome': data.get('ending', '미상')
            }
            result = generate_ghost_story_pipeline(pipeline_data)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                "title": "오류 발생", 
                "content": str(e), 
                "summary": "서버 오류"
            }, status=400)
    return JsonResponse({"error": "Invalid method"}, status=405)
