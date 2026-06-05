import json


def _extract_json_object(raw_text: str) -> str:
    text = str(raw_text).strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("JSON object not found", text, 0)

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    raise json.JSONDecodeError("JSON object is incomplete", text, start)


def _normalize_story_payload(data: dict) -> dict:
    return {
        "title": str(data.get("title") or "제목 없는 기록"),
        "content": str(data.get("content") or "생성된 본문이 없습니다."),
        "summary": str(data.get("summary") or ""),
    }


def parse_llm_response(raw_text: str) -> dict:
    """LLM의 텍스트 응답을 파이썬 딕셔너리로 안전하게 변환합니다."""
    try:
        parsed = json.loads(_extract_json_object(raw_text))
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("JSON root is not an object", str(raw_text), 0)
        return _normalize_story_payload(parsed)
    except (TypeError, json.JSONDecodeError):
        return {
            "title": "기록 오염 발생",
            "content": "데이터 파싱에 실패했습니다.",
            "summary": "시스템 오류"
        }
