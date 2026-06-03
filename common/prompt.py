STORY_SYSTEM_PROMPT = """
너는 괴담 아카이브 서비스의 이야기 생성기다.
사용자의 입력과 검색된 맥락을 바탕으로 짧고 몰입감 있는 괴담 초안을 작성한다.
"""

STORY_GENERATION_PROMPT = """
아래 조건을 바탕으로 괴담을 작성하라.

지역: {region}
장소: {place}
괴이 유형: {entity_type}
금기: {taboo}
시간: {time}
발생 조건: {condition}
결말: {ending}

참고 맥락:
{context}
"""

RAG_QUERY_PROMPT = """
사용자 입력에서 검색에 사용할 핵심 키워드를 추출하라.
"""

EVALUATION_PROMPT = """
생성된 괴담이 검색 맥락과 사용자 조건을 얼마나 잘 반영했는지 평가하라.
"""


def build_story_generation_prompt(data: dict, context: str = '') -> str:
    return STORY_GENERATION_PROMPT.format(
        region=data.get('region', ''),
        place=data.get('place', ''),
        entity_type=data.get('entity_type', ''),
        taboo=data.get('taboo', ''),
        time=data.get('time', ''),
        condition=data.get('condition', ''),
        ending=data.get('ending', ''),
        context=context,
    )
