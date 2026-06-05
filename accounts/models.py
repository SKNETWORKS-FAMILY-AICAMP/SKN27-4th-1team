from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class Bookmark(models.Model):
    """외부 괴담 자료를 사용자의 보관함에 저장한 기록이다.

    이 모델은 Django 내부 테이블을 FK로 참조하지 않는다.
    Neo4j 데이터, 원천 JSON 데이터, 외부 자료처럼 PostgreSQL 모델로 직접 관리하지 않는
    콘텐츠를 보관함에 담기 위해 필요한 최소 정보를 복사해서 저장한다.
    """

    # 보관함을 소유한 사용자다.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")

    # 외부 콘텐츠의 식별자다.
    # 예: Neo4j 노드 ID, 원천 데이터 ID, SCP 코드처럼 외부 시스템에서 쓰는 값.
    horror_id = models.CharField(max_length=100)

    # 보관함 목록에서 바로 보여줄 수 있도록 외부 콘텐츠 제목을 복사 저장한다.
    horror_title = models.CharField(max_length=255)

    # 외부 콘텐츠의 종류다.
    # 예: Story, Myth, Superstition, Neo4jNode 등 화면 분류에 사용할 수 있다.
    horror_type = models.CharField(max_length=50, default="Story")

    # 사용자가 보관함에 추가한 시각이다.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 보관함 화면에서 최신 저장 항목이 먼저 보이도록 정렬한다.
        ordering = ["-created_at"]

        # 같은 사용자가 같은 외부 콘텐츠를 중복 저장하지 못하게 한다.
        unique_together = ("user", "horror_id")

    def __str__(self):
        # Django admin이나 shell에서 객체를 읽기 쉽게 표시한다.
        return f"{self.user.username} -> {self.horror_title}"


class GeneratedStoryBookmark(models.Model):
    """사용자가 AI 생성 괴담을 나의 보관함에 저장한 기록이다.

    GeneratedStory 본문을 복사하지 않고 FK로 참조한다.
    그래서 생성 괴담 내용이 수정되면 보관함에서도 같은 원본을 바라보게 된다.
    """

    # 보관함을 소유한 사용자다.
    # settings.AUTH_USER_MODEL을 사용해서 커스텀 유저 모델에도 대응할 수 있게 한다.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_story_bookmarks",
    )

    # 사용자가 저장한 AI 생성 괴담 원본이다.
    # 생성 괴담이 삭제되면 해당 보관 기록도 함께 삭제된다.
    generated_story = models.ForeignKey(
        "generator.GeneratedStory",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    # 사용자가 보관 항목에 남기는 개인 메모다.
    # 필수 입력이 아니므로 빈 문자열을 허용한다.
    memo = models.TextField(blank=True)

    # 보관함에 저장한 시각이다.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ERD와 실제 PostgreSQL 테이블명을 맞춘다.
        db_table = "generated_story_bookmarks"

        constraints = [
            # 같은 사용자가 같은 AI 생성 괴담을 중복 저장하지 못하게 한다.
            models.UniqueConstraint(
                fields=["user", "generated_story"],
                name="uq_generated_story_bookmarks_user_story",
            )
        ]

    def __str__(self):
        # user_id:generated_story_id 형식으로 관계를 간단히 표시한다.
        return f"{self.user_id}:{self.generated_story_id}"


class PostBookmark(models.Model):
    """사용자가 열린 게시판 글을 나의 보관함에 저장한 기록이다.

    게시글 제목이나 본문을 복사하지 않고 Post를 FK로 참조한다.
    그래서 게시글이 수정되면 보관함에서도 수정된 게시글을 그대로 확인하게 된다.
    """

    # 보관함을 소유한 사용자다.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_bookmarks",
    )

    # 사용자가 저장한 게시글 원본이다.
    # 게시글이 삭제되면 해당 보관 기록도 함께 삭제된다.
    post = models.ForeignKey(
        "post.Post",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    # 사용자가 보관 항목에 남기는 개인 메모다.
    memo = models.TextField(blank=True)

    # 보관함에 저장한 시각이다.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ERD와 실제 PostgreSQL 테이블명을 맞춘다.
        db_table = "post_bookmarks"

        constraints = [
            # 같은 사용자가 같은 게시글을 중복 저장하지 못하게 한다.
            models.UniqueConstraint(
                fields=["user", "post"],
                name="uq_post_bookmarks_user_post",
            )
        ]

    def __str__(self):
        # user_id:post_id 형식으로 관계를 간단히 표시한다.
        return f"{self.user_id}:{self.post_id}"
