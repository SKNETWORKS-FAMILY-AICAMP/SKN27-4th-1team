from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from archive.services.session_state import clear_user_archive_session


@receiver(user_logged_out)
def clear_archive_session_on_logout(sender: object, request: object, user: object, **kwargs: object) -> None:
    """Django 로그아웃 시그널을 받아 해당 사용자의 archive 챗봇 기록만 지운다."""
    if request is None or user is None:
        return

    clear_user_archive_session(request, user)
