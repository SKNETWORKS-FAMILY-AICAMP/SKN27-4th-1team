import json
import logging
from http import HTTPStatus

from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError

from .models import Superstition
from .services.graph import run_archive_chatbot, run_archive_record_chatbot
from .services.graph_nodes import convert_story_to_narration
from .services.session_state import (
    clear_last_tts_error,
    clear_user_archive_session,
    get_archive_context,
    get_conversation_history,
    get_last_tts_error,
    get_last_tts_narration,
    get_last_tts_text,
    save_archive_context,
    save_conversation_history,
    save_last_tts_error,
    save_last_tts_narration,
    save_last_tts_text,
)
from .services.taboo import (
    get_taboo,
    get_today_taboo,
    list_taboos,
    search_taboos,
    serialize_taboo,
)
from .services.tts import (
    get_chatbot_audio_volume_settings,
    iter_audio_chunks,
    open_story_audio_stream,
)


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


def summarize_archive_record(record: dict) -> dict:
    """세션에 보관할 archive 기록 요약을 만든다."""
    regions = record.get('regions', [])
    if not isinstance(regions, list):
        regions = []

    return {
        'id': record.get('id'),
        'type': record.get('type', ''),
        'name': record.get('name', ''),
        'regions': regions,
    }


def build_archive_search_context(
    previous_context: dict,
    query: str,
    chatbot_result: dict,
) -> dict:
    """최근 검색 결과를 추천 참조용 context로 만든다."""
    results = [
        summarize_archive_record(record)
        for record in chatbot_result.get('results', [])[:10]
    ]
    result_types = []
    for record in results:
        record_type = record.get('type', '')
        if record_type and record_type not in result_types:
            result_types.append(record_type)

    context = dict(previous_context)
    context.update({
        'last_query': query,
        'last_keywords': chatbot_result.get('keywords', []),
        'last_query_analysis': chatbot_result.get('query_analysis', {}),
        'last_results': results,
        'last_result_types': result_types,
    })
    return context


def build_archive_selected_context(
    previous_context: dict,
    query: str,
    chatbot_result: dict,
) -> dict:
    """최근 선택 기록을 추천 참조용 context로 만든다."""
    context = dict(previous_context)
    source_story = chatbot_result.get('source_story', {})
    if source_story:
        context['last_selected_record'] = summarize_archive_record(source_story)

    context['last_selected_query'] = query
    context['last_keywords'] = chatbot_result.get(
        'keywords',
        context.get('last_keywords', []),
    )
    context['last_query_analysis'] = chatbot_result.get(
        'query_analysis',
        context.get('last_query_analysis', {}),
    )
    return context


def index(request):
    """archive 앱의 첫 진입 화면을 렌더링한다."""
    return render(request, 'archive/index.html')


def chatbot(request):
    """괴담 조회 챗봇 화면을 렌더링한다."""
    clear_user_archive_session(request, request.user)
    return render(
        request,
        'archive/chatbot.html',
        {'audio_volume_settings': get_chatbot_audio_volume_settings()},
    )


