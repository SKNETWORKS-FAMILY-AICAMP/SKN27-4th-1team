import json
from http import HTTPStatus

from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError

from .models import HorrorStory, MythEntity, Superstition
from .services.graph import run_archive_chatbot, run_archive_record_chatbot
from .services.session_state import (
    get_conversation_history,
    get_last_tts_text,
    save_conversation_history,
    save_last_search_results,
    save_last_tts_text,
)
from .services.taboo import (
    get_taboo,
    get_today_taboo,
    list_taboos,
    search_taboos,
    serialize_taboo,
)
from .services.tts import iter_audio_chunks, open_story_audio_stream


SEARCH_RESULT_LIMIT = 10
BODY_PREVIEW_LIMIT = 1200


def is_rate_limit_error(error: Exception) -> bool:
    """LLM 제공자의 호출 제한 오류인지 확인한다."""
    status_code = getattr(error, "status_code", None)
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return True

    response = getattr(error, "response", None)
    response_status_code = getattr(response, "status_code", None)
    if response_status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return True

    if error.__class__.__name__ == "RateLimitError":
        return True

    return False


def make_rate_limit_response(query: str) -> JsonResponse:
    """Groq 호출 제한 상황을 프론트에서 그대로 표시할 JSON 응답으로 만든다."""
    return JsonResponse({
        'status': 'rate_limited',
        'query': query,
        'results': [],
        'llm_response': 'Groq 호출 한도가 잠시 초과됐습니다. 잠시 후 다시 시도해 주세요.',
    }, status=HTTPStatus.TOO_MANY_REQUESTS)


def index(request):
    """archive 앱의 첫 진입 화면을 렌더링한다."""
    return render(request, 'archive/index.html')


def chatbot(request):
    """괴담 조회 챗봇 화면을 렌더링한다."""
    return render(request, 'archive/chatbot.html')


def chatbot_view(request):
    """이전 이름으로 들어온 챗봇 뷰 호출을 현재 뷰로 연결한다."""
    return chatbot(request)


