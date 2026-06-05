from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    horror_id = models.CharField(max_length=100) # Neo4j ID or SCP Code
    horror_title = models.CharField(max_length=255)
    horror_type = models.CharField(max_length=50, default='Story')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'horror_id')

    def __str__(self):
        return f"{self.user.username} -> {self.horror_title}"



class GeneratedStoryBookmark(models.Model):
    """사용자가 AI 생성 괴담을 나의 보관함에 저장한 기록이다."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_story_bookmarks",
    )
    generated_story = models.ForeignKey(
        "generator.GeneratedStory",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "generated_story_bookmarks"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "generated_story"],
                name="uq_generated_story_bookmarks_user_story",
            )
        ]

    def __str__(self):
        return f"{self.user_id}:{self.generated_story_id}"


class PostBookmark(models.Model):
    """사용자가 열린 게시판 글을 나의 보관함에 저장한 기록이다."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_bookmarks",
    )
    post = models.ForeignKey(
        "post.Post",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "post_bookmarks"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="uq_post_bookmarks_user_post",
            )
        ]

    def __str__(self):
        return f"{self.user_id}:{self.post_id}"
