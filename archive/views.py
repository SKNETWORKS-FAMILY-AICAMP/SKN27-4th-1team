from django.shortcuts import render
from django.http import JsonResponse
from .graph import search_graph


def sillokgwan_view(request):
    """Renders the main sillokgwan template."""
    return render(request, 'archive/sillokgwan.html')


def sillok_search_api(request):
    """API endpoint: runs LangGraph search pipeline and returns JSON."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'status': 'empty', 'results': []})

    conversation_history = request.session.get('conversation_history', [])

    result = search_graph.invoke({
        "query": query,
        "search_query": query,
        "conversation_history": conversation_history,
        "search_results": [],
        "is_certain": False,
        "picked_index": None,
        "llm_response": ""
    })

    picked_index = result["picked_index"]
    llm_response = result["llm_response"]
    all_results = result["search_results"]

    certain_results = []
    if picked_index is not None and all_results:
        try:
            idx = int(picked_index) - 1
            if 0 <= idx < len(all_results):
                certain_results = [all_results[idx]]
        except Exception:
            certain_results = []

    # Update conversation history (keep last 10 messages = 5 exchanges)
    conversation_history.append({"role": "user", "content": query})
    conversation_history.append({"role": "assistant", "content": llm_response})
    request.session['conversation_history'] = conversation_history[-10:]
    request.session.modified = True

    # Store for inline detail view (digit selection)
    request.session['last_search_results'] = [
        {'name': r['name'], 'body': r['body'], 'regions': r['regions'], 'type': r['type']}
        for r in certain_results
    ]

    return JsonResponse({
        'status': 'success',
        'query': query,
        'results': certain_results,
        'llm_response': llm_response
    })
