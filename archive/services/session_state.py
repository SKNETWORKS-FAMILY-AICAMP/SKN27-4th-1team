import hashlib
from typing import Any


CONVERSATION_HISTORY_PREFIX = "archive_conversation_history"
ARCHIVE_CONTEXT_PREFIX = "archive_context"
LAST_TTS_TEXT_PREFIX = "archive_last_tts_text"
LAST_TTS_ERROR_PREFIX = "archive_last_tts_error"
LAST_TTS_NARRATION_PREFIX = "archive_last_tts_narration"
ANONYMOUS_SESSION_SUFFIX = "anonymous"


def get_archive_session_keys(user: Any) -> dict[str, str]:
    """archive 챗봇 대화 기록과 검색 결과용 세션 키를 반환한다."""
    suffix = ANONYMOUS_SESSION_SUFFIX
    if getattr(user, "is_authenticated", False):
        suffix = f"user_{user.id}"

    return {
        "conversation_history": f"{CONVERSATION_HISTORY_PREFIX}_{suffix}",
        "archive_context": f"{ARCHIVE_CONTEXT_PREFIX}_{suffix}",
        "last_tts_text": f"{LAST_TTS_TEXT_PREFIX}_{suffix}",
        "last_tts_error": f"{LAST_TTS_ERROR_PREFIX}_{suffix}",
        "last_tts_narration": f"{LAST_TTS_NARRATION_PREFIX}_{suffix}",
    }


def get_conversation_history(request: Any) -> list[dict[str, str]]:
    """현재 요청 사용자에 해당하는 archive 챗봇 대화 기록을 읽는다."""
    keys = get_archive_session_keys(request.user)
    return request.session.get(keys["conversation_history"], [])


def save_conversation_history(
    request: Any,
    conversation_history: list[dict[str, str]],
    limit: int = 16,
) -> None:
    """현재 요청 사용자에 해당하는 archive 챗봇 대화 기록을 제한 개수만큼 저장한다."""
    keys = get_archive_session_keys(request.user)
    request.session[keys["conversation_history"]] = conversation_history[-limit:]
    request.session.modified = True


def get_archive_context(request: Any) -> dict[str, Any]:
    """최근 검색/선택 맥락을 읽는다."""
    keys = get_archive_session_keys(request.user)
    context = request.session.get(keys["archive_context"], {})
    if isinstance(context, dict):
        return context

    return {}


def save_archive_context(request: Any, archive_context: dict[str, Any]) -> None:
    """최근 검색/선택 맥락을 저장한다."""
    keys = get_archive_session_keys(request.user)
    request.session[keys["archive_context"]] = archive_context
    request.session.modified = True


def get_last_tts_text(request: Any) -> str:
    """현재 요청 사용자에게 마지막으로 생성된 괴담 낭독 본문을 읽는다."""
    keys = get_archive_session_keys(request.user)
    return str(request.session.get(keys["last_tts_text"], ""))


def save_last_tts_text(request: Any, text: str, limit: int = 6000) -> None:
    """현재 요청 사용자에게 마지막으로 생성된 괴담 낭독 본문을 저장한다."""
    keys = get_archive_session_keys(request.user)
    request.session[keys["last_tts_text"]] = text.strip()[:limit]
    request.session.modified = True


def hash_tts_source(text: str) -> str:
    """낭독 대본 캐시 무효화에 쓸 원문 해시를 만든다."""
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()


def get_last_tts_narration(request: Any, source_text: str) -> str:
    """저장된 낭독 대본이 같은 원문에서 만든 것이면 반환하고, 아니면 빈 문자열을 반환한다."""
    keys = get_archive_session_keys(request.user)
    cached = request.session.get(keys["last_tts_narration"], {})
    if not isinstance(cached, dict):
        return ""

    if cached.get("source_hash") != hash_tts_source(source_text):
        return ""

    return str(cached.get("script", ""))


def save_last_tts_narration(
    request: Any,
    source_text: str,
    script: str,
    limit: int = 8000,
) -> None:
    """원문 해시와 함께 낭독 대본을 저장해 같은 본문 재낭독 시 변환을 생략한다."""
    keys = get_archive_session_keys(request.user)
    request.session[keys["last_tts_narration"]] = {
        "source_hash": hash_tts_source(source_text),
        "script": script.strip()[:limit],
    }
    request.session.modified = True


def get_last_tts_error(request: Any) -> str:
    """현재 요청 사용자에게 마지막으로 발생한 TTS 오류 메시지를 읽는다."""
    keys = get_archive_session_keys(request.user)
    return str(request.session.get(keys["last_tts_error"], ""))


def save_last_tts_error(request: Any, message: str, limit: int = 300) -> None:
    """현재 요청 사용자에게 마지막으로 발생한 TTS 오류 메시지를 저장한다."""
    keys = get_archive_session_keys(request.user)
    request.session[keys["last_tts_error"]] = message.strip()[:limit]
    request.session.modified = True


def clear_last_tts_error(request: Any) -> None:
    """현재 요청 사용자에게 저장된 마지막 TTS 오류 메시지를 제거한다."""
    keys = get_archive_session_keys(request.user)
    request.session.pop(keys["last_tts_error"], None)
    request.session.modified = True


def clear_user_archive_session(request: Any, user: Any) -> None:
    """로그아웃한 사용자에게 연결된 archive 세션 기록만 제거한다."""
    keys = get_archive_session_keys(user)
    request.session.pop(keys["conversation_history"], None)
    request.session.pop(keys["archive_context"], None)
    request.session.pop(keys["last_tts_text"], None)
    request.session.pop(keys["last_tts_error"], None)
    request.session.pop(keys["last_tts_narration"], None)
    request.session.modified = True
