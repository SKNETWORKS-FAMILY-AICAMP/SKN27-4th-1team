"""Business logic for the accounts app."""
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User

from .models import Bookmark, GeneratedStoryBookmark, PostBookmark


def signup_user(data):
    return User.objects.create_user(
        username=data["username"],
        email=data.get("email", ""),
        password=data["password"],
    )


def login_user(request, username, password):
    user = authenticate(request, username=username, password=password)
    if user is None:
        return None

    auth_login(request, user)
    return user


def logout_user(request):
    auth_logout(request)


def get_user_profile(user):
    return {
        "username": user.username,
        "email": user.email,
        "date_joined": user.date_joined,
        "last_login": user.last_login,
        "external_bookmark_count": Bookmark.objects.filter(user=user).count(),
        "generated_bookmark_count": GeneratedStoryBookmark.objects.filter(user=user).count(),
        "post_bookmark_count": PostBookmark.objects.filter(user=user).count(),
    }


def list_external_bookmarks(user):
    return Bookmark.objects.filter(user=user)


def list_generated_story_bookmarks(user):
    return GeneratedStoryBookmark.objects.filter(user=user).select_related("generated_story")


def list_post_bookmarks(user):
    return PostBookmark.objects.filter(user=user).select_related("post")
