from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    name = 'archive'

    def ready(self) -> None:
        """archive 앱이 로딩될 때 로그아웃 시그널을 등록한다."""
        import archive.signals
