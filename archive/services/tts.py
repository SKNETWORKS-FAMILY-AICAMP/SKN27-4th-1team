import json
import os
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv()

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
ELEVENLABS_TIMEOUT_SECONDS = 60
CHATBOT_BGM_VOLUME = 35
CHATBOT_TTS_VOLUME = 90
CHATBOT_MAX_VOLUME = 100


def get_chatbot_audio_volume_settings() -> dict[str, int]:
    """챗봇 낭독에 사용할 고정 음량 비율을 반환한다."""
    return {
        "bgm": CHATBOT_BGM_VOLUME,
        "tts": CHATBOT_TTS_VOLUME,
        "max": CHATBOT_MAX_VOLUME,
    }


def open_story_audio_stream(text: str) -> Any:
    """ElevenLabs 음성 스트림 응답을 연다."""
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("낭독할 괴담 본문이 없습니다.")

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if not api_key or not voice_id:
        raise ValueError("ElevenLabs API 설정이 없습니다.")

    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()
    payload = build_tts_payload(cleaned_text, model_id)
    request = Request(
        url=build_tts_url(voice_id, model_id),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )

    try:
        return urlopen(request, timeout=ELEVENLABS_TIMEOUT_SECONDS)
    except HTTPError as error:
        raise RuntimeError(read_elevenlabs_error(error)) from error
    except URLError as error:
        raise RuntimeError("ElevenLabs 음성 생성 서버에 연결할 수 없습니다.") from error


def iter_audio_chunks(response: Any, chunk_size: int = 8192) -> Iterator[bytes]:
    """열린 ElevenLabs 응답을 작은 오디오 조각으로 순차 반환한다."""
    try:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break

            yield chunk
    finally:
        response.close()


def build_tts_url(voice_id: str, model_id: str) -> str:
    """선택한 목소리와 기본 출력 설정을 포함한 ElevenLabs 스트리밍 TTS URL을 만든다."""
    url = ELEVENLABS_API_URL.format(voice_id=voice_id) + "?output_format=mp3_44100_128"
    if model_id != "eleven_v3":
        url += "&optimize_streaming_latency=1"

    return url


def build_tts_payload(text: str, model_id: str) -> dict[str, Any]:
    """괴담 낭독용 ElevenLabs 요청 본문을 만든다."""
    return {
        "text": text,
        "model_id": model_id,
        "language_code": "ko",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.8,
            "style": 0.35,
            "speed": 0.82,
            "use_speaker_boost": True,
        },
        "apply_text_normalization": "auto",
    }


def read_elevenlabs_error(error: HTTPError) -> str:
    """ElevenLabs 오류 응답에서 화면에 보여줄 메시지를 추출한다."""
    raw_body = error.read().decode("utf-8", errors="ignore")
    if not raw_body:
        return f"ElevenLabs 음성 생성 실패: HTTP {error.code}"

    try:
        parsed_body = json.loads(raw_body)
    except json.JSONDecodeError:
        return f"ElevenLabs 음성 생성 실패: {raw_body[:200]}"

    detail = parsed_body.get("detail")
    if isinstance(detail, dict):
        message = detail.get("message")
        if message:
            return str(message)

    if detail:
        return str(detail)

    return f"ElevenLabs 음성 생성 실패: HTTP {error.code}"
