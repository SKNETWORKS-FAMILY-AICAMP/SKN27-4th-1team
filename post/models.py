from django.db import models

class Post(models.Model):
    CATEGORY_CHOICES = [
        ('WITNESS', '목격담'),
        ('CREATION', '창작담'),
    ]
    
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

