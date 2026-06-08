from generator.services.prompts import USER_PROMPT_TEMPLATE, SYSTEM_PROMPT
from common.llm_factory import get_post_generation_llm

def request_ghost_story(data: dict) -> str:
    """유저 데이터를 받아 프롬프트를 조립하고 LLM에게 원본 텍스트(JSON 스트링)를 요청합니다."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        region=data.get('region', '미상'),
        location=data.get('location', '미상'),
        anomaly_type=data.get('anomaly_type', '미상'),
        taboo=data.get('taboo', '미상'),
        time=data.get('time', '미상'),
        condition=data.get('condition', '미상'),
        outcome=data.get('outcome', '미상')
    )
    
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
    
    # common.llm_factory를 연동하여 실제 LLM 호출
    llm = get_post_generation_llm()
    try:
        response = llm.invoke(full_prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        # LLM 호출 실패 시 에러 로깅 후 파서에서 안전하게 처리할 수 있는 기본 에러 응답 반환
        return '{"title": "기록 오염 발생", "content": "LLM 통신 중 오류가 발생했습니다."}'
