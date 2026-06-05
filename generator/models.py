from django.conf import settings
from django.db import models


class GeneratedStory(models.Model):
    """신규 기록실에서 사용자가 만든 AI 괴담 결과를 저장한다."""

    # draft는 생성만 된 상태, saved는 사용자가 보관/저장한 상태를 뜻한다.
    STATUS_DRAFT = "draft"
    STATUS_SAVED = "saved"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SAVED, "Saved"),
    ]

    # private은 본인만 보는 기록, public은 공개 가능한 기록이다.
    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_stories",
    )
    # region은 Neo4j FK가 아니라 사용자가 입력한 화면 표시용 문자열이다.
    region = models.CharField(max_length=100, blank=True)
    place = models.TextField(blank=True)
    entity_type = models.CharField(max_length=100, blank=True)
    # 별도 taboos 테이블을 참조하지 않고 사용자가 입력한 금기 문장을 그대로 저장한다.
    taboo_text = models.TextField(blank=True)
    event_time = models.CharField(max_length=100, blank=True)
    condition = models.TextField(blank=True)
    ending = models.TextField(blank=True)
    title = models.TextField(blank=True)
    content = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    visibility = models.CharField(
        max_length=30,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PRIVATE,
    )
    # AI 호출에 사용한 입력 조건 원본을 저장해 재현/디버깅에 활용한다.
    prompt_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "generated_stories"

    def __str__(self):
        return self.title or f"Generated story #{self.pk}"
