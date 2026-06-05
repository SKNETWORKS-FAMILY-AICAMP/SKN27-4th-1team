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

