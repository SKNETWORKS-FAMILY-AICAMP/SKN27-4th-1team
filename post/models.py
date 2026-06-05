from django.db import models
from django.contrib.auth.models import User


class Post(models.Model):
    """열린 게시판에 등록되는 사용자 작성 게시글이다.

    목격담과 창작담을 하나의 테이블에서 관리한다.
    화면에서는 board/category 값에 따라 탭을 나누어 보여줄 수 있다.
    """

    # 게시글 종류를 제한한다.
    # WITNESS: 실제 목격담 게시판
    # CREATION: 창작담 게시판
    CATEGORY_CHOICES = [
        ("WITNESS", "목격담"),
        ("CREATION", "창작담"),
    ]

    # 작성자 계정이다.
    # 사용자가 탈퇴해도 게시글 자체는 남길 수 있도록 SET_NULL을 사용한다.
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )

    # 게시글이 목격담인지 창작담인지 구분한다.
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default="WITNESS")

    # 목록과 상세 화면에 노출되는 게시글 제목이다.
    title = models.CharField(max_length=200)

    # 지역 정보실/목격담 화면에서 지역 필터나 표시용으로 사용할 수 있는 문자열이다.
    # Neo4j의 지역 노드와 직접 FK로 연결하지 않고 PostgreSQL에는 텍스트만 저장한다.
    region = models.CharField(max_length=100, default="지역 미상")

    # 게시글 본문이다.
    body = models.TextField()

    # 목격담 목록에서 조회수 표시용으로 사용한다.
    views = models.IntegerField(default=0)

    # 창작담에서 좋아요 개수 표시용으로 사용한다.
    # Like 테이블이 실제 누가 눌렀는지 기록하고, 이 값은 빠른 화면 표시용 카운터로 쓸 수 있다.
    likes = models.IntegerField(default=0)

    # 게시글 최초 작성 시각이다.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 최신 글이 먼저 보이도록 기본 정렬을 지정한다.
        ordering = ["-created_at"]

    def __str__(self):
        # Django admin이나 shell에서 객체를 읽기 쉽게 표시한다.
        return f"[{self.get_category_display()}] {self.title}"


class Like(models.Model):
    """사용자가 게시글에 누른 좋아요 기록이다.

    Post.likes는 숫자 카운터이고, 이 모델은 '누가 어떤 글에 좋아요를 눌렀는지'를 저장한다.
    unique_together로 같은 사용자가 같은 글에 중복 좋아요를 누르지 못하게 한다.
    """

    # 좋아요를 누른 사용자다.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")

    # 좋아요 대상 게시글이다.
    # 게시글이 삭제되면 해당 좋아요 기록도 함께 삭제된다.
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_likes")

    # 좋아요를 누른 시각이다.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 한 사용자가 같은 게시글에 좋아요를 여러 번 누르지 못하게 한다.
        unique_together = ("user", "post")

    def __str__(self):
        # Django admin이나 shell에서 관계를 읽기 쉽게 표시한다.
        return f"{self.user.username} -> {self.post.title}"