def sillok_search_api(request):
    """사용자 질문을 받아 괴담 검색 목록 또는 일반 대화 응답을 JSON으로 반환한다."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'status': 'empty', 'results': []})

    conversation_history = get_conversation_history(request)
    try:
        chatbot_result = run_archive_chatbot(query, conversation_history)
    except DatabaseError:
        return JsonResponse({
            'status': 'error',
            'query': query,
            'results': [],
            'llm_response': '괴담 데이터베이스를 사용할 수 없습니다. DB 상태를 확인해 주세요.',
        }, status=503)
    except Exception as error:
        if is_rate_limit_error(error):
            return make_rate_limit_response(query)

        return JsonResponse({
            'status': 'error',
            'query': query,
            'results': [],
            'llm_response': 'LLM 생성 중 오류가 발생했습니다. Groq API와 모델 상태를 확인해 주세요.',
        }, status=503)

    results = chatbot_result.get('results', [])
    llm_response = chatbot_result.get('llm_response', '')
    conversation_history.append({"role": "user", "content": query})
    conversation_history.append({"role": "assistant", "content": llm_response})
    save_conversation_history(request, conversation_history)
    save_last_search_results(request, results)
    save_last_tts_text(request, "")

    return JsonResponse({
        'status': chatbot_result.get('status', 'success'),
        'query': query,
        'intent': chatbot_result.get('intent', ''),
        'keywords': chatbot_result.get('keywords', []),
        'results': results,
        'source_story': chatbot_result.get('source_story', {}),
        'llm_response': llm_response,
        'evaluation': chatbot_result.get('evaluation', {}),
        'is_passed': chatbot_result.get('is_passed', False),
        'revised': chatbot_result.get('revised', False),
    })


def sillok_rewrite_api(request):
    """사용자가 선택한 특정 archive 기록을 기준으로 괴담 재구성 결과를 반환한다."""
    query = request.GET.get('q', '').strip()
    record_type = request.GET.get('type', '').strip()
    record_id = request.GET.get('id', '').strip()
    if not record_type or not record_id.isdecimal():
        return JsonResponse({
            'status': 'error',
            'query': query,
            'results': [],
            'llm_response': '선택한 기록 정보를 확인할 수 없습니다.',
        }, status=400)

    conversation_history = get_conversation_history(request)
    try:
        chatbot_result = run_archive_record_chatbot(
            query,
            record_type,
            int(record_id),
            conversation_history,
        )
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'not_found',
            'query': query,
            'results': [],
            'llm_response': '선택한 기록을 찾을 수 없습니다.',
        }, status=404)
    except DatabaseError:
        return JsonResponse({
            'status': 'error',
            'query': query,
            'results': [],
            'llm_response': '괴담 데이터베이스를 사용할 수 없습니다. DB 상태를 확인해 주세요.',
        }, status=503)
    except Exception as error:
        if is_rate_limit_error(error):
            return make_rate_limit_response(query)

        return JsonResponse({
            'status': 'error',
            'query': query,
            'results': [],
            'llm_response': 'LLM 생성 중 오류가 발생했습니다. Groq API와 모델 상태를 확인해 주세요.',
        }, status=503)

    results = chatbot_result.get('results', [])
    llm_response = chatbot_result.get('llm_response', '')
    conversation_history.append({"role": "user", "content": query or record_type})
    conversation_history.append({"role": "assistant", "content": llm_response})
    save_conversation_history(request, conversation_history)
    save_last_search_results(request, results)
    save_last_tts_text(request, llm_response)

    return JsonResponse({
        'status': chatbot_result.get('status', 'success'),
        'query': query,
        'intent': chatbot_result.get('intent', ''),
        'keywords': chatbot_result.get('keywords', []),
        'results': results,
        'source_story': chatbot_result.get('source_story', {}),
        'llm_response': llm_response,
        'evaluation': chatbot_result.get('evaluation', {}),
        'is_passed': chatbot_result.get('is_passed', False),
        'revised': chatbot_result.get('revised', False),
    })


def sillok_tts_api(request):
    """생성된 괴담 본문을 ElevenLabs 음성 MP3 스트림으로 반환한다."""
    if request.method == 'GET':
        text = get_last_tts_text(request).strip()
    elif request.method == 'POST':
        try:
            request_data = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '요청 본문을 확인할 수 없습니다.',
            }, status=400)

        text = str(request_data.get('text', '')).strip()
    elif request.method not in ['GET', 'POST']:
        return JsonResponse({
            'status': 'error',
            'message': 'GET 또는 POST 요청만 사용할 수 있습니다.',
        }, status=405)

    if not text:
        return JsonResponse({
            'status': 'empty',
            'message': '낭독할 괴담 본문이 없습니다.',
        }, status=400)

    try:
        audio_response = open_story_audio_stream(text)
    except ValueError as error:
        return JsonResponse({
            'status': 'error',
            'message': str(error),
        }, status=400)
    except RuntimeError as error:
        return JsonResponse({
            'status': 'error',
            'message': str(error),
        }, status=503)

    response = StreamingHttpResponse(
        iter_audio_chunks(audio_response),
        content_type='audio/mpeg',
    )
    response['Cache-Control'] = 'no-store'
    return response


def archive(request):
    """금기 자료실 화면을 렌더링한다."""
    return render(request, 'archive/archive.html')


def taboo_list_api(request):
    """금기 전체 목록을 API 응답 형식으로 반환한다."""
    try:
        taboos = [serialize_taboo(taboo) for taboo in list_taboos()]
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
    """검색어에 맞는 금기 목록을 API 응답 형식으로 반환한다."""
    query = request.GET.get('q', '').strip()
    try:
        taboos = [serialize_taboo(taboo) for taboo in search_taboos(query)]
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
    """오늘 날짜에 대응하는 금기 하나를 반환한다."""
    try:
        taboo = get_today_taboo()
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
        'taboo': serialize_taboo(taboo),
    })


def taboo_detail_api(request, taboo_id):
    """선택한 금기 ID의 상세 정보를 반환한다."""
    try:
        taboo = get_taboo(taboo_id)
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
        'taboo': serialize_taboo(taboo),
    })


def search_archive_records(query):
    """키워드로 괴담, 존재, 금기 모델을 검색하는 기존 검색 함수다."""
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
    """기존 검색 함수용 결과 안내 문구를 만든다."""
    if result_count:
        return (
            f"'{query}' search returned {result_count} record(s). "
            "Select a number to open a record."
        )
    return f"No archive records found for '{query}'."


def make_preview(*parts):
    """여러 본문 조각을 합쳐 화면 표시용 미리보기 길이로 줄인다."""
    body = "\n".join(str(part).strip() for part in parts if part)
    if len(body) <= BODY_PREVIEW_LIMIT:
        return body
    return f"{body[:BODY_PREVIEW_LIMIT].rstrip()}..."


def clean_regions(*values):
    """빈 지역값을 제외하고 문자열 지역 목록을 만든다."""
    return [str(value).strip() for value in values if str(value).strip()]
