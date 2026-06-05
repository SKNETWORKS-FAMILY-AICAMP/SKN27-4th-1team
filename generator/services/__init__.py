from .llm_service import request_ghost_story
from .parser_service import parse_llm_response


def generate_ghost_story_pipeline(data: dict) -> dict:
    """LLM 요청과 파싱 레이어를 연결하는 메인 파이프라인 함수"""
    raw_response = request_ghost_story(data)
    parsed_data = parse_llm_response(raw_response)
    return parsed_data


def list_user_generated_stories(user):
    """나의 보관함에서 보여줄 사용자의 AI 생성 괴담 목록을 조회합니다."""
    from generator.models import GeneratedStory

    return GeneratedStory.objects.filter(user=user).order_by("-created_at")
