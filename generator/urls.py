from django.urls import path

from . import views

app_name = 'generator'

urlpatterns = [
    path('storymaker/', views.storymaker, name='storymaker'),
    path('generate/', views.generate_story_api, name='generate'),
]
