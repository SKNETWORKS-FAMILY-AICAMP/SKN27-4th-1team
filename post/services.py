"""Business logic for the post app."""
from django.db import models as db_models
from .models import Post


def list_posts(category=None):
    qs = Post.objects.select_related('author').all()
    if category:
        qs = qs.filter(category=category)
    return qs


def search_posts(category, keyword, limit=100):
    keyword = str(keyword or '').strip()
    qs = list_posts(category=category)
    if not keyword:
        return qs[:limit]

    filters = (
        db_models.Q(title__icontains=keyword)
        | db_models.Q(region__icontains=keyword)
        | db_models.Q(body__icontains=keyword)
    )
    if keyword.isdecimal():
        filters |= db_models.Q(id=int(keyword))

    return qs.filter(filters).distinct()[:limit]


def create_post(author, category, title, region, body):
    return Post.objects.create(
        author=author,
        category=category,
        title=title.strip() or '제목 없는 기록',
        region=region.strip() or '지역 미상',
        body=body.strip(),
    )


def get_post(post_id):
    return Post.objects.select_related('author').get(id=post_id)


def increment_views(post_id):
    Post.objects.filter(id=post_id).update(views=db_models.F('views') + 1)


def increment_likes(post_id):
    Post.objects.filter(id=post_id).update(likes=db_models.F('likes') + 1)


def update_post(post, title, region, body):
    post.title = title.strip() or post.title
    post.region = region.strip() or '지역 미상'
    post.body = body.strip() or post.body
    post.save(update_fields=['title', 'region', 'body'])
    return post


def delete_post(post):
    post.delete()


def list_user_posts(user):
    return Post.objects.filter(author=user).select_related('author').order_by('-created_at')