def sillok_search_api(request):
    """사용자 질문을 받아 괴담 검색 목록 또는 일반 대화 응답을 JSON으로 반환한다."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'status': 'empty', 'results': []})

    conversation_history = get_conversation_history(request)
    archive_context = get_archive_context(request)
    try:
        chatbot_result = run_archive_chatbot(
            query,
            conversation_history,
            archive_context,
        )
    except DatabaseError:
        return JsonResponse({
            'status': 'error',
            'query': query,
            'results': [],
            'llm_response': '괴담 데이터베이스를 사용할 수 없습니다. DB 상태를 확인해 주세요.',
        }, status=503)
    except Exception as error:
        logging.getLogger(__name__).exception("Archive search API failed")
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
    if chatbot_result.get('intent') == 'tts_request':
        has_tts_text = bool(get_last_tts_text(request).strip())
        response_status = chatbot_result.get('status', 'tts_ready')
        if not has_tts_text:
            response_status = 'tts_empty'
            llm_response = '아직 낭독할 괴담 본문이 없습니다. 먼저 기록 하나를 열어 주십시오.'

        conversation_history.append({"role": "user", "content": query})
        conversation_history.append({"role": "assistant", "content": llm_response})
        save_conversation_history(request, conversation_history)
        return JsonResponse({
            'status': response_status,
            'query': query,
            'intent': 'tts_request',
            'keywords': [],
            'results': [],
            'source_story': {},
            'llm_response': llm_response,
            'evaluation': {},
            'is_passed': has_tts_text,
            'revised': False,
            'has_tts_text': has_tts_text,
        })

    conversation_history.append({"role": "user", "content": query})
    conversation_history.append({"role": "assistant", "content": llm_response})
    save_conversation_history(request, conversation_history)
    if results:
        save_archive_context(
            request,
            build_archive_search_context(archive_context, query, chatbot_result),
        )

    return JsonResponse({
        'status': chatbot_result.get('status', 'success'),
        'query': query,
        'intent': chatbot_result.get('intent', ''),
        'keywords': chatbot_result.get('keywords', []),
        'query_analysis': chatbot_result.get('query_analysis', {}),
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
    archive_context = get_archive_context(request)
    try:
        chatbot_result = run_archive_record_chatbot(
            query,
            record_type,
            int(record_id),
            conversation_history,
            archive_context,
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
        logging.getLogger(__name__).exception("Archive rewrite API failed")
        if is_rate_limit_error(error):
            return make_rate_limit_response(query)

        return JsonResponse({
            'status': 'error',
            'query': query,
            'results': [],
            'llm_response': 'LLM 생성 중 오류가 발생했습니다. Groq API와 모델 상태를 확인해 주세요.',
        }, status=503)

    results = chatbot_result.get('results', [])
    response_status = chatbot_result.get('status', 'success')
    llm_response = chatbot_result.get('llm_response', '').strip()
    if not llm_response:
        logging.getLogger(__name__).warning(
            "Archive rewrite returned empty llm_response",
            extra={
                "record_type": record_type,
                "record_id": record_id,
                "query": query,
            },
        )
        response_status = 'error'
        llm_response = '선택한 기록을 다시 엮지 못했습니다. 잠시 후 다시 시도해 주세요.'

    conversation_history.append({"role": "user", "content": query or record_type})
    conversation_history.append({"role": "assistant", "content": llm_response})
    save_conversation_history(request, conversation_history)
    if response_status == 'success':
        save_last_tts_text(request, llm_response)
    elif response_status == 'error':
        save_last_tts_text(request, "")

    save_archive_context(
        request,
        build_archive_selected_context(archive_context, query, chatbot_result),
    )

    return JsonResponse({
        'status': response_status,
        'query': query,
        'intent': chatbot_result.get('intent', ''),
        'keywords': chatbot_result.get('keywords', []),
        'query_analysis': chatbot_result.get('query_analysis', {}),
        'results': results,
        'source_story': chatbot_result.get('source_story', {}),
        'llm_response': llm_response,
        'evaluation': chatbot_result.get('evaluation', {}),
        'is_passed': chatbot_result.get('is_passed', False),
        'revised': chatbot_result.get('revised', False),
    })


def prepare_tts_narration(request, text: str) -> str:
    """낭독 직전에 괴담 본문을 감정 낭독 대본으로 바꾸고 같은 본문은 세션에 캐시한다."""
    cached_narration = get_last_tts_narration(request, text)
    if cached_narration:
        return cached_narration

    narration = convert_story_to_narration(text)
    if narration.strip() and narration != text:
        save_last_tts_narration(request, text, narration)
        return narration

    return text


def sillok_tts_api(request):
    """생성된 괴담 본문을 ElevenLabs 음성 MP3 스트림으로 반환한다."""
    if request.method == 'GET' and request.GET.get('error') == '1':
        return JsonResponse({
            'status': 'success',
            'message': get_last_tts_error(request),
        })

    if request.method == 'GET' and request.GET.get('diagnose') == '1':
        text = get_last_tts_text(request).strip()
        if not text:
            error_message = '낭독할 괴담 본문이 없습니다.'
            save_last_tts_error(request, error_message)
            return JsonResponse({
                'status': 'empty',
                'message': error_message,
            }, status=400)

        try:
            clear_last_tts_error(request)
            audio_response = open_story_audio_stream(text)
            audio_response.close()
        except ValueError as error:
            error_message = str(error)
            save_last_tts_error(request, error_message)
            logging.getLogger(__name__).warning("ElevenLabs TTS 설정 오류: %s", error_message)
            return JsonResponse({
                'status': 'error',
                'message': error_message,
            }, status=400)
        except RuntimeError as error:
            error_message = str(error)
            save_last_tts_error(request, error_message)
            logging.getLogger(__name__).warning("ElevenLabs TTS 생성 실패: %s", error_message)
            return JsonResponse({
                'status': 'error',
                'message': error_message,
            }, status=503)

        return JsonResponse({
            'status': 'ready',
            'message': 'TTS 스트림을 열 수 있습니다.',
        })

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
        if request_data.get('prepare_only'):
            if not text:
                return JsonResponse({
                    'status': 'empty',
                    'message': '낭독할 괴담 본문이 없습니다.',
                }, status=400)

            save_last_tts_text(request, text)
            return JsonResponse({
                'status': 'prepared',
                'message': '낭독 본문을 준비했습니다.',
            })
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

    narration_text = prepare_tts_narration(request, text)

    try:
        clear_last_tts_error(request)
        audio_response = open_story_audio_stream(narration_text)
    except ValueError as error:
        error_message = str(error)
        save_last_tts_error(request, error_message)
        logging.getLogger(__name__).warning("ElevenLabs TTS 설정 오류: %s", error_message)
        return JsonResponse({
            'status': 'error',
            'message': error_message,
        }, status=400)
    except RuntimeError as error:
        error_message = str(error)
        save_last_tts_error(request, error_message)
        logging.getLogger(__name__).warning("ElevenLabs TTS 생성 실패: %s", error_message)
        return JsonResponse({
            'status': 'error',
            'message': error_message,
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
