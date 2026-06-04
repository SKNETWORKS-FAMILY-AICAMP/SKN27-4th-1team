import logging
import os


def set_logging() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)

    #로그 생성
    logger = logging.getLogger("post_mk_pipe_logger") #로그 이름 설정
    logger.setLevel(logging.INFO) #로그 레벨 설정
    logger.propagate = False #로그 전파 방지

    if logger.handlers: #이미 핸들러가 있으면 기존 핸들러 반환
        return logger

    # 콘솔 핸들러를 추가해 실행 상태를 터미널에서도 확인 가능하게 함
    console_handler = logging.StreamHandler()
    # 터미널에는 단계/성공 로그 포함 전체 진행 상황 출력
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)
    return logger