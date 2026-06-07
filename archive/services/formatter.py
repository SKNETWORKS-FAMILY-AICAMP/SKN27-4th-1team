from typing import Any


def format_conversation_history(history: list[dict[str, str]], limit: int = 8) -> str:
    """최근 대화 기록을 프롬프트에 넣기 쉬운 짧은 문자열로 바꾼다."""
    if not history:
        return "이전 대화 없음"

    lines = []
    for item in history[-limit:]:
        role = item.get("role", "unknown")
        role_label = role
        if role == "user":
            role_label = "사용자"
        elif role == "assistant":
            role_label = "기록 열람실"
        elif role == "system":
            role_label = "시스템"

        content = item.get("content", "").strip()
        if content:
            lines.append(f"{role_label}: {content}")

    if lines:
        return "\n".join(lines)

    return "이전 대화 없음"


def format_source_story(source_story: dict[str, Any]) -> str:
    """검색된 원본 기록을 제목, 유형, 지역, 본문 형식으로 정리한다."""
    regions = ", ".join(source_story.get("regions", []))
    if not regions:
        regions = "지역 미상"

    return "\n".join([
        f"제목: {source_story.get('name', '제목 없음')}",
        f"유형: {source_story.get('type', 'unknown')}",
        f"지역: {regions}",
        "본문:",
        source_story.get("body", ""),
    ])
