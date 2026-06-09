from django.db import models


class HorrorStory(models.Model):
    """검증된 한국 괴담/도시전설 원천 데이터를 저장한다."""

    # source + source_ref_id 조합으로 JSON 재적재 시 중복 저장을 막는다.
    source = models.CharField(max_length=100)
    source_ref_id = models.CharField(max_length=100)
    title = models.TextField()
    language = models.CharField(max_length=20, default="ko")
    # 지역 관계는 Neo4j가 담당하므로 PostgreSQL에는 화면 표시용 문자열만 둔다.
    region = models.CharField(max_length=100, blank=True)
    url = models.TextField(blank=True)
    # 원본 JSON에는 없으며 import 단계에서 content 앞부분으로 생성한다.
    preview = models.TextField(blank=True)
    content = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    # 원본 보존이나 추후 확장 필드를 담기 위한 JSON 영역이다.
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "horror_stories"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_horror_stories_source_ref",
            )
        ]

    def __str__(self):
        return self.title


class MythEntity(models.Model):
    """신화/전설/괴이 존재 데이터를 저장한다."""

    # 같은 원본 id라도 데이터셋이 달라질 수 있어 source를 함께 저장한다.
    source = models.CharField(
        max_length=100,
        default="ultimate_global_mythology_1000",
    )
    source_ref_id = models.CharField(max_length=100)
    name = models.TextField()
    origin = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    behavior = models.TextField(blank=True)
    weakness = models.TextField(blank=True)
    history = models.TextField(blank=True)
    signs = models.TextField(blank=True)
    # survival_rules는 원본에서 리스트 형태이므로 JSONField로 보존한다.
    survival_rules = models.JSONField(default=list, blank=True)
    source_site = models.CharField(max_length=100, blank=True)
    source_url = models.TextField(blank=True)
    # habitats처럼 컬럼으로 고정하지 않은 가변 데이터를 저장한다.
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "myth_entities"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_myth_entities_source_ref",
            )
        ]

    def __str__(self):
        return self.name


class Superstition(models.Model):
    """misin.json의 미신/금기 문장을 원문 그대로 저장한다."""

    # taboos로 구조화하지 않고 superstitions에 단순 문장으로 저장한다.
    source = models.CharField(max_length=100, default="misin")
    source_ref_id = models.CharField(max_length=100)
    content = models.TextField()
    # 현재는 비워두지만, 추후 분류/지역 필터가 필요하면 사용할 수 있다.
    category = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "superstitions"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_superstitions_source_ref",
            )
        ]

    def __str__(self):
        return self.content[:50]


class DcinsidePost(models.Model):
    """DCInside 공포 게시판에서 수집한 외부 게시글을 저장한다.

    사용자가 직접 작성하는 열린 게시판 글은 post.Post가 담당한다.
    이 모델은 외부 수집 데이터를 분리해서 보관하고, 필요하면 pgvector 검색 대상으로도 사용한다.
    """

    CATEGORY_CHOICES = [
        ("WITNESS", "목격담"),
        ("CREATION", "창작담"),
    ]

    # 수집 출처와 원본 식별값이다.
    # 두 값을 unique로 묶어 import 스크립트를 반복 실행해도 중복 저장되지 않게 한다.
    source = models.CharField(max_length=100, default="dcinside_gongpow")
    source_ref_id = models.CharField(max_length=100)

    # DCInside 원본 title은 [경험], [창작] 같은 태그인 경우가 많다.
    # import 단계에서 태그를 category로 변환하고, 화면용 title은 본문 앞부분으로 만든다.
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    region = models.CharField(max_length=100, default="한국")
    content = models.TextField()

    # 원본 title 태그처럼 컬럼으로 고정하지 않을 보조 정보를 보관한다.
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dcinside_posts"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_dcinside_posts_source_ref",
            )
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
