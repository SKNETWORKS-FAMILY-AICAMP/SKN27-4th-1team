import json

def parse_llm_response(raw_text: str) -> dict:
    """LLM의 텍스트 응답을 파이썬 딕셔너리로 안전하게 변환합니다."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "title": "기록 오염 발생",
            "content": "데이터 파싱에 실패했습니다.",
            "danger_level": "등급 미상",
            "summary": "시스템 오류"
        }
