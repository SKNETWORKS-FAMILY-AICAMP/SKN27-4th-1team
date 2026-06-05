from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} -> {self.post.title}"




class Post(models.Model):
    """열린 게시판의 목격담/창작담 게시글을 저장한다."""

    BOARD_WITNESS = "witness"
    BOARD_CREATION = "creation"
    BOARD_TYPE_CHOICES = [
        (BOARD_WITNESS, "Witness"),
        (BOARD_CREATION, "Creation"),
    ]
    CATEGORY_CHOICES = BOARD_TYPE_CHOICES

    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        null=True,
        blank=True,
    )
    board_type = models.CharField(max_length=30, choices=BOARD_TYPE_CHOICES, default=BOARD_WITNESS)
    title = models.TextField(default='')
    region = models.CharField(max_length=100, blank=True)
    content = models.TextField(default='')
    view_count = models.PositiveIntegerField(default=0)
    visibility = models.CharField(
        max_length=30,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "posts"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"[{self.get_board_type_display()}] {self.title}"

    @property
    def author(self):
        return self.user

    @author.setter
    def author(self, value):
        self.user = value

    @property
    def category(self):
        return self.board_type

    @category.setter
    def category(self, value):
        self.board_type = value

    @property
    def body(self):
        return self.content

    @body.setter
    def body(self, value):
        self.content = value

    @property
    def views(self):
        return self.view_count

    @views.setter
    def views(self, value):
        self.view_count = value
