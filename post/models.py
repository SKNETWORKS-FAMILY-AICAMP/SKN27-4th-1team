from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class Post(models.Model):
    CATEGORY_CHOICES = [
        ('WITNESS', '목격담'),
        ('CREATION', '창작담'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='WITNESS')
    title = models.CharField(max_length=200)
    region = models.CharField(max_length=100, default='지역 미상')
    body = models.TextField()
    views = models.IntegerField(default=0)  # For witness posts
    likes = models.IntegerField(default=0)  # For creation posts
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} -> {self.post.title}"


<<<<<<< HEAD

class Post(models.Model):
    """열린 게시판의 목격담/창작담 게시글을 저장한다."""

    # witness는 목격담, creation은 창작담 탭을 의미한다.
    BOARD_WITNESS = "witness"
    BOARD_CREATION = "creation"
    BOARD_TYPE_CHOICES = [
        (BOARD_WITNESS, "Witness"),
        (BOARD_CREATION, "Creation"),
    ]
    # 팀 내 다른 코드에서 category라는 이름을 쓰는 경우를 위한 별칭이다.
    CATEGORY_CHOICES = BOARD_TYPE_CHOICES

    # 게시글 공개 범위를 구분한다.
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
    )
    board_type = models.CharField(max_length=30, choices=BOARD_TYPE_CHOICES)
    title = models.TextField()
    # 지역 관계는 Neo4j가 담당하므로 게시글에는 문자열 지역명만 둔다.
    region = models.CharField(max_length=100, blank=True)
    content = models.TextField()
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
        """다른 코드에서 author라는 이름을 쓰더라도 user와 같은 의미로 읽게 한다."""
        return self.user

    @author.setter
    def author(self, value):
        self.user = value

    @property
    def category(self):
        """다른 코드의 category는 현재 모델의 board_type과 같은 의미다."""
        return self.board_type

    @category.setter
    def category(self, value):
        self.board_type = value

    @property
    def body(self):
        """다른 코드의 body는 현재 모델의 content와 같은 의미다."""
        return self.content

    @body.setter
    def body(self, value):
        self.content = value

    @property
    def views(self):
        """다른 코드의 views는 현재 모델의 view_count와 같은 의미다."""
        return self.view_count

    @views.setter
    def views(self, value):
        self.view_count = value
=======
>>>>>>> a541dd6bb95b49aff9424be19c2b83c51d1b1aba
